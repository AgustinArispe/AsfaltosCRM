from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from app.db.session import SessionLocal


@dataclass(frozen=True, slots=True)
class CriticalQuery:
    name: str
    sql: str


class ExplainFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    planning_ms: float
    execution_ms: float
    estimated_rows_max: int
    actual_rows_max: int
    loops_max: int
    shared_hit_blocks: int
    shared_read_blocks: int
    temp_read_blocks: int
    temp_written_blocks: int
    sequential_scans: tuple[str, ...]
    sort_spill: bool
    plan: tuple[str, ...]


class ExplainReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    database: str
    postgres_version: str
    findings: tuple[ExplainFinding, ...]


CHANGE_CURSOR = "timestamptz '2023-01-01 00:00:00+00'"


QUERIES = (
    CriticalQuery(
        "conversation_changes_polling",
        f"""
        SELECT conversation.id,
               greatest(
                   conversation.updated_at,
                   coalesce(customer.updated_at, conversation.updated_at),
                   coalesce((
                       SELECT max(greatest(link.linked_at,
                           coalesce(link.unlinked_at, link.linked_at)))
                       FROM whatsapp_conversation_opportunities AS link
                       WHERE link.conversation_id = conversation.id
                   ), conversation.updated_at),
                   coalesce((
                       SELECT max(opportunity.updated_at)
                       FROM opportunities AS opportunity
                       WHERE opportunity.customer_id = conversation.customer_id
                   ), conversation.updated_at)
               ) AS resource_updated_at
        FROM whatsapp_conversations AS conversation
        LEFT JOIN customers AS customer ON customer.id = conversation.customer_id
        WHERE greatest(
                   conversation.updated_at,
                   coalesce(customer.updated_at, conversation.updated_at),
                   coalesce((SELECT max(greatest(link.linked_at,
                       coalesce(link.unlinked_at, link.linked_at)))
                       FROM whatsapp_conversation_opportunities AS link
                       WHERE link.conversation_id = conversation.id), conversation.updated_at),
                   coalesce((SELECT max(opportunity.updated_at)
                       FROM opportunities AS opportunity
                       WHERE opportunity.customer_id = conversation.customer_id), conversation.updated_at)
              ) > {CHANGE_CURSOR}
        ORDER BY resource_updated_at, conversation.id
        LIMIT 501
        """,
    ),
    CriticalQuery(
        "message_changes_polling",
        f"""
        SELECT message.id,
               greatest(
                   message.updated_at,
                   coalesce((SELECT max(attachment.updated_at)
                       FROM whatsapp_attachments AS attachment
                       WHERE attachment.message_id = message.id), message.updated_at),
                   coalesce((SELECT max(greatest(status.occurred_at, status.received_at))
                       FROM whatsapp_message_status_events AS status
                       WHERE status.message_id = message.id), message.updated_at)
               ) AS resource_updated_at
        FROM whatsapp_messages AS message
        WHERE message.conversation_id = (SELECT min(id) FROM whatsapp_conversations)
          AND greatest(
                   message.updated_at,
                   coalesce((SELECT max(attachment.updated_at)
                       FROM whatsapp_attachments AS attachment
                       WHERE attachment.message_id = message.id), message.updated_at),
                   coalesce((SELECT max(greatest(status.occurred_at, status.received_at))
                       FROM whatsapp_message_status_events AS status
                       WHERE status.message_id = message.id), message.updated_at)
              ) > {CHANGE_CURSOR}
        ORDER BY resource_updated_at, message.id
        LIMIT 501
        """,
    ),
    CriticalQuery(
        "metrics_overview_filtered",
        """
        SELECT count(opportunity.id) FILTER (
                   WHERE opportunity.created_at >= timestamptz '2024-01-01 00:00:00+00'
                     AND opportunity.created_at < timestamptz '2025-01-01 00:00:00+00'),
               count(opportunity.id) FILTER (WHERE opportunity.status = 'GANADA'),
               count(opportunity.id) FILTER (WHERE opportunity.status = 'PERDIDA')
        FROM opportunities AS opportunity
        JOIN customers AS customer ON customer.id = opportunity.customer_id
        WHERE opportunity.deleted_at IS NULL
          AND customer.province = 'Buenos Aires'
          AND opportunity.source = 'WEB'
          AND EXISTS (
              SELECT 1 FROM opportunity_products AS filter_line
              WHERE filter_line.opportunity_id = opportunity.id
                AND filter_line.product_id = (SELECT min(id) FROM products)
          )
        """,
    ),
    CriticalQuery(
        "metrics_products_filtered",
        """
        SELECT product.id, product.name, count(DISTINCT opportunity.id),
               sum(line.quantity_kg)
        FROM opportunity_products AS line
        JOIN products AS product ON product.id = line.product_id
        JOIN opportunities AS opportunity ON opportunity.id = line.opportunity_id
        JOIN customers AS customer ON customer.id = opportunity.customer_id
        WHERE opportunity.deleted_at IS NULL
          AND customer.province = 'Buenos Aires'
          AND opportunity.source = 'WEB'
          AND EXISTS (
              SELECT 1 FROM opportunity_products AS filter_line
              WHERE filter_line.opportunity_id = opportunity.id
                AND filter_line.product_id = (SELECT min(id) FROM products)
          )
          AND opportunity.created_at >= timestamptz '2024-01-01 00:00:00+00'
          AND opportunity.created_at < timestamptz '2025-01-01 00:00:00+00'
        GROUP BY product.id, product.name
        ORDER BY sum(line.quantity_kg) DESC, product.id
        """,
    ),
    CriticalQuery(
        "metrics_provinces_filtered",
        """
        SELECT customer.province, count(opportunity.id),
               count(opportunity.id) FILTER (WHERE opportunity.status = 'GANADA'),
               count(opportunity.id) FILTER (WHERE opportunity.status = 'PERDIDA')
        FROM opportunities AS opportunity
        JOIN customers AS customer ON customer.id = opportunity.customer_id
        WHERE opportunity.deleted_at IS NULL
          AND opportunity.source = 'WEB'
          AND EXISTS (
              SELECT 1 FROM opportunity_products AS filter_line
              WHERE filter_line.opportunity_id = opportunity.id
                AND filter_line.product_id = (SELECT min(id) FROM products)
          )
          AND opportunity.created_at >= timestamptz '2024-01-01 00:00:00+00'
          AND opportunity.created_at < timestamptz '2025-01-01 00:00:00+00'
        GROUP BY customer.province
        ORDER BY customer.province NULLS LAST
        """,
    ),
    CriticalQuery(
        "metrics_timeline_filtered",
        """
        SELECT date_trunc('day', timezone('America/Argentina/Buenos_Aires',
                   opportunity.created_at))::date AS bucket,
               count(opportunity.id)
        FROM opportunities AS opportunity
        JOIN customers AS customer ON customer.id = opportunity.customer_id
        WHERE opportunity.deleted_at IS NULL
          AND customer.province = 'Buenos Aires'
          AND opportunity.source = 'WEB'
          AND EXISTS (
              SELECT 1 FROM opportunity_products AS filter_line
              WHERE filter_line.opportunity_id = opportunity.id
                AND filter_line.product_id = (SELECT min(id) FROM products)
          )
          AND opportunity.created_at >= timestamptz '2024-01-01 00:00:00+00'
          AND opportunity.created_at < timestamptz '2025-01-01 00:00:00+00'
        GROUP BY bucket
        """,
    ),
    CriticalQuery(
        "broadcast_recipient_claiming",
        """
        SELECT recipient.id
        FROM whatsapp_broadcast_recipients AS recipient
        WHERE recipient.broadcast_id = (SELECT max(id) FROM whatsapp_broadcasts)
          AND recipient.status = 'READY'
        ORDER BY recipient.id
        LIMIT 10
        FOR UPDATE SKIP LOCKED
        """,
    ),
    CriticalQuery(
        "latest_marketing_consent_single",
        """
        SELECT consent.*
        FROM whatsapp_marketing_consent_events AS consent
        WHERE consent.customer_id = (SELECT min(id) FROM customers)
          AND consent.normalized_phone = (SELECT phone FROM customers ORDER BY id LIMIT 1)
          AND consent.effective_at <= timestamptz '2025-01-01 00:00:00+00'
        ORDER BY consent.effective_at DESC, consent.id DESC
        LIMIT 1
        """,
    ),
    CriticalQuery(
        "latest_marketing_consent_batched",
        """
        WITH requested AS (
            SELECT id AS customer_id, phone AS normalized_phone
            FROM customers ORDER BY id LIMIT 120
        ), ranked AS (
            SELECT consent.*,
                   row_number() OVER (
                       PARTITION BY consent.customer_id, consent.normalized_phone
                       ORDER BY consent.effective_at DESC, consent.id DESC
                   ) AS consent_rank
            FROM whatsapp_marketing_consent_events AS consent
            JOIN requested USING (customer_id, normalized_phone)
            WHERE consent.effective_at <= timestamptz '2025-01-01 00:00:00+00'
        )
        SELECT * FROM ranked WHERE consent_rank = 1
        """,
    ),
    CriticalQuery(
        "opportunity_list_reopen_count",
        """
        SELECT opportunity.*,
               (SELECT count(reopen.id)
                FROM opportunity_reopen_events AS reopen
                WHERE reopen.opportunity_id = opportunity.id) AS reopen_count
        FROM opportunities AS opportunity
        WHERE opportunity.deleted_at IS NULL
          AND opportunity.status <> 'PERDIDA'
        ORDER BY opportunity.created_at DESC, opportunity.id DESC
        LIMIT 50
        """,
    ),
    CriticalQuery(
        "opportunity_detail_reopen_count",
        """
        SELECT opportunity.*,
               (SELECT count(reopen.id)
                FROM opportunity_reopen_events AS reopen
                WHERE reopen.opportunity_id = opportunity.id) AS reopen_count
        FROM opportunities AS opportunity
        WHERE opportunity.id = (SELECT min(id) FROM opportunities)
          AND opportunity.deleted_at IS NULL
        """,
    ),
)


