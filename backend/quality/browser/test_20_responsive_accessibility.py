from __future__ import annotations

import re
from typing import cast

import pytest
from playwright.sync_api import expect

from quality.browser.support import (
    FRONTEND_URL,
    QaPageFactory,
    Theme,
    assert_no_horizontal_overflow,
    run_axe,
    stable_screenshot,
    wait_for_workspace,
)


@pytest.mark.parametrize("viewport", [(1440, 900), (768, 920), (390, 844)])
def test_lost_workspace_reason_filter_and_detail(
    qa_pages: QaPageFactory, viewport: tuple[int, int]
) -> None:
    qa_page = qa_pages.create(role="VENDEDOR", viewport=viewport)
    page = qa_page.page
    wait_for_workspace(page, "lost?period=all")
    reasons = page.get_by_role("region", name="Motivos de pérdida")
    reason_list = reasons.get_by_role("list")
    first_reason = reason_list.get_by_role("button").first
    expect(first_reason).to_be_visible()
    recommendation = page.get_by_role("complementary", name="Qué mejorar")
    history = page.get_by_role("region", name="Historial de pérdidas")
    expect(recommendation).to_be_visible()
    assert recommendation.evaluate(
        "node => node.previousElementSibling?.classList.contains('closed-summary')"
        " && node.nextElementSibling?.classList.contains('closed-history')"
    )
    recommendation_box = recommendation.bounding_box()
    history_box = history.bounding_box()
    assert recommendation_box is not None and history_box is not None
    assert recommendation_box["width"] == history_box["width"]
    if viewport[0] == 1440:
        assert recommendation.evaluate("""node => {
            const heading = node.querySelector('h2');
            const message = node.querySelector('p');
            return Math.abs(heading.getBoundingClientRect().top - message.getBoundingClientRect().top) < 1;
        }""")
    assert_no_horizontal_overflow(page)
    rows = page.get_by_role("table", name="Oportunidades actualmente perdidas").locator(
        "tbody tr"
    )
    assert rows.count() > 1
    assert rows.evaluate_all(
        "rows => rows.every(row => Array.from(row.cells).every(cell => "
        "cell.getBoundingClientRect().bottom <= row.getBoundingClientRect().bottom))"
    )
    run_axe(page)
    stable_screenshot(page, f"lost-workspace-{viewport[0]}")
    page.get_by_role("button", name="Fichas", exact=True).click()
    cards = page.get_by_role("list", name="Fichas de oportunidades perdidas")
    expect(cards.get_by_role("link").first).to_be_visible()
    assert_no_horizontal_overflow(page)
    run_axe(page)
    stable_screenshot(page, f"lost-cards-{viewport[0]}")
    page.get_by_role("button", name="Tabla", exact=True).click()
    reasons.get_by_role("button", name="Por kilos").click()
    expect(first_reason).to_contain_text("kg")
    stable_screenshot(page, f"lost-workspace-kg-{viewport[0]}")
    filters = page.get_by_role("button", name="Filtros adicionales")
    expect(filters).to_have_attribute("aria-expanded", "false")
    filters.click()
    expect(page.get_by_label("Responsable")).to_be_visible()
    page.get_by_label("Más períodos").select_option("custom")
    expect(page.get_by_label("Desde")).to_be_visible()
    assert_no_horizontal_overflow(page)
    run_axe(page)
    stable_screenshot(page, f"lost-filters-{viewport[0]}")
    filters.click()

    first_reason.click()
    selected_reason = reason_list.get_by_role("button", pressed=True)
    expect(selected_reason).to_have_count(1)
    expect(recommendation).to_contain_text(
        selected_reason.locator("strong").inner_text()
    )
    expect(
        reasons.get_by_role("button", name="Por kilos", pressed=True)
    ).to_be_visible()
    expect(page).to_have_url(re.compile(r"/lost\?.*reason="))
    page.get_by_role("button", name="Fichas", exact=True).click()
    expect(cards.get_by_role("link").first).to_be_visible()
    assert_no_horizontal_overflow(page)
    cards.get_by_role("link").first.press("Enter")
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    dialog.get_by_role("link", name="Volver a Perdidas").click()
    expect(dialog).to_have_count(0)
    expect(reason_list.get_by_role("button", pressed=True)).to_have_count(1)
    expect(page.get_by_role("button", name="Fichas", pressed=True)).to_be_visible()
    page.get_by_role("button", name="Tabla", exact=True).click()
    expect(rows.first).to_be_visible()


