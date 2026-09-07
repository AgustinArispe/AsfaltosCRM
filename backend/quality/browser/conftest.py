from __future__ import annotations

import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, Playwright, sync_playwright

from quality.browser.support import QaPageFactory

FAILED_KEY = pytest.StashKey[bool]()


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> None:
    if call.excinfo is not None:
        item.stash[FAILED_KEY] = True


@pytest.fixture(scope="session")
def playwright_runtime() -> Iterator[Playwright]:
    with sync_playwright() as runtime:
        yield runtime


@pytest.fixture(scope="session")
def browser(playwright_runtime: Playwright) -> Iterator[Browser]:
    instance = playwright_runtime.chromium.launch(headless=True)
    yield instance
    instance.close()


@pytest.fixture
def qa_pages(
    request: pytest.FixtureRequest, browser: Browser
) -> Iterator[QaPageFactory]:
    artifact_prefix = re.sub(r"[^a-zA-Z0-9_.-]+", "-", request.node.nodeid).strip("-")
    factory = QaPageFactory(browser, artifact_prefix)
    yield factory
    failed = request.node.stash.get(FAILED_KEY, False)
    log_failures: list[str] = []
    for qa_page in factory.pages:
        try:
            qa_page.quality_log.assert_clean()
        except AssertionError as error:
            log_failures.append(str(error))
    failed = failed or bool(log_failures)
    for qa_page in factory.pages:
        qa_page.close(failed=failed)
    if log_failures:
        pytest.fail(
            "Browser console/network quality failures:\n" + "\n".join(log_failures)
        )
