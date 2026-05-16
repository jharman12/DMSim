"""
Persistent AoE spell zones — concentration spells that remain on the battlefield.

A PersistentSpell is created when a concentration spell with an area effect is cast.
It stores the affected hexes, remaining duration, and spell data so the engine can:
  - Apply per-turn damage/CC to actors in the zone at the start of their turn
  - Roll concentration saves when the caster takes damage
  - Auto-expire after the spell's duration runs out
  - End early when concentration is broken or caster casts another concentration spell
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from engine.utils import safe_log
from engine.dice import rollDice, rollSave

if TYPE_CHECKING:
    from model.actor import Actor


@dataclass
class PersistentSpell:
    caster: object          # Actor — kept as `object` to avoid circular import
    spell_name: str
    spell: dict             # full spell dict from spellList.json
    affected_hex_indices: list  # GUI-side hex indices (for coloring)
    affected_coords: list       # Engine-side map coords (for zone checks)
    rounds_remaining: int

    @property
    def save_type(self) -> str:
        """First word of the 'save' field, e.g. 'Strength'."""
        words = self.spell.get('save', '').split()
        return words[0] if words else ''

    @property
    def dc(self) -> int:
        return int(getattr(self.caster, 'spellDC', 10))

    @property
    def dice(self) -> list:
        return self.spell.get('dice', [''])

    @property
    def has_damage(self) -> bool:
        return bool(self.dice and self.dice[0] and 'd' in self.dice[0])

    @property
    def effect(self) -> str:
        return self.spell.get('effect', '')


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def _parse_duration_rounds(duration_str: str) -> int:
    """Convert a duration string to rounds (1 minute = 10 rounds)."""
    s = duration_str.lower()
    nums = re.findall(r'\d+', s)
    n = int(nums[0]) if nums else 1
    if 'hour' in s:
        return min(n * 600, 600)  # cap at 10 minutes for playability
    if 'minute' in s:
        return n * 10
    if 'round' in s:
        return n
    return 10


def create_persistent_spell(caster, spell_name: str, spell: dict,
                             hex_indices: list, map_coords: list) -> PersistentSpell:
    """Create a PersistentSpell for a just-cast concentration area spell."""
    rounds = _parse_duration_rounds(spell.get('duration', '1 Minute'))
    return PersistentSpell(
        caster=caster,
        spell_name=spell_name,
        spell=spell,
        affected_hex_indices=list(hex_indices),
        affected_coords=list(map_coords),
        rounds_remaining=rounds,
    )


# ---------------------------------------------------------------------------
# Per-turn zone application
# ---------------------------------------------------------------------------

def apply_zone_to_actor(ps: PersistentSpell, actor, map_obj) -> bool:
    """
    Apply *ps*'s effect to *actor* if they are standing in the zone this turn.
    Skips the caster.  Returns True if any effect was applied.
    """
    if actor is ps.caster:
        return False

    actor_coords = [c for c, v in map_obj.arrayCenters.items() if v == actor]
    if not actor_coords or actor_coords[0] not in ps.affected_coords:
        return False

    safe_log(f'\t{actor.name} starts their turn in {ps.spell_name}!', map_obj)

    if ps.has_damage:
        dmg = 0
        for di in ps.dice:
            if not di or 'd' not in di:
                continue
            parts = re.findall(r'\d+', di)
            if len(parts) >= 2:
                dmg += sum(rollDice(int(parts[0]), int(parts[1]), map_obj))

        if dmg > 0:
            from engine.combat import takeDmg  # local import to break cycle
            if ps.save_type:
                failed = rollSave(actor, ps.save_type, ps.dc, map_obj)
                takeDmg(ps.caster, actor, dmg if failed else dmg // 2, map_obj)
            else:
                takeDmg(ps.caster, actor, dmg, map_obj)

    elif ps.effect and ps.save_type:
        # CC-only spell — Restrained gets its own flag (actor can still act but can't move).
        # Other conditions fall back to generic hard CC.
        if ps.effect.lower() in ('restrained',):
            # Always re-roll — a success this turn frees the actor even if restrained before.
            actor.restrained = []
            failed = rollSave(actor, ps.save_type, ps.dc, map_obj)
            if failed:
                actor.restrained = [ps.save_type, ps.dc]
                safe_log(f'\t{actor.name} is Restrained by {ps.spell_name}!', map_obj)
        else:
            failed = rollSave(actor, ps.save_type, ps.dc, map_obj)
            if failed:
                # Mark cc as zone-applied this turn (4th element = True) so calcTurn
                # skips the redundant second save and just loses the actor's turn.
                actor.cc = [ps.spell.get('lvl', 1), [ps.save_type], ps.dc, True]
                safe_log(f'\t{actor.name} is affected by {ps.spell_name}!', map_obj)

    return True


# ---------------------------------------------------------------------------
# Concentration helpers
# ---------------------------------------------------------------------------

def concentration_save(caster, dmg: int, map_obj) -> bool:
    """
    Roll a concentration save for *caster* after taking *dmg* damage.
    DC = max(10, dmg // 2).  Returns True if concentration is held.
    Ends the concentration spell automatically on failure.
    """
    if getattr(caster, 'concentration_spell', None) is None:
        return True

    dc = max(10, dmg // 2)
    safe_log(f'\t{caster.name} must make a concentration save (DC {dc})!', map_obj)
    failed = rollSave(caster, 'Constitution', dc, map_obj)
    if failed:
        safe_log(f'\t{caster.name} FAILED concentration — spell ends!', map_obj)
        end_concentration(caster, map_obj)
        return False
    safe_log(f'\t{caster.name} held concentration.', map_obj)
    return True


def end_concentration(caster, map_obj) -> PersistentSpell | None:
    """
    Immediately end the caster's active concentration spell.
    Returns the ended PersistentSpell, or None if not concentrating.
    """
    ps = getattr(caster, 'concentration_spell', None)
    if ps is None:
        return None
    safe_log(f'\t{caster.name} loses concentration on {ps.spell_name}.', map_obj)
    caster.concentration_spell = None
    if hasattr(map_obj, 'persistent_spells') and ps in map_obj.persistent_spells:
        map_obj.persistent_spells.remove(ps)
    return ps


# ---------------------------------------------------------------------------
# Round tick
# ---------------------------------------------------------------------------

def tick_persistent_spells(map_obj) -> list:
    """
    Called at the start of each new round.
    Decrements duration; removes and returns expired spells.
    """
    expired = []
    active = []
    for ps in getattr(map_obj, 'persistent_spells', []):
        ps.rounds_remaining -= 1
        if ps.rounds_remaining <= 0:
            expired.append(ps)
            if getattr(ps.caster, 'concentration_spell', None) is ps:
                ps.caster.concentration_spell = None
            safe_log(f'\t{ps.spell_name} has expired after running its full duration.', map_obj)
        else:
            active.append(ps)
    map_obj.persistent_spells = active
    return expired
