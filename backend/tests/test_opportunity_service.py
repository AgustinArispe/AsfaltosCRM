from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    LeadSource,
    LossReason,
    Opportunity,
    OpportunityProduct,
    OpportunityStatus,
    OpportunityStatusHistory,
    Product,
    User,
    UserRole,
)
from app.services import (
    ClosedOpportunityError,
    DeletedCustomerError,
    EntityNotFoundError,
    InactiveProductError,
    InactiveUserError,
    InvalidLossReasonError,
    InvalidQuoteProductsError,
    InvalidStateTransitionError,
    OpportunityService,
    QuoteProductInput,
)


def persist(db_session: Session, *entities: object) -> None:
    db_session.add_all(entities)
    db_session.commit()


def make_customer(name: str = "Cliente de servicio") -> Customer:
    return Customer(name=name)


def make_user(
    *,
    email: str = "service-user@faa.test",
    is_active: bool = True,
) -> User:
    return User(
        full_name="Usuario de servicio",
        email=email,
        password_hash="hashed-password",
        role=UserRole.VENDEDOR,
        is_active=is_active,
    )


def make_product(
    name: str = "Producto de servicio",
    *,
    is_active: bool = True,
) -> Product:
    return Product(name=name, is_active=is_active)


def quote_item(
    product: Product,
    quantity: str = "1000.000",
) -> QuoteProductInput:
    return QuoteProductInput(
        product_id=product.id,
        quantity_kg=Decimal(quantity),
    )


def create_new_opportunity(
    db_session: Session,
    *,
    customer: Customer | None = None,
    assigned_user_id: int | None = None,
    changed_by_user_id: int | None = None,
) -> tuple[OpportunityService, Opportunity]:
    persisted_customer = customer or make_customer()
    if persisted_customer.id is None:
        persist(db_session, persisted_customer)
    service = OpportunityService(db_session)
    opportunity = service.create_opportunity(
        customer_id=persisted_customer.id,
        source=LeadSource.WEB,
        assigned_user_id=assigned_user_id,
        changed_by_user_id=changed_by_user_id,
    )
    return service, opportunity


def create_quoted_opportunity(
    db_session: Session,
    *,
    products: list[Product] | None = None,
) -> tuple[OpportunityService, Opportunity, list[Product]]:
    customer = make_customer()
    quoted_products = products or [make_product()]
    persist(db_session, customer, *quoted_products)
    service = OpportunityService(db_session)
    opportunity = service.create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
    )
    service.quote_opportunity(
        opportunity.id,
        [quote_item(product) for product in quoted_products],
    )
    return service, opportunity, quoted_products


def create_negotiating_opportunity(
    db_session: Session,
) -> tuple[OpportunityService, Opportunity, Product]:
    service, opportunity, products = create_quoted_opportunity(db_session)
    service.move_to_negotiation(opportunity.id)
    return service, opportunity, products[0]


def get_history(
    db_session: Session,
    opportunity_id: int,
) -> list[OpportunityStatusHistory]:
    return list(
        db_session.scalars(
            select(OpportunityStatusHistory)
            .where(OpportunityStatusHistory.opportunity_id == opportunity_id)
            .order_by(OpportunityStatusHistory.changed_at)
        )
    )


def get_quote_lines(
    db_session: Session,
    opportunity_id: int,
) -> list[OpportunityProduct]:
    return list(
        db_session.scalars(
            select(OpportunityProduct)
            .where(OpportunityProduct.opportunity_id == opportunity_id)
            .order_by(OpportunityProduct.product_id)
        )
    )


def test_create_opportunity_starts_new_and_records_history(
    db_session: Session,
) -> None:
    customer = make_customer()
    persist(db_session, customer)
    service = OpportunityService(db_session)

    opportunity = service.create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WHATSAPP,
    )
    history = get_history(db_session, opportunity.id)

    assert opportunity.status is OpportunityStatus.NUEVA
    assert opportunity.loss_reason is None
    assert opportunity.assigned_user_id is None
    assert opportunity.current_status_entered_at.tzinfo is not None
    assert len(history) == 1
    assert history[0].from_status is None
    assert history[0].to_status is OpportunityStatus.NUEVA
    assert history[0].changed_by_user_id is None
    assert history[0].changed_at == opportunity.current_status_entered_at