def test_wheel_over_pipeline_cards_scrolls_the_page_in_both_directions(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR", viewport=(1440, 540))
    page = qa_page.page
    column = page.get_by_role("region", name="Cotizada", exact=True)
    column.get_by_role("button").first.hover()
    page.mouse.wheel(0, 400)
    page.wait_for_function("window.scrollY > 100")
    before = cast(float, page.evaluate("window.scrollY"))
    page.mouse.wheel(0, -350)
    page.wait_for_function("(before) => window.scrollY < before", arg=before)
    assert cast(float, page.evaluate("window.scrollY")) < before


def test_opportunity_modal_keeps_the_pipeline_in_place_while_scrolling(
    qa_pages: QaPageFactory,
) -> None:
    page = qa_pages.create(role="SUPERVISOR", viewport=(1440, 480)).page
    trigger = page.get_by_role(
        "button",
        name=re.compile("Abrir oportunidad de Vial Patagonia, origen Web"),
    )
    expect(trigger).to_be_visible()
    page.evaluate("window.scrollTo(0, 100)")
    trigger.scroll_into_view_if_needed()
    before = cast(float, page.evaluate("window.scrollY"))
    assert before > 0
    trigger.click()

    detail = page.get_by_role("dialog", name="Vial Patagonia")
    expect(detail.get_by_role("button", name="Cotizar")).to_be_visible()
    progress = detail.get_by_role("region", name="Avance de la oportunidad")
    expect(progress.locator('[aria-current="step"]')).to_contain_text("Para cotizar")
    progress_box = progress.bounding_box()
    delete_box = detail.get_by_role(
        "button", name="Eliminar oportunidad"
    ).bounding_box()
    assert progress_box is not None and delete_box is not None
    assert progress_box["y"] >= delete_box["y"] + delete_box["height"]
    surface = detail.locator(":scope > .crm-modal__surface")
    surface.hover(position={"x": 24, "y": 200})
    page.mouse.wheel(0, 400)
    page.wait_for_function(
        "surface => surface.scrollTop > 0", arg=surface.element_handle()
    )
    assert page.evaluate("window.scrollY") == before

    # Extra wheel input at the dialog's scroll boundary stays inside the modal.
    surface.evaluate("surface => { surface.scrollTop = surface.scrollHeight }")
    page.mouse.wheel(0, 400)
    page.mouse.move(20, 240)
    page.mouse.wheel(0, -400)
    page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
    )
    assert page.evaluate("window.scrollY") == before

    detail.get_by_role("button", name="Cerrar detalle de oportunidad").click()
    expect(detail).not_to_be_visible()
    expect(trigger).to_be_focused()
    assert page.evaluate("window.scrollY") == before
    page.mouse.move(220, 300)
    page.mouse.wheel(0, -400)
    page.wait_for_function("before => window.scrollY < before", arg=before)


@pytest.mark.matrix
@pytest.mark.parametrize(
    ("theme", "viewport"),
    [
        ("light", (1440, 900)),
        ("dark", (1440, 900)),
        ("light", (390, 844)),
        ("dark", (390, 844)),
    ],
)
def test_login_theme_and_responsive_accessibility(
    qa_pages: QaPageFactory,
    theme: Theme,
    viewport: tuple[int, int],
) -> None:
    qa_page = qa_pages.create(theme=theme, viewport=viewport)
    page = qa_page.page
    page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
    expect(page.locator("html")).to_have_attribute("data-theme", theme)
    expect(page.get_by_role("heading", name="Ingresar al sistema")).to_be_visible()
    run_axe(page)
    assert_no_horizontal_overflow(page)


