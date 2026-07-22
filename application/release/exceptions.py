class ReleaseCreatureAssignedToTeam(Exception):
    """Raised when one or more creatures are currently assigned to a team."""

    def __init__(self, collection_numbers: list[int]) -> None:
        self.collection_numbers = collection_numbers
        super().__init__("Creatures assigned to the trainer team cannot be released.")
