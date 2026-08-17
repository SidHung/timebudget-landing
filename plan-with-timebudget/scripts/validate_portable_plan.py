#!/usr/bin/env python3
"""Validate TimeBudget portable plan 1.0.0 without third-party packages."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_BYTES = 256 * 1024
MAX_TASKS = 200
MAX_RESERVES = 50
MAX_TITLE = 200
MAX_ID = 128
MAX_DURATION = 1440
SUPPORTED_VERSIONS = {"1.0.0"}

MINUTE_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00(?:Z|[+-]\d{2}:\d{2})$"
)
AUDIT_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FORBIDDEN_TEXT_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
STRICT_TEXT_RE = re.compile(r"[\x00-\x1f\x7f]")

TOP_KEYS = {
    "format",
    "schema_version",
    "revision",
    "exported_at",
    "plan",
    "reserves",
    "tasks",
    "snapshot",
}
PLAN_KEYS = {
    "id",
    "date",
    "timezone",
    "start_at",
    "end_at",
    "lifecycle_status",
    "closed_at",
    "close_reason",
    "buffer_original_minutes",
    "buffer_target_minutes",
}
RESERVE_KEYS = {
    "id",
    "type",
    "title",
    "minutes",
    "status",
    "start_at",
    "end_at",
    "remaining_minutes",
    "actual_minutes",
    "consumed_at",
}
TASK_KEYS = {
    "id",
    "title",
    "priority",
    "status",
    "baseline_estimated_minutes",
    "estimate_source",
    "estimate_range_minutes",
    "actual_minutes",
    "actual_source",
    "remaining_estimate_minutes",
    "not_before_at",
    "deadline_at",
    "completed_at",
    "carried_from_plan_id",
    "carried_from_task_id",
}
SNAPSHOT_KEYS = {
    "as_of",
    "total_plan_minutes",
    "clock_minutes_remaining",
    "unfinished_estimated_minutes",
    "pending_reserve_minutes",
    "raw_slack_minutes",
    "buffer_target_minutes",
    "safe_slack_minutes",
    "capacity_status",
}


class DuplicateKeyError(ValueError):
    pass


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_plan(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError(f"artifact exceeds {MAX_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("artifact must be UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_no_duplicates,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite number is not allowed: {token}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}") from exc
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def _expect_object(value: Any, path: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return None
    return value


def _expect_exact_keys(value: dict[str, Any], keys: set[str], path: str, errors: list[str]) -> None:
    missing = keys - value.keys()
    extra = value.keys() - keys
    if missing:
        errors.append(f"{path} missing required properties: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"{path} has unsupported properties: {', '.join(sorted(extra))}")


def _expect_enum(value: Any, allowed: set[str], path: str, errors: list[str]) -> None:
    if value not in allowed:
        errors.append(f"{path} must be one of {', '.join(sorted(allowed))}")


def _expect_int(
    value: Any,
    path: str,
    errors: list[str],
    minimum: int = 0,
    maximum: int | None = None,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{path} must be an integer")
        return
    if value < minimum:
        errors.append(f"{path} must be at least {minimum}")
    if maximum is not None and value > maximum:
        errors.append(f"{path} must be at most {maximum}")


def _expect_nullable_int(
    value: Any, path: str, errors: list[str], maximum: int = MAX_DURATION
) -> None:
    if value is not None:
        _expect_int(value, path, errors, maximum=maximum)


def _expect_text(value: Any, path: str, errors: list[str], maximum: int, strict: bool = True) -> None:
    if not isinstance(value, str):
        errors.append(f"{path} must be a string")
        return
    if not value:
        errors.append(f"{path} must not be empty")
    if len(value) > maximum:
        errors.append(f"{path} exceeds {maximum} characters")
    matcher = STRICT_TEXT_RE if strict else FORBIDDEN_TEXT_RE
    if matcher.search(value):
        errors.append(f"{path} contains forbidden control characters")


def _parse_timestamp(
    value: Any, path: str, errors: list[str], *, minute_aligned: bool, nullable: bool = False
) -> datetime | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        errors.append(f"{path} must be an ISO 8601 timestamp string")
        return None
    pattern = MINUTE_TIMESTAMP_RE if minute_aligned else AUDIT_TIMESTAMP_RE
    if not pattern.fullmatch(value):
        label = "minute-aligned " if minute_aligned else ""
        errors.append(f"{path} must be a {label}ISO 8601 timestamp with an explicit offset")
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{path} is not a valid calendar timestamp")
        return None


def _timestamp_matches_zone(value: datetime, zone: ZoneInfo) -> bool:
    round_tripped = value.astimezone(timezone.utc).astimezone(zone)
    return (
        round_tripped.replace(tzinfo=None) == value.replace(tzinfo=None)
        and round_tripped.utcoffset() == value.utcoffset()
    )


def _minutes_between(start: datetime, end: datetime) -> int:
    return math.floor((end.timestamp() - start.timestamp()) / 60)


def _validate_global_strings(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, str) and FORBIDDEN_TEXT_RE.search(value):
        errors.append(f"{path} contains forbidden control characters")
    elif isinstance(value, dict):
        for key, child in value.items():
            _validate_global_strings(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_global_strings(child, f"{path}[{index}]", errors)


def _validate_plan_fields(data: dict[str, Any], errors: list[str]) -> tuple[datetime | None, datetime | None, ZoneInfo | None]:
    plan = _expect_object(data.get("plan"), "plan", errors)
    if plan is None:
        return None, None, None
    _expect_exact_keys(plan, PLAN_KEYS, "plan", errors)
    _expect_text(plan.get("id"), "plan.id", errors, MAX_ID)
    _expect_enum(plan.get("lifecycle_status"), {"draft", "active", "closed"}, "plan.lifecycle_status", errors)
    _expect_int(plan.get("buffer_original_minutes"), "plan.buffer_original_minutes", errors, maximum=MAX_DURATION)
    _expect_int(plan.get("buffer_target_minutes"), "plan.buffer_target_minutes", errors, maximum=MAX_DURATION)

    date_value = plan.get("date")
    if not isinstance(date_value, str) or not DATE_RE.fullmatch(date_value):
        errors.append("plan.date must be YYYY-MM-DD")
    else:
        try:
            datetime.strptime(date_value, "%Y-%m-%d")
        except ValueError:
            errors.append("plan.date is not a valid calendar date")

    zone: ZoneInfo | None = None
    zone_name = plan.get("timezone")
    if not isinstance(zone_name, str):
        errors.append("plan.timezone must be an IANA timezone string")
    else:
        try:
            zone = ZoneInfo(zone_name)
        except ZoneInfoNotFoundError:
            errors.append("plan.timezone is not a recognized IANA timezone")

    start = _parse_timestamp(plan.get("start_at"), "plan.start_at", errors, minute_aligned=True)
    end = _parse_timestamp(plan.get("end_at"), "plan.end_at", errors, minute_aligned=True)
    if start and end:
        window = _minutes_between(start, end)
        if window <= 0:
            errors.append("planning window must end after it starts")
        elif window > MAX_DURATION:
            errors.append("planning window must not exceed 1440 minutes")
    if zone and start:
        if not _timestamp_matches_zone(start, zone):
            errors.append("plan.start_at offset or local time is inconsistent with plan.timezone")
        elif isinstance(date_value, str) and start.astimezone(zone).date().isoformat() != date_value:
            errors.append("plan.date must equal the local calendar date of plan.start_at")
    if zone and end and not _timestamp_matches_zone(end, zone):
        errors.append("plan.end_at offset or local time is inconsistent with plan.timezone")

    lifecycle = plan.get("lifecycle_status")
    closed_at = _parse_timestamp(plan.get("closed_at"), "plan.closed_at", errors, minute_aligned=False, nullable=True)
    close_reason = plan.get("close_reason")
    if lifecycle == "closed":
        if closed_at is None:
            errors.append("closed plan requires plan.closed_at")
        _expect_enum(close_reason, {"all_resolved", "user_ended", "window_ended"}, "plan.close_reason", errors)
    elif closed_at is not None or close_reason is not None:
        errors.append("non-closed plan must have null closed_at and close_reason")
    return start, end, zone


def _validate_reserves(
    data: dict[str, Any],
    start: datetime | None,
    end: datetime | None,
    zone: ZoneInfo | None,
    errors: list[str],
) -> set[str]:
    reserves = data.get("reserves")
    if not isinstance(reserves, list):
        errors.append("reserves must be an array")
        return set()
    if len(reserves) > MAX_RESERVES:
        errors.append(f"reserves must contain no more than {MAX_RESERVES} items")
    ids: set[str] = set()
    for index, item in enumerate(reserves):
        path = f"reserves[{index}]"
        reserve = _expect_object(item, path, errors)
        if reserve is None:
            continue
        _expect_exact_keys(reserve, RESERVE_KEYS, path, errors)
        reserve_id = reserve.get("id")
        _expect_text(reserve_id, f"{path}.id", errors, MAX_ID)
        if isinstance(reserve_id, str):
            if reserve_id in ids:
                errors.append(f"duplicate reserve id: {reserve_id!r}")
            ids.add(reserve_id)
        _expect_text(reserve.get("title"), f"{path}.title", errors, MAX_TITLE)
        _expect_enum(reserve.get("type"), {"meal", "break", "fixed_commitment"}, f"{path}.type", errors)
        status = reserve.get("status")
        _expect_enum(status, {"planned", "in_progress", "consumed", "skipped", "cancelled"}, f"{path}.status", errors)
        _expect_int(reserve.get("minutes"), f"{path}.minutes", errors, maximum=MAX_DURATION)
        _expect_int(reserve.get("remaining_minutes"), f"{path}.remaining_minutes", errors, maximum=MAX_DURATION)
        _expect_nullable_int(reserve.get("actual_minutes"), f"{path}.actual_minutes", errors)

        reserve_start = _parse_timestamp(reserve.get("start_at"), f"{path}.start_at", errors, minute_aligned=True, nullable=True)
        reserve_end = _parse_timestamp(reserve.get("end_at"), f"{path}.end_at", errors, minute_aligned=True, nullable=True)
        if (reserve_start is None) != (reserve_end is None):
            errors.append(f"{path}.start_at and end_at must both be timestamps or both be null")
        if reserve_start and reserve_end:
            if zone and not _timestamp_matches_zone(reserve_start, zone):
                errors.append(f"{path}.start_at is inconsistent with plan.timezone")
            if zone and not _timestamp_matches_zone(reserve_end, zone):
                errors.append(f"{path}.end_at is inconsistent with plan.timezone")
            if start and reserve_start < start:
                errors.append(f"{path} starts before the planning window")
            if end and reserve_end > end:
                errors.append(f"{path} ends after the planning window")
            minutes = _minutes_between(reserve_start, reserve_end)
            if minutes < 0 or minutes != reserve.get("minutes"):
                errors.append(f"{path}.minutes must equal the whole-minute scheduled duration")

        consumed_at = _parse_timestamp(
            reserve.get("consumed_at"), f"{path}.consumed_at", errors, minute_aligned=False, nullable=True
        )
        if status == "consumed":
            if reserve.get("remaining_minutes") != 0:
                errors.append(f"{path} consumed reserve must have zero remaining_minutes")
            if consumed_at is None:
                errors.append(f"{path} consumed reserve requires consumed_at")
        elif consumed_at is not None:
            errors.append(f"{path} non-consumed reserve must have null consumed_at")
        if status in {"skipped", "cancelled"} and reserve.get("remaining_minutes") != 0:
            errors.append(f"{path} {status} reserve must have zero remaining_minutes")
        if (
            status in {"planned", "in_progress"}
            and isinstance(reserve.get("remaining_minutes"), int)
            and not isinstance(reserve.get("remaining_minutes"), bool)
            and isinstance(reserve.get("minutes"), int)
            and not isinstance(reserve.get("minutes"), bool)
            and reserve["remaining_minutes"] > reserve["minutes"]
        ):
            errors.append(f"{path}.remaining_minutes must not exceed minutes")
    return ids


def _validate_tasks(
    data: dict[str, Any], used_ids: set[str], zone: ZoneInfo | None, errors: list[str]
) -> None:
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks must be an array")
        return
    if len(tasks) > MAX_TASKS:
        errors.append(f"tasks must contain no more than {MAX_TASKS} items")
    for index, item in enumerate(tasks):
        path = f"tasks[{index}]"
        task = _expect_object(item, path, errors)
        if task is None:
            continue
        _expect_exact_keys(task, TASK_KEYS, path, errors)
        task_id = task.get("id")
        _expect_text(task_id, f"{path}.id", errors, MAX_ID)
        if isinstance(task_id, str):
            if task_id in used_ids:
                errors.append(f"duplicate task or reserve id: {task_id!r}")
            used_ids.add(task_id)
        _expect_text(task.get("title"), f"{path}.title", errors, MAX_TITLE)
        _expect_enum(task.get("priority"), {"must", "should", "could"}, f"{path}.priority", errors)
        status = task.get("status")
        _expect_enum(status, {"planned", "in_progress", "completed", "deferred", "cancelled"}, f"{path}.status", errors)
        _expect_int(task.get("baseline_estimated_minutes"), f"{path}.baseline_estimated_minutes", errors, maximum=MAX_DURATION)
        _expect_int(task.get("remaining_estimate_minutes"), f"{path}.remaining_estimate_minutes", errors, maximum=MAX_DURATION)
        _expect_nullable_int(task.get("actual_minutes"), f"{path}.actual_minutes", errors)

        estimate_source = task.get("estimate_source")
        _expect_enum(estimate_source, {"user", "ai_suggested"}, f"{path}.estimate_source", errors)
        estimate_range = task.get("estimate_range_minutes")
        if estimate_range is not None:
            if estimate_source != "ai_suggested":
                errors.append(f"{path}.estimate_range_minutes is only valid for ai_suggested estimates")
            range_object = _expect_object(estimate_range, f"{path}.estimate_range_minutes", errors)
            if range_object is not None:
                _expect_exact_keys(range_object, {"min", "max"}, f"{path}.estimate_range_minutes", errors)
                _expect_int(range_object.get("min"), f"{path}.estimate_range_minutes.min", errors, maximum=MAX_DURATION)
                _expect_int(range_object.get("max"), f"{path}.estimate_range_minutes.max", errors, maximum=MAX_DURATION)
                if (
                    isinstance(range_object.get("min"), int)
                    and not isinstance(range_object.get("min"), bool)
                    and isinstance(range_object.get("max"), int)
                    and not isinstance(range_object.get("max"), bool)
                    and range_object["min"] > range_object["max"]
                ):
                    errors.append(f"{path}.estimate_range_minutes.min must not exceed max")

        actual = task.get("actual_minutes")
        actual_source = task.get("actual_source")
        if actual is None and actual_source is not None:
            errors.append(f"{path}.actual_source must be null when actual_minutes is null")
        if actual is not None and actual_source != "user_reported":
            errors.append(f"{path}.actual_source must be user_reported when actual_minutes exists")

        not_before = _parse_timestamp(
            task.get("not_before_at"), f"{path}.not_before_at", errors, minute_aligned=True, nullable=True
        )
        deadline = _parse_timestamp(
            task.get("deadline_at"), f"{path}.deadline_at", errors, minute_aligned=True, nullable=True
        )
        if zone and not_before and not _timestamp_matches_zone(not_before, zone):
            errors.append(f"{path}.not_before_at is inconsistent with plan.timezone")
        if zone and deadline and not _timestamp_matches_zone(deadline, zone):
            errors.append(f"{path}.deadline_at is inconsistent with plan.timezone")
        completed_at = _parse_timestamp(task.get("completed_at"), f"{path}.completed_at", errors, minute_aligned=False, nullable=True)
        if status == "completed":
            if task.get("remaining_estimate_minutes") != 0:
                errors.append(f"{path} completed task must have zero remaining_estimate_minutes")
            if completed_at is None:
                errors.append(f"{path} completed task requires completed_at")
        elif completed_at is not None:
            errors.append(f"{path} non-completed task must have null completed_at")
        if status in {"deferred", "cancelled"} and task.get("remaining_estimate_minutes") != 0:
            errors.append(f"{path} {status} task must have zero remaining_estimate_minutes")

        carried_plan = task.get("carried_from_plan_id")
        carried_task = task.get("carried_from_task_id")
        if (carried_plan is None) != (carried_task is None):
            errors.append(f"{path} carry provenance fields must both be strings or both be null")
        for key, value in (("carried_from_plan_id", carried_plan), ("carried_from_task_id", carried_task)):
            if value is not None:
                _expect_text(value, f"{path}.{key}", errors, MAX_ID)


def _validate_snapshot(data: dict[str, Any], errors: list[str]) -> None:
    snapshot = _expect_object(data.get("snapshot"), "snapshot", errors)
    if snapshot is None:
        return
    _expect_exact_keys(snapshot, SNAPSHOT_KEYS, "snapshot", errors)
    _parse_timestamp(snapshot.get("as_of"), "snapshot.as_of", errors, minute_aligned=False)
    _expect_int(snapshot.get("total_plan_minutes"), "snapshot.total_plan_minutes", errors, maximum=MAX_DURATION)
    _expect_nullable_int(snapshot.get("clock_minutes_remaining"), "snapshot.clock_minutes_remaining", errors)
    _expect_int(snapshot.get("unfinished_estimated_minutes"), "snapshot.unfinished_estimated_minutes", errors, maximum=MAX_TASKS * MAX_DURATION)
    _expect_int(snapshot.get("pending_reserve_minutes"), "snapshot.pending_reserve_minutes", errors, maximum=MAX_RESERVES * MAX_DURATION)
    for key in ("raw_slack_minutes", "safe_slack_minutes"):
        value = snapshot.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            errors.append(f"snapshot.{key} must be an integer or null")
    _expect_int(snapshot.get("buffer_target_minutes"), "snapshot.buffer_target_minutes", errors, maximum=MAX_DURATION)
    _expect_enum(
        snapshot.get("capacity_status"),
        {"not_evaluated", "healthy", "at_risk", "replan_required"},
        "snapshot.capacity_status",
        errors,
    )
    plan = data.get("plan")
    lifecycle = plan.get("lifecycle_status") if isinstance(plan, dict) else None
    if lifecycle == "closed" and snapshot.get("capacity_status") != "not_evaluated":
        errors.append("closed plan snapshot must use capacity_status not_evaluated")
    if snapshot.get("capacity_status") != "not_evaluated":
        for key in ("clock_minutes_remaining", "raw_slack_minutes", "safe_slack_minutes"):
            if snapshot.get(key) is None:
                errors.append(f"snapshot.{key} cannot be null when capacity is evaluated")
    else:
        for key in ("clock_minutes_remaining", "raw_slack_minutes", "safe_slack_minutes"):
            if snapshot.get(key) is not None:
                errors.append(f"snapshot.{key} must be null when capacity is not_evaluated")


def validate_plan(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _validate_global_strings(data, "$", errors)
    _expect_exact_keys(data, TOP_KEYS, "$", errors)
    if data.get("format") != "timebudget-plan":
        errors.append("format must equal timebudget-plan")
    if data.get("schema_version") not in SUPPORTED_VERSIONS:
        errors.append("schema_version is unsupported; supported versions: 1.0.0")
    _expect_int(data.get("revision"), "revision", errors)
    _parse_timestamp(data.get("exported_at"), "exported_at", errors, minute_aligned=False)
    start, end, zone = _validate_plan_fields(data, errors)
    reserve_ids = _validate_reserves(data, start, end, zone, errors)
    _validate_tasks(data, reserve_ids, zone, errors)
    _validate_snapshot(data, errors)
    return errors


def expected_snapshot(data: dict[str, Any]) -> dict[str, Any] | None:
    """Recalculate the convenience snapshot at its own as_of time.

    Return None when authoritative fields are invalid. This is a comparison aid, not
    an importer decision: importers should recalculate at their reliable current time.
    """

    if validate_plan(data):
        return None
    plan = data["plan"]
    supplied = data["snapshot"]
    as_of = datetime.fromisoformat(supplied["as_of"].replace("Z", "+00:00"))
    start = datetime.fromisoformat(plan["start_at"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(plan["end_at"].replace("Z", "+00:00"))
    total = _minutes_between(start, end)
    unfinished = sum(
        task["remaining_estimate_minutes"]
        for task in data["tasks"]
        if task["status"] in {"planned", "in_progress"}
    )

    pending = 0
    unresolved_reserve = False
    for reserve in data["reserves"]:
        status = reserve["status"]
        if status in {"consumed", "skipped", "cancelled"}:
            continue
        reserve_start = reserve["start_at"]
        reserve_end = reserve["end_at"]
        if status == "in_progress" and reserve_end is not None:
            parsed_end = datetime.fromisoformat(reserve_end.replace("Z", "+00:00"))
            pending += max(0, _minutes_between(as_of, parsed_end))
        elif status == "planned" and reserve_start is not None:
            parsed_start = datetime.fromisoformat(reserve_start.replace("Z", "+00:00"))
            parsed_end = datetime.fromisoformat(reserve_end.replace("Z", "+00:00"))
            if parsed_start <= as_of:
                unresolved_reserve = True
            else:
                pending += reserve["remaining_minutes"]
        else:
            pending += reserve["remaining_minutes"]

    lifecycle = plan["lifecycle_status"]
    expired_active = lifecycle == "active" and as_of >= end
    evaluated = lifecycle != "closed" and not unresolved_reserve and not expired_active
    clock: int | None
    raw: int | None
    safe: int | None
    if evaluated:
        clock = max(0, _minutes_between(max(as_of, start), end))
        raw = clock - unfinished - pending
        safe = raw - plan["buffer_target_minutes"]
        if raw < 0:
            status = "replan_required"
        elif raw < plan["buffer_target_minutes"]:
            status = "at_risk"
        else:
            status = "healthy"

        current = max(as_of, start)
        constrained = [
            task
            for task in data["tasks"]
            if task["status"] in {"planned", "in_progress"}
            and task["deadline_at"] is not None
            and task["not_before_at"] is None
        ]
        deadlines = sorted(
            {
                min(datetime.fromisoformat(task["deadline_at"].replace("Z", "+00:00")), end)
                for task in constrained
            }
        )
        for deadline in deadlines:
            task_demand = sum(
                task["remaining_estimate_minutes"]
                for task in constrained
                if min(datetime.fromisoformat(task["deadline_at"].replace("Z", "+00:00")), end)
                <= deadline
            )
            reserve_demand = 0
            for reserve in data["reserves"]:
                if reserve["status"] not in {"planned", "in_progress"} or reserve["start_at"] is None:
                    continue
                reserve_start = datetime.fromisoformat(reserve["start_at"].replace("Z", "+00:00"))
                reserve_end = datetime.fromisoformat(reserve["end_at"].replace("Z", "+00:00"))
                overlap_start = max(current, reserve_start)
                overlap_end = min(deadline, reserve_end)
                reserve_demand += max(0, _minutes_between(overlap_start, overlap_end))
            available = max(0, _minutes_between(current, deadline))
            if task_demand + reserve_demand > available:
                status = "replan_required"
                break
    else:
        clock = None
        raw = None
        safe = None
        status = "not_evaluated"

    return {
        "as_of": supplied["as_of"],
        "total_plan_minutes": total,
        "clock_minutes_remaining": clock,
        "unfinished_estimated_minutes": unfinished,
        "pending_reserve_minutes": pending,
        "raw_slack_minutes": raw,
        "buffer_target_minutes": plan["buffer_target_minutes"],
        "safe_slack_minutes": safe,
        "capacity_status": status,
    }


def snapshot_warnings(data: dict[str, Any]) -> Iterable[str]:
    expected = expected_snapshot(data)
    if expected is None:
        return []
    supplied = data["snapshot"]
    return [
        f"snapshot.{key} is stale or inconsistent (supplied {supplied.get(key)!r}, recalculated {value!r})"
        for key, value in expected.items()
        if supplied.get(key) != value
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="Path to a .timebudget.json file")
    args = parser.parse_args(argv)
    try:
        data = load_plan(args.artifact)
    except (OSError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    errors = validate_plan(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    for warning in snapshot_warnings(data):
        print(f"WARNING: {warning}", file=sys.stderr)
    print("VALID: TimeBudget portable plan 1.0.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
