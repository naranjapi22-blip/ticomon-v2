class StarterService:

    def __init__(
        self,
        species_repository,
    ):
        self._species_repository = species_repository

    async def get_starters(self): ...
