from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict, cast

import pytest
from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import (
    Browser,
    BrowserContext,
    ConsoleMessage,
    Page,
    Request,
    Response,
)

FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"
QA_ANCHOR = datetime(2026, 8, 18, 15, tzinfo=UTC)
ARTIFACTS_DIR = Path("artifacts/playwright")
BASELINES_DIR = Path("quality/browser/baselines")
AXE_PATH = Path("../frontend/node_modules/axe-core/axe.min.js")

Role = Literal["SUPERVISOR", "VENDEDOR"]
Theme = Literal["light", "dark"]


class AxeNode(TypedDict):
    target: list[str]
    html: str
    failureSummary: str


class AxeViolation(TypedDict):
    id: str
    impact: str | None
    help: str
    nodes: list[AxeNode]


class AxeResult(TypedDict):
    violations: list[AxeViolation]


@dataclass
class BrowserQualityLog:
    allowed_statuses: set[int] = field(default_factory=set)
    failures: list[str] = field(default_factory=list)

    def allow_status(self, status: int) -> None:
        self.allowed_statuses.add(status)

    def on_console(self, message: ConsoleMessage) -> None:
        if message.type == "error":
            if self.allowed_statuses and message.text.startswith(
                "Failed to load resource"
            ):
                return
            self.failures.append(f"console.error: {message.text}")
        elif message.type == "warning" and re.search(
            r"react|hydration|uncaught|deprecated", message.text, re.IGNORECASE
        ):
            self.failures.append(f"runtime warning: {message.text}")

    def on_page_error(self, error: Exception) -> None:
        self.failures.append(f"uncaught page error: {error}")

    def on_response(self, response: Response) -> None:
        if response.status >= 500 and response.status not in self.allowed_statuses:
            self.failures.append(f"unexpected HTTP {response.status}: {response.url}")

    def on_request_failed(self, request: Request) -> None:
        failure = request.failure
        if failure and "ERR_ABORTED" not in failure:
            self.failures.append(
                f"failed request: {request.method} {request.url}: {failure}"
            )

    def assert_clean(self) -> None:
        assert not self.failures, "\n".join(self.failures)


@dataclass
class QaPage:
    context: BrowserContext
    page: Page
    quality_log: BrowserQualityLog
    artifact_name: str

    def close(self, *, failed: bool) -> None:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        if failed:
            self.page.screenshot(
                path=ARTIFACTS_DIR / f"{self.artifact_name}.png",
                full_page=True,
            )
            self.context.tracing.stop(path=ARTIFACTS_DIR / f"{self.artifact_name}.zip")
        else:
            self.context.tracing.stop()
        self.context.close()


class QaPageFactory:
    def __init__(self, browser: Browser, artifact_prefix: str) -> None:
        self._browser = browser
        self._artifact_prefix = artifact_prefix
        self._pages: list[QaPage] = []

    @property
    def pages(self) -> list[QaPage]:
        return self._pages

    def create(
        self,
        *,
        role: Role | None = None,
        viewport: tuple[int, int] = (1440, 900),
        theme: Theme = "light",
        reduced_motion: Literal["reduce", "no-preference"] = "reduce",
        artifact_suffix: str = "page",
    ) -> QaPage:
        context = self._browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]},
            locale="es-AR",
            timezone_id="America/Argentina/Buenos_Aires",
            color_scheme=theme,
            reduced_motion=reduced_motion,
        )
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.clock.set_fixed_time(QA_ANCHOR)
        quality_log = BrowserQualityLog()
        page.on("console", quality_log.on_console)
        page.on("pageerror", quality_log.on_page_error)
        page.on("response", quality_log.on_response)
        page.on("requestfailed", quality_log.on_request_failed)
        qa_page = QaPage(
            context=context,
            page=page,
            quality_log=quality_log,
            artifact_name=f"{self._artifact_prefix}-{artifact_suffix}",
        )
        self._pages.append(qa_page)
        if role is not None:
            login_as(qa_page, role)
            select_theme(page, theme)
        return qa_page


