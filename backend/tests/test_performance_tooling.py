from pathlib import Path

import pytest
from performance.benchmark import (
    PROFILES,
    PerformanceProfile,
    option,
    parse_positive,
)
from performance.explain import QUERIES


def test_performance_profiles_are_release_scale_and_deterministic() -> None:
    assert PROFILES[PerformanceProfile.BASELINE].conversations == 1_000
    assert PROFILES[PerformanceProfile.BASELINE].messages == 10_000
    assert PROFILES[PerformanceProfile.BASELINE].status_events == 10_000
    assert PROFILES[PerformanceProfile.LARGE].conversations == 10_000
    assert PROFILES[PerformanceProfile.LARGE].messages == 100_000
    assert PROFILES[PerformanceProfile.LARGE].status_events == 100_000


def test_performance_cli_options_are_typed_and_bounded() -> None:
    assert option(("--samples", "20"), "--samples", "10") == "20"
    assert option((), "--samples", "10") == "10"
    assert parse_positive("20", "samples") == 20
    with pytest.raises(RuntimeError, match="requires a value"):
        option(("--samples",), "--samples", "10")
    with pytest.raises(RuntimeError, match="integer"):
        parse_positive("many", "samples")
    with pytest.raises(RuntimeError, match="positive"):
        parse_positive("0", "samples")


def test_explain_suite_covers_every_critical_query() -> None:
    names = {query.name for query in QUERIES}
    assert names == {
        "broadcast_recipient_claiming",
        "conversation_changes_polling",
        "latest_marketing_consent_batched",
        "latest_marketing_consent_single",
        "message_changes_polling",
        "metrics_overview_filtered",
        "metrics_products_filtered",
        "metrics_provinces_filtered",
        "metrics_timeline_filtered",
        "opportunity_detail_reopen_count",
        "opportunity_list_reopen_count",
    }
    assert all("EXPLAIN" not in query.sql.upper() for query in QUERIES)


def test_seed_refuses_non_performance_or_non_empty_database() -> None:
    seed = (Path(__file__).parents[1] / "performance" / "seed.sql").read_text(
        encoding="utf-8"
    )
    assert "current_database() !~ '_performance$'" in seed
    assert "Performance database is not empty" in seed
    assert "TRUNCATE" not in seed.upper()
