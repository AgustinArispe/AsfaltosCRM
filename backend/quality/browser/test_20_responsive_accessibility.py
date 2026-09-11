from __future__ import annotations

import re
from typing import cast

import pytest
from playwright.sync_api import expect

from quality.browser.support import (
    QaPageFactory,
    Theme,
    assert_no_horizontal_overflow,
    run_axe,
    wait_for_workspace,
)


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
        name=re.compile("Abrir oportunidad de Constructora del Sur, origen Web"),
    )
    trigger.focus()
    trigger.click()
    detail = page.get_by_role("dialog", name="Constructora del Sur")
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
    for path in ("pipeline", "dashboard", "whatsapp", "won"):
        wait_for_workspace(page, path)
        run_axe(page)
        assert_no_horizontal_overflow(page)
