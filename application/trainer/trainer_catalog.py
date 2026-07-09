from application.trainer.trainer import Trainer

PAGE_SIZE = 6

TRAINERS = {
    1: Trainer(1, "Red", "red.png", "red.gif"),
    2: Trainer(2, "Leaf", "leaf.png", "leaf.gif"),
    3: Trainer(3, "Blue", "blue.png", "blue.gif"),
    4: Trainer(4, "Silver", "silver.png", "silver.gif"),
    5: Trainer(5, "Ethan", "ethan.png", "ethan.gif"),
    6: Trainer(6, "Lyra", "lyra.png", "lyra.gif"),
    7: Trainer(7, "Brendan", "brendan.png", "brendan.gif"),
    8: Trainer(8, "Dawn", "dawn.png", "dawn.gif"),
    9: Trainer(9, "Lucas", "lucas.png", "lucas.gif"),
    10: Trainer(10, "Barry", "barry.png", "barry.gif"),
    11: Trainer(11, "Dawn (Platinum)", "dawn_platinum.png", "dawn_platinum.gif"),
    12: Trainer(12, "Lucas (Platinum)", "lucas_platinum.png", "lucas_platinum.gif"),
    13: Trainer(13, "Lance", "lance.png", "lance.gif"),
    14: Trainer(14, "Cheryl", "cheryl.png", "cheryl.gif"),
    15: Trainer(15, "Buck", "buck.png", "buck.gif"),
    16: Trainer(16, "Marley", "marley.png", "marley.gif"),
    17: Trainer(17, "Mira", "mira.png", "mira.gif"),
    18: Trainer(18, "Riley", "riley.png", "riley.gif"),
}


def get_trainer(trainer_id: int) -> Trainer:
    return TRAINERS[trainer_id]


def list_trainers() -> list[Trainer]:
    return list(TRAINERS.values())


def get_page(page: int) -> list[Trainer]:
    trainers = list_trainers()

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    return trainers[start:end]
