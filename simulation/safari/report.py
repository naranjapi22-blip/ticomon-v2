from __future__ import annotations

from simulation.safari.simulator import SafariSimulationReport


def render_console_report(report: SafariSimulationReport) -> str:
    lines = [
        "Safari simulation report",
        f"catalog={report.catalog_source} size={report.catalog_size}",
        f"seed={report.config.seed} simulations={report.config.simulations}",
    ]
    for scenario in report.scenarios:
        data = scenario.to_dict()
        lines.append(
            f"level={scenario.level} participants={scenario.participant_count} "
            f"strategy={scenario.strategy_name} runs={data['runs']} "
            f"captured={data['captures']['total']} "
            f"finish={data['finalization']['reasons']}"
        )
    if report.anomalies:
        lines.append("anomalies:")
        lines.extend(f"- {anomaly}" for anomaly in report.anomalies[:25])
    return "\n".join(lines)