def parse_number(lines: tuple[str, ...], label: str) -> float:
    pattern = re.compile(rf"^{re.escape(label)}: ([0-9.]+) ms$")
    for line in lines:
        match = pattern.match(line.strip())
        if match is not None:
            return float(match.group(1))
    raise RuntimeError(f"EXPLAIN output omitted {label}")


def integer_values(lines: tuple[str, ...], pattern: str) -> tuple[int, ...]:
    compiled = re.compile(pattern)
    return tuple(
        int(match.group(1))
        for line in lines
        for match in (compiled.search(line),)
        if match is not None
    )


def explain(query: CriticalQuery) -> ExplainFinding:
    with SessionLocal() as session:
        rows = session.execute(
            text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {query.sql}")
        ).all()
        session.rollback()
    lines = tuple(str(row[0]) for row in rows)
    estimated = integer_values(lines, r"cost=[^ ]+ rows=([0-9]+)")
    actual = integer_values(lines, r"actual time=[^ ]+ rows=([0-9]+)")
    loops = integer_values(lines, r"loops=([0-9]+)")
    shared_hits = integer_values(lines, r"shared hit=([0-9]+)")
    shared_reads = integer_values(lines, r"shared (?:hit=[0-9]+ )?read=([0-9]+)")
    temp_reads = integer_values(lines, r"temp read=([0-9]+)")
    temp_writes = integer_values(lines, r"temp (?:read=[0-9]+ )?written=([0-9]+)")
    scans = tuple(
        line.strip()
        for line in lines
        if "Seq Scan" in line or "Bitmap" in line or "Index Scan" in line
    )
    return ExplainFinding(
        query=query.name,
        planning_ms=parse_number(lines, "Planning Time"),
        execution_ms=parse_number(lines, "Execution Time"),
        estimated_rows_max=max(estimated, default=0),
        actual_rows_max=max(actual, default=0),
        loops_max=max(loops, default=0),
        shared_hit_blocks=sum(shared_hits),
        shared_read_blocks=sum(shared_reads),
        temp_read_blocks=sum(temp_reads),
        temp_written_blocks=sum(temp_writes),
        sequential_scans=scans,
        sort_spill=any("Sort Method: external" in line for line in lines),
        plan=lines,
    )


