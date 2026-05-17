"""
SimController: the single bridge between the pure engine layer and the PyQt5 GUI.

The GUI should only ever import from this module when it needs to interact with
the simulation. The engine/model layer must never import Qt.
"""
from PyQt5.QtCore import QObject, pyqtSignal
from engine.combat import doAction
from engine.targeting import calcMoveHexes
import engine.dice as _dice


class SimController(QObject):
    """
    Wraps an interactiveEncounter and translates engine events into Qt signals.

    Signals
    -------
    turn_changed : emits the current Actor at the start of each turn
    hp_changed   : emits (actor, current_hp, max_hp) when health changes
    actor_died   : emits the Actor that just died
    encounter_ended : emits 'Party' or 'Enemy' depending on who won
    log_message  : emits a plain-text log string
    action_choices_ready : emits a list of myAction objects for a player's turn
    actor_moved  : emits (actor, hex_index, remaining_speed) after a move
    """

    turn_changed = pyqtSignal(object)
    hp_changed = pyqtSignal(object, int, int)
    actor_died = pyqtSignal(object)
    encounter_ended = pyqtSignal(str)
    log_message = pyqtSignal(str)
    action_choices_ready = pyqtSignal(list)
    actor_moved = pyqtSignal(object, int, int)  # actor, hex_index, remaining_speed
    persistent_spell_created = pyqtSignal(object)  # PersistentSpell
    persistent_spell_ended = pyqtSignal(object)    # PersistentSpell

    def __init__(self, encounter, parent=None):
        """
        Parameters
        ----------
        encounter : interactiveEncounter
            A fully initialised encounter instance.
        """
        super().__init__(parent)
        self._encounter = encounter

        # --- Manual dice rolling ---
        # Names of actors whose rolls should be entered manually by the user.
        self.manual_actors: set = set()

        # --- Interactive action selection ---
        # Names of actors whose action choices are made by the user via the GUI
        # (rather than decided by the AI engine).  Players are interactive by default;
        # monsters are automated by default but can be added here.
        self.interactive_actors: set = set()

        # Factory called with (actor_name) -> callable(n, sides, context) -> list[int]|None
        # Set by MapWidget so the dialog is parented to the correct widget.
        self.roll_provider_factory = None

    # ------------------------------------------------------------------
    # Public API used by the GUI
    # ------------------------------------------------------------------

    def start(self):
        """Begin (or restart) the encounter."""
        self._encounter.startEncounter()

    def submit_action(self, action):
        """
        Forward a player's chosen action back into the engine.

        Parameters
        ----------
        action : myAction
            The action selected in the GUI.
        """
        self._encounter.submitAction(action)

    @property
    def encounter(self):
        """Direct access to the underlying interactiveEncounter (for MapWidget internals)."""
        return self._encounter

    def get_map(self):
        """Return the underlying Map object (read-only for the GUI)."""
        return self._encounter.map

    def get_party(self):
        return self._encounter.map.party if self._encounter.map else []

    def get_enemies(self):
        return self._encounter.map.enemy if self._encounter.map else []

    # ------------------------------------------------------------------
    # Manual dice helpers
    # ------------------------------------------------------------------

    def set_manual_actors(self, names: set):
        """Replace the set of actor names that roll dice manually and reinstall the provider."""
        self.manual_actors = set(names)
        self._refresh_roll_provider()

    def set_interactive_actors(self, names: set):
        """Replace the set of actor names whose action choices are made by the user."""
        self.interactive_actors = set(names)
        # Propagate to the encounter so calcTurn knows which actors are interactive.
        if hasattr(self._encounter, 'interactive_actors'):
            self._encounter.interactive_actors = self.interactive_actors

    def _refresh_roll_provider(self):
        """Install (or clear) the global roll provider based on current manual_actors."""
        if self.manual_actors and self.roll_provider_factory is not None:
            controller = self

            def _provider(n, sides, context, actor_name=None):
                # Only intercept if the rolling actor is in the manual list.
                # actor_name is None for rollDice calls where no actor is tracked
                # (e.g. attacker's attack/damage) — treat None as the active actor.
                if actor_name is not None and actor_name not in controller.manual_actors:
                    return None  # let engine roll randomly
                if actor_name is None:
                    # rollDice without an actor_name — skip dialog (random)
                    return None
                return controller.roll_provider_factory(actor_name)(n, sides, context)

            _dice.set_roll_provider(_provider)
        else:
            _dice.clear_roll_provider()

    def _install_roll_provider(self, actor):
        """Ensure the persistent provider is active when a manual actor takes a turn."""
        if actor.name in self.manual_actors and self.roll_provider_factory is not None:
            # Provider already installed persistently; update the active actor hint
            # so rollDice (no actor_name) shows dialogs for the acting actor.
            controller = self
            acting_name = actor.name

            def _provider(n, sides, context, actor_name=None):
                name = actor_name if actor_name is not None else acting_name
                if name not in controller.manual_actors:
                    return None
                return controller.roll_provider_factory(name)(n, sides, context)

            _dice.set_roll_provider(_provider)

    def _clear_roll_provider(self):
        """After an action, revert to the persistent provider (or clear if none needed)."""
        self._refresh_roll_provider()

    # ------------------------------------------------------------------
    # Action methods — GUI calls these instead of touching the encounter
    # ------------------------------------------------------------------

    def move_actor(self, actor, coord, dest_hex_index: int):
        """
        Move *actor* to *coord* on the map, reduce their speed, and emit
        ``actor_moved`` with the destination hex index and remaining speed.

        Returns
        -------
        tuple[int, list]
            ``(distance_moved_in_hexes, new_reachable_hex_indexes)``
        """
        map_obj = self._encounter.map
        orig_index = next(
            i for i, c in enumerate(map_obj.arrayCenters)
            if map_obj.arrayCenters[c] == actor
        )
        map_obj.moveActor(actor, coord)
        dist = map_obj.distanceCalc(dest_hex_index, orig_index)
        actor.speed -= dist * 5
        new_move_hexes = calcMoveHexes(actor, map_obj)
        self.actor_moved.emit(actor, dest_hex_index, actor.speed)
        return dist, new_move_hexes

    def take_action(self, actor, turn_choice):
        """
        Execute *turn_choice* for *actor*, remove any actors that died, and
        rebuild spell-slot state.  Does **not** advance the turn.
        Manual roll provider is installed/cleared around the engine call.
        Emits persistent_spell_created / persistent_spell_ended as appropriate.
        """
        map_obj = self._encounter.map
        spells_before = {id(ps): ps for ps in map_obj.persistent_spells}

        self._install_roll_provider(actor)
        try:
            doAction(actor, map_obj, turn_choice)
            self._encounter.removeDeadActors()
        finally:
            self._clear_roll_provider()

        # Detect newly created persistent spells
        for ps in map_obj.persistent_spells:
            if id(ps) not in spells_before:
                self.persistent_spell_created.emit(ps)

        # Detect spells that ended during this action (concentration broken by damage, etc.)
        spells_after = {id(ps) for ps in map_obj.persistent_spells}
        for ps_id, ps in spells_before.items():
            if ps_id not in spells_after:
                self.persistent_spell_ended.emit(ps)

    def end_turn(self, actor):
        """
        Process end of *actor*'s turn:
        - trigger legendary actions for eligible enemies
        - advance the initiative order
        - reset the actor's speed
        - emit ``turn_changed`` with the next actor

        Returns the raw ``calcTurn()`` tuple so the GUI can update its state.
        Manual roll provider is installed for the current actor's legendary reactions.
        """
        map_obj = self._encounter.map
        self._encounter.removeDeadActors()

        for enemy in map_obj.enemy:
            if enemy.legActions >= 1 and len(map_obj.party) != 0:
                self.log_message.emit(f'Legendary Action check by: {enemy.name}\n')
                self._install_roll_provider(enemy)
                try:
                    enemy.takeLegAction(map_obj)
                    self._encounter.removeDeadActors()
                finally:
                    self._clear_roll_provider()

        spells_before = {id(ps): ps for ps in map_obj.persistent_spells}
        self._encounter.nextTurn()
        actor.speed = int(actor.maxSpeed)

        # Emit signals for any persistent spells that expired during nextTurn (round wrap)
        spells_after = {id(ps) for ps in map_obj.persistent_spells}
        for ps_id, ps in spells_before.items():
            if ps_id not in spells_after:
                self.persistent_spell_ended.emit(ps)

        # Snapshot again before calcTurn — auto-turns (monsters) can break concentration
        spells_before2 = {id(ps): ps for ps in map_obj.persistent_spells}
        turns = self._encounter.calcTurn()

        spells_after2 = {id(ps) for ps in map_obj.persistent_spells}
        for ps_id, ps in spells_before2.items():
            if ps_id not in spells_after2:
                self.persistent_spell_ended.emit(ps)

        if turns:
            self.turn_changed.emit(turns[0])
        return turns

    # ------------------------------------------------------------------
    # Slots called by the encounter thread (engine → GUI)
    # ------------------------------------------------------------------

    def _on_turn_changed(self, actor):
        self.turn_changed.emit(actor)

    def _on_hp_changed(self, actor, current, maximum):
        self.hp_changed.emit(actor, current, maximum)

    def _on_actor_died(self, actor):
        self.actor_died.emit(actor)

    def _on_encounter_ended(self, winner):
        self.encounter_ended.emit(winner)

    def _on_log_message(self, message):
        self.log_message.emit(message)

    def _on_action_choices_ready(self, choices):
        self.action_choices_ready.emit(choices)

