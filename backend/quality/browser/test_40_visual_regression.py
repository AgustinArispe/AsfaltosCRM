from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from quality.browser.support import (
    QaPageFactory,
    assert_visual_baseline,
    wait_for_workspace,
)


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
    wait_for_workspace(qa_page.page, "whatsapp")
    conversations = qa_page.page.get_by_role(
        "list", name="Conversaciones de WhatsApp"
    ).get_by_role("button")
    expect(conversations).to_have_count(10)
    conversations.first.click()
    expect(
        qa_page.page.get_by_role("log", name="Historial de mensajes")
    ).to_be_visible()
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
    expect(
        qa_page.page.get_by_role(
            "button", name=re.compile("Abrir oportunidad de Constructora del Sur")
        ).first
    ).to_be_visible()
    assert_visual_baseline(qa_page.page, "pipeline-150-percent")


@pytest.mark.visual
def test_whatsapp_responsive_baseline(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR", viewport=(390, 844))
    wait_for_workspace(qa_page.page, "whatsapp")
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
