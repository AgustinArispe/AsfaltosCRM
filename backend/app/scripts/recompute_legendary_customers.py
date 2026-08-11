import argparse
from collections.abc import Sequence
from datetime import UTC, datetime

from app.db.session import SessionLocal
from app.services.legendary_service import LegendaryService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recompute automatic Legendary state")
    parser.add_argument("--after-customer-id", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--max-batches", type=int, default=100)
    parser.add_argument("--now", type=str)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(arguments)
    if (
        args.after_customer_id < 0
        or not 1 <= args.batch_size <= 1000
        or args.max_batches <= 0
    ):
        print("Invalid Legendary recomputation bounds")
        return 2
    try:
        evaluated_at = (
            datetime.fromisoformat(args.now) if args.now else datetime.now(UTC)
        )
    except ValueError:
        print("--now must be an ISO-8601 datetime")
        return 2
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        print("--now must include a timezone")
        return 2
    after_customer_id = args.after_customer_id
    total_evaluated = 0
    total_changed = 0
    has_more = False
    with SessionLocal() as session:
        service = LegendaryService(session)
        for _ in range(args.max_batches):
            result = service.recompute_batch(
                after_customer_id=after_customer_id,
                batch_size=args.batch_size,
                evaluated_at=evaluated_at,
            )
            total_evaluated += result.evaluated
            total_changed += result.changed
            has_more = result.has_more
            if result.last_customer_id is not None:
                after_customer_id = result.last_customer_id
            if not has_more:
                break
    print(
        "Legendary recomputation "
        f"evaluated={total_evaluated} changed={total_changed} "
        f"resume_after={after_customer_id}"
    )
    return 2 if has_more else 0


if __name__ == "__main__":
    raise SystemExit(main())
