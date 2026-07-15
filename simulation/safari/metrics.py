from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from application.safari import SafariFinalSummary
from core.safari.domain import SafariComposition
from core.safari.regional_encounter import SafariRegionalEncounterForm
from core.species.regional_species import is_regional_species
from core.species.species import Species


@dataclass(frozen=True, slots=True)
class SafariEncounterTrace:
    encounter_id: UUID
    composition: SafariComposition
    event: str
    regional_form: SafariRegionalEncounterForm | None
    global_shiny: bool
    slot_count: int
    species_ids: tuple[int, ...]
    slot_categories: tuple[str, ...]
    slot_is_shiny: tuple[bool, ...]
    competitor_counts: tuple[int, ...]
    captured_slot_count: int
    escaped_slot_count: int
    attempts_executed: int
    balls_committed: int
    balls_not_executed: int

    def __post_init__(self) -> None:
        if self.slot_count != len(self.species_ids):
            raise ValueError("slot_count must match species_ids length.")
        if self.slot_count != len(self.slot_categories):
            raise ValueError("slot_count must match slot_categories length.")
        if self.slot_count != len(self.slot_is_shiny):
            raise ValueError("slot_count must match slot_is_shiny length.")
        if self.slot_count != len(self.competitor_counts):
            raise ValueError("slot_count must match competitor_counts length.")


@dataclass(frozen=True, slots=True)
class SafariRunTrace:
    summary: SafariFinalSummary
    encounter_traces: tuple[SafariEncounterTrace, ...]
    composition_fallbacks: int
    event_fallbacks: int
    normal_fallbacks: int
    anomalies: tuple[str, ...] = ()


