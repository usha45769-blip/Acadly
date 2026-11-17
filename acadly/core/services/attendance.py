"""Attendance % and the 85% threshold analysis."""
import math


def attendance_stats(held, attended, threshold=85):
    """Attendance % = attended / held x 100, compared against the threshold.

    Returns percentage, status, how many classes must be attended in a row to get back
    to the threshold, and how many classes can still be missed while staying above it.
    """
    held, attended = int(held), int(attended)
    pct = round(attended * 100 / held, 2) if held else 0.0
    if held == 0:
        status = "no-data"
    elif pct >= threshold + 5:
        status = "safe"
    elif pct >= threshold:
        status = "borderline"
    else:
        status = "short"

    need = can_miss = 0
    if held and threshold < 100:
        if pct < threshold:
            # (a + x) / (h + x) >= t   ->   x >= (t*h - 100*a) / (100 - t)
            need = math.ceil((threshold * held - 100 * attended) / (100 - threshold))
        else:
            can_miss = max(0, math.floor(attended * 100 / threshold - held))
    return {"held": held, "attended": attended, "pct": pct, "status": status,
            "need_to_attend": need, "can_miss": can_miss}