def test_create_opportunity_rejects_missing_customer(db_session: Session) -> None:
    service = OpportunityService(db_session)
    count_before = db_session.scalar(
        select(func.count()).select_from(Opportunity)
    )
    db_session.rollback()

    with pytest.raises(EntityNotFoundError):
        service.create_opportunity(
            customer_id=999_999_999,
            source=LeadSource.WEB,
        )

    count_after = db_session.scalar(select(func.count()).select_from(Opportunity))
    assert count_after == count_before


def test_create_opportunity_rejects_deleted_customer(db_session: Session) -> None:
    customer = make_customer()
    persist(db_session, customer)
    customer.deleted_at = datetime.now(UTC)
    db_session.commit()
    service = OpportunityService(db_session)

    with pytest.raises(DeletedCustomerError):
        service.create_opportunity(customer_id=customer.id, source=LeadSource.WEB)


def test_create_opportunity_accepts_active_assigned_user_and_actor(
    db_session: Session,
) -> None:
    customer = make_customer()
    user = make_user()
    persist(db_session, customer, user)
    service = OpportunityService(db_session)

    opportunity = service.create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
        assigned_user_id=user.id,
        changed_by_user_id=user.id,
    )
    history = get_history(db_session, opportunity.id)

    assert opportunity.assigned_user_id == user.id
    assert history[0].changed_by_user_id == user.id


def test_create_opportunity_rejects_inactive_assigned_user(
    db_session: Session,
) -> None:
    customer = make_customer()
    user = make_user(is_active=False)
    persist(db_session, customer, user)
    service = OpportunityService(db_session)

    with pytest.raises(InactiveUserError):
        service.create_opportunity(
            customer_id=customer.id,
            source=LeadSource.WEB,
            assigned_user_id=user.id,
        )


@pytest.mark.parametrize("product_count", [1, 2])
def test_quote_opportunity_accepts_one_or_multiple_products(
    db_session: Session,
    product_count: int,
) -> None:
    customer = make_customer()
    actor = make_user()
    products = [make_product(f"Producto {index}") for index in range(product_count)]
    persist(db_session, customer, actor, *products)
    service = OpportunityService(db_session)
    opportunity = service.create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
    )
    previous_status_time = opportunity.current_status_entered_at

    service.quote_opportunity(
        opportunity.id,
        [
            quote_item(product, quantity=str((index + 1) * 1000))
            for index, product in enumerate(products)
        ],
        changed_by_user_id=actor.id,
    )
    lines = get_quote_lines(db_session, opportunity.id)
    history = get_history(db_session, opportunity.id)

    assert opportunity.status is OpportunityStatus.COTIZADA
    assert opportunity.current_status_entered_at > previous_status_time
    assert len(lines) == product_count
    assert {line.product_id for line in lines} == {product.id for product in products}
    assert [entry.to_status for entry in history] == [
        OpportunityStatus.NUEVA,
        OpportunityStatus.COTIZADA,
    ]
    assert history[-1].from_status is OpportunityStatus.NUEVA
    assert history[-1].changed_by_user_id == actor.id
    assert history[-1].changed_at == opportunity.current_status_entered_at


def test_quote_opportunity_rejects_empty_product_set(db_session: Session) -> None:
    service, opportunity = create_new_opportunity(db_session)

    with pytest.raises(InvalidQuoteProductsError):
        service.quote_opportunity(opportunity.id, [])


def test_quote_opportunity_rejects_missing_product(db_session: Session) -> None:
    service, opportunity = create_new_opportunity(db_session)

    with pytest.raises(EntityNotFoundError):
        service.quote_opportunity(
            opportunity.id,
            [QuoteProductInput(999_999_999, Decimal("1"))],
        )


def test_quote_opportunity_rejects_inactive_product(db_session: Session) -> None:
    customer = make_customer()
    product = make_product(is_active=False)
    persist(db_session, customer, product)
    service = OpportunityService(db_session)
    opportunity = service.create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
    )

    with pytest.raises(InactiveProductError):
        service.quote_opportunity(opportunity.id, [quote_item(product)])


@pytest.mark.parametrize("quantity", ["0", "-0.001", "NaN"])
def test_quote_opportunity_rejects_non_positive_or_non_finite_quantity(
    db_session: Session,
    quantity: str,
) -> None:
    customer = make_customer()
    product = make_product()
    persist(db_session, customer, product)
    service = OpportunityService(db_session)
    opportunity = service.create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
    )

    with pytest.raises(InvalidQuoteProductsError):
        service.quote_opportunity(
            opportunity.id,
            [quote_item(product, quantity)],
        )


