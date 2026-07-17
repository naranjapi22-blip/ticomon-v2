import discord


async def resolve_trainer_display_name(
    client: discord.Client,
    guild: discord.Guild | None,
    trainer_id: int,
) -> str:
    if guild is not None:
        member = guild.get_member(trainer_id)
        if member is None:
            try:
                member = await guild.fetch_member(trainer_id)
            except discord.HTTPException:
                member = None
        if member is not None:
            return member.display_name

    user = client.get_user(trainer_id)
    if user is None:
        try:
            user = await client.fetch_user(trainer_id)
        except discord.HTTPException:
            return f"Trainer {trainer_id}"

    if user.global_name:
        return user.global_name

    return user.display_name or user.name
