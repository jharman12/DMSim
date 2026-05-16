"""
SimController: the single bridge between the pure engine layer and the PyQt5 GUI.

The GUI should only ever import from this module when it needs to interact with
the simulation. The engine/model layer must never import Qt.
"""
from PyQt5.QtCore import QObject, pyqtSignal
from engine.combat import doAction
from engine.targeting import calcMoveHexes


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
    actor_moved  : emits (actor, new_hex_index, remaining_speed) after a move
    """

    turn_changed = pyqtSignal(object)
    hp_changed = pyqtSignal(object, int, int)
    actor_died = pyqtSignal(object)
    encounter_ended = pyqtSignal(str)
    log_message = pyqtSignal(str)
    action_choices_ready = pyqtSignal(list)
    actor_moved = pyqtSignal(object, int, int)  # actor, hex_index, remaining_speed

    def __init__(self, encounter, parent=None):
        """
        Parameters
        ----------
        encounter : interactiveEncounter
            A fully initialised encounter instance.
        """
        super().__init__(parent)
        self._encounter = encounter

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
        """
        map_obj = self._encounter.map
        doAction(actor, map_obj, turn_choice)
        self._encounter.removeDeadActors()

    def end_turn(self, actor):
        """
        Process end of *actor*'s turn:
        - trigger legendary actions for eligible enemies
        - advance the initiative order
        - reset the actor's speed
        - emit ``turn_changed`` with the next actor

        Returns the raw ``calcTurn()`` tuple so the GUI can update its state.
        """
        map_obj = self._encounter.map
        self._encounter.removeDeadActors()

        for enemy in map_obj.enemy:
            if enemy.legActions >= 1 and len(map_obj.party) != 0:
                self.log_message.emit(f'Legendary Action check by: {enemy.name}\n')
                enemy.takeLegAction(map_obj)
                self._encounter.removeDeadActors()

        self._encounter.nextTurn()
        actor.speed = int(actor.maxSpeed)

        turns = self._encounter.calcTurn()
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
