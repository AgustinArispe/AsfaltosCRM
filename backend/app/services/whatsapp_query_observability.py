from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Protocol


class WhatsAppQueryMetricName(StrEnum):
    DURATION_SECONDS = "whatsapp_query_duration_seconds"
    ROWS_RETURNED = "whatsapp_query_rows_returned"
    DB_STATEMENTS_TOTAL = "whatsapp_query_db_statements_total"
    CURSOR_REJECTIONS_TOTAL = "whatsapp_query_cursor_rejections_total"
    ERRORS_TOTAL = "whatsapp_query_errors_total"
    PROJECTION_MAPPING_ERRORS_TOTAL = "whatsapp_query_projection_mapping_errors_total"


class WhatsAppQueryOperation(StrEnum):
    CONVERSATION_LIST = "conversation_list"
    CONVERSATION_DETAIL = "conversation_detail"
    MESSAGE_HISTORY = "message_history"
    POLLING = "polling"


class WhatsAppQueryOutcome(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


class WhatsAppQueryErrorCategory(StrEnum):
    NOT_FOUND = "not_found"
    DATABASE = "database"
    PROJECTION = "projection"
    INTERNAL = "internal"


class WhatsAppCursorKind(StrEnum):
    CONVERSATION_PAGE = "conversation_page"
    MESSAGE_PAGE = "message_page"
    CONVERSATION_CHANGES = "conversation_changes"
    MESSAGE_CHANGES = "message_changes"


class WhatsAppCursorRejectionReason(StrEnum):
    MALFORMED = "malformed"
    UNSUPPORTED_VERSION = "unsupported_version"
    INVALID_VALUE = "invalid_value"


class WhatsAppProjectionType(StrEnum):
    CONVERSATION_SUMMARY = "conversation_summary"
    CONVERSATION_DETAIL = "conversation_detail"
    MESSAGE = "message"


@dataclass(frozen=True, slots=True)
class QueryMeasurement:
    metric_names: ClassVar[tuple[WhatsAppQueryMetricName, ...]] = (
        WhatsAppQueryMetricName.DURATION_SECONDS,
        WhatsAppQueryMetricName.ROWS_RETURNED,
        WhatsAppQueryMetricName.DB_STATEMENTS_TOTAL,
    )
    operation: WhatsAppQueryOperation
    outcome: WhatsAppQueryOutcome
    duration_seconds: float
    rows_returned: int
    db_statements: int


@dataclass(frozen=True, slots=True)
class CursorRejectionMeasurement:
    metric_name: ClassVar[WhatsAppQueryMetricName] = (
        WhatsAppQueryMetricName.CURSOR_REJECTIONS_TOTAL
    )
    cursor_kind: WhatsAppCursorKind
    reason: WhatsAppCursorRejectionReason


@dataclass(frozen=True, slots=True)
class QueryErrorMeasurement:
    metric_name: ClassVar[WhatsAppQueryMetricName] = (
        WhatsAppQueryMetricName.ERRORS_TOTAL
    )
    operation: WhatsAppQueryOperation
    category: WhatsAppQueryErrorCategory


class WhatsAppQueryMetrics(Protocol):
    def record_query(self, measurement: QueryMeasurement) -> None: ...

    def record_cursor_rejection(
        self,
        measurement: CursorRejectionMeasurement,
    ) -> None: ...

    def record_error(self, measurement: QueryErrorMeasurement) -> None: ...

    def record_projection_mapping_error(
        self,
        projection_type: WhatsAppProjectionType,
    ) -> None: ...


class NullWhatsAppQueryMetrics:
    def record_query(self, measurement: QueryMeasurement) -> None:
        del measurement

    def record_cursor_rejection(
        self,
        measurement: CursorRejectionMeasurement,
    ) -> None:
        del measurement

    def record_error(self, measurement: QueryErrorMeasurement) -> None:
        del measurement

    def record_projection_mapping_error(
        self,
        projection_type: WhatsAppProjectionType,
    ) -> None:
        del projection_type


class RecordingWhatsAppQueryMetrics:
    """Typed in-memory metric sink for tests and future exporter adapters."""

    def __init__(self) -> None:
        self._queries: list[QueryMeasurement] = []
        self._cursor_rejections: list[CursorRejectionMeasurement] = []
        self._errors: list[QueryErrorMeasurement] = []
        self._projection_mapping_errors: list[WhatsAppProjectionType] = []

    @property
    def queries(self) -> tuple[QueryMeasurement, ...]:
        return tuple(self._queries)

    @property
    def cursor_rejections(self) -> tuple[CursorRejectionMeasurement, ...]:
        return tuple(self._cursor_rejections)

    @property
    def errors(self) -> tuple[QueryErrorMeasurement, ...]:
        return tuple(self._errors)

    @property
    def projection_mapping_errors(self) -> tuple[WhatsAppProjectionType, ...]:
        return tuple(self._projection_mapping_errors)

    def record_query(self, measurement: QueryMeasurement) -> None:
        self._queries.append(measurement)

    def record_cursor_rejection(
        self,
        measurement: CursorRejectionMeasurement,
    ) -> None:
        self._cursor_rejections.append(measurement)

    def record_error(self, measurement: QueryErrorMeasurement) -> None:
        self._errors.append(measurement)

    def record_projection_mapping_error(
        self,
        projection_type: WhatsAppProjectionType,
    ) -> None:
        self._projection_mapping_errors.append(projection_type)