def login_as(qa_page: QaPage, role: Role) -> None:
    credentials = {
        "SUPERVISOR": ("qa.supervisor@faa.test", "FAA-Visual-QA-2026!"),
        "VENDEDOR": ("qa.vendedor@faa.test", "FAA-Vendedor-QA-2026!"),
    }
    email, password = credentials[role]
    page = qa_page.page
    page.goto(f"{FRONTEND_URL}/login", wait_until="domcontentloaded")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Contraseña").fill(password)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_url("**/pipeline")
    page.get_by_role("heading", name="Oportunidades", exact=True).wait_for()


def select_theme(page: Page, theme: Theme) -> None:
    page.locator("html").wait_for(state="attached")
    assert page.locator("html").get_attribute("data-theme") == theme


def wait_for_workspace(page: Page, path: str, heading: str | None = None) -> None:
    page.goto(f"{FRONTEND_URL}/{path}", wait_until="networkidle")
    if heading:
        page.get_by_role("heading", name=heading, exact=True).first.wait_for()


def assert_no_horizontal_overflow(page: Page) -> None:
    has_overflow = cast(
        bool,
        page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        ),
    )
    overflow_sources = cast(
        str,
        page.evaluate(
            """
            JSON.stringify([...document.querySelectorAll('*')]
              .map((element) => {
                const rect = element.getBoundingClientRect()
                return {
                  tag: element.tagName,
                  class: element.className,
                  left: Math.round(rect.left),
                  right: Math.round(rect.right),
                  width: Math.round(rect.width),
                  overflowX: getComputedStyle(element).overflowX
                }
              })
              .filter((item) =>
                item.right > document.documentElement.clientWidth + 1 &&
                item.right <= document.documentElement.scrollWidth + 1)
              .sort((left, right) => right.right - left.right)
              .slice(0, 8))
            """
        ),
    )
    assert not has_overflow, (
        f"page overflow: {page.url} "
        f"({page.evaluate('document.documentElement.scrollWidth')} > "
        f"{page.evaluate('document.documentElement.clientWidth')}): {overflow_sources}"
    )


def run_axe(page: Page) -> None:
    page.add_script_tag(path=AXE_PATH)
    result = cast(
        AxeResult,
        page.evaluate(
            """
            async () => await axe.run(document, {
              runOnly: {
                type: 'tag',
                values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']
              }
            })
            """
        ),
    )
    if not result["violations"]:
        return
    summaries = []
    for violation in result["violations"]:
        targets = [", ".join(node["target"]) for node in violation["nodes"][:5]]
        summaries.append(
            f"{violation['impact']} {violation['id']}: {violation['help']} "
            f"({'; '.join(targets)})"
        )
    pytest.fail("Axe violations:\n" + "\n".join(summaries))


def stable_screenshot(page: Page, name: str) -> None:
    page.evaluate("document.fonts.ready")
    page.screenshot(path=ARTIFACTS_DIR / f"actual-{name}.png", full_page=True)


def assert_visual_baseline(page: Page, name: str) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    actual_path = ARTIFACTS_DIR / f"actual-{name}.png"
    expected_path = BASELINES_DIR / f"{name}.png"
    page.evaluate("document.fonts.ready")
    page.screenshot(path=actual_path, full_page=True)
    if not expected_path.exists() or _update_visual_baselines():
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.write_bytes(actual_path.read_bytes())
        return
    with (
        Image.open(expected_path).convert("RGB") as expected,
        Image.open(actual_path).convert("RGB") as actual,
    ):
        assert actual.size == expected.size, (
            f"visual size changed for {name}: {actual.size} != {expected.size}"
        )
        difference = ImageChops.difference(expected, actual)
        statistics = ImageStat.Stat(difference)
        grayscale_histogram = difference.convert("L").histogram()
        changed = actual.width * actual.height - grayscale_histogram[0]
        changed_ratio = changed / (actual.width * actual.height)
        mean_delta = sum(statistics.mean) / 3
        if changed_ratio > 0.01 or mean_delta > 0.75:
            difference.save(ARTIFACTS_DIR / f"diff-{name}.png")
            pytest.fail(
                f"visual regression for {name}: "
                f"{changed_ratio:.2%} pixels changed, mean delta {mean_delta:.2f}"
            )


def _update_visual_baselines() -> bool:
    from os import environ

    return environ.get("UPDATE_VISUAL_BASELINES") == "1"
