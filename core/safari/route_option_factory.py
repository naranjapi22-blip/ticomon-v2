from __future__ import annotations

import random
from collections.abc import Sequence

from core.safari.domain import SAFARI_ZONE_DEFINITION_BY_ZONE, SafariZone
from core.safari.route import SafariRouteOption


class SafariRouteConfigurationError(ValueError):
    pass


class SafariRouteOptionFactory:
    _RECENT_ZONE_COUNT = 3
    _RECENT_ZONE_WEIGHT = 0.5
    _DEFAULT_ZONE_WEIGHT = 1.0
    _STAY_WEIGHT = 0.75
    _MAX_OPTIONS = 3

    def create_options(
        self,
        current_zone: SafariZone,
        visited_zones: Sequence[SafariZone],
        previous_option: SafariRouteOption | None,
        random_source: random.Random,
    ) -> tuple[SafariRouteOption, ...]:
        current_definition = SAFARI_ZONE_DEFINITION_BY_ZONE[current_zone]
        destinations = list(current_definition.transitions)

        previous_was_stay_here = (
            previous_option is not None
            and previous_option.stays_in_same_zone
            and previous_option.destination_zone == current_zone
        )
        if not previous_was_stay_here:
            destinations.append(current_zone)

        destinations = list(dict.fromkeys(destinations))
        if len(destinations) < 2:
            raise SafariRouteConfigurationError(
                "route configuration cannot produce two options."
            )

        selected_destinations = self._select_destinations(
            destinations=destinations,
            current_zone=current_zone,
            visited_zones=visited_zones,
            random_source=random_source,
        )

        return tuple(
            self._create_option(current_zone, destination)
            for destination in selected_destinations
        )

    def _select_destinations(
        self,
        destinations: list[SafariZone],
        current_zone: SafariZone,
        visited_zones: Sequence[SafariZone],
        random_source: random.Random,
    ) -> list[SafariZone]:
        if len(destinations) == 2:
            return destinations

        option_count = random_source.choice(
            (2, min(len(destinations), self._MAX_OPTIONS))
        )

        recent_zones = set(visited_zones[-self._RECENT_ZONE_COUNT :])
        available = list(destinations)
        selected: list[SafariZone] = []

        while len(selected) < option_count:
            weights = [
                self._selection_weight(
                    destination=destination,
                    current_zone=current_zone,
                    recent_zones=recent_zones,
                )
                for destination in available
            ]
            destination = random_source.choices(
                available,
                weights=weights,
                k=1,
            )[0]
            selected.append(destination)
            available.remove(destination)

        return selected

    def _selection_weight(
        self,
        destination: SafariZone,
        current_zone: SafariZone,
        recent_zones: set[SafariZone],
    ) -> float:
        weight = (
            self._STAY_WEIGHT
            if destination == current_zone
            else self._DEFAULT_ZONE_WEIGHT
        )
        if destination in recent_zones:
            weight *= self._RECENT_ZONE_WEIGHT
        return weight

    def _create_option(
        self,
        source_zone: SafariZone,
        destination_zone: SafariZone,
    ) -> SafariRouteOption:
        destination_definition = SAFARI_ZONE_DEFINITION_BY_ZONE[destination_zone]

        return SafariRouteOption(
            id=f"{source_zone.value}:{destination_zone.value}",
            source_zone=source_zone,
            destination_zone=destination_zone,
            type_weight_modifiers=destination_definition.base_type_weights,
            allowed_events=destination_definition.allowed_events,
            narrative_key=(
                f"{source_zone.value.lower()}_to_" f"{destination_zone.value.lower()}"
            ),
        )
