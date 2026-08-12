from __future__ import annotations

import math
import os
import platform
import subprocess
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from statistics import median
from time import perf_counter
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict
from sqlalchemy import event, func, select, text

from app.db.session import SessionLocal, engine
from app.models import (
    LeadSource,
    Opportunity,
    Product,
    User,
    WhatsAppAttachment,
    WhatsAppBroadcast,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppMessageStatusEvent,
)
from app.services.metrics_service import (
    MetricsDimensions,
    MetricsFilters,
    MetricsPeriod,
    MetricsService,
    TimelineGranularity,
)
from app.services.whatsapp_broadcast_service import WhatsAppBroadcastService
from app.services.whatsapp_query_projections import (
    ChangePageRequest,
    ConversationListFilters,
    ConversationPageRequest,
    MessagePageCursor,
    MessagePageRequest,
    ResourceChangeCursor,
)
from app.services.whatsapp_query_service import (
    ConversationQueryService,
    MessageQueryService,
    PollingQueryService,
)
from app.whatsapp import (
    FakeMediaStorage,
    FakeWhatsAppProvider,
    ProviderTemplateSnapshot,
    TemplateHeaderType,
)


class PerformanceProfile(StrEnum):
    BASELINE = "baseline"
    LARGE = "large"


@dataclass(frozen=True, slots=True)
class ProfileDefinition:
    conversations: int
    messages: int
    status_events: int


PROFILES = {
    PerformanceProfile.BASELINE: ProfileDefinition(1_000, 10_000, 10_000),
    PerformanceProfile.LARGE: ProfileDefinition(10_000, 100_000, 100_000),
}
BENCHMARK_NOW = datetime(2025, 1, 1, tzinfo=UTC)
METRICS_START = datetime(2024, 1, 1, 3, tzinfo=UTC)
METRICS_END = datetime(2025, 1, 1, 3, tzinfo=UTC)


class BenchmarkSample(BaseModel):
    model_config = ConfigDict(frozen=True)

    duration_ms: float
    query_count: int
    rows_returned: int


