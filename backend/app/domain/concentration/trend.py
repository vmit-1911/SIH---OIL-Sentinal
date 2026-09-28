"""Deterministic observed trend calculation across chronological time periods."""

from typing import Dict, List, Optional
from app.domain.enums import ObservedTrend


class TrendEvaluator:
    """Evaluates descriptive observed trends from historical time period counts.

    These are descriptive engineering algorithms for observed trend classification
    across chronological reporting periods. They are NOT:
    - OIL safety thresholds
    - IOGP thresholds
    - Calibrated statistical significance thresholds
    - SIF probabilities
    - Predictive risk thresholds

    Trend classification is purely descriptive of observed historical reporting distributions
    and must not be described as prediction or forecasting.
    """

    @staticmethod
    def evaluate_trend(
        temporal_distribution: Dict[str, int],
        min_periods: int = 2,
        increase_ratio: float = 1.25,
        decrease_ratio: float = 0.80,
    ) -> ObservedTrend:
        """Determine observed trend classification from chronological time buckets (e.g. {'2026-01': 2, '2026-02': 4}).

        Parameters:
            temporal_distribution: Mapping of period strings (e.g. 'YYYY-MM') to integer occurrence counts.
            min_periods: Minimum populated periods required to determine trend (otherwise INSUFFICIENT_DATA).
            increase_ratio: Ratio threshold (e.g. 1.25) above which recent activity vs baseline is classified INCREASING.
            decrease_ratio: Ratio threshold (e.g. 0.80) below which recent activity vs baseline is classified DECREASING.
        """
        if not temporal_distribution:
            return ObservedTrend.INSUFFICIENT_DATA

        # Sort periods chronologically
        sorted_periods = sorted(temporal_distribution.keys())
        populated_counts: List[int] = [temporal_distribution[p] for p in sorted_periods]

        if len(populated_counts) < min_periods:
            return ObservedTrend.INSUFFICIENT_DATA

        # Case 1: Identical counts across all periods -> STABLE
        if len(set(populated_counts)) == 1:
            return ObservedTrend.STABLE

        # Case 2: Monotonically increasing or non-decreasing with net increase -> INCREASING
        is_increasing = all(
            populated_counts[i] <= populated_counts[i + 1] for i in range(len(populated_counts) - 1)
        ) and (populated_counts[-1] > populated_counts[0])

        if is_increasing:
            return ObservedTrend.INCREASING

        # Case 3: Monotonically decreasing or non-increasing with net decrease -> DECREASING
        is_decreasing = all(
            populated_counts[i] >= populated_counts[i + 1] for i in range(len(populated_counts) - 1)
        ) and (populated_counts[-1] < populated_counts[0])

        if is_decreasing:
            return ObservedTrend.DECREASING

        # Case 4: Non-monotonic fluctuations -> compare latest vs baseline half-aggregates
        mid = len(populated_counts) // 2
        first_half = populated_counts[:mid]
        second_half = populated_counts[mid:]

        first_half_sum = sum(first_half)
        second_half_sum = sum(second_half)

        baseline_rate = first_half_sum / len(first_half)
        recent_rate = second_half_sum / len(second_half)

        if baseline_rate == 0.0:
            if recent_rate > 0.0:
                return ObservedTrend.INCREASING
            return ObservedTrend.STABLE

        ratio = recent_rate / baseline_rate

        if ratio >= increase_ratio and populated_counts[-1] >= populated_counts[0]:
            return ObservedTrend.INCREASING
        elif ratio <= decrease_ratio and populated_counts[-1] <= populated_counts[0]:
            return ObservedTrend.DECREASING
        else:
            return ObservedTrend.STABLE
