SAFARI_ROUTE_SEGMENT_SCHEDULES: dict[int, tuple[int, ...]] = {
    5: (1, 2, 2),
    7: (1, 3, 3),
    9: (1, 3, 2, 3),
    11: (1, 3, 3, 4),
    13: (1, 3, 3, 3, 3),
}


class SafariRouteSchedulePolicy:
    def segment_lengths_for(
        self,
        total_encounters: int,
    ) -> tuple[int, ...]:
        try:
            return SAFARI_ROUTE_SEGMENT_SCHEDULES[total_encounters]
        except KeyError as error:
            raise ValueError("unsupported Safari encounter total.") from error

    def segment_length_for(
        self,
        total_encounters: int,
        segment_index: int,
    ) -> int:
        lengths = self.segment_lengths_for(total_encounters)

        if segment_index < 0 or segment_index >= len(lengths):
            raise ValueError("segment_index is out of range.")

        return lengths[segment_index]