@dataclass(slots=True)
class ScenarioMetrics:
    level: int
    participant_count: int
    strategy_name: str
    catalog_species_count: int
    catalog_regional_species_count: int
    runs: int = 0
    map_counts: Counter[str] = field(default_factory=Counter)
    weather_counts_by_map: dict[str, Counter[str]] = field(
        default_factory=lambda: defaultdict(Counter)
    )
    time_counts: Counter[str] = field(default_factory=Counter)
    composition_counts: Counter[str] = field(default_factory=Counter)
    event_counts: Counter[str] = field(default_factory=Counter)
    regional_form_counts: Counter[str] = field(default_factory=Counter)
    regional_safaris: int = 0
    regional_encounters: int = 0
    regional_species_seen: set[int] = field(default_factory=set)
    legendary_safaris: int = 0
    mythical_safaris: int = 0
    shiny_global_safaris: int = 0
    regional_herd_safaris: int = 0
    extraordinary_first_positions: dict[str, Counter[int]] = field(
        default_factory=lambda: defaultdict(Counter)
    )
    encounters_completed_total: int = 0
    encounter_size_counts: Counter[int] = field(default_factory=Counter)
    competitor_counts: Counter[int] = field(default_factory=Counter)
    single_competitor_slots: int = 0
    multi_competitor_slots: int = 0
    slots_total: int = 0
    species_seen: set[int] = field(default_factory=set)
    repeated_species_encounters: int = 0
    balls_initial_total: int = 0
    balls_committed_total: int = 0
    balls_remaining_total: int = 0
    attempts_executed_total: int = 0
    balls_not_executed_total: int = 0
    captures_total: int = 0
    captures_by_participant: Counter[int] = field(default_factory=Counter)
    captures_by_composition: Counter[str] = field(default_factory=Counter)
    base_category_attempts: Counter[str] = field(default_factory=Counter)
    base_category_captures: Counter[str] = field(default_factory=Counter)
    shiny_slot_count: int = 0
    shiny_capture_count: int = 0
    no_capture_participants_total: int = 0
    top_capture_share_total: float = 0.0
    finish_reason_counts: Counter[str] = field(default_factory=Counter)
    finish_encounter_indices: list[int] = field(default_factory=list)
    finish_balls_remaining_total: int = 0
    composition_fallbacks: int = 0
    event_fallbacks: int = 0
    normal_fallbacks: int = 0
    anomalies: list[str] = field(default_factory=list)
    route_path_samples: list[str] = field(default_factory=list)
    generation_sequence_samples: list[str] = field(default_factory=list)

    def record_run(self, trace: SafariRunTrace) -> None:
        summary = trace.summary
        self.runs += 1
        self.map_counts[summary.safari_map.value] += 1
        self.weather_counts_by_map[summary.safari_map.value][summary.weather.value] += 1
        self.time_counts[summary.time_of_day.value] += 1
        self.finish_reason_counts[summary.finish_reason.value] += 1
        self.encounters_completed_total += summary.totals.encounters_completed
        self.composition_fallbacks += trace.composition_fallbacks
        self.event_fallbacks += trace.event_fallbacks
        self.normal_fallbacks += trace.normal_fallbacks
        self.anomalies.extend(trace.anomalies)
        self.finish_encounter_indices.append(summary.totals.encounters_completed)
        self.finish_balls_remaining_total += sum(
            participant.balls_remaining for participant in summary.ranking
        )
        self.no_capture_participants_total += sum(
            1 for participant in summary.ranking if participant.capture_count == 0
        )
        if summary.ranking:
            total_captures = sum(
                participant.capture_count for participant in summary.ranking
            )
            top_captures = max(
                participant.capture_count for participant in summary.ranking
            )
            if total_captures > 0:
                self.top_capture_share_total += top_captures / total_captures

        route_path = " -> ".join(
            segment.zone.value for segment in summary.route.segments
        )
        if len(self.route_path_samples) < 5:
            self.route_path_samples.append(route_path)

        sequence = " | ".join(
            f"{trace_entry.composition.value}:{trace_entry.event}"
            for trace_entry in trace.encounter_traces
        )
        if len(self.generation_sequence_samples) < 5:
            self.generation_sequence_samples.append(sequence)

        if any(entry.regional_form is not None for entry in trace.encounter_traces):
            self.regional_safaris += 1
        if any(
            entry.composition == SafariComposition.LEGENDARY
            for entry in trace.encounter_traces
        ):
            self.legendary_safaris += 1
        if any(
            entry.composition == SafariComposition.MYTHICAL
            for entry in trace.encounter_traces
        ):
            self.mythical_safaris += 1
        if any(entry.global_shiny for entry in trace.encounter_traces):
            self.shiny_global_safaris += 1
        if any(
            entry.regional_form == SafariRegionalEncounterForm.HERD
            for entry in trace.encounter_traces
        ):
            self.regional_herd_safaris += 1

        encounter_summaries = summary.encounters
        if len(encounter_summaries) != len(trace.encounter_traces):
            self.anomalies.append(
                "encounter history count does not match generation trace count."
            )

        for encounter_summary, encounter_trace in zip(
            encounter_summaries,
            trace.encounter_traces,
            strict=False,
        ):
            self.composition_counts[encounter_trace.composition.value] += 1
            self.event_counts[encounter_trace.event] += 1
            if encounter_trace.regional_form is not None:
                self.regional_form_counts[encounter_trace.regional_form.value] += 1
                self.regional_encounters += 1

            self.encounter_size_counts[encounter_trace.slot_count] += 1
            self.slots_total += encounter_trace.slot_count
            self.competitor_counts.update(encounter_trace.competitor_counts)
            self.single_competitor_slots += sum(
                1 for count in encounter_trace.competitor_counts if count == 1
            )
            self.multi_competitor_slots += sum(
                1 for count in encounter_trace.competitor_counts if count > 1
            )
            self.attempts_executed_total += encounter_trace.attempts_executed
            self.balls_committed_total += encounter_trace.balls_committed
            self.balls_not_executed_total += encounter_trace.balls_not_executed

            self.species_seen.update(encounter_trace.species_ids)
            self.regional_species_seen.update(
                species_id
                for species_id, category in zip(
                    encounter_trace.species_ids,
                    encounter_trace.slot_categories,
                    strict=True,
                )
                if category == "regional"
            )

            if len(set(encounter_trace.species_ids)) != len(
                encounter_trace.species_ids
            ):
                if (
                    encounter_trace.composition not in (SafariComposition.HERD,)
                    and encounter_trace.regional_form
                    != SafariRegionalEncounterForm.HERD
                ):
                    self.anomalies.append(
                        "duplicate species detected in "
                        f"{encounter_trace.composition.value} encounter."
                    )

            for index, slot_summary in enumerate(encounter_summary.slot_summaries):
                category = encounter_trace.slot_categories[index]
                self.base_category_attempts[category] += 1
                if slot_summary.captured_creature is not None:
                    self.base_category_captures[category] += 1
                if encounter_trace.slot_is_shiny[index]:
                    self.shiny_slot_count += 1
                    if slot_summary.captured_creature is not None:
                        self.shiny_capture_count += 1

            self.captures_total += encounter_summary.captured_slot_count
            for slot_summary in encounter_summary.slot_summaries:
                if slot_summary.captured_creature is not None:
                    self.captures_by_participant[
                        slot_summary.winner_trainer_id or 0
                    ] += 1

            self.captures_by_composition[
                encounter_trace.composition.value
            ] += encounter_summary.captured_slot_count

            first_capture_position = next(
                (
                    index
                    for index, slot_summary in enumerate(
                        encounter_summary.slot_summaries,
                        start=1,
                    )
                    if slot_summary.captured_creature is not None
                ),
                None,
            )
            if first_capture_position is not None:
                self.extraordinary_first_positions[encounter_trace.composition.value][
                    first_capture_position
                ] += 1

        self.balls_initial_total += sum(
            participant.initial_balls for participant in summary.ranking
        )
        self.balls_remaining_total += sum(
            participant.balls_remaining for participant in summary.ranking
        )

    def to_dict(self) -> dict[str, Any]:
        total_participants = self.runs * self.participant_count
        regional_coverage = (
            len(self.regional_species_seen) / self.catalog_regional_species_count
            if self.catalog_regional_species_count
            else 0.0
        )
        return {
            "level": self.level,
            "participant_count": self.participant_count,
            "strategy": self.strategy_name,
            "runs": self.runs,
            "maps": dict(self.map_counts),
            "weather_by_map": {
                safari_map: dict(weather_counts)
                for safari_map, weather_counts in self.weather_counts_by_map.items()
            },
            "time_of_day": dict(self.time_counts),
            "compositions": dict(self.composition_counts),
            "events": dict(self.event_counts),
            "regional_forms": dict(self.regional_form_counts),
            "regional": {
                "safaris": self.regional_safaris,
                "encounters": self.regional_encounters,
                "species_seen": sorted(self.regional_species_seen),
                "catalog_size": self.catalog_regional_species_count,
                "coverage": regional_coverage,
                "herd_safaris": self.regional_herd_safaris,
            },
            "extraordinary": {
                "legendary_safaris": self.legendary_safaris,
                "mythical_safaris": self.mythical_safaris,
                "shiny_global_safaris": self.shiny_global_safaris,
                "regional_herd_safaris": self.regional_herd_safaris,
                "first_positions": {
                    kind: dict(counts)
                    for kind, counts in self.extraordinary_first_positions.items()
                },
            },
            "encounters": {
                "completed": self.encounters_completed_total,
                "sizes": dict(self.encounter_size_counts),
                "average_size": (
                    self.slots_total / self.encounters_completed_total
                    if self.encounters_completed_total
                    else 0.0
                ),
                "species_seen": len(self.species_seen),
                "repeated_species_encounters": self.repeated_species_encounters,
            },
            "competition": {
                "slots_total": self.slots_total,
                "competitors": dict(self.competitor_counts),
                "single_competitor_slots": self.single_competitor_slots,
                "multi_competitor_slots": self.multi_competitor_slots,
                "average_competitors_per_slot": (
                    sum(
                        count * amount
                        for count, amount in self.competitor_counts.items()
                    )
                    / self.slots_total
                    if self.slots_total
                    else 0.0
                ),
                "no_capture_participants": self.no_capture_participants_total,
                "no_capture_participant_rate": (
                    self.no_capture_participants_total / total_participants
                    if total_participants
                    else 0.0
                ),
                "top_capture_share_average": (
                    self.top_capture_share_total / self.runs if self.runs else 0.0
                ),
            },
            "balls": {
                "initial": self.balls_initial_total,
                "committed": self.balls_committed_total,
                "spent": self.attempts_executed_total,
                "remaining": self.balls_remaining_total,
                "attempts_executed": self.attempts_executed_total,
                "committed_not_executed": self.balls_not_executed_total,
                "balanced": self.balls_initial_total
                == self.attempts_executed_total + self.balls_remaining_total,
            },
            "captures": {
                "total": self.captures_total,
                "by_participant": dict(self.captures_by_participant),
                "by_composition": dict(self.captures_by_composition),
                "base_category_attempts": dict(self.base_category_attempts),
                "base_category_captures": dict(self.base_category_captures),
                "shiny_slots": self.shiny_slot_count,
                "shiny_captures": self.shiny_capture_count,
            },
            "finalization": {
                "reasons": dict(self.finish_reason_counts),
                "average_finish_encounter": (
                    sum(self.finish_encounter_indices) / self.runs if self.runs else 0.0
                ),
                "balls_remaining_average": (
                    self.finish_balls_remaining_total / self.runs if self.runs else 0.0
                ),
            },
            "fallbacks": {
                "composition": self.composition_fallbacks,
                "event": self.event_fallbacks,
                "normal_none": self.normal_fallbacks,
            },
            "anomalies": list(self.anomalies),
            "route_samples": list(self.route_path_samples),
            "generation_samples": list(self.generation_sequence_samples),
        }


