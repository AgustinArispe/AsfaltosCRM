from __future__ import annotations

import re

from playwright.sync_api import expect

from quality.browser.support import (
    FRONTEND_URL,
    QaPageFactory,
    assert_no_horizontal_overflow,
    run_axe,
    wait_for_workspace,
)


def test_authentication_and_protected_route_behavior(qa_pages: QaPageFactory) -> None:
    anonymous = qa_pages.create(artifact_suffix="anonymous")
    page = anonymous.page
    page.goto(f"{FRONTEND_URL}/dashboard")
    page.wait_for_url("**/login")
    expect(page.get_by_role("heading", name="Ingresar al sistema")).to_be_visible()

    anonymous.quality_log.allow_status(401)
    page.get_by_label("Email").fill("qa.supervisor@faa.test")
    page.get_by_label("Contraseña").fill("credencial-incorrecta")
    page.get_by_role("button", name="Ingresar").click()
    expect(page.get_by_role("alert")).to_contain_text("no son correctos")
    expect(page).to_have_url(re.compile(r"/login$"))

    supervisor = qa_pages.create(role="SUPERVISOR", artifact_suffix="logout")
    supervisor.page.get_by_role("button", name="Cuenta de Sofía Supervisora QA").click()
    supervisor.page.get_by_role("button", name="Cerrar sesión").click()
    supervisor.page.wait_for_url("**/login")
    supervisor.page.goto(f"{FRONTEND_URL}/pipeline")
    supervisor.page.wait_for_url("**/login")


def test_role_navigation_and_authorized_workspace_behavior(
    qa_pages: QaPageFactory,
) -> None:
    supervisor = qa_pages.create(role="SUPERVISOR", artifact_suffix="supervisor")
    seller = qa_pages.create(role="VENDEDOR", artifact_suffix="seller")

    expect(supervisor.page.get_by_role("link", name="Usuarios")).to_be_visible()
    expect(supervisor.page.get_by_role("link", name="Envíos masivos")).to_be_visible()
    wait_for_workspace(supervisor.page, "users")
    expect(
        supervisor.page.get_by_role("region", name="Administración de usuarios")
    ).to_be_visible()

    expect(seller.page.get_by_role("link", name="Usuarios")).to_have_count(0)
    expect(seller.page.get_by_role("link", name="Envíos masivos")).to_be_visible()
    seller.page.goto(f"{FRONTEND_URL}/users")
    seller.page.wait_for_url("**/pipeline")
    wait_for_workspace(seller.page, "products")
    expect(
        seller.page.get_by_role("button", name=re.compile("Desactivar|Reactivar"))
    ).to_have_count(0)
    wait_for_workspace(seller.page, "customers")
    expect(
        seller.page.get_by_role("button", name=re.compile("Importar|Eliminar"))
    ).to_have_count(0)


