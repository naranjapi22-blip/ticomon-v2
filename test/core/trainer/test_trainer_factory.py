from core.trainer.trainer_factory import TrainerFactory


def test_create_trainer():
    trainer = TrainerFactory.create(
        trainer_id=123,
        starter_creature_id=456,
    )

    assert trainer.trainer_id == 123
    assert trainer.starter_creature_id == 456
    assert trainer.started_at is not None