def classify_slot_category(species: Species) -> str:
    if species.metadata.is_legendary:
        return "legendary"
    if species.metadata.is_mythical:
        return "mythical"
    if is_regional_species(species):
        return "regional"
    return "ordinary"


def build_encounter_trace(
    *,
    encounter,
    generated,
    resolution,
    global_shiny: bool = False,
) -> SafariEncounterTrace:
    slot_categories = tuple(
        classify_slot_category(slot.opportunity.species) for slot in encounter.slots
    )
    slot_is_shiny = tuple(slot.opportunity.is_shiny for slot in encounter.slots)
    competitor_counts = tuple(
        len(outcome.balls_committed_by_trainer) for outcome in resolution.slot_outcomes
    )
    species_ids = tuple(slot.species_id for slot in encounter.slots)
    return SafariEncounterTrace(
        encounter_id=encounter.id,
        composition=encounter.composition,
        event=str(
            getattr(generated, "event", "NONE").value
            if hasattr(getattr(generated, "event", None), "value")
            else getattr(generated, "event", "NONE")
        ),
        regional_form=getattr(generated, "regional_form", None),
        global_shiny=global_shiny,
        slot_count=len(encounter.slots),
        species_ids=species_ids,
        slot_categories=slot_categories,
        slot_is_shiny=slot_is_shiny,
        competitor_counts=competitor_counts,
        captured_slot_count=resolution.captured_slot_ids.__len__(),
        escaped_slot_count=resolution.escaped_slot_ids.__len__(),
        attempts_executed=resolution.attempts_executed,
        balls_committed=resolution.balls_committed,
        balls_not_executed=resolution.balls_committed - resolution.attempts_executed,
    )


def build_run_trace(
    *,
    summary: SafariFinalSummary,
    encounter_traces: tuple[SafariEncounterTrace, ...],
    composition_fallbacks: int,
    event_fallbacks: int,
    normal_fallbacks: int,
    anomalies: tuple[str, ...] = (),
) -> SafariRunTrace:
    return SafariRunTrace(
        summary=summary,
        encounter_traces=encounter_traces,
        composition_fallbacks=composition_fallbacks,
        event_fallbacks=event_fallbacks,
        normal_fallbacks=normal_fallbacks,
        anomalies=anomalies,
    )
