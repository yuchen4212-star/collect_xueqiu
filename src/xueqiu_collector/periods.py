from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional


CHINA_TZ = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class PeriodWindow:
    key: str
    label: str
    start_local: datetime
    end_local: datetime

    @property
    def start_utc(self) -> datetime:
        return self.start_local.astimezone(timezone.utc)

    @property
    def end_utc(self) -> datetime:
        return self.end_local.astimezone(timezone.utc)


PERIOD_CHOICES = ("auto", "overnight", "morning", "midday", "evening")


def _local_now(now: Optional[datetime]) -> datetime:
    current = now or datetime.now(CHINA_TZ)
    if current.tzinfo is None:
        return current.replace(tzinfo=CHINA_TZ)
    return current.astimezone(CHINA_TZ)


def _parse_report_date(report_date: Optional[str], fallback: date) -> date:
    if report_date:
        return date.fromisoformat(report_date)
    return fallback


def _combine(day: date, value: time) -> datetime:
    return datetime.combine(day, value).replace(tzinfo=CHINA_TZ)


def _window_for_key(key: str, day: date) -> PeriodWindow:
    if key == "overnight":
        return PeriodWindow(
            key=key,
            label="00:00-09:30",
            start_local=_combine(day, time(0, 0)),
            end_local=_combine(day, time(9, 30)),
        )
    if key == "morning":
        return PeriodWindow(
            key=key,
            label="09:30-12:30",
            start_local=_combine(day, time(9, 30)),
            end_local=_combine(day, time(12, 30)),
        )
    if key == "midday":
        return PeriodWindow(
            key=key,
            label="12:30-14:50",
            start_local=_combine(day, time(12, 30)),
            end_local=_combine(day, time(14, 50)),
        )
    if key == "evening":
        return PeriodWindow(
            key=key,
            label="14:50-24:00",
            start_local=_combine(day, time(14, 50)),
            end_local=_combine(day + timedelta(days=1), time(0, 0)),
        )
    raise ValueError("unknown period {}".format(key))


def _last_completed_key(local: datetime) -> str:
    current_time = local.time()
    if current_time >= time(14, 50):
        return "midday"
    if current_time >= time(12, 30):
        return "morning"
    if current_time >= time(9, 30):
        return "overnight"
    return "evening"


def resolve_period_window(
    period: str,
    now: Optional[datetime] = None,
    report_date: Optional[str] = None,
) -> PeriodWindow:
    local = _local_now(now)
    key = _last_completed_key(local) if period == "auto" else period
    if key not in PERIOD_CHOICES or key == "auto":
        raise ValueError("unsupported period {}".format(period))

    fallback_date = local.date()
    if key == "evening" and not report_date:
        fallback_date = fallback_date - timedelta(days=1)

    return _window_for_key(key, _parse_report_date(report_date, fallback_date))