class BenchmarkMeasurement(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation: str
    warmups: int
    samples: int
    query_count_min: int
    query_count_max: int
    rows_returned_min: int
    rows_returned_max: int
    p50_ms: float
    p95_ms: float
    max_ms: float
    observations: tuple[BenchmarkSample, ...]


class BenchmarkMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile: PerformanceProfile
    database: str
    postgres_version: str
    alembic_revision: str
    git_commit: str
    git_dirty: bool
    host: str
    seed: int
    conversations: int
    messages: int
    status_events: int
    attachments: int
    opportunities: int
    warmups: int
    samples: int
    command_arguments: tuple[str, ...]


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: BenchmarkMetadata
    measurements: tuple[BenchmarkMeasurement, ...]


@dataclass(frozen=True, slots=True)
class BenchmarkOperation:
    name: str
    execute: Callable[[], int]
    prepare: Callable[[], None] | None = None


@dataclass(slots=True)
class QueryCounter:
    count: int = 0


@contextmanager
def count_queries() -> Iterator[tuple[QueryCounter]]:
    counter = QueryCounter()

    def count_statement(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        normalized = statement.lstrip().upper()
        if normalized.startswith(("SELECT", "WITH")):
            counter.count += 1

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        yield (counter,)
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)


def run_operation(
    operation: BenchmarkOperation,
    *,
    warmups: int,
    samples: int,
) -> BenchmarkMeasurement:
    for _ in range(warmups):
        if operation.prepare is not None:
            operation.prepare()
        operation.execute()
    observations: list[BenchmarkSample] = []
    for _ in range(samples):
        if operation.prepare is not None:
            operation.prepare()
        with count_queries() as counters:
            started_at = perf_counter()
            rows = operation.execute()
            duration_ms = (perf_counter() - started_at) * 1_000
        observations.append(
            BenchmarkSample(
                duration_ms=duration_ms,
                query_count=counters[0].count,
                rows_returned=rows,
            )
        )
    durations = sorted(item.duration_ms for item in observations)
    query_counts = [item.query_count for item in observations]
    row_counts = [item.rows_returned for item in observations]
    if len(set(query_counts)) != 1 or len(set(row_counts)) != 1:
        raise RuntimeError(
            f"Benchmark operation {operation.name} changed its query or row count"
        )
    return BenchmarkMeasurement(
        operation=operation.name,
        warmups=warmups,
        samples=samples,
        query_count_min=min(query_counts),
        query_count_max=max(query_counts),
        rows_returned_min=min(row_counts),
        rows_returned_max=max(row_counts),
        p50_ms=median(durations),
        p95_ms=durations[math.ceil(len(durations) * 0.95) - 1],
        max_ms=max(durations),
        observations=tuple(observations),
    )


def database_metadata(
    profile: PerformanceProfile,
    *,
    warmups: int,
    samples: int,
    command_arguments: tuple[str, ...],
) -> BenchmarkMetadata:
    expected = PROFILES[profile]
    with SessionLocal() as session:
        database = session.scalar(text("SELECT current_database()"))
        postgres_version = session.scalar(text("SHOW server_version"))
        alembic_revision = session.scalar(
            text("SELECT version_num FROM alembic_version")
        )
        conversations = session.scalar(select(func.count(WhatsAppConversation.id)))
        messages = session.scalar(select(func.count(WhatsAppMessage.id)))
        status_events = session.scalar(
            select(func.count(WhatsAppMessageStatusEvent.id))
        )
        attachments = session.scalar(select(func.count(WhatsAppAttachment.id)))
        opportunities = session.scalar(select(func.count(Opportunity.id)))
    if not isinstance(database, str) or not database.endswith("_performance"):
        raise RuntimeError("Benchmark requires a database ending in _performance")
    if not isinstance(postgres_version, str) or not isinstance(alembic_revision, str):
        raise TypeError("PostgreSQL/Alembic metadata is unavailable")
    if opportunities is None or attachments is None:
        raise RuntimeError("Opportunity or attachment count is unavailable")
    if (
        conversations != expected.conversations
        or messages != expected.messages
        or status_events != expected.status_events
    ):
        raise RuntimeError(
            "Seeded row counts do not match the requested performance profile"
        )
    supplied_commit = os.getenv("BENCHMARK_GIT_COMMIT")
    commit = (
        supplied_commit
        if supplied_commit is not None
        else subprocess.run(
            ("git", "rev-parse", "HEAD"),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    git_dirty = os.getenv("BENCHMARK_GIT_DIRTY", "false").lower() == "true"
    return BenchmarkMetadata(
        profile=profile,
        database=database,
        postgres_version=postgres_version,
        alembic_revision=alembic_revision,
        git_commit=commit,
        git_dirty=git_dirty,
        host=platform.node(),
        seed=14,
        conversations=conversations,
        messages=messages,
        status_events=status_events,
        attachments=attachments,
        opportunities=opportunities,
        warmups=warmups,
        samples=samples,
        command_arguments=command_arguments,
    )


def provider() -> FakeWhatsAppProvider:
    return FakeWhatsAppProvider(
        now=BENCHMARK_NOW,
        templates=(
            ProviderTemplateSnapshot(
                external_id="performance-marketing",
                name="performance_offer",
                language="es_AR",
                category="MARKETING",
                status="APPROVED",
                header_type=TemplateHeaderType.TEXT,
                parameter_names=("fecha",),
            ),
        ),
    )


def operations(*, required_broadcasts: int) -> tuple[BenchmarkOperation, ...]:
    with SessionLocal() as session:
        conversation_ids = tuple(
            session.scalars(
                select(WhatsAppConversation.id).order_by(WhatsAppConversation.id)
            )
        )
        broadcast_ids = tuple(
            session.scalars(select(WhatsAppBroadcast.id).order_by(WhatsAppBroadcast.id))
        )
        actor_user_id = session.scalar(select(func.min(User.id)))
        product_id = session.scalar(select(func.min(Product.id)))
    if actor_user_id is None or product_id is None:
        raise RuntimeError("Performance profile has no actor User or Product")
    if not conversation_ids or len(broadcast_ids) < required_broadcasts + 1:
        raise RuntimeError("Performance profile is missing required benchmark records")
    first_conversation_id = conversation_ids[0]
    middle_conversation_id = conversation_ids[len(conversation_ids) // 2]
    poll_cursor = ResourceChangeCursor(
        datetime(2023, 1, 1, tzinfo=UTC),
        0,
    )
    older_cursor = _older_message_cursor(first_conversation_id)
    broadcast_provider = provider()
    storage = FakeMediaStorage()
    confirmation_position = 1

    def conversation_list() -> int:
        with SessionLocal() as session:
            return len(
                ConversationQueryService(session)
                .list_conversations(
                    ConversationListFilters(),
                    ConversationPageRequest(limit=50),
                    snapshot_at=BENCHMARK_NOW,
                )
                .items
            )

    def conversation_search() -> int:
        with SessionLocal() as session:
            return len(
                ConversationQueryService(session)
                .list_conversations(
                    ConversationListFilters(search="customer 000500"),
                    ConversationPageRequest(limit=50),
                    snapshot_at=BENCHMARK_NOW,
                )
                .items
            )

    def conversation_waiting_unread() -> int:
        with SessionLocal() as session:
            return len(
                ConversationQueryService(session)
                .list_conversations(
                    ConversationListFilters(waiting_only=True, unread_only=True),
                    ConversationPageRequest(limit=50),
                    snapshot_at=BENCHMARK_NOW,
                )
                .items
            )

    def conversation_detail() -> int:
        with SessionLocal() as session:
            ConversationQueryService(session).get_conversation_detail(
                middle_conversation_id
            )
            return 1

    def message_newest() -> int:
        with SessionLocal() as session:
            return len(
                MessageQueryService(session)
                .list_message_history(
                    first_conversation_id,
                    MessagePageRequest(limit=5),
                    snapshot_at=BENCHMARK_NOW,
                )
                .items
            )

    def message_older() -> int:
        with SessionLocal() as session:
            return len(
                MessageQueryService(session)
                .list_message_history(
                    first_conversation_id,
                    MessagePageRequest(limit=5, before=older_cursor),
                )
                .items
            )

    def conversation_polling() -> int:
        with SessionLocal() as session:
            return len(
                PollingQueryService(session)
                .list_conversation_changes(
                    ChangePageRequest(cursor=poll_cursor, limit=500)
                )
                .items
            )

    def message_polling() -> int:
        with SessionLocal() as session:
            return len(
                PollingQueryService(session)
                .list_message_changes(
                    first_conversation_id,
                    ChangePageRequest(cursor=poll_cursor, limit=500),
                )
                .items
            )

    metrics_filters = MetricsFilters(
        period=MetricsPeriod(METRICS_START, METRICS_END),
        dimensions=MetricsDimensions(
            source=LeadSource.WEB,
            product_id=product_id,
            province="Buenos Aires",
        ),
    )

    def metric_rows(method: str) -> int:
        with SessionLocal() as session:
            service = MetricsService(session)
            if method == "overview":
                service.overview(metrics_filters)
                return 1
            if method == "products":
                return len(service.products(metrics_filters))
            if method == "provinces":
                return len(service.provinces(metrics_filters))
            granularity = (
                TimelineGranularity.DAY
                if method == "timeline_day"
                else TimelineGranularity.MONTH
            )
            return len(service.timeline(metrics_filters, granularity=granularity))

    def validate_broadcast() -> int:
        with SessionLocal() as session:
            result = WhatsAppBroadcastService(
                session,
                broadcast_provider,
                storage,
                batch_size=10,
                claim_timeout=timedelta(minutes=5),
            ).validate(
                broadcast_ids[0],
                expected_version=1,
                actor_user_id=actor_user_id,
                now=BENCHMARK_NOW,
            )
            return result.recipient_count

    prepared_confirmation: tuple[int, UUID] | None = None

    def prepare_confirmation() -> None:
        nonlocal confirmation_position, prepared_confirmation
        broadcast_id = broadcast_ids[confirmation_position]
        confirmation_position += 1
        with SessionLocal() as session:
            validation = WhatsAppBroadcastService(
                session,
                broadcast_provider,
                storage,
                batch_size=10,
                claim_timeout=timedelta(minutes=5),
            ).validate(
                broadcast_id,
                expected_version=1,
                actor_user_id=actor_user_id,
                now=BENCHMARK_NOW,
            )
        if validation.validation_token is None:
            raise RuntimeError("Seeded Broadcast did not validate")
        prepared_confirmation = (broadcast_id, validation.validation_token)

    def confirm_broadcast() -> int:
        if prepared_confirmation is None:
            raise RuntimeError("Confirmation benchmark was not prepared")
        broadcast_id, validation_token = prepared_confirmation
        with SessionLocal() as session:
            WhatsAppBroadcastService(
                session,
                broadcast_provider,
                storage,
                batch_size=10,
                claim_timeout=timedelta(minutes=5),
            ).confirm(
                broadcast_id,
                command_id=uuid5(NAMESPACE_URL, f"performance-confirm-{broadcast_id}"),
                expected_version=1,
                validation_token=validation_token,
                actor_user_id=actor_user_id,
                now=BENCHMARK_NOW,
            )
            return 120

    return (
        BenchmarkOperation("conversation_list", conversation_list),
        BenchmarkOperation("conversation_list_search", conversation_search),
        BenchmarkOperation(
            "conversation_list_waiting_unread", conversation_waiting_unread
        ),
        BenchmarkOperation("conversation_detail", conversation_detail),
        BenchmarkOperation("message_history_newest", message_newest),
        BenchmarkOperation("message_history_older", message_older),
        BenchmarkOperation("conversation_changes_polling", conversation_polling),
        BenchmarkOperation("message_changes_polling", message_polling),
        BenchmarkOperation(
            "metrics_overview_filtered", lambda: metric_rows("overview")
        ),
        BenchmarkOperation(
            "metrics_products_filtered", lambda: metric_rows("products")
        ),
        BenchmarkOperation(
            "metrics_provinces_filtered", lambda: metric_rows("provinces")
        ),
        BenchmarkOperation(
            "metrics_timeline_day_filtered", lambda: metric_rows("timeline_day")
        ),
        BenchmarkOperation(
            "metrics_timeline_month_filtered", lambda: metric_rows("timeline_month")
        ),
        BenchmarkOperation("broadcast_validation", validate_broadcast),
        BenchmarkOperation(
            "broadcast_confirmation_revalidation",
            confirm_broadcast,
            prepare_confirmation,
        ),
    )


def _older_message_cursor(conversation_id: int) -> MessagePageCursor:
    with SessionLocal() as session:
        cursor = (
            MessageQueryService(session)
            .list_message_history(
                conversation_id,
                MessagePageRequest(limit=5),
                snapshot_at=BENCHMARK_NOW,
            )
            .next_before_cursor
        )
    if cursor is None:
        raise RuntimeError("Seeded conversation needs older message history")
    return cursor


def parse_positive(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error
    if parsed <= 0:
        raise RuntimeError(f"{name} must be positive")
    return parsed


def option(arguments: Sequence[str], name: str, default: str) -> str:
    if name not in arguments:
        return default
    position = arguments.index(name)
    if position + 1 >= len(arguments):
        raise RuntimeError(f"{name} requires a value")
    return arguments[position + 1]


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(argv if argv is not None else sys.argv[1:])
    profile = PerformanceProfile(option(arguments, "--profile", "baseline"))
    warmups = parse_positive(option(arguments, "--warmups", "2"), "warmups")
    samples = parse_positive(option(arguments, "--samples", "10"), "samples")
    output = Path(option(arguments, "--output", "performance-benchmark.json"))
    metadata = database_metadata(
        profile,
        warmups=warmups,
        samples=samples,
        command_arguments=arguments,
    )
    measurements = tuple(
        run_operation(operation, warmups=warmups, samples=samples)
        for operation in operations(required_broadcasts=warmups + samples)
    )
    report = BenchmarkReport(metadata=metadata, measurements=measurements)
    output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print("operation\tqueries\trows\tp50_ms\tp95_ms\tmax_ms")
    for measurement in measurements:
        print(
            f"{measurement.operation}\t"
            f"{measurement.query_count_min}-{measurement.query_count_max}\t"
            f"{measurement.rows_returned_min}-{measurement.rows_returned_max}\t"
            f"{measurement.p50_ms:.3f}\t{measurement.p95_ms:.3f}\t"
            f"{measurement.max_ms:.3f}"
        )
    print(f"JSON artifact: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
