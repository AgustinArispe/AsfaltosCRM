from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from quality.browser.support import QaPageFactory, wait_for_workspace


@pytest.mark.mutating
def test_pipeline_keyboard_drag_persists_after_reload(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    page = qa_page.page
    source = page.get_by_role(
        "button",
        name=re.compile(
            "Abrir oportunidad de Rutas del Centro, origen WhatsApp.*arrastrar"
        ),
    )
    source.focus()
    page.keyboard.press("Space")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("Space")
    target = page.get_by_role("region", name="Negociación")
    expect(
        target.get_by_role("button", name=re.compile("Rutas del Centro"))
    ).to_be_visible()
    page.reload(wait_until="networkidle")
    expect(
        page.get_by_role("region", name="Negociación").get_by_role(
            "button", name=re.compile("Rutas del Centro")
        )
    ).to_be_visible()


@pytest.mark.mutating
def test_pipeline_drag_persists_after_reload(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    page = qa_page.page
    source = page.get_by_role(
        "button",
        name=re.compile("Abrir oportunidad de Vial Patagonia, origen Web.*arrastrar"),
    ).first
    target = page.get_by_role("region", name="Negociación")
    source_box = source.bounding_box()
    target_box = target.bounding_box()
    assert source_box is not None and target_box is not None
    page.mouse.move(
        source_box["x"] + source_box["width"] / 2,
        source_box["y"] + source_box["height"] / 2,
    )
    page.mouse.down()
    page.mouse.move(
        target_box["x"] + target_box["width"] / 2,
        target_box["y"] + target_box["height"] / 2,
        steps=12,
    )
    page.mouse.up()
    expect(
        target.get_by_role("button", name=re.compile("Vial Patagonia"))
    ).to_be_visible()
    page.reload(wait_until="networkidle")
    expect(
        page.get_by_role("region", name="Negociación").get_by_role(
            "button", name=re.compile("Vial Patagonia")
        )
    ).to_be_visible()


@pytest.mark.mutating
def test_quote_keyboard_validation_edit_remove_and_persistence(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="VENDEDOR")
    page = qa_page.page
    page.get_by_role(
        "button",
        name=re.compile("Abrir oportunidad de Constructora del Sur, origen Web"),
    ).click()
    detail = page.get_by_role("dialog", name="Constructora del Sur")
    detail.get_by_role("button", name="Cotizar").click()
    quote = page.get_by_role("dialog", name="Cotizar oportunidad")

    quote.get_by_role("radio", name="CA-30").check()
    page.keyboard.press("Enter")
    quantity = quote.get_by_label("Cantidad (kg)")
    quantity.fill("0")
    page.keyboard.press("Enter")
    expect(quote.get_by_text("Ingresá una cantidad mayor que cero.")).to_be_visible()
    quantity.fill("1200")
    page.keyboard.press("Enter")
    expect(quote.get_by_role("heading", name="Revisá la cotización")).to_be_visible()

    quote.get_by_role("button", name="Agregar otro producto").click()
    quote.get_by_role("radio", name="CA-20").check()
    quote.get_by_role("button", name="Continuar con cantidad").click()
    quote.get_by_label("Cantidad (kg)").fill("300")
    quote.get_by_role("button", name="Agregar producto").click()
    quote.get_by_role("button", name="Editar").first.click()
    quote.get_by_role("button", name="Continuar con cantidad").click()
    quote.get_by_label("Cantidad (kg)").fill("1500")
    quote.get_by_role("button", name="Guardar línea").click()
    quote.get_by_role("button", name="Quitar").nth(1).click()
    expect(quote.get_by_text("CA-20")).to_have_count(0)

    quote.get_by_role("button", name="Revisar y confirmar").click()
    expect(quote.get_by_role("heading", name="Confirmá la cotización")).to_be_visible()
    expect(quote.get_by_text("1.500 kg", exact=True).first).to_be_visible()
    expect(quote.get_by_role("button", name="Confirmar cotización")).to_have_count(1)
    quote.get_by_role("button", name="Confirmar cotización").click()
    expect(detail.get_by_text("Cotizada", exact=True)).to_be_visible()
    expect(detail.get_by_text("CA-30", exact=True)).to_be_visible()
    page.reload(wait_until="networkidle")
    expect(
        page.get_by_role("dialog", name="Constructora del Sur")
        .get_by_text("1.500 kg")
        .first
    ).to_be_visible()


@pytest.mark.mutating
def test_loss_action_redirects_from_hidden_workspace_to_dashboard(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    page = qa_page.page
    page.get_by_role(
        "button", name=re.compile("Abrir oportunidad de Ramiro Sosa")
    ).click()
    detail = page.get_by_role("dialog", name="Ramiro Sosa")
    detail.get_by_role("button", name="Marcar perdida").click()
    loss = page.get_by_role("dialog", name="Marcar como perdida")
    loss.get_by_role("button", name="Confirmar pérdida").click()
    expect(loss.get_by_role("alert")).to_have_text("Seleccioná un motivo de pérdida.")
    loss.get_by_label("Motivo").select_option("PRECIO")
    loss.get_by_role("button", name="Confirmar pérdida").click()
    page.wait_for_url("**/dashboard")
    expect(page.get_by_role("heading", name="Dashboard", level=1)).to_be_visible()
    expect(page.get_by_role("link", name="Perdidas")).to_have_count(0)


@pytest.mark.mutating
def test_notifications_read_action_and_badge_synchronize(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="VENDEDOR")
    page = qa_page.page
    navigation = page.get_by_role("navigation", name="Navegación principal")
    expect(
        navigation.get_by_role("link", name=re.compile("Notificaciones"))
    ).to_contain_text(re.compile(r"[1-9]"))
    wait_for_workspace(page, "notifications")
    page.get_by_role(
        "button",
        name=re.compile(r"Seguimiento pendiente:.*sin leer, activa", re.IGNORECASE),
    ).first.click()
    detail = page.get_by_role("dialog", name=re.compile(".+"))
    expect(detail).to_be_visible()
    detail.get_by_role("button", name="Cerrar detalle de oportunidad").click()
    page.wait_for_url("**/notifications")
    page.get_by_role("button", name="Sin leer", exact=True).click()
    expect(page.get_by_role("button", name="Sin leer", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    page.get_by_role("button", name="Marcar activas como leídas").click()
    expect(
        page.get_by_role("button", name=re.compile(r"sin leer, activa", re.IGNORECASE))
    ).to_have_count(0)
    expect(
        page.get_by_text(re.compile(r"Se marcaron \d+ notificaciones activas"))
    ).to_be_attached()
    expect(navigation.get_by_role("link", name="Notificaciones")).to_be_visible()


@pytest.mark.mutating
def test_whatsapp_expired_window_requires_approved_template(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="VENDEDOR")
    page = qa_page.page
    wait_for_workspace(page, "whatsapp")
    conversations = page.get_by_role("list", name="Conversaciones de WhatsApp")
    composer = page.get_by_role("textbox", name="Mensaje")
    conversations.get_by_role("button", name=re.compile("Paula Benítez")).click()
    expect(composer).to_be_disabled()
    expect(
        page.get_by_text(
            "La ventana de respuesta está cerrada. Se requiere un template aprobado."
        )
    ).to_be_visible()
    expect(page.get_by_role("button", name="Usar plantilla")).to_be_enabled()


@pytest.mark.mutating
def test_customer_product_and_user_administration(qa_pages: QaPageFactory) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    page = qa_page.page

    wait_for_workspace(page, "customers")
    page.get_by_role("button", name="Nuevo cliente").click()
    customer = page.get_by_role("dialog", name="Nuevo cliente")
    customer.get_by_label("Nombre").fill("Cliente CRM-026")
    customer.get_by_label("Empresa").fill("QA Navegador")
    customer.get_by_label("Email").fill("crm026@visual-qa.invalid")
    customer.get_by_label("Teléfono").fill("+54 9 11 5550-2026")
    customer.get_by_label("Provincia").fill("Buenos Aires")
    customer.get_by_role("button", name="Crear cliente").click()
    search = page.get_by_role("searchbox", name="Buscar clientes")
    search.fill("Cliente CRM-026")
    created_customer = page.get_by_role("link", name="Cliente CRM-026")
    expect(created_customer).to_be_visible()
    created_customer.click()
    customer_detail = page.get_by_role("dialog", name="Ficha de cliente")
    expect(
        customer_detail.get_by_role("heading", name="Cliente CRM-026")
    ).to_be_visible()
    customer_detail.get_by_role("button", name="Editar").click()
    customer_editor = page.get_by_role("dialog", name="Editar cliente")
    customer_editor.get_by_label("Empresa").fill("QA Navegador editado")
    customer_editor.get_by_role("button", name="Guardar cambios").click()
    expect(
        customer_detail.get_by_text("QA Navegador editado", exact=True)
    ).to_be_visible()

    wait_for_workspace(page, "products")
    page.get_by_role("button", name="Nuevo producto").click()
    product = page.get_by_role("dialog", name="Nuevo producto")
    product.get_by_label("Nombre").fill("Producto CRM-026")
    product.get_by_role("button", name="Crear producto").click()
    expect(page.get_by_text("Producto CRM-026", exact=True)).to_be_visible()
    page.get_by_role("button", name="Editar Producto CRM-026").click()
    editor = page.get_by_role("dialog", name="Editar producto")
    editor.get_by_label("Nombre").fill("Producto CRM-026 editado")
    editor.get_by_role("button", name="Guardar cambios").click()
    page.get_by_role("button", name="Desactivar Producto CRM-026 editado").click()
    deactivate = page.get_by_role(
        "dialog", name=re.compile("Desactivar Producto CRM-026")
    )
    deactivate.get_by_role("button", name="Desactivar producto", exact=True).click()
    page.get_by_role("button", name="Reactivar Producto CRM-026 editado").click()
    expect(
        page.get_by_role("button", name="Desactivar Producto CRM-026 editado")
    ).to_be_visible()

    wait_for_workspace(page, "users")
    page.get_by_role("button", name="Nuevo usuario").click()
    user = page.get_by_role("dialog", name="Nuevo usuario")
    user.get_by_label("Nombre completo").fill("Usuario CRM-026")
    user.get_by_label("Email").fill("usuario.crm026@faa.test")
    user.get_by_label("Rol").select_option("VENDEDOR")
    user.get_by_label("Contraseña inicial").fill("CRM-026-password-2026!")
    user.get_by_role("button", name="Guardar usuario").click()
    row = page.get_by_role("row", name=re.compile("Usuario CRM-026"))
    row.get_by_role("button", name="Editar").click()
    user_editor = page.get_by_role("dialog", name="Editar usuario")
    user_editor.get_by_label("Nombre completo").fill("Usuario CRM-026 editado")
    user_editor.get_by_role("button", name="Guardar usuario").click()
    row = page.get_by_role("row", name=re.compile("Usuario CRM-026 editado"))
    row.get_by_role("button", name="Contraseña").click()
    password = page.get_by_role("dialog", name="Reemplazar contraseña")
    password.get_by_label("Nueva contraseña").fill("CRM-026-password-new-2026!")
    password.get_by_role("button", name=re.compile("Reemplazar|Guardar")).click()
    row.get_by_role("button", name="Desactivar").click()
    page.get_by_role("dialog", name="Desactivar acceso").get_by_role(
        "button", name="Desactivar usuario"
    ).click()
    expect(row.get_by_text("Inactivo", exact=True)).to_be_visible()
    row.get_by_role("button", name="Activar").click()
    page.get_by_role("dialog", name="Activar acceso").get_by_role(
        "button", name="Activar usuario"
    ).click()
    expect(row.get_by_text("Activo", exact=True)).to_be_visible()
