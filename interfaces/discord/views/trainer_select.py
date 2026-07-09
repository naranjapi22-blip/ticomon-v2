import discord

from application.trainer.trainer import Trainer


class TrainerSelect(discord.ui.Select):
    def __init__(
        self,
        trainers: list[Trainer],
    ):
        options = [
            discord.SelectOption(
                label=trainer.name,
                value=str(trainer.id),
            )
            for trainer in trainers
        ]

        super().__init__(
            placeholder="Choose a trainer...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        view = self.view

        trainer_id = int(self.values[0])

        await view.core.profile_service.set_trainer(
            trainer_id=view.trainer_id,
            selected_trainer=trainer_id,
        )

        await view.refresh(interaction)
