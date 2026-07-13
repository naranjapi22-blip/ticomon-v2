from rendering.safari.layout import layout_slot_cards


def _intersects(first, second) -> bool:
    return not (
        first.x + first.width <= second.x
        or second.x + second.width <= first.x
        or first.y + first.height <= second.y
        or second.y + second.height <= first.y
    )


def test_layout_slot_cards_supports_one_to_five_slots() -> None:
    for count in range(1, 6):
        placements = layout_slot_cards(count)
        assert len(placements) == count
        assert all(placement.width > 0 for placement in placements)
        assert all(placement.height > 0 for placement in placements)
        for index, placement in enumerate(placements):
            for other in placements[index + 1 :]:
                assert not _intersects(placement, other)
