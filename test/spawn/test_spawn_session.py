from core.spawn.session import SpawnSession


class DummyOpportunity:
    pass


def test_select_opportunity():
    first = DummyOpportunity()
    second = DummyOpportunity()
    third = DummyOpportunity()

    session = SpawnSession(
        owner_id=123,
        opportunities=[
            first,
            second,
            third,
        ],
    )

    selected = session.select_opportunity(2)

    assert selected is second
    assert session.selected_opportunity is second
    assert session.opportunities == [
        first,
        second,
        third,
    ]
