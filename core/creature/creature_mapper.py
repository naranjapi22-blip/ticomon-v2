from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.species.variant import Variant


class CreatureMapper:

    @staticmethod
    def from_row(row, species):
        def _row_value(key):
            try:
                return row[key]
            except (KeyError, IndexError, TypeError):
                return None

        original_trainer_id = _row_value("original_trainer_id")
        if original_trainer_id is None:
            original_trainer_id = row["trainer_id"]

        return Creature(
            id=row["id"],
            collection_number=row["collection_number"],
            species=species,
            trainer_id=row["trainer_id"],
            ivs=IVs(
                hp=row["hp_iv"],
                attack=row["attack_iv"],
                defense=row["defense_iv"],
                special_attack=row["special_attack_iv"],
                special_defense=row["special_defense_iv"],
                speed=row["speed_iv"],
            ),
            size=Size(row["size"]),
            nature=Nature(row["nature"]),
            is_shiny=row["is_shiny"],
            current_form=(
                Variant(
                    id=row["variant_id"],
                    name=row["variant_name"],
                )
                if row["variant_id"] is not None
                else None
            ),
            minted_nature=(
                Nature(row["minted_nature"])
                if row["minted_nature"] is not None
                else None
            ),
            original_trainer_id=original_trainer_id,
        )

    @staticmethod
    def to_row(creature: Creature) -> tuple:
        original_trainer_id = creature.original_trainer_id
        if original_trainer_id is None:
            original_trainer_id = creature.trainer_id

        return (
            creature.trainer_id,
            original_trainer_id,
            creature.species.id,
            creature.current_form.id if creature.current_form else None,
            creature.is_shiny,
            creature.nature.name,
            creature.size.value,
            creature.ivs.hp,
            creature.ivs.attack,
            creature.ivs.defense,
            creature.ivs.special_attack,
            creature.ivs.special_defense,
            creature.ivs.speed,
            creature.minted_nature.name if creature.minted_nature else None,
        )
