from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.species.variant import Variant


class CreatureMapper:

    @staticmethod
    def from_row(row, species):
        return Creature(
            id=row["id"],
            collection_number=row["collection_number"],
            species=species,
            variant=Variant(row["variant"]) if row["variant"] else None,
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
            current_form=row["current_form"],
        )

    @staticmethod
    def to_row(creature: Creature) -> tuple:
        return (
            creature.trainer_id,
            creature.species.id,
            creature.variant.name if creature.variant else None,
            creature.is_shiny,
            creature.nature.name,
            creature.size.value,
            creature.ivs.hp,
            creature.ivs.attack,
            creature.ivs.defense,
            creature.ivs.special_attack,
            creature.ivs.special_defense,
            creature.ivs.speed,
            creature.current_form,
        )
