class BattleApplicationError(Exception):
    """Base error for battle application layer."""


class BattleNotFound(BattleApplicationError):
    def __init__(self, battle_id: int) -> None:
        super().__init__(f"Battle {battle_id} was not found.")
        self.battle_id = battle_id


class BattleCreatureNotOnTeam(BattleApplicationError):
    def __init__(self, identifier: int) -> None:
        super().__init__(f"Creature {identifier} is not on the trainer's saved team.")
        self.identifier = identifier
