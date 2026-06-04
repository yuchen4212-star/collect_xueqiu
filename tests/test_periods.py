from datetime import datetime, timezone

from xueqiu_collector.periods import CHINA_TZ, resolve_period_window


def test_auto_period_at_0930_reports_overnight_window():
    window = resolve_period_window(
        "auto", now=datetime(2026, 6, 4, 9, 30, tzinfo=CHINA_TZ)
    )

    assert window.key == "overnight"
    assert window.start_local.isoformat() == "2026-06-04T00:00:00+08:00"
    assert window.end_local.isoformat() == "2026-06-04T09:30:00+08:00"
    assert window.start_utc.isoformat() == "2026-06-03T16:00:00+00:00"
    assert window.end_utc.isoformat() == "2026-06-04T01:30:00+00:00"


def test_auto_period_at_midnight_reports_previous_evening_window():
    window = resolve_period_window(
        "auto", now=datetime(2026, 6, 4, 0, 3, tzinfo=CHINA_TZ)
    )

    assert window.key == "evening"
    assert window.start_local.isoformat() == "2026-06-03T14:50:00+08:00"
    assert window.end_local.isoformat() == "2026-06-04T00:00:00+08:00"


def test_explicit_evening_defaults_to_last_completed_evening_window():
    window = resolve_period_window(
        "evening", now=datetime(2026, 6, 4, 10, 0, tzinfo=CHINA_TZ)
    )

    assert window.start_local.isoformat() == "2026-06-03T14:50:00+08:00"
    assert window.end_local.isoformat() == "2026-06-04T00:00:00+08:00"


def test_explicit_period_uses_requested_report_date():
    window = resolve_period_window(
        "midday",
        now=datetime(2026, 6, 4, 6, 50, tzinfo=timezone.utc),
        report_date="2026-06-03",
    )

    assert window.key == "midday"
    assert window.start_local.isoformat() == "2026-06-03T12:30:00+08:00"
    assert window.end_local.isoformat() == "2026-06-03T14:50:00+08:00"
