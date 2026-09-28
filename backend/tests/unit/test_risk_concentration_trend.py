"""Unit tests for deterministic observed trend evaluation (TrendEvaluator)."""

from app.domain.concentration.trend import TrendEvaluator
from app.domain.enums import ObservedTrend


def test_trend_monotonic_increasing():
    """Verify strictly increasing temporal counts result in INCREASING trend."""
    dist = {"2026-01": 1, "2026-02": 2, "2026-03": 4}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2)
    assert trend == ObservedTrend.INCREASING


def test_trend_monotonic_decreasing():
    """Verify strictly decreasing temporal counts result in DECREASING trend."""
    dist = {"2026-01": 4, "2026-02": 2, "2026-03": 1}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2)
    assert trend == ObservedTrend.DECREASING


def test_trend_constant_stable():
    """Verify identical temporal counts across periods result in STABLE trend."""
    dist = {"2026-01": 2, "2026-02": 2, "2026-03": 2}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2)
    assert trend == ObservedTrend.STABLE


def test_trend_insufficient_single_period():
    """Verify single observation period results in INSUFFICIENT_DATA."""
    dist = {"2026-01": 5}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2)
    assert trend == ObservedTrend.INSUFFICIENT_DATA


def test_trend_empty_distribution():
    """Verify empty dictionary results in INSUFFICIENT_DATA."""
    trend = TrendEvaluator.evaluate_trend({}, min_periods=2)
    assert trend == ObservedTrend.INSUFFICIENT_DATA


def test_trend_two_periods_increasing():
    """Verify 2 periods with growth evaluate to INCREASING."""
    dist = {"2026-01": 2, "2026-02": 5}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2)
    assert trend == ObservedTrend.INCREASING


def test_trend_two_periods_decreasing():
    """Verify 2 periods with drop evaluate to DECREASING."""
    dist = {"2026-01": 5, "2026-02": 1}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2)
    assert trend == ObservedTrend.DECREASING


def test_trend_configurable_min_periods():
    """Verify configurable min_periods parameter."""
    dist = {"2026-01": 1, "2026-02": 2}
    # With min_periods=3, 2 periods must yield INSUFFICIENT_DATA
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=3)
    assert trend == ObservedTrend.INSUFFICIENT_DATA


def test_trend_exactly_increase_threshold():
    """Verify non-monotonic distribution with ratio exactly at increase_ratio (1.25) evaluates to INCREASING."""
    # baseline [4, 4] mean = 4.0; recent [3, 7] mean = 5.0; ratio = 5.0 / 4.0 = 1.25
    dist = {"2026-01": 4, "2026-02": 4, "2026-03": 3, "2026-04": 7}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2, increase_ratio=1.25, decrease_ratio=0.80)
    assert trend == ObservedTrend.INCREASING


def test_trend_just_above_increase_threshold():
    """Verify non-monotonic distribution with ratio just above increase_ratio (1.25) evaluates to INCREASING."""
    # baseline [4, 4] mean = 4.0; recent [3, 8] mean = 5.5; ratio = 5.5 / 4.0 = 1.375 > 1.25
    dist = {"2026-01": 4, "2026-02": 4, "2026-03": 3, "2026-04": 8}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2, increase_ratio=1.25, decrease_ratio=0.80)
    assert trend == ObservedTrend.INCREASING


def test_trend_just_below_increase_threshold():
    """Verify non-monotonic distribution with ratio just below increase_ratio (1.25) evaluates to STABLE."""
    # baseline [4, 4] mean = 4.0; recent [3, 6] mean = 4.5; ratio = 4.5 / 4.0 = 1.125 < 1.25
    dist = {"2026-01": 4, "2026-02": 4, "2026-03": 3, "2026-04": 6}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2, increase_ratio=1.25, decrease_ratio=0.80)
    assert trend == ObservedTrend.STABLE


def test_trend_exactly_decrease_threshold():
    """Verify non-monotonic distribution with ratio exactly at decrease_ratio (0.80) evaluates to DECREASING."""
    # baseline [5, 5] mean = 5.0; recent [6, 2] mean = 4.0; ratio = 4.0 / 5.0 = 0.80
    dist = {"2026-01": 5, "2026-02": 5, "2026-03": 6, "2026-04": 2}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2, increase_ratio=1.25, decrease_ratio=0.80)
    assert trend == ObservedTrend.DECREASING


def test_trend_just_below_decrease_threshold():
    """Verify non-monotonic distribution with ratio just below decrease_ratio (0.80) evaluates to DECREASING."""
    # baseline [5, 5] mean = 5.0; recent [6, 1] mean = 3.5; ratio = 3.5 / 5.0 = 0.70 < 0.80
    dist = {"2026-01": 5, "2026-02": 5, "2026-03": 6, "2026-04": 1}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2, increase_ratio=1.25, decrease_ratio=0.80)
    assert trend == ObservedTrend.DECREASING


def test_trend_just_above_decrease_threshold():
    """Verify non-monotonic distribution with ratio just above decrease_ratio (0.80) evaluates to STABLE."""
    # baseline [5, 5] mean = 5.0; recent [6, 3] mean = 4.5; ratio = 4.5 / 5.0 = 0.90 > 0.80
    dist = {"2026-01": 5, "2026-02": 5, "2026-03": 6, "2026-04": 3}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2, increase_ratio=1.25, decrease_ratio=0.80)
    assert trend == ObservedTrend.STABLE


def test_trend_zero_baseline_with_recent_activity():
    """Verify zero baseline with subsequent positive activity evaluates to INCREASING."""
    dist = {"2026-01": 0, "2026-02": 0, "2026-03": 1, "2026-04": 2}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2)
    assert trend == ObservedTrend.INCREASING


def test_trend_zero_baseline_all_zeros():
    """Verify zero count across all periods evaluates to STABLE."""
    dist = {"2026-01": 0, "2026-02": 0, "2026-03": 0}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2)
    assert trend == ObservedTrend.STABLE


def test_trend_sparse_non_consecutive_periods():
    """Verify sparse/non-consecutive period keys are ordered chronologically and evaluated deterministically."""
    dist = {"2026-01": 2, "2026-07": 4, "2026-11": 6}
    trend = TrendEvaluator.evaluate_trend(dist, min_periods=2)
    assert trend == ObservedTrend.INCREASING


def test_trend_evaluation_determinism():
    """Verify evaluation is 100% deterministic across repeated runs."""
    dist = {"2026-01": 3, "2026-02": 1, "2026-03": 4, "2026-04": 2}
    results = [TrendEvaluator.evaluate_trend(dist, min_periods=2) for _ in range(50)]
    assert all(r == results[0] for r in results)

