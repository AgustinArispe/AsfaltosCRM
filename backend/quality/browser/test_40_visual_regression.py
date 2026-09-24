from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from quality.browser.support import (
    FRONTEND_URL,
    QaPage,
    QaPageFactory,
    Theme,
    assert_visual_baseline,
    wait_for_workspace,
)

QA_WHATSAPP_VISUAL_CONVERSATION_ID = 2
QA_WHATSAPP_VISUAL_READ_SEQUENCE = (5, 6, 4, 3, QA_WHATSAPP_VISUAL_CONVERSATION_ID)


def _open_login(qa_page: QaPage, theme: Theme) -> None:
    page = qa_page.page
    page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
    expect(page.locator("html")).to_have_attribute("data-theme", theme)
    expect(page.get_by_role("heading", name="Ingresar al sistema")).to_be_visible()


def _open_canonical_whatsapp_conversation(qa_page: QaPage) -> None:
    page = qa_page.page
    for conversation_id in QA_WHATSAPP_VISUAL_READ_SEQUENCE:
        with page.expect_response(
            f"**/api/whatsapp/conversations/{conversation_id}/read"
        ):
            wait_for_workspace(page, f"whatsapp/conversations/{conversation_id}")
    expect(
        page.get_by_role("heading", name="Paula Benítez", exact=True)
    ).to_be_visible()


@pytest.mark.visual
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_login_desktop_baseline(qa_pages: QaPageFactory, theme: Theme) -> None:
    qa_page = qa_pages.create(viewport=(1440, 900), theme=theme)
    _open_login(qa_page, theme)
    expect(qa_page.page.get_by_role("img", name="PULSE CRM")).to_be_visible()
    logo = qa_page.page.locator(".login-brand-panel__anchor svg")
    expect(logo).to_be_visible()
    expect(logo.locator("image")).to_have_attribute(
        "href", "/pulse-brand-lockup-dark.png"
    )
    assert_visual_baseline(qa_page.page, f"login-{theme}", animations="allow")


@pytest.mark.visual
def test_login_mobile_baseline(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(viewport=(390, 844))
    _open_login(qa_page, "light")
    expect(qa_page.page.get_by_role("img", name="PULSE CRM")).to_have_count(0)
    assert_visual_baseline(qa_page.page, "login-mobile", animations="allow")


@pytest.mark.visual
def test_pipeline_desktop_baseline(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR", viewport=(1440, 900))
    expect(
        qa_page.page.get_by_role(
            "button", name=re.compile("Abrir oportunidad de Constructora del Sur")
        ).first
    ).to_be_visible()
    assert_visual_baseline(qa_page.page, "pipeline-desktop")


@pytest.mark.visual
def test_dashboard_desktop_baseline(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR", viewport=(1440, 900))
    wait_for_workspace(qa_page.page, "dashboard")
    assert_visual_baseline(qa_page.page, "dashboard-desktop")


@pytest.mark.visual
def test_whatsapp_desktop_baseline(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR", viewport=(1440, 900))
    _open_canonical_whatsapp_conversation(qa_page)
    conversations = qa_page.page.get_by_role(
        "list", name="Conversaciones de WhatsApp"
    ).get_by_role("button")
    expect(conversations).to_have_count(10)
    expect(
        qa_page.page.get_by_role("log", name="Historial de mensajes")
    ).to_be_visible()
    composer = qa_page.page.get_by_role("textbox", name="Mensaje")
    expect(composer).to_be_visible()
    composer_box = composer.bounding_box()
    assert composer_box is not None
    assert composer_box["y"] + composer_box["height"] <= 900
    assert qa_page.page.evaluate(
        "document.documentElement.scrollHeight <= window.innerHeight"
    )
    assert_visual_baseline(qa_page.page, "whatsapp-desktop")


@pytest.mark.visual
def test_opportunity_detail_baseline(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR", viewport=(1440, 900))
    qa_page.page.get_by_role(
        "button",
        name=re.compile("Abrir oportunidad de Constructora del Sur, origen Web"),
    ).click()
    expect(
        qa_page.page.get_by_role("dialog", name="Constructora del Sur")
    ).to_be_visible()
    expect(
        qa_page.page.get_by_role("dialog", name="Constructora del Sur").get_by_role(
            "heading", name="Constructora del Sur"
        )
    ).to_be_visible()
    assert_visual_baseline(qa_page.page, "opportunity-detail")


@pytest.mark.visual
def test_quote_modal_baseline(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR", viewport=(1440, 900))
    qa_page.page.get_by_role(
        "button",
        name=re.compile("Abrir oportunidad de Constructora del Sur, origen Web"),
    ).click()
    qa_page.page.get_by_role("dialog", name="Constructora del Sur").get_by_role(
        "button", name="Cotizar"
    ).click()
    expect(
        qa_page.page.get_by_role("dialog", name="Cotizar oportunidad")
    ).to_be_visible()
    expect(
        qa_page.page.get_by_role("dialog", name="Cotizar oportunidad").get_by_role(
            "radio", name="CA-30"
        )
    ).to_be_visible()
    assert_visual_baseline(qa_page.page, "quote-modal")


@pytest.mark.visual
def test_dashboard_dark_baseline(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR", viewport=(1440, 900), theme="dark")
    wait_for_workspace(qa_page.page, "dashboard")
    assert_visual_baseline(qa_page.page, "dashboard-dark")


@pytest.mark.visual
def test_pipeline_effective_150_percent_baseline(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR", viewport=(1280, 720))
    qa_page.page.mouse.move(0, 0)
    expect(
        qa_page.page.get_by_role(
            "button", name=re.compile("Abrir oportunidad de Constructora del Sur")
        ).first
    ).to_be_visible()
    assert_visual_baseline(qa_page.page, "pipeline-150-percent")


@pytest.mark.visual
def test_whatsapp_responsive_baseline(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR", viewport=(390, 844))
    _open_canonical_whatsapp_conversation(qa_page)
    page = qa_page.page
    log = page.get_by_role("log", name="Historial de mensajes")
    expect(log).to_be_visible()
    for element in (
        page.get_by_role("button", name="Contexto CRM", exact=True),
        log.get_by_role("article").first,
    ):
        box = element.bounding_box()
        assert box is not None
        assert box["x"] >= 0
        assert box["x"] + box["width"] <= 391
    assert_visual_baseline(qa_page.page, "whatsapp-responsive")