def test_pipeline_controls_search_detail_and_opportunity_evidence(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    page = qa_page.page
    expect(
        page.get_by_role("region", name=re.compile("Etapas del pipeline"))
    ).to_be_visible()
    for stage in ("Nueva", "Cotizada", "Negociación", "Ganada"):
        expect(page.get_by_role("heading", name=stage, exact=True)).to_be_visible()

    controls = page.get_by_role("form", name="Filtros del pipeline")
    expect(
        controls.get_by_role("searchbox", name="Buscar oportunidades")
    ).to_be_visible()
    expect(controls.get_by_role("combobox", name="Orden")).to_be_visible()
    expect(controls.get_by_role("combobox", name="Origen")).to_be_visible()
    expect(controls.get_by_text("Filtros", exact=True)).to_be_visible()
    expect(controls.get_by_role("button", name="Actualizar")).to_be_visible()

    normalized_controls = (
        controls.get_by_role("searchbox", name="Buscar oportunidades"),
        controls.get_by_role("combobox", name="Orden"),
        controls.get_by_role("combobox", name="Origen"),
        controls.get_by_text("Filtros", exact=True),
        controls.get_by_role("button", name="Actualizar"),
    )
    heights = {
        round(box["height"])
        for control in normalized_controls
        if (box := control.bounding_box()) is not None
    }
    assert len(heights) == 1
    assert next(iter(heights)) >= 36

    search = controls.get_by_role("searchbox", name="Buscar oportunidades")
    search.fill("Pavimentos del Litoral")
    expect(
        page.get_by_role("button", name=re.compile("Pavimentos del Litoral"))
    ).to_be_visible()
    expect(page.get_by_role("button", name=re.compile("Vial Patagonia"))).to_have_count(
        0
    )
    search.fill("")

    sort = controls.get_by_role("combobox", name="Orden")
    origin = controls.get_by_role("combobox", name="Origen")
    sort.select_option("oldest")
    origin.select_option("WHATSAPP")
    expect(sort).to_have_value("oldest")
    expect(origin).to_have_value("WHATSAPP")
    expect(page.get_by_role("button", name=re.compile(r", origen Web"))).to_have_count(
        0
    )
    controls.get_by_text("Filtros", exact=False).first.click()
    controls.get_by_label("Producto").select_option(label="CA-30")
    expect(controls.get_by_label("Producto")).to_have_value(re.compile(r"\d+"))
    controls.get_by_role("button", name="Limpiar").click()
    expect(sort).to_have_value("newest")
    expect(origin).to_have_value("ALL")
    with page.expect_response(re.compile(r"/api/opportunities\?")):
        controls.get_by_role("button", name="Actualizar").click()

    page.get_by_role(
        "button",
        name=re.compile("Abrir oportunidad de Constructora del Sur, origen Web"),
    ).click()
    dialog = page.get_by_role("dialog", name="Constructora del Sur")
    expect(dialog).to_be_visible()
    expect(dialog.get_by_role("heading", name="Constructora del Sur")).to_be_visible()
    expect(dialog.get_by_text("maria.lopez@visual-qa.invalid")).to_be_visible()
    expect(dialog.get_by_text("+54 9 11 5550-1001")).to_be_visible()
    expect(dialog.get_by_role("button", name="Actividad")).to_be_visible()
    expect(dialog.get_by_role("button", name="Notas")).to_be_visible()
    expect(dialog.get_by_role("button", name="Abrir WhatsApp")).to_be_visible()
    expect(dialog.get_by_role("button", name="Cotizar")).to_be_visible()
    expect(dialog.get_by_role("button", name="Marcar perdida")).to_be_visible()
    dialog.get_by_role("button", name="Cerrar detalle de oportunidad").click()
    expect(dialog).not_to_be_visible()


def test_dashboard_business_semantics_and_keyboard_day_detail(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    page = qa_page.page
    wait_for_workspace(page, "dashboard", "Dashboard")
    expect(page.get_by_role("heading", name="Necesita atención")).to_be_visible()
    for action in ("Ver seguimientos", "Abrir pendientes"):
        expect(page.get_by_role("link", name=re.compile(action))).to_be_visible()

    result = page.get_by_role("region", name="Resultado del período")
    expect(result).to_be_visible()
    expect(result.get_by_role("link", name="Ver ganadas")).to_be_visible()
    expect(result.get_by_role("link", name="Ver pérdidas")).to_be_visible()
    expect(page.get_by_role("region", name="Oportunidades activas ahora")).to_be_visible()
    expect(page.get_by_role("heading", name="Evolución comercial")).to_be_visible()
    series = page.get_by_role("list", name="Series de evolución")
    for label in ("Creadas", "Ganadas", "Pérdidas"):
        expect(series.get_by_text(label, exact=True)).to_be_visible()

    page.get_by_label("Período", exact=True).select_option("custom")
    page.get_by_label("Desde").fill("2026-08-10")
    page.get_by_label("Hasta").fill("2026-08-14")
    peak = page.get_by_role("button", name=re.compile(r"Creadas [1-9].*abrir oportunidades"))
    expect(peak.first).to_be_visible()
    peak.first.focus()
    peak.first.click()
    detail = page.get_by_role("region", name="Oportunidades del día seleccionado")
    expect(detail).to_be_visible()
    expect(detail.get_by_role("link").first).to_be_visible()
    detail.get_by_role("button", name="Cerrar detalle del día").click()
    expect(detail).not_to_be_visible()

    expect(
        page.get_by_role(
            "img", name=re.compile("Nueva: .*Cotizada: .*Negociación:")
        )
    ).to_be_visible()
    expect(page.get_by_role("region", name="Origen de oportunidades")).to_be_visible()
    for dimension in ("Productos", "Provincias"):
        page.get_by_role("button", name=dimension, exact=True).click()
        expect(
            page.get_by_role("button", name=dimension, exact=True)
        ).to_have_attribute("aria-pressed", "true")
    expect(
        page.get_by_role("region", name="Productos y provincias").get_by_role("list")
    ).to_be_visible()


def test_whatsapp_three_panel_semantics_and_states(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="VENDEDOR")
    page = qa_page.page
    wait_for_workspace(page, "whatsapp", "WhatsApp")
    conversations = page.get_by_role("list", name="Conversaciones de WhatsApp")
    expect(conversations).to_be_visible()
    expect(page.get_by_role("button", name="Esperando")).to_have_attribute(
        "aria-pressed", "false"
    )
    expect(page.get_by_role("button", name="No leídas")).to_have_attribute(
        "aria-pressed", "false"
    )
    conversations.get_by_role("button").first.click()
    expect(page.get_by_role("region", name="Chat activo")).to_be_visible()
    expect(page.get_by_role("log", name="Historial de mensajes")).to_be_visible()
    expect(
        page.get_by_role(
            "article", name=re.compile("Mensaje recibido|Mensaje enviado")
        ).first
    ).to_be_visible()
    expect(page.get_by_role("textbox", name="Mensaje")).to_be_visible()
    expect(page.get_by_text("Adjuntar imagen o PDF")).to_be_visible()
    expect(page.get_by_role("button", name="Usar plantilla")).to_be_visible()
    page.get_by_role("button", name="Contexto CRM", exact=True).click()
    context = page.get_by_role("dialog", name="Contexto CRM")
    expect(context).to_be_visible()
    expect(context.get_by_role("complementary", name="Detalle CRM")).to_be_visible()


def test_broadcast_customers_products_lost_and_users_are_understandable(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    page = qa_page.page

    wait_for_workspace(page, "whatsapp-sends", "Envíos masivos")
    expect(page.get_by_role("heading", name="Envíos masivos recientes")).to_be_visible()
    expect(
        page.get_by_text(
            "Enviá una plantilla de WhatsApp aprobada a clientes seleccionados."
        )
    ).to_be_visible()
    expect(page.get_by_role("button", name="Nuevo envío masivo")).to_be_visible()
    expect(
        page.get_by_text(re.compile("Borrador|Enviando|Completado")).first
    ).to_be_visible()

    wait_for_workspace(page, "customers", "Clientes")
    expect(page.get_by_role("searchbox", name=re.compile("Buscar"))).to_be_visible()
    expect(page.get_by_role("button", name=re.compile("Nuevo cliente"))).to_be_visible()
    expect(page.get_by_text(re.compile("CSV|Importar")).first).to_be_visible()

    wait_for_workspace(page, "products", "Productos")
    expect(page.get_by_role("region", name="Listado de productos FAA")).to_be_visible()
    expect(
        page.get_by_role("table", name="Productos disponibles en el CRM")
    ).to_be_visible()
    expect(
        page.get_by_role("button", name=re.compile("Desactivar|Reactivar")).first
    ).to_be_visible()

    wait_for_workspace(page, "lost", "Perdidas")
    expect(page.get_by_role("region", name="Resumen de pérdidas")).to_be_visible()
    expect(
        page.get_by_role("region", name="Oportunidades perdidas actuales")
    ).to_be_visible()
    expect(
        page.get_by_role("button", name=re.compile("Aplicar|Filtrar"))
    ).to_be_visible()

    wait_for_workspace(page, "users", "Usuarios")
    expect(page.get_by_role("region", name="Usuarios de FAA")).to_be_visible()
    expect(page.get_by_role("button", name="Nuevo usuario")).to_be_visible()
    expect(page.get_by_role("button", name="Editar").first).to_be_visible()
    expect(page.get_by_role("button", name="Contraseña").first).to_be_visible()


def test_primary_workspaces_have_no_automated_wcag_violations(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    page = qa_page.page
    for path in (
        "pipeline",
        "dashboard",
        "notifications",
        "whatsapp",
        "whatsapp-sends",
        "customers",
        "products",
        "lost",
        "users",
    ):
        wait_for_workspace(page, path)
        assert_no_horizontal_overflow(page)
        run_axe(page)
