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
        return (SlotPlacement(280, 178, 460, 230),)
    if slot_count == 2:
        return (
            SlotPlacement(95, 178, 410, 230),
            SlotPlacement(515, 178, 410, 230),
        )
    if slot_count == 3:
        return (
            SlotPlacement(40, 182, 300, 210),
            SlotPlacement(360, 182, 300, 210),
            SlotPlacement(680, 182, 300, 210),
        )
    if slot_count == 4:
        return (
            SlotPlacement(100, 150, 390, 180),
            SlotPlacement(530, 150, 390, 180),
            SlotPlacement(100, 350, 390, 180),
            SlotPlacement(530, 350, 390, 180),
        )
    return (
        SlotPlacement(60, 152, 290, 160),
        SlotPlacement(365, 152, 290, 160),
        SlotPlacement(670, 152, 290, 160),
        SlotPlacement(110, 334, 390, 160),
        SlotPlacement(520, 334, 390, 160),
    )