def test_quote_opportunity_rejects_duplicate_products(db_session: Session) -> None:
    customer = make_customer()
    product = make_product()
    persist(db_session, customer, product)
    service = OpportunityService(db_session)
    opportunity = service.create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
    )

    with pytest.raises(InvalidQuoteProductsError):
        service.quote_opportunity(
            opportunity.id,
            [quote_item(product, "100"), quote_item(product, "200")],
        )


def test_quote_failure_rolls_back_products_status_and_history(
    db_session: Session,
) -> None:
    customer = make_customer()
    valid_product = make_product("Producto válido")
    persist(db_session, customer, valid_product)
    service = OpportunityService(db_session)
    opportunity = service.create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
    )
    original_status_time = opportunity.current_status_entered_at

    with pytest.raises(EntityNotFoundError):
        service.quote_opportunity(
            opportunity.id,
            [
                quote_item(valid_product),
                QuoteProductInput(999_999_999, Decimal("500")),
            ],
        )

    assert opportunity.status is OpportunityStatus.NUEVA
    assert opportunity.current_status_entered_at == original_status_time
    assert get_quote_lines(db_session, opportunity.id) == []
    assert len(get_history(db_session, opportunity.id)) == 1


def test_normal_pipeline_transitions_and_history_are_coherent(
    db_session: Session,
) -> None:
    customer = make_customer()
    actor = make_user()
    product = make_product()
    persist(db_session, customer, actor, product)
    service = OpportunityService(db_session)
    opportunity = service.create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
        changed_by_user_id=actor.id,
    )
    service.quote_opportunity(
        opportunity.id,
        [quote_item(product)],
        changed_by_user_id=actor.id,
    )
    quoted_at = opportunity.current_status_entered_at
    service.move_to_negotiation(
        opportunity.id,
        changed_by_user_id=actor.id,
    )
    negotiation_at = opportunity.current_status_entered_at
    service.mark_as_won(opportunity.id, changed_by_user_id=actor.id)
    history = get_history(db_session, opportunity.id)

    assert opportunity.status is OpportunityStatus.GANADA
    assert opportunity.loss_reason is None
    assert quoted_at < negotiation_at < opportunity.current_status_entered_at
    assert [(entry.from_status, entry.to_status) for entry in history] == [
        (None, OpportunityStatus.NUEVA),
        (OpportunityStatus.NUEVA, OpportunityStatus.COTIZADA),
        (OpportunityStatus.COTIZADA, OpportunityStatus.NEGOCIACION),
        (OpportunityStatus.NEGOCIACION, OpportunityStatus.GANADA),
    ]
    assert all(entry.changed_by_user_id == actor.id for entry in history)
    assert [entry.changed_at for entry in history] == sorted(
        entry.changed_at for entry in history
    )


def test_move_to_negotiation_rejects_new_opportunity(db_session: Session) -> None:
    service, opportunity = create_new_opportunity(db_session)

    with pytest.raises(InvalidStateTransitionError):
        service.move_to_negotiation(opportunity.id)


@pytest.mark.parametrize(
    "starting_status",
    [OpportunityStatus.NUEVA, OpportunityStatus.COTIZADA],
)
def test_mark_as_won_rejects_state_jumps(
    db_session: Session,
    starting_status: OpportunityStatus,
) -> None:
    if starting_status is OpportunityStatus.NUEVA:
        service, opportunity = create_new_opportunity(db_session)
    else:
        service, opportunity, _ = create_quoted_opportunity(db_session)

    with pytest.raises(InvalidStateTransitionError):
        service.mark_as_won(opportunity.id)


@pytest.mark.parametrize(
    ("starting_status", "transition_method"),
    [
        (OpportunityStatus.COTIZADA, "move_to_negotiation"),
        (OpportunityStatus.NEGOCIACION, "mark_as_won"),
    ],
)
def test_forward_transition_requires_quoted_products(
    db_session: Session,
    starting_status: OpportunityStatus,
    transition_method: str,
) -> None:
    customer = make_customer()
    persist(db_session, customer)
    now = datetime.now(UTC)
    opportunity = Opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
        status=starting_status,
        current_status_entered_at=now,
        created_at=now,
        updated_at=now,
    )
    persist(db_session, opportunity)
    service = OpportunityService(db_session)

    with pytest.raises(InvalidQuoteProductsError):
        getattr(service, transition_method)(opportunity.id)


