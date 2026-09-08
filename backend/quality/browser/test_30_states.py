from __future__ import annotations

import re

from playwright.sync_api import Route, expect

from quality.browser.support import QaPageFactory, run_axe, wait_for_workspace


def test_empty_search_and_filter_states_explain_next_action(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    page = qa_page.page

    pipeline_search = page.get_by_role("searchbox", name="Buscar oportunidades")
    pipeline_search.fill("cliente que no existe")
    expect(page.get_by_role("heading", name="Sin resultados")).to_be_visible()
    expect(page.get_by_role("button", name="Limpiar filtros")).to_be_visible()

    wait_for_workspace(page, "customers")
    customer_search = page.get_by_role("searchbox", name="Buscar clientes")
    customer_search.fill("cliente que no existe")
    expect(page.get_by_role("heading", name="No encontramos clientes")).to_be_visible()
    expect(page.get_by_text("Probá con otro nombre", exact=False)).to_be_visible()

    wait_for_workspace(page, "lost")
    page.get_by_role("searchbox", name="Buscar").fill("cliente que no existe")
    page.get_by_role("button", name="Aplicar").click()
    expect(
        page.get_by_role("heading", name="No hay pérdidas con estos filtros")
    ).to_be_visible()
    expect(
        page.get_by_text("Modificá o restablecé los filtros", exact=False)
    ).to_be_visible()

    wait_for_workspace(page, "dashboard")
    page.get_by_label("Período", exact=True).select_option("custom")
    page.get_by_label("Desde").fill("2025-01-01")
    page.get_by_label("Hasta").fill("2025-02-01")
    expect(page.get_by_text("Máximo 0")).to_be_visible()
    expect(page.get_by_role("list", name="Series de evolución")).to_be_visible()
    expect(
        page.get_by_role(
            "button", name=re.compile("abrir oportunidades", re.IGNORECASE)
        )
    ).to_have_count(0)
    expect(page.get_by_text("No hay datos para esta dimensión.").first).to_be_visible()
    expect(page.get_by_role("button", name="Restablecer")).to_be_visible()


def test_representative_api_failure_is_actionable_and_expected(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    qa_page.quality_log.allow_status(503)
    page = qa_page.page

    def fail_opportunities(route: Route) -> None:
        route.fulfill(
            status=503, content_type="application/json", body='{"detail":"Unavailable"}'
        )

    page.route(re.compile(r"/api/opportunities\?.*"), fail_opportunities)
    page.reload(wait_until="networkidle")
    expect(page.get_by_role("alert").first).to_be_visible()
    expect(page.get_by_role("button", name="Reintentar").first).to_be_visible()
    run_axe(page)


def test_whatsapp_template_required_failed_and_unknown_evidence(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    page = qa_page.page
    wait_for_workspace(page, "whatsapp")
    conversations = page.get_by_role(
        "list", name="Conversaciones de WhatsApp"
    ).get_by_role("button")
    found_template_required = False
    found_failed = False
    for index in range(min(conversations.count(), 10)):
        conversation = conversations.nth(index)
        if conversation.get_attribute("aria-current") != "true":
            with page.expect_response(re.compile(r"/api/whatsapp/conversations/\d+$")):
                conversation.click()
        expect(conversation).to_have_attribute("aria-current", "true")
        expect(page.get_by_role("log", name="Historial de mensajes")).to_be_visible()
        if page.get_by_text(
            re.compile(
                r"(?:plantilla|template).*ventana|ventana.*(?:plantilla|template)",
                re.IGNORECASE,
            )
        ).count():
            found_template_required = True
            expect(page.get_by_role("button", name="Usar plantilla")).to_be_enabled()
        if page.get_by_text("No se envió").count():
            found_failed = True
            expect(
                page.get_by_role("button", name="Reenviar explícitamente").first
            ).to_be_visible()
        if found_template_required and found_failed:
            break
    assert found_template_required, (
        "canonical dataset must expose a template-required conversation"
    )
    assert found_failed, "canonical dataset must expose a failed WhatsApp message"

    wait_for_workspace(page, "whatsapp-sends")
    expect(
        page.get_by_text(re.compile("inciertos|UNKNOWN", re.IGNORECASE)).first
    ).to_be_visible()