@pytest.mark.matrix
@pytest.mark.parametrize(
    ("width", "height"),
    [(1920, 1080), (1440, 900), (1366, 768), (1280, 800), (390, 844)],
)
def test_representative_viewport_matrix(
    qa_pages: QaPageFactory,
    width: int,
    height: int,
) -> None:
    qa_page = qa_pages.create(
        role="SUPERVISOR",
        viewport=(width, height),
        artifact_suffix=f"{width}x{height}",
    )
    page = qa_page.page
    for path in (
        "pipeline",
        "dashboard",
        "whatsapp",
        "won",
        "customers",
        "users",
    ):
        wait_for_workspace(page, path)
        assert_no_horizontal_overflow(page)
        if path == "whatsapp":
            expect(page.get_by_role("heading", name="WhatsApp", level=1)).to_have_count(
                0
            )
            if width >= 768:
                expect(
                    page.get_by_role("list", name="Conversaciones de WhatsApp")
                ).to_be_visible()
            else:
                expect(
                    page.get_by_role("button", name="Abrir navegación")
                ).to_be_visible()
        else:
            expect(page.get_by_role("heading", level=1)).to_be_visible()
    if width < 1024:
        expect(page.get_by_role("button", name="Abrir navegación")).to_be_visible()
    else:
        expect(
            page.get_by_role("button", name=re.compile("Contraer|Expandir navegación"))
        ).to_be_visible()


@pytest.mark.matrix
@pytest.mark.parametrize(
    ("scale", "css_width", "css_height"),
    [(100, 1920, 1080), (125, 1536, 864), (150, 1280, 720), (200, 960, 540)],
)
def test_effective_zoom_matrix_uses_reduced_css_viewport(
    qa_pages: QaPageFactory,
    scale: int,
    css_width: int,
    css_height: int,
) -> None:
    qa_page = qa_pages.create(
        role="SUPERVISOR",
        viewport=(css_width, css_height),
        artifact_suffix=f"zoom-{scale}",
    )
    page = qa_page.page
    for path in ("dashboard", "pipeline", "whatsapp", "customers", "users"):
        wait_for_workspace(page, path)
        assert_no_horizontal_overflow(page)
    wait_for_workspace(page, "pipeline")
    trigger = page.get_by_role(
        "button",
        name=re.compile("Abrir oportunidad de Constructora del Sur, origen Web"),
    )
    trigger.click()
    dialog = page.get_by_role("dialog", name="Constructora del Sur")
    expect(dialog).to_be_visible()
    box = dialog.bounding_box()
    assert box is not None
    assert box["x"] >= 0 and box["y"] >= 0
    assert box["x"] + box["width"] <= css_width + 1
    assert box["y"] + box["height"] <= css_height + 1
    expect(
        dialog.get_by_role("button", name="Cerrar detalle de oportunidad")
    ).to_be_visible()