def test_mark_new_opportunity_as_lost_without_products(db_session: Session) -> None:
    actor = make_user()
    persist(db_session, actor)
    service, opportunity = create_new_opportunity(db_session)

    service.mark_as_lost(
        opportunity.id,
        LossReason.SIN_RESPUESTA,
        changed_by_user_id=actor.id,
    )
    history = get_history(db_session, opportunity.id)

    assert opportunity.status is OpportunityStatus.PERDIDA
    assert opportunity.loss_reason is LossReason.SIN_RESPUESTA
    assert get_quote_lines(db_session, opportunity.id) == []
    assert history[-1].from_status is OpportunityStatus.NUEVA
    assert history[-1].to_status is OpportunityStatus.PERDIDA
    assert history[-1].changed_by_user_id == actor.id


@pytest.mark.parametrize(
    "starting_status",
    [OpportunityStatus.COTIZADA, OpportunityStatus.NEGOCIACION],
)
def test_mark_quoted_or_negotiating_opportunity_as_lost_preserves_products(
    db_session: Session,
    starting_status: OpportunityStatus,
) -> None:
    service, opportunity, products = create_quoted_opportunity(db_session)
    if starting_status is OpportunityStatus.NEGOCIACION:
        service.move_to_negotiation(opportunity.id)

    service.mark_as_lost(opportunity.id, LossReason.PRECIO)
    lines = get_quote_lines(db_session, opportunity.id)
    history = get_history(db_session, opportunity.id)

    assert opportunity.status is OpportunityStatus.PERDIDA
    assert opportunity.loss_reason is LossReason.PRECIO
    assert [line.product_id for line in lines] == [products[0].id]
    assert history[-1].from_status is starting_status
    assert history[-1].to_status is OpportunityStatus.PERDIDA


def test_mark_as_lost_requires_loss_reason(db_session: Session) -> None:
    service, opportunity = create_new_opportunity(db_session)

    with pytest.raises(InvalidLossReasonError):
        service.mark_as_lost(opportunity.id, None)

    assert opportunity.status is OpportunityStatus.NUEVA
    assert opportunity.loss_reason is None


@pytest.mark.parametrize(
    "terminal_status",
    [OpportunityStatus.GANADA, OpportunityStatus.PERDIDA],
)
def test_terminal_opportunity_rejects_further_transitions_and_quote_edits(
    db_session: Session,
    terminal_status: OpportunityStatus,
) -> None:
    if terminal_status is OpportunityStatus.GANADA:
        service, opportunity, _ = create_negotiating_opportunity(db_session)
        service.mark_as_won(opportunity.id)
    else:
        service, opportunity = create_new_opportunity(db_session)
        service.mark_as_lost(opportunity.id, LossReason.OTRO)
    opportunity_id = opportunity.id

    with pytest.raises(ClosedOpportunityError):
        service.mark_as_lost(opportunity_id, LossReason.OTRO)
    with pytest.raises(ClosedOpportunityError):
        service.update_quote_products(
            opportunity_id,
            [QuoteProductInput(999_999_999, Decimal("1"))],
        )


def test_update_quote_products_replaces_current_set_without_status_change(
    db_session: Session,
) -> None:
    products = [
        make_product("Producto inicial 1"),
        make_product("Producto inicial 2"),
    ]
    service, opportunity, _ = create_quoted_opportunity(
        db_session,
        products=products,
    )
    added_product = make_product("Producto agregado")
    persist(db_session, added_product)
    status_time = opportunity.current_status_entered_at

    service.update_quote_products(
        opportunity.id,
        [quote_item(products[0], "2500"), quote_item(added_product, "750")],
    )
    lines = get_quote_lines(db_session, opportunity.id)
    history = get_history(db_session, opportunity.id)

    assert opportunity.status is OpportunityStatus.COTIZADA
    assert opportunity.current_status_entered_at == status_time
    assert {line.product_id for line in lines} == {
        products[0].id,
        added_product.id,
    }
    assert {line.product_id: line.quantity_kg for line in lines} == {
        products[0].id: Decimal("2500.000"),
        added_product.id: Decimal("750.000"),
    }
    assert len(history) == 2


