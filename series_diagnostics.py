"""Isolated, bounded diagnostics for the series maintenance page."""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

PLUGIN_ID = "astrbot_plugin_update_manager"
PLUGIN_NAME = "核"
DIAGNOSTIC_CONTRACT = "series.diagnostics@1.0"
_MAX_EVENTS = 1000
_SENSITIVE_KEY = re.compile(
    r"(?i)(?:^|[_-])(?:token|api[_-]?key|secret|password|authorization|cookie|"
    r"jwt|private[_-]?key|ssh[_-]?key|provider[_-]?key|bridge[_-]?key)(?:$|[_-])"
)
_SECRET_VALUE = re.compile(
    r"(?i)(token|api[_-]?key|secret|password|authorization|cookie|jwt|"
    r"private[_-]?key|ssh[_-]?key|provider[_-]?key|bridge[_-]?key)"
    r"(?:\s*[:=]\s*|\s+)"
    r"(?:bearer\s+)?([^,\s]+)"
)


def _safe_text(value: Any, *, limit: int | None = None) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    text = _SECRET_VALUE.sub(r"\1=<已隐藏>", text)
    return (
        text if limit is None or len(text) <= limit else text[: max(1, limit - 1)] + "…"
    )


def _safe_value(value: Any, *, key: str = "") -> Any:
    """Preserve diagnostic data while masking only credential values."""
    if _SENSITIVE_KEY.search(key):
        if isinstance(value, (bool, int, float)) or value is None:
            return value
        return "<已隐藏凭据>"
    if isinstance(value, dict):
        return {
            str(name)[:256]: _safe_value(item, key=str(name))
            for name, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe_value(item) for item in value]
    if isinstance(value, bytes):
        return _safe_text(value.decode(errors="replace"))
    if isinstance(value, str):
        return _safe_text(value)
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return _safe_text(value)


def _safe_details(details: Any) -> dict[str, Any]:
    if not isinstance(details, dict):
        return {}
    return {
        str(key)[:256]: _safe_value(value, key=str(key))
        for key, value in details.items()
    }


class DiagnosticBuffer(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self._events: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)
        self._stream_id = uuid.uuid4().hex
        self._sequence = 0
        self._lock = threading.Lock()

    def append(
        self, level: str, code: str, summary: Any, details: Any = None
    ) -> dict[str, Any]:
        with self._lock:
            self._sequence += 1
            event = {
                "seq": self._sequence,
                "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
                "plugin_id": PLUGIN_ID,
                "plugin_name": PLUGIN_NAME,
                "level": str(level).upper(),
                "code": _safe_text(code, limit=80),
                "summary": _safe_text(summary),
                "details": _safe_details(details),
            }
            self._events.append(event)
            return event

    def emit(self, record: logging.LogRecord) -> None:
        if not record.name or not record.name.startswith(PLUGIN_ID):
            return
        try:
            module = _safe_text(record.module or "plugin", limit=40)
            details: dict[str, Any] = {
                "module": module,
                "function": _safe_text(record.funcName or "", limit=60),
                "line": max(0, int(record.lineno or 0)),
            }
            if record.getMessage():
                details["log_detail"] = _safe_text(record.getMessage())
            if record.exc_info and record.exc_info[0] is not None:
                details["exception_type"] = record.exc_info[0].__name__
            self.append(
                record.levelname,
                f"logger.{record.levelname.lower()}.{module}",
                f"{module} recorded a {record.levelname} diagnostic event",
                details,
            )
        except Exception:
            pass

    def snapshot(self, *, after_seq: int = 0, limit: int = 200) -> dict[str, Any]:
        after, size = max(0, int(after_seq or 0)), min(1000, max(1, int(limit or 200)))
        with self._lock:
            events = [item for item in self._events if item["seq"] > after][-size:]
            first = self._events[0]["seq"] if self._events else self._sequence + 1
            return {
                "contract": DIAGNOSTIC_CONTRACT,
                "plugin_id": PLUGIN_ID,
                "plugin_name": PLUGIN_NAME,
                "stream_id": self._stream_id,
                "events": events,
                "next_seq": self._sequence,
                "dropped_before": max(0, first - 1),
            }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._stream_id = uuid.uuid4().hex


_buffer = DiagnosticBuffer()
logger = logging.getLogger(PLUGIN_ID)
logger.setLevel(logging.DEBUG)


def isolate_logger() -> None:
    logger.propagate = False
    for handler in list(logger.handlers):
        if not isinstance(handler, (logging.NullHandler, DiagnosticBuffer)):
            logger.removeHandler(handler)
    if not any(isinstance(handler, logging.NullHandler) for handler in logger.handlers):
        logger.addHandler(logging.NullHandler())
    if _buffer not in logger.handlers:
        logger.addHandler(_buffer)


isolate_logger()


def diagnostic_event(
    code: str, summary: Any, *, level: str = "INFO", details: Any = None
) -> dict[str, Any]:
    isolate_logger()
    return _buffer.append(level, code, summary, details)


class DiagnosticOperation:
    """Bounded breadcrumb-style timeline for one internal operation."""

    def __init__(
        self,
        component: str,
        operation: str,
        summary: str,
        *,
        level: str = "INFO",
        details: dict[str, Any] | None = None,
        emit_start: bool = True,
    ) -> None:
        self.component = _safe_text(component, limit=40)
        self.operation = _safe_text(operation, limit=80)
        self.summary = _safe_text(summary, limit=240)
        self.level = level
        self.operation_ref = uuid.uuid4().hex[:12]
        self.started = time.monotonic()
        self.finished = False
        self.details = dict(details or {})
        if emit_start:
            self.event("started", f"{self.summary}开始")

    def _details(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            **self.details,
            **(extra or {}),
            "component": self.component,
            "operation": self.operation,
            "operation_ref": self.operation_ref,
        }

    def event(
        self,
        phase: str,
        summary: str,
        *,
        level: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return diagnostic_event(
            f"{self.component}.{self.operation}.{phase}",
            summary,
            level=level or self.level,
            details=self._details(details),
        )

    def finish(
        self,
        *,
        outcome: str = "success",
        summary: str | None = None,
        level: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if self.finished:
            return None
        self.finished = True
        return self.event(
            "completed",
            summary or f"{self.summary}完成",
            level=level,
            details={
                **(details or {}),
                "outcome": outcome,
                "duration_ms": round((time.monotonic() - self.started) * 1000, 3),
            },
        )

    def fail(
        self,
        error: BaseException,
        *,
        summary: str | None = None,
        reason: str = "OPERATION_FAILED",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if self.finished:
            return None
        self.finished = True
        return self.event(
            "failed",
            summary or f"{self.summary}失败",
            level="ERROR",
            details={
                **(details or {}),
                "outcome": "failed",
                "reason": reason,
                "error_type": type(error).__name__,
                "duration_ms": round((time.monotonic() - self.started) * 1000, 3),
            },
        )


def diagnostic_operation(
    component: str,
    operation: str,
    summary: str,
    *,
    level: str = "INFO",
    details: dict[str, Any] | None = None,
    emit_start: bool = True,
) -> DiagnosticOperation:
    isolate_logger()
    return DiagnosticOperation(
        component,
        operation,
        summary,
        level=level,
        details=details,
        emit_start=emit_start,
    )


def diagnostic_events(*, after_seq: int = 0, limit: int = 200) -> dict[str, Any]:
    return _buffer.snapshot(after_seq=after_seq, limit=limit)


def diagnostic_clear() -> None:
    _buffer.clear()