def option(arguments: Sequence[str], name: str, default: str) -> str:
    if name not in arguments:
        return default
    position = arguments.index(name)
    if position + 1 >= len(arguments):
        raise RuntimeError(f"{name} requires a value")
    return arguments[position + 1]


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(argv if argv is not None else sys.argv[1:])
    output_directory = Path(option(arguments, "--output-dir", "performance-plans"))
    output_directory.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as session:
        database = session.scalar(text("SELECT current_database()"))
        postgres_version = session.scalar(text("SHOW server_version"))
        if not isinstance(database, str) or not database.endswith("_performance"):
            raise RuntimeError("EXPLAIN requires a database ending in _performance")
        if not isinstance(postgres_version, str):
            raise TypeError("PostgreSQL version is unavailable")
        session.execute(text("ANALYZE"))
        session.commit()
    findings = tuple(explain(query) for query in QUERIES)
    report = ExplainReport(
        generated_at=datetime.now(UTC),
        database=database,
        postgres_version=postgres_version,
        findings=findings,
    )
    (output_directory / "plans.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    for finding in findings:
        (output_directory / f"{finding.query}.txt").write_text(
            "\n".join(finding.plan) + "\n", encoding="utf-8"
        )
    print("query\tplanning_ms\texecution_ms\tactual_rows\tloops\tread_blocks\tspill")
    for finding in findings:
        print(
            f"{finding.query}\t{finding.planning_ms:.3f}\t"
            f"{finding.execution_ms:.3f}\t{finding.actual_rows_max}\t"
            f"{finding.loops_max}\t{finding.shared_read_blocks}\t"
            f"{'yes' if finding.sort_spill else 'no'}"
        )
    print(f"Plan artifacts: {output_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
