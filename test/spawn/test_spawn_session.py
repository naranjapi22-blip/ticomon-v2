from core.spawn.session import SpawnSession


class DummyOpportunity:
    pass


def test_remove_opportunity():
    first = DummyOpportunity()
    second = DummyOpportunity()
    third = DummyOpportunity()

    session = SpawnSession(
        opportunities=[
            first,
            second,
            third,
        ],
    )

    session.remove_opportunity(2)

    assert len(session.opportunities) == 2
    assert session.opportunities == [
        first,
        third,
    ]
