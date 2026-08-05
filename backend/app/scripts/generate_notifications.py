from datetime import UTC, datetime

from app.core.config import get_stale_opportunity_days
from app.db.session import SessionLocal
from app.services import NotificationService


def main() -> int:
    with SessionLocal() as session:
        created_count = NotificationService(
            session
        ).generate_stale_opportunity_notifications(
            now=datetime.now(UTC),
            threshold_days=get_stale_opportunity_days(),
        )
    print(f"Created {created_count} stale opportunity notifications")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
