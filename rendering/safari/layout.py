from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SlotPlacement:
    x: int
    y: int
    width: int
    height: int


def layout_slot_cards(slot_count: int) -> tuple[SlotPlacement, ...]:
    if slot_count <= 0:
        return ()
    if slot_count == 1:
        return (SlotPlacement(185, 136, 650, 360),)
    if slot_count == 2:
        return (
            SlotPlacement(40, 150, 450, 300),
            SlotPlacement(530, 150, 450, 300),
        )
    if slot_count == 3:
        return (
            SlotPlacement(30, 165, 310, 260),
            SlotPlacement(355, 165, 310, 260),
            SlotPlacement(680, 165, 310, 260),
        )
    if slot_count == 4:
        return (
            SlotPlacement(25, 120, 460, 210),
            SlotPlacement(535, 120, 460, 210),
            SlotPlacement(25, 330, 460, 210),
            SlotPlacement(535, 330, 460, 210),
        )
    return (
        SlotPlacement(25, 124, 310, 210),
        SlotPlacement(355, 124, 310, 210),
        SlotPlacement(685, 124, 310, 210),
        SlotPlacement(135, 344, 350, 190),
        SlotPlacement(535, 344, 350, 190),
    )
