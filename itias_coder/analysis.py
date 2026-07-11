"""Analysis computations for ITIAS coding sessions."""
from __future__ import annotations

from .models import Profile, Session


def padded_sequence(session: Session, profile: Profile) -> list[int]:
    """Code sequence with optional head/tail padding for ITIAS analysis."""
    codes = [s.code_id for s in session.segments if s.code_id is not None]
    pad = profile.analysis_padding_code
    if pad is not None:
        return [pad] + codes + [pad]
    return codes


def behavior_counts(session: Session, profile: Profile) -> dict[int, int]:
    """Count occurrences per code id."""
    counts: dict[int, int] = {}
    for seg in session.segments:
        if seg.code_id is not None:
            counts[seg.code_id] = counts.get(seg.code_id, 0) + 1
    return counts


def category_counts(session: Session, profile: Profile) -> dict[str, int]:
    """Aggregate coded segments into profile category buckets."""
    counts: dict[str, int] = {}
    for seg in session.segments:
        if seg.code_id is None:
            continue
        code_def = profile.get_code(seg.code_id)
        if code_def:
            cat = code_def.category
            counts[cat] = counts.get(cat, 0) + 1
    return counts


def proportions(counts: dict, total: int) -> dict:
    """Convert raw counts to percentage shares."""
    if total == 0:
        return {k: 0.0 for k in counts}
    return {k: v / total * 100.0 for k, v in counts.items()}


def _segment_timestamp(session: Session, seg_index: int) -> int:
    return seg_index * session.segment_duration


def time_matrix(
    session: Session,
    profile: Profile,
    bin_seconds: int = 60,
) -> dict[int, dict[int, int]]:
    """Bin timeline by ``bin_seconds``; count each code per bin."""
    matrix: dict[int, dict[int, int]] = {}
    for seg in session.segments:
        if seg.code_id is None:
            continue
        timestamp = _segment_timestamp(session, seg.index)
        bin_start = ((timestamp - 1) // bin_seconds) * bin_seconds
        if bin_start not in matrix:
            matrix[bin_start] = {}
        bucket = matrix[bin_start]
        bucket[seg.code_id] = bucket.get(seg.code_id, 0) + 1
    return matrix


def time_series_by_category(
    session: Session,
    profile: Profile,
    bin_seconds: int = 60,
) -> dict[str, list[tuple[int, int]]]:
    """Per-category time series: (bin_start_seconds, count) pairs."""
    bins: dict[int, dict[str, int]] = {}
    categories = list(profile.category_labels.keys())
    for seg in session.segments:
        if seg.code_id is None:
            continue
        code_def = profile.get_code(seg.code_id)
        if not code_def:
            continue
        timestamp = _segment_timestamp(session, seg.index)
        bin_start = ((timestamp - 1) // bin_seconds) * bin_seconds
        if bin_start not in bins:
            bins[bin_start] = {cat: 0 for cat in categories}
        bins[bin_start][code_def.category] = bins[bin_start].get(code_def.category, 0) + 1

    series: dict[str, list[tuple[int, int]]] = {cat: [] for cat in categories}
    for bin_start in sorted(bins):
        for cat in categories:
            series[cat].append((bin_start, bins[bin_start].get(cat, 0)))
    return series


def total_duration_seconds(session: Session) -> int:
    """Estimated lesson length from last coded segment."""
    if not session.segments:
        return 0
    max_index = max(s.index for s in session.segments)
    return max_index * session.segment_duration


def bin_labels(bin_seconds: int, total_seconds: int) -> list[tuple[int, str]]:
    """Ordered (bin_start, display_label) rows for matrix tables."""
    if total_seconds <= 0:
        return [(0, f"0–{bin_seconds}s")]
    labels = []
    bin_start = 0
    while bin_start < total_seconds:
        end = min(bin_start + bin_seconds, total_seconds)
        labels.append((bin_start, f"{bin_start}–{end}s"))
        bin_start += bin_seconds
    return labels
