"""Deterministic validation — no LLM. Pure Python math."""

import json
from langchain_core.tools import tool


@tool
def validate_claim(claimed_value: float, source_value: float, unit: str = "") -> str:
    """Compares a claimed value from the PDF against the source document value.

    Args:
        claimed_value: The value stated in the PDF
        source_value: The value found in the source document (Excel/CSV)
        unit: Measurement unit (e.g. 'tCO2e', 'MWh', 'fő')

    Returns:
        JSON with flag (green/yellow/red), deviation percentage, claimed and source values
    """
    if source_value == 0:
        return json.dumps({
            "flag": "red",
            "deviation_pct": 100.0,
            "claimed_value": claimed_value,
            "source_value": source_value,
            "unit": unit,
            "explanation": f"Source value is zero, cannot compute deviation. Claimed: {claimed_value} {unit}"
        })

    deviation = abs(claimed_value - source_value) / abs(source_value)

    if deviation < 0.005:
        flag = "green"
    elif deviation <= 0.05:
        flag = "yellow"
    else:
        flag = "red"

    return json.dumps({
        "flag": flag,
        "deviation_pct": round(deviation * 100, 2),
        "claimed_value": claimed_value,
        "source_value": source_value,
        "unit": unit,
        "explanation": (
            f"Claimed: {claimed_value} {unit}, "
            f"Source: {source_value} {unit}, "
            f"Deviation: {round(deviation * 100, 2)}%"
        )
    })


@tool
def compute_total(values: str) -> str:
    """Computes the sum of a list of numbers. Used to validate arithmetic in the PDF.

    Args:
        values: JSON array of numbers, e.g. '[1850, 4020]'

    Returns:
        JSON with the computed sum
    """
    nums = json.loads(values)
    total = sum(nums)
    return json.dumps({
        "values": nums,
        "computed_total": total,
        "count": len(nums)
    })