def test_update_quote_products_is_allowed_in_negotiation(
    db_session: Session,
) -> None:
    service, opportunity, product = create_negotiating_opportunity(db_session)
    status_time = opportunity.current_status_entered_at

    service.update_quote_products(
        opportunity.id,
        [quote_item(product, "1800")],
    )
    lines = get_quote_lines(db_session, opportunity.id)
    history = get_history(db_session, opportunity.id)

    assert opportunity.status is OpportunityStatus.NEGOCIACION
    assert opportunity.current_status_entered_at == status_time
    assert lines[0].quantity_kg == Decimal("1800.000")
    assert len(history) == 3


def test_update_quote_allows_existing_inactive_product_quantity_change(
    db_session: Session,
) -> None:
    service, opportunity, products = create_quoted_opportunity(db_session)
    product = products[0]
    product.is_active = False
    db_session.commit()

    service.update_quote_products(
        opportunity.id,
        [quote_item(product, "2200")],
    )
    lines = get_quote_lines(db_session, opportunity.id)

    assert lines[0].product_id == product.id
    assert lines[0].quantity_kg == Decimal("2200.000")


def test_update_quote_rejects_new_inactive_product_and_preserves_existing_set(
    db_session: Session,
) -> None:
    service, opportunity, existing_products = create_quoted_opportunity(db_session)
    inactive_product = make_product("Producto inactivo", is_active=False)
    persist(db_session, inactive_product)

    with pytest.raises(InactiveProductError):
        service.update_quote_products(
            opportunity.id,
            [quote_item(existing_products[0]), quote_item(inactive_product)],
        )

    lines = get_quote_lines(db_session, opportunity.id)
    assert [line.product_id for line in lines] == [existing_products[0].id]


def test_update_quote_rejects_empty_set_and_preserves_existing_products(
    db_session: Session,
) -> None:
    service, opportunity, products = create_quoted_opportunity(db_session)

    with pytest.raises(InvalidQuoteProductsError):
        service.update_quote_products(opportunity.id, [])

    lines = get_quote_lines(db_session, opportunity.id)
    assert [line.product_id for line in lines] == [products[0].id]


def test_update_quote_rejects_new_opportunity(db_session: Session) -> None:
    service, opportunity = create_new_opportunity(db_session)

    with pytest.raises(InvalidQuoteProductsError):
        service.update_quote_products(opportunity.id, [])


def test_assign_user_does_not_change_status_time_or_history(
    db_session: Session,
) -> None:
    user = make_user()
    persist(db_session, user)
    service, opportunity = create_new_opportunity(db_session)
    status_time = opportunity.current_status_entered_at

    service.assign_user(opportunity.id, user.id)
    history = get_history(db_session, opportunity.id)

    assert opportunity.assigned_user_id == user.id
    assert opportunity.status is OpportunityStatus.NUEVA
    assert opportunity.current_status_entered_at == status_time
    assert len(history) == 1


def test_assign_user_can_clear_assignment(db_session: Session) -> None:
    customer = make_customer()
    user = make_user()
    persist(db_session, customer, user)
    service = OpportunityService(db_session)
    opportunity = service.create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
        assigned_user_id=user.id,
    )

    service.assign_user(opportunity.id, None)

    assert opportunity.assigned_user_id is None


def test_assign_user_rejects_inactive_user(db_session: Session) -> None:
    inactive_user = make_user(is_active=False)
    persist(db_session, inactive_user)
    service, opportunity = create_new_opportunity(db_session)
    status_time = opportunity.current_status_entered_at

    with pytest.raises(InactiveUserError):
        service.assign_user(opportunity.id, inactive_user.id)

    assert opportunity.assigned_user_id is None
    assert opportunity.current_status_entered_at == status_time


def test_opportunity_mutations_lock_the_row_for_update(db_session: Session) -> None:
    service, opportunity = create_new_opportunity(db_session)
    statements: list[str] = []
    connection = db_session.get_bind()
    assert isinstance(connection, Connection)

    def capture_statement(
        _connection: Connection,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", capture_statement)
    try:
        service.assign_user(opportunity.id, None)
    finally:
        event.remove(connection, "before_cursor_execute", capture_statement)

    assert any(
        "FROM opportunities" in statement and "FOR UPDATE" in statement
        for statement in statements
    )
