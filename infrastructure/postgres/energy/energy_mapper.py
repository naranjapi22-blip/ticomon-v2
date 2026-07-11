from core.energy.trainer_energy import TrainerEnergy


class EnergyMapper:

    @staticmethod
    def to_domain(row) -> TrainerEnergy:

        return TrainerEnergy(
            trainer_id=row["trainer_id"],
            current_energy=row["current_energy"],
            max_energy=row["max_energy"],
            last_regenerated_at=row["last_regenerated_at"],
        )