def test_sidebar_collapsed_and_mobile_drawer_keyboard_contract(
    qa_pages: QaPageFactory,
) -> None:
    desktop = qa_pages.create(role="SUPERVISOR", artifact_suffix="collapsed")
    collapse = desktop.page.get_by_role("button", name="Contraer navegación")
    collapse.click()
    expect(
        desktop.page.get_by_role("button", name="Expandir navegación")
    ).to_be_visible()
    expect(desktop.page.get_by_role("link", name="Oportunidades")).to_have_attribute(
        "title", "Oportunidades"
    )
    desktop.page.get_by_role("button", name="Cambiar a modo oscuro").press("Enter")
    expect(desktop.page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(
        desktop.page.get_by_role("button", name="Cambiar a modo claro")
    ).to_have_attribute("title", "Cambiar a modo claro")
    desktop.page.get_by_role("button", name="Expandir navegación").click()
    expect(
        desktop.page.get_by_role("button", name="Contraer navegación")
    ).to_be_visible()

    mobile = qa_pages.create(
        role="SUPERVISOR", viewport=(390, 844), artifact_suffix="mobile-drawer"
    )
    trigger = mobile.page.get_by_role("button", name="Abrir navegación")
    trigger.focus()
    trigger.click()
    drawer = mobile.page.get_by_role("complementary", name="Navegación móvil")
    expect(drawer).to_be_visible()
    expect(drawer.get_by_role("link", name="Resumen comercial")).to_be_visible()
    final_links = drawer.get_by_role("navigation").get_by_role("link")
    assert final_links.all_text_contents()[-4:] == [
        "Perdidas",
        "Ganadas",
        "Productos",
        "Usuarios",
    ]
    drawer.get_by_role("button", name="Cambiar a modo oscuro").click()
    expect(mobile.page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(drawer.get_by_role("button", name="Cambiar a modo claro")).to_be_visible()
    stable_screenshot(mobile.page, "sidebar-mobile-dark")
    mobile.page.keyboard.press("Escape")
    expect(drawer).not_to_be_visible()
    expect(trigger).to_be_focused()


def test_modal_traps_and_restores_focus_and_quote_escape_preserves_draft(
    qa_pages: QaPageFactory,
) -> None:
    qa_page = qa_pages.create(role="SUPERVISOR")
    page = qa_page.page
    trigger = page.get_by_role(
        "button",
        name=re.compile(
            "Abrir oportunidad de Vial Patagonia, origen Web, estado Para cotizar"
        ),
    )
    trigger.focus()
    trigger.click()
    detail = page.get_by_role("dialog", name="Vial Patagonia")
    expect(detail).to_be_visible()
    page.keyboard.press("Tab")
    focused_inside = cast(
        bool,
        detail.evaluate("(dialog) => dialog.contains(document.activeElement)"),
    )
    assert focused_inside
    detail.get_by_role("button", name="Cotizar").click()
    quote = page.get_by_role("dialog", name="Cotizar oportunidad")
    expect(quote).to_be_visible()
    quote.get_by_role("radio", name="CA-30").check()
    page.keyboard.press("Enter")
    expect(quote.get_by_role("heading", name="Indicá la cantidad")).to_be_visible()
    quote.get_by_label("Cantidad (kg)").fill("1250")
    page.keyboard.press("Escape")
    expect(quote.get_by_role("heading", name="Elegí un producto")).to_be_visible()
    page.keyboard.press("Escape")
    expect(quote.get_by_role("heading", name="¿Descartar los cambios?")).to_be_visible()
    quote.get_by_role("button", name="Seguir editando").click()
    expect(quote.get_by_role("radio", name="CA-30")).to_be_checked()
    quote.get_by_role("button", name=re.compile("Cerrar cotizar oportunidad")).click()
    quote.get_by_role("button", name="Descartar cambios").click()
    expect(detail).to_be_visible()
    detail.get_by_role("button", name="Cerrar detalle de oportunidad").click()
    expect(trigger).to_be_focused()


@pytest.mark.matrix
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_light_dark_accessibility_and_reduced_motion(
    qa_pages: QaPageFactory,
    theme: Theme,
) -> None:
    qa_page = qa_pages.create(
        role="SUPERVISOR",
        theme=theme,
        reduced_motion="reduce",
        artifact_suffix=theme,
    )
    page = qa_page.page
    reduced = cast(
        bool, page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    )
    assert reduced
    for path in ("pipeline", "dashboard", "notifications", "whatsapp", "won"):
        wait_for_workspace(page, path)
        run_axe(page)
        assert_no_horizontal_overflow(page)
        if path == "notifications":
            unread_row = page.locator(".notification-row--unread").first
            read_row = page.locator(
                ".notification-row:not(.notification-row--unread)"
            ).first
            expect(unread_row).to_be_visible()
            expect(read_row).to_be_visible()
            expect(
                page.get_by_role(
                    "button", name=re.compile("Marcar como (?:no )?leída")
                ).first
            ).to_be_visible()
