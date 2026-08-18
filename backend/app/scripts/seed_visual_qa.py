from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from os import getenv
from uuid import UUID, uuid5

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import (
    RuntimeEnvironment,
    get_app_environment,
    get_database_url,
    get_whatsapp_provider_name,
)
from app.db.session import SessionLocal
from app.models import (
    Customer,
    LeadSource,
    LossReason,
    Notification,
    NotificationType,
    Opportunity,
    OpportunityProduct,
    OpportunityStatus,
    Product,
    User,
    UserRole,
    WhatsAppAttachment,
    WhatsAppBroadcast,
    WhatsAppBroadcastAuditEvent,
    WhatsAppBroadcastAuditEventType,
    WhatsAppBroadcastRecipient,
    WhatsAppBroadcastRecipientStatus,
    WhatsAppConsentDecision,
    WhatsAppConsentSource,
    WhatsAppConversation,
    WhatsAppDispatchState,
    WhatsAppMessage,
    WhatsAppMessageType,
    WhatsAppProviderState,
    WhatsAppStorageStatus,
)
from app.services.customer_service import CustomerService
from app.services.legendary_service import LegendaryService
from app.services.notification_service import NotificationService
from app.services.opportunity_note_service import OpportunityNoteService
from app.services.opportunity_service import OpportunityService, QuoteProductInput
from app.services.product_service import ProductService
from app.services.user_service import UserService
from app.services.whatsapp_broadcast_projection_service import (
    recompute_broadcast_recipient_projection,
)
from app.services.whatsapp_broadcast_service import (
    BroadcastCreateInput,
    BroadcastParameterInput,
    WhatsAppBroadcastService,
)
from app.services.whatsapp_consent_service import (
    ConsentEventInput,
    WhatsAppConsentService,
)
from app.services.whatsapp_conversation_service import WhatsAppConversationService
from app.services.whatsapp_inbound_service import (
    InboundAttachmentInput,
    InboundMessageInput,
    WhatsAppInboundService,
)
from app.services.whatsapp_message_service import (
    OutboundMessageInput,
    WhatsAppMessageService,
)
from app.services.whatsapp_status_service import (
    ProviderStatusInput,
    WhatsAppStatusService,
)
from app.whatsapp import (
    FakeMediaStorage,
    FakeWhatsAppProvider,
    ProviderErrorKind,
)
from app.whatsapp.runtime import development_fake_templates

_NAMESPACE = UUID("a81d2509-16e8-47ad-9c5a-49ea24be7471")
_SUPERVISOR_EMAIL = "qa.supervisor@faa.test"
_SELLER_EMAIL = "qa.vendedor@faa.test"
_LEGACY_QA_EMAILS = frozenset({_SUPERVISOR_EMAIL, "crm027.visual@faa.test"})
_DATASET_VERSION = "crm027-visual-qa-v1"


@dataclass(frozen=True, slots=True)
class CustomerSeed:
    name: str
    company: str | None
    email: str | None
    phone: str | None
    province: str | None
    legendary_override: bool = False


@dataclass(frozen=True, slots=True)
class OpportunitySeed:
    customer_index: int
    source: LeadSource
    status: OpportunityStatus
    age_days: int
    stage_age_days: int
    quote: tuple[tuple[str, str], ...] = ()
    loss_reason: LossReason | None = None
    reopen: bool = False


PRODUCT_NAMES = (
    "CA-30",
    "CA-20",
    "Emulsión catiónica CRR-1",
    "Emulsión catiónica CSS-1h",
    "Asfalto modificado AM-3",
    "Mezcla asfáltica en frío",
    "Sellador asfáltico",
    "Imprimación asfáltica",
    "Asfalto diluido MC-30",
)

CUSTOMERS = (
    CustomerSeed(
        "María López",
        "Constructora del Sur",
        "maria.lopez@visual-qa.invalid",
        "+54 9 11 5550-1001",
        "Buenos Aires",
        True,
    ),
    CustomerSeed(
        "Esteban Ríos",
        "Vial Patagonia",
        "esteban.rios@visual-qa.invalid",
        "+54 9 11 5550-1002",
        "Neuquén",
    ),
    CustomerSeed(
        "Lucía Fernández",
        None,
        None,
        "+54 9 11 5550-1003",
        "Córdoba",
    ),
    CustomerSeed(
        "Nicolás Pereyra",
        "Rutas del Centro",
        "nicolas.pereyra@visual-qa.invalid",
        "+54 9 11 5550-1004",
        "Santa Fe",
    ),
    CustomerSeed(
        "Carolina Méndez",
        "Obras Cuyo",
        "carolina.mendez@visual-qa.invalid",
        "+54 9 11 5550-1005",
        "Mendoza",
    ),
    CustomerSeed(
        "Jorge Acosta",
        None,
        "jorge.acosta@visual-qa.invalid",
        None,
        "Tucumán",
    ),
    CustomerSeed(
        "Valentina Suárez",
        "Pavimentos del Litoral",
        None,
        "+54 9 11 5550-1007",
        "Entre Ríos",
    ),
    CustomerSeed(
        "Federico Luna",
        "Infraestructura Andina",
        "federico.luna@visual-qa.invalid",
        "+54 9 11 5550-1008",
        "San Juan",
    ),
    CustomerSeed(
        "Paula Benítez",
        "Caminos Bonaerenses",
        "paula.benitez@visual-qa.invalid",
        "+54 9 11 5550-1009",
        "Buenos Aires",
    ),
    CustomerSeed(
        "Ramiro Sosa",
        None,
        None,
        "+54 9 11 5550-1010",
        "Río Negro",
    ),
    CustomerSeed(
        "Andrea Molina",
        "Urbanizaciones Norte",
        "andrea.molina@visual-qa.invalid",
        "+54 9 11 5550-1011",
        "Buenos Aires",
    ),
    CustomerSeed(
        "Tomás Cabrera",
        "Consorcio Vial 18",
        "tomas.cabrera@visual-qa.invalid",
        "+54 9 11 5550-1012",
        "Córdoba",
    ),
    CustomerSeed(
        "Sofía Quiroga",
        "Desarrollos Pampeanos",
        "sofia.quiroga@visual-qa.invalid",
        "+54 9 11 5550-1013",
        "La Pampa",
    ),
    CustomerSeed(
        "Gonzalo Vera",
        "Servicios Viales NOA",
        None,
        "+54 9 11 5550-1014",
        "Salta",
    ),
    CustomerSeed(
        "Contacto duplicado A",
        "Revisión QA A",
        "revision.a@visual-qa.invalid",
        "+54 9 11 5550-1099",
        "Buenos Aires",
    ),
    CustomerSeed(
        "Contacto duplicado B",
        "Revisión QA B",
        "revision.b@visual-qa.invalid",
        "+54 9 11 5550-1099",
        "Buenos Aires",
    ),
)

OPPORTUNITIES = (
    OpportunitySeed(0, LeadSource.WEB, OpportunityStatus.NUEVA, 2, 2),
    OpportunitySeed(2, LeadSource.WHATSAPP, OpportunityStatus.NUEVA, 7, 7),
    OpportunitySeed(4, LeadSource.WEB, OpportunityStatus.NUEVA, 18, 18),
    OpportunitySeed(6, LeadSource.WHATSAPP, OpportunityStatus.NUEVA, 31, 31),
    OpportunitySeed(
        1, LeadSource.WEB, OpportunityStatus.COTIZADA, 6, 3, (("CA-30", "18000"),)
    ),
    OpportunitySeed(
        3, LeadSource.WHATSAPP, OpportunityStatus.COTIZADA, 17, 12, (("CA-20", "9500"),)
    ),
    OpportunitySeed(
        5,
        LeadSource.WEB,
        OpportunityStatus.COTIZADA,
        38,
        22,
        (("Sellador asfáltico", "4200"),),
    ),
    OpportunitySeed(
        7,
        LeadSource.WHATSAPP,
        OpportunityStatus.COTIZADA,
        76,
        28,
        (("Emulsión catiónica CRR-1", "24000"),),
    ),
    OpportunitySeed(
        0,
        LeadSource.WHATSAPP,
        OpportunityStatus.NEGOCIACION,
        10,
        4,
        (("CA-30", "32000"),),
    ),
    OpportunitySeed(
        8,
        LeadSource.WEB,
        OpportunityStatus.NEGOCIACION,
        24,
        16,
        (("Asfalto modificado AM-3", "14500"),),
    ),
    OpportunitySeed(
        9,
        LeadSource.WHATSAPP,
        OpportunityStatus.NEGOCIACION,
        58,
        20,
        (("Mezcla asfáltica en frío", "7000"),),
    ),
    OpportunitySeed(
        10,
        LeadSource.WEB,
        OpportunityStatus.NEGOCIACION,
        96,
        36,
        (("Imprimación asfáltica", "28000"),),
    ),
    OpportunitySeed(
        1, LeadSource.WEB, OpportunityStatus.GANADA, 13, 1, (("CA-30", "46000"),)
    ),
    OpportunitySeed(
        2, LeadSource.WHATSAPP, OpportunityStatus.GANADA, 48, 30, (("CA-20", "21000"),)
    ),
    OpportunitySeed(
        3,
        LeadSource.WEB,
        OpportunityStatus.GANADA,
        122,
        100,
        (("Emulsión catiónica CSS-1h", "16500"),),
    ),
    OpportunitySeed(
        4, LeadSource.WEB, OpportunityStatus.GANADA, 1500, 1460, (("CA-30", "88000"),)
    ),
    OpportunitySeed(
        5,
        LeadSource.WEB,
        OpportunityStatus.PERDIDA,
        21,
        8,
        loss_reason=LossReason.SIN_RESPUESTA,
    ),
    OpportunitySeed(
        6,
        LeadSource.WHATSAPP,
        OpportunityStatus.PERDIDA,
        66,
        42,
        (("CA-20", "12000"),),
        LossReason.PRECIO,
    ),
    OpportunitySeed(
        7,
        LeadSource.WEB,
        OpportunityStatus.PERDIDA,
        103,
        70,
        (("Asfalto modificado AM-3", "19000"),),
        LossReason.COMPETENCIA,
    ),
    OpportunitySeed(
        8,
        LeadSource.WHATSAPP,
        OpportunityStatus.PERDIDA,
        182,
        150,
        (("Sellador asfáltico", "6500"),),
        LossReason.PROYECTO_CANCELADO,
    ),
    OpportunitySeed(
        9,
        LeadSource.WEB,
        OpportunityStatus.PERDIDA,
        9,
        2,
        (("CA-30", "11000"),),
        LossReason.OTRO,
    ),
    OpportunitySeed(
        10,
        LeadSource.WEB,
        OpportunityStatus.NEGOCIACION,
        84,
        5,
        (("Emulsión catiónica CRR-1", "27500"),),
        LossReason.PRECIO,
        True,
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or reset the development-only CRM-027 visual QA dataset."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Remove only a recognized visual-QA dataset before recreating it.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print current visual-QA row counts without changing data.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    _guard_runtime()
    with SessionLocal() as session:
        if args.summary:
            _print_summary(session)
            return 0
        if args.reset:
            _reset_owned_dataset(session)
        elif _dataset_is_complete(session):
            print(f"Visual QA dataset {_DATASET_VERSION} is already present.")
            _print_summary(session)
            return 0
        elif _business_root_count(session) > 0:
            raise SystemExit(
                "Database is not empty. Use --reset only after confirming it contains "
                "the recognized visual-QA dataset."
            )

        session.rollback()
        supervisor_password = _required_secret("QA_SUPERVISOR_PASSWORD")
        seller_password = _required_secret("QA_SELLER_PASSWORD")
        anchor = datetime.now(UTC).replace(microsecond=0)
        _seed_dataset(
            session,
            supervisor_password=supervisor_password,
            seller_password=seller_password,
            anchor=anchor,
        )
        _print_summary(session)
    return 0


def _seed_dataset(
    session: Session,
    *,
    supervisor_password: str,
    seller_password: str,
    anchor: datetime,
) -> None:
    supervisor, seller = _seed_users(
        session,
        supervisor_password=supervisor_password,
        seller_password=seller_password,
    )
    products = _seed_products(session)
    customers = _seed_customers(session, actor_user_id=supervisor.id)
    opportunities = _seed_opportunities(
        session,
        customers=customers,
        products=products,
        actor_user_id=supervisor.id,
        anchor=anchor,
    )
    _apply_historical_timestamps(session, opportunities, anchor=anchor)
    _seed_notes(session, opportunities, actor_user_id=seller.id)
    _seed_legendary_evidence(session, customers, anchor=anchor)
    _seed_notifications(session, opportunities, anchor=anchor)
    provider = FakeWhatsAppProvider(
        now=anchor,
        freeform_window=timedelta(hours=24),
        templates=development_fake_templates(),
    )
    conversations = _seed_whatsapp(
        session,
        provider=provider,
        customers=customers,
        opportunities=opportunities,
        actor_user_id=seller.id,
        anchor=anchor,
    )
    _seed_broadcasts(
        session,
        provider=provider,
        customers=customers,
        actor_user_id=supervisor.id,
        anchor=anchor,
    )
    print(
        f"Created visual QA dataset {_DATASET_VERSION} with "
        f"{len(opportunities)} opportunities and {len(conversations)} conversations."
    )


def _guard_runtime() -> None:
    if get_app_environment() is not RuntimeEnvironment.DEVELOPMENT:
        raise SystemExit("Visual QA seed requires APP_ENVIRONMENT=development.")
    if get_whatsapp_provider_name() != "fake":
        raise SystemExit("Visual QA seed requires WHATSAPP_PROVIDER=fake.")
    database_name = make_url(get_database_url()).database
    if database_name != "asfaltos_crm":
        raise SystemExit("Visual QA seed requires the canonical asfaltos_crm database.")


def _required_secret(name: str) -> str:
    value = getenv(name)
    if value is None or not 8 <= len(value) <= 128:
        raise SystemExit(f"{name} must contain between 8 and 128 characters.")
    return value


def _stable_uuid(label: str) -> UUID:
    return uuid5(_NAMESPACE, label)


def _business_root_count(session: Session) -> int:
    return sum(
        _count(session, model)
        for model in (User, Product, Customer, WhatsAppConversation, WhatsAppBroadcast)
    )


def _dataset_is_complete(session: Session) -> bool:
    emails = set(session.scalars(select(User.email)))
    product_names = set(session.scalars(select(Product.name)))
    return (
        {_SUPERVISOR_EMAIL, _SELLER_EMAIL}.issubset(emails)
        and set(PRODUCT_NAMES).issubset(product_names)
        and _count(session, Customer) >= len(CUSTOMERS)
        and _count(session, Opportunity) >= len(OPPORTUNITIES)
        and _count(session, WhatsAppConversation) >= 5
        and _count(session, WhatsAppBroadcast) >= 3
    )


def _reset_owned_dataset(session: Session) -> None:
    unexpected_users = set(session.scalars(select(User.email))) - (
        _LEGACY_QA_EMAILS | {_SELLER_EMAIL}
    )
    unexpected_products = set(session.scalars(select(Product.name))) - set(
        PRODUCT_NAMES
    )
    unexpected_customers = set(session.scalars(select(Customer.name))) - {
        item.name for item in CUSTOMERS
    }
    unexpected_conversations = {
        phone
        for phone in session.scalars(select(WhatsAppConversation.external_phone))
        if "5550-" not in phone
    }
    unexpected_broadcasts = {
        label
        for label in session.scalars(select(WhatsAppBroadcast.label))
        if not label.startswith("QA visual ·")
    }
    session.rollback()
    if any(
        (
            unexpected_users,
            unexpected_products,
            unexpected_customers,
            unexpected_conversations,
            unexpected_broadcasts,
        )
    ):
        raise SystemExit(
            "Reset refused: the database contains roots not owned by the visual-QA dataset."
        )
    with session.begin():
        session.execute(
            text("TRUNCATE TABLE users, products, customers RESTART IDENTITY CASCADE")
        )
    print("Recognized visual-QA data reset safely.")


def _seed_users(
    session: Session,
    *,
    supervisor_password: str,
    seller_password: str,
) -> tuple[User, User]:
    service = UserService(session)
    supervisor = service.create_user(
        full_name="Sofía Supervisora QA",
        email=_SUPERVISOR_EMAIL,
        password=supervisor_password,
        role=UserRole.SUPERVISOR,
    )
    seller = service.create_user(
        full_name="Martín Vendedor QA",
        email=_SELLER_EMAIL,
        password=seller_password,
        role=UserRole.VENDEDOR,
    )
    return supervisor, seller


def _seed_products(session: Session) -> dict[str, Product]:
    service = ProductService(session)
    products = {name: service.create_product(name=name) for name in PRODUCT_NAMES}
    service.update_product(products["Asfalto diluido MC-30"].id, {"is_active": False})
    return products


def _seed_customers(session: Session, *, actor_user_id: int) -> list[Customer]:
    service = CustomerService(session)
    return [
        service.create_customer(
            name=item.name,
            company=item.company,
            email=item.email,
            phone=item.phone,
            province=item.province,
            legendary_historical_override=item.legendary_override,
            actor_user_id=actor_user_id,
        )
        for item in CUSTOMERS
    ]


def _seed_opportunities(
    session: Session,
    *,
    customers: list[Customer],
    products: dict[str, Product],
    actor_user_id: int,
    anchor: datetime,
) -> list[Opportunity]:
    service = OpportunityService(session)
    created: list[Opportunity] = []
    for index, item in enumerate(OPPORTUNITIES):
        created_at = anchor - timedelta(days=item.age_days)
        entered_at = anchor - timedelta(days=item.stage_age_days)
        transition_count = _transition_count(index, item)
        transition_times = iter(
            created_at + (entered_at - created_at) * step / transition_count
            for step in range(1, transition_count + 1)
        )
        opportunity = service.create_opportunity(
            customer_id=customers[item.customer_index].id,
            source=item.source,
            assigned_user_id=actor_user_id if index % 3 else None,
            changed_by_user_id=actor_user_id,
            occurred_at=created_at,
        )
        quote = [
            QuoteProductInput(products[name].id, Decimal(quantity))
            for name, quantity in item.quote
        ]
        if item.status is not OpportunityStatus.NUEVA and quote:
            opportunity = service.quote_opportunity(
                opportunity.id,
                quote,
                changed_by_user_id=actor_user_id,
                occurred_at=next(transition_times),
            )
        if item.reopen:
            opportunity = service.move_to_negotiation(
                opportunity.id,
                changed_by_user_id=actor_user_id,
                occurred_at=next(transition_times),
            )
            opportunity = service.mark_as_lost(
                opportunity.id,
                item.loss_reason,
                changed_by_user_id=actor_user_id,
                occurred_at=next(transition_times),
            )
            opportunity = service.reopen(
                opportunity.id,
                command_id=_stable_uuid(f"reopen-{index}"),
                expected_status=OpportunityStatus.PERDIDA,
                changed_by_user_id=actor_user_id,
                occurred_at=next(transition_times),
            )
        elif item.status is OpportunityStatus.COTIZADA:
            pass
        elif item.status in {OpportunityStatus.NEGOCIACION, OpportunityStatus.GANADA}:
            opportunity = service.move_to_negotiation(
                opportunity.id,
                changed_by_user_id=actor_user_id,
                occurred_at=next(transition_times),
            )
            if item.status is OpportunityStatus.GANADA:
                opportunity = service.mark_as_won(
                    opportunity.id,
                    changed_by_user_id=actor_user_id,
                    occurred_at=next(transition_times),
                )
        elif item.status is OpportunityStatus.PERDIDA:
            if quote and index % 2 == 0:
                opportunity = service.move_to_negotiation(
                    opportunity.id,
                    changed_by_user_id=actor_user_id,
                    occurred_at=next(transition_times),
                )
            opportunity = service.mark_as_lost(
                opportunity.id,
                item.loss_reason,
                changed_by_user_id=actor_user_id,
                occurred_at=next(transition_times),
            )
        created.append(opportunity)
    return created


def _transition_count(index: int, item: OpportunitySeed) -> int:
    if item.reopen:
        return 4
    if item.status is OpportunityStatus.NUEVA:
        return 0
    if item.status is OpportunityStatus.COTIZADA:
        return 1
    if item.status is OpportunityStatus.NEGOCIACION:
        return 2
    if item.status is OpportunityStatus.GANADA:
        return 3
    if item.status is OpportunityStatus.PERDIDA:
        return 1 + int(bool(item.quote)) + int(bool(item.quote) and index % 2 == 0)
    raise RuntimeError(f"Unsupported seeded status: {item.status}")


def _apply_historical_timestamps(
    session: Session,
    opportunities: list[Opportunity],
    *,
    anchor: datetime,
) -> None:
    with session.begin():
        for product in session.scalars(select(Product)):
            product.created_at = anchor - timedelta(days=1800)
            product.updated_at = anchor - timedelta(days=10)
        for customer in session.scalars(select(Customer)):
            customer.created_at = anchor - timedelta(days=1600)
            customer.updated_at = anchor - timedelta(days=1)
        for opportunity, definition in zip(opportunities, OPPORTUNITIES, strict=True):
            created_at = anchor - timedelta(days=definition.age_days)
            persisted = session.get(Opportunity, opportunity.id)
            if persisted is None:
                raise RuntimeError("Seeded Opportunity disappeared")
            for line in session.scalars(
                select(OpportunityProduct).where(
                    OpportunityProduct.opportunity_id == persisted.id
                )
            ):
                line.created_at = created_at + timedelta(hours=6)
                line.updated_at = persisted.updated_at


def _seed_notes(
    session: Session,
    opportunities: list[Opportunity],
    *,
    actor_user_id: int,
) -> None:
    notes = (
        (0, "Confirmar volumen final y acceso a obra antes del viernes.", True),
        (4, "Cotización enviada. El cliente está revisando logística y plazo.", False),
        (
            8,
            "Buena recepción de la propuesta; falta definición técnica del tramo.",
            True,
        ),
        (
            9,
            "Solicitar plano actualizado para ajustar la recomendación de producto.",
            False,
        ),
        (12, "Entrega coordinada y validada con el responsable de obra.", False),
        (
            17,
            "El proyecto priorizó una alternativa por precio. Mantener seguimiento.",
            False,
        ),
        (
            21,
            "Oportunidad reabierta luego de confirmar presupuesto y nueva fecha.",
            True,
        ),
    )
    service = OpportunityNoteService(session)
    for position, (opportunity_index, body, pinned) in enumerate(notes):
        service.create(
            opportunities[opportunity_index].id,
            command_id=_stable_uuid(f"note-{position}"),
            body=body,
            is_pinned=pinned,
            actor_user_id=actor_user_id,
        )


def _seed_legendary_evidence(
    session: Session,
    customers: list[Customer],
    *,
    anchor: datetime,
) -> None:
    LegendaryService(session).recompute_customer(customers[4].id, evaluated_at=anchor)


def _seed_notifications(
    session: Session,
    opportunities: list[Opportunity],
    *,
    anchor: datetime,
) -> None:
    service = NotificationService(session)
    service.generate_stale_opportunity_notifications(now=anchor, threshold_days=14)
    unread_ids = list(
        session.scalars(
            select(Notification.id)
            .where(Notification.read_at.is_(None))
            .order_by(Notification.id)
        )
    )
    session.commit()
    if unread_ids:
        service.mark_as_read(unread_ids[0], now=anchor + timedelta(minutes=1))
    won = opportunities[12]
    with session.begin():
        session.add(
            Notification(
                type=NotificationType.OPPORTUNITY_STALE,
                opportunity_id=won.id,
                created_at=anchor - timedelta(days=5),
                read_at=anchor - timedelta(days=4, hours=20),
                resolved_at=anchor - timedelta(days=1),
            )
        )


def _seed_whatsapp(
    session: Session,
    *,
    provider: FakeWhatsAppProvider,
    customers: list[Customer],
    opportunities: list[Opportunity],
    actor_user_id: int,
    anchor: datetime,
) -> list[int]:
    inbound_service = WhatsAppInboundService(session, provider)
    conversation_ids: list[int] = []

    first = inbound_service.receive(
        InboundMessageInput(
            external_message_id="qa-inbound-001",
            external_phone=customers[0].phone or "",
            provider_contact_id="qa-contact-001",
            display_name=customers[0].name,
            message_type=WhatsAppMessageType.TEXT,
            body="Hola, necesitamos confirmar disponibilidad para la próxima semana.",
            provider_message_at=anchor - timedelta(hours=3),
        ),
        now=anchor - timedelta(hours=3),
    )
    conversation_ids.append(first.conversation_id)
    WhatsAppConversationService(session).link_opportunity(
        first.conversation_id,
        opportunities[8].id,
        linked_by_user_id=actor_user_id,
        now=anchor - timedelta(hours=2, minutes=50),
    )
    provider.set_now(anchor - timedelta(hours=2))
    sent = WhatsAppMessageService(session, provider).send(
        OutboundMessageInput(
            conversation_id=first.conversation_id,
            client_generated_id=_stable_uuid("human-reply-read"),
            sent_by_user_id=actor_user_id,
            message_type=WhatsAppMessageType.TEXT,
            body="Tenemos disponibilidad. Te envío la coordinación durante la tarde.",
        ),
        now=anchor - timedelta(hours=2),
    )
    if sent.external_message_id is None:
        raise RuntimeError("Fake provider did not accept seeded reply")
    _record_status(
        session,
        sent.external_message_id,
        WhatsAppProviderState.DELIVERED,
        anchor - timedelta(hours=1, minutes=55),
    )
    _record_status(
        session,
        sent.external_message_id,
        WhatsAppProviderState.READ,
        anchor - timedelta(hours=1, minutes=40),
    )

    waiting = inbound_service.receive(
        InboundMessageInput(
            external_message_id="qa-inbound-002",
            external_phone=customers[8].phone or "",
            provider_contact_id="qa-contact-002",
            display_name=customers[8].name,
            message_type=WhatsAppMessageType.TEXT,
            body="¿Podemos revisar la cantidad cotizada antes de cerrar?",
            provider_message_at=anchor - timedelta(minutes=24),
        ),
        now=anchor - timedelta(minutes=24),
    )
    conversation_ids.append(waiting.conversation_id)
    WhatsAppConversationService(session).link_opportunity(
        waiting.conversation_id,
        opportunities[9].id,
        linked_by_user_id=actor_user_id,
        now=anchor - timedelta(minutes=20),
    )

    failed_conversation = inbound_service.receive(
        InboundMessageInput(
            external_message_id="qa-inbound-003",
            external_phone=customers[3].phone or "",
            provider_contact_id="qa-contact-003",
            display_name=customers[3].name,
            message_type=WhatsAppMessageType.TEXT,
            body="Quedo atento al detalle de la entrega.",
            provider_message_at=anchor - timedelta(hours=8),
        ),
        now=anchor - timedelta(hours=8),
    )
    conversation_ids.append(failed_conversation.conversation_id)
    failed_id = _stable_uuid("human-reply-failed")
    provider.configure_error(
        failed_id,
        ProviderErrorKind.PERMANENT_FAILURE,
        code="QA_DESTINATION_UNAVAILABLE",
        safe_message="No se pudo entregar el mensaje de prueba.",
    )
    WhatsAppMessageService(session, provider).send(
        OutboundMessageInput(
            conversation_id=failed_conversation.conversation_id,
            client_generated_id=failed_id,
            sent_by_user_id=actor_user_id,
            message_type=WhatsAppMessageType.TEXT,
            body="Te compartimos el detalle en cuanto esté confirmado.",
        ),
        now=anchor - timedelta(hours=7, minutes=45),
    )

    unknown_conversation = inbound_service.receive(
        InboundMessageInput(
            external_message_id="qa-inbound-004",
            external_phone=customers[7].phone or "",
            provider_contact_id="qa-contact-004",
            display_name=customers[7].name,
            message_type=WhatsAppMessageType.TEXT,
            body="Necesito la ficha técnica del producto recomendado.",
            provider_message_at=anchor - timedelta(hours=5),
        ),
        now=anchor - timedelta(hours=5),
    )
    conversation_ids.append(unknown_conversation.conversation_id)
    unknown_id = _stable_uuid("human-reply-unknown")
    provider.configure_error(
        unknown_id,
        ProviderErrorKind.TIMEOUT_UNKNOWN_ACCEPTANCE,
        code="QA_ACCEPTANCE_UNKNOWN",
        safe_message="No se pudo confirmar si el proveedor aceptó el mensaje.",
    )
    WhatsAppMessageService(session, provider).send(
        OutboundMessageInput(
            conversation_id=unknown_conversation.conversation_id,
            client_generated_id=unknown_id,
            sent_by_user_id=actor_user_id,
            message_type=WhatsAppMessageType.TEXT,
            body="La ficha técnica está siendo preparada para enviarte.",
        ),
        now=anchor - timedelta(hours=4, minutes=50),
    )

    media = inbound_service.receive(
        InboundMessageInput(
            external_message_id="qa-inbound-image-001",
            external_phone=customers[11].phone or "",
            provider_contact_id="qa-contact-005",
            display_name=customers[11].name,
            message_type=WhatsAppMessageType.IMAGE,
            body="Estado actual del acceso a obra",
            provider_message_at=anchor - timedelta(days=1, hours=2),
            attachment=InboundAttachmentInput(
                provider_media_id="qa-media-image-001",
                mime_type="image/jpeg",
                filename="acceso-obra.jpg",
                size_bytes=184_320,
            ),
        ),
        now=anchor - timedelta(days=1, hours=2),
    )
    conversation_ids.append(media.conversation_id)
    inbound_service.receive(
        InboundMessageInput(
            external_message_id="qa-inbound-document-001",
            external_phone=customers[11].phone or "",
            provider_contact_id="qa-contact-005",
            display_name=customers[11].name,
            message_type=WhatsAppMessageType.DOCUMENT,
            body="Pliego técnico de referencia",
            provider_message_at=anchor - timedelta(days=1, hours=1, minutes=45),
            attachment=InboundAttachmentInput(
                provider_media_id="qa-media-document-001",
                mime_type="application/pdf",
                filename="pliego-tecnico.pdf",
                size_bytes=524_288,
            ),
        ),
        now=anchor - timedelta(days=1, hours=1, minutes=45),
    )
    unresolved = inbound_service.receive(
        InboundMessageInput(
            external_message_id="qa-inbound-review-001",
            external_phone=customers[14].phone or "",
            provider_contact_id="qa-contact-review",
            display_name="Contacto para revisar",
            message_type=WhatsAppMessageType.TEXT,
            body="Hola, necesito que confirmen a qué ficha corresponde este número.",
            provider_message_at=anchor - timedelta(hours=1),
        ),
        now=anchor - timedelta(hours=1),
    )
    conversation_ids.append(unresolved.conversation_id)
    with session.begin():
        for attachment in session.scalars(select(WhatsAppAttachment)):
            attachment.storage_status = WhatsAppStorageStatus.FAILED
            attachment.storage_error = "Contenido sintético: vista previa no persistida"
            attachment.updated_at = max(datetime.now(UTC), attachment.created_at)
    return conversation_ids


def _record_status(
    session: Session,
    external_message_id: str,
    state: WhatsAppProviderState,
    occurred_at: datetime,
) -> None:
    WhatsAppStatusService(session).record(
        ProviderStatusInput(
            external_message_id=external_message_id,
            state=state,
            occurred_at=occurred_at,
        ),
        received_at=occurred_at,
    )


def _seed_broadcasts(
    session: Session,
    *,
    provider: FakeWhatsAppProvider,
    customers: list[Customer],
    actor_user_id: int,
    anchor: datetime,
) -> None:
    for index in range(8):
        customer = customers[index]
        if customer.phone is None:
            continue
        WhatsAppConsentService(session).append(
            ConsentEventInput(
                client_event_id=_stable_uuid(f"consent-{index}"),
                customer_id=customer.id,
                decision=WhatsAppConsentDecision.OPT_IN,
                source=WhatsAppConsentSource.FAA_CRM,
                occurred_at=anchor - timedelta(days=30 + index),
                effective_at=None,
                evidence_reference=None,
                recorded_by_user_id=actor_user_id,
            ),
            now=anchor - timedelta(days=30 + index),
        )

    service = WhatsAppBroadcastService(
        session,
        provider,
        FakeMediaStorage(),
        batch_size=10,
        claim_timeout=timedelta(minutes=5),
    )
    draft, _ = service.create(
        _broadcast_input(
            "draft", "QA visual · Borrador con elegibilidad", actor_user_id
        ),
        now=anchor - timedelta(days=3),
    )
    service.replace_recipients(
        draft.id,
        command_id=_stable_uuid("broadcast-draft-recipients"),
        customer_ids=(customers[0].id, customers[5].id, customers[12].id),
        expected_version=draft.version,
        actor_user_id=actor_user_id,
        now=anchor - timedelta(days=3, hours=-1),
    )

    processing, _ = service.create(
        _broadcast_input("processing", "QA visual · Ejecución en curso", actor_user_id),
        now=anchor - timedelta(days=2),
    )
    selection = service.replace_recipients(
        processing.id,
        command_id=_stable_uuid("broadcast-processing-recipients"),
        customer_ids=(customers[0].id, customers[1].id),
        expected_version=processing.version,
        actor_user_id=actor_user_id,
        now=anchor - timedelta(days=2, hours=-1),
    )
    validation = service.validate(
        processing.id,
        expected_version=selection.version,
        actor_user_id=actor_user_id,
        now=anchor - timedelta(days=2, hours=-2),
    )
    if validation.validation_token is None:
        raise RuntimeError("Processing Broadcast seed did not validate")
    service.confirm(
        processing.id,
        command_id=_stable_uuid("broadcast-processing-confirm"),
        expected_version=selection.version,
        validation_token=validation.validation_token,
        actor_user_id=actor_user_id,
        now=anchor - timedelta(days=2, hours=-2, minutes=-1),
    )
    service.start(
        processing.id,
        command_id=_stable_uuid("broadcast-processing-start"),
        actor_user_id=actor_user_id,
        now=anchor - timedelta(days=2, hours=-2, minutes=-2),
    )

    completed, _ = service.create(
        _broadcast_input(
            "completed", "QA visual · Seguimiento de obras", actor_user_id
        ),
        now=anchor - timedelta(days=8),
    )
    completed_selection = service.replace_recipients(
        completed.id,
        command_id=_stable_uuid("broadcast-completed-recipients"),
        customer_ids=tuple(customers[index].id for index in (0, 1, 2, 3, 4, 6)),
        expected_version=completed.version,
        actor_user_id=actor_user_id,
        now=anchor - timedelta(days=8, hours=-1),
    )
    completed_validation = service.validate(
        completed.id,
        expected_version=completed_selection.version,
        actor_user_id=actor_user_id,
        now=anchor - timedelta(days=8, hours=-2),
    )
    if completed_validation.validation_token is None:
        raise RuntimeError("Completed Broadcast seed did not validate")
    service.confirm(
        completed.id,
        command_id=_stable_uuid("broadcast-completed-confirm"),
        expected_version=completed_selection.version,
        validation_token=completed_validation.validation_token,
        actor_user_id=actor_user_id,
        now=anchor - timedelta(days=8, hours=-2, minutes=-1),
    )
    service.start(
        completed.id,
        command_id=_stable_uuid("broadcast-completed-start"),
        actor_user_id=actor_user_id,
        now=anchor - timedelta(days=8, hours=-2, minutes=-2),
    )
    provider.set_now(anchor - timedelta(days=8, hours=-2, minutes=-3))
    service.process_batch(
        completed.id,
        command_id=_stable_uuid("broadcast-completed-process"),
        actor_user_id=actor_user_id,
        now=anchor - timedelta(days=8, hours=-2, minutes=-3),
    )
    _diversify_completed_broadcast(session, completed.id, anchor=anchor)


def _broadcast_input(
    key: str,
    label: str,
    actor_user_id: int,
) -> BroadcastCreateInput:
    return BroadcastCreateInput(
        client_generated_id=_stable_uuid(f"broadcast-{key}"),
        label=label,
        external_campaign_reference=f"QA-{key.upper()}",
        template_external_id="qa-marketing",
        parameters=(BroadcastParameterInput(name="mes", value="Agosto"),),
        header_media_ref=None,
        created_by_user_id=actor_user_id,
    )


def _diversify_completed_broadcast(
    session: Session,
    broadcast_id: int,
    *,
    anchor: datetime,
) -> None:
    recipients = list(
        session.scalars(
            select(WhatsAppBroadcastRecipient)
            .where(WhatsAppBroadcastRecipient.broadcast_id == broadcast_id)
            .order_by(WhatsAppBroadcastRecipient.id)
        )
    )
    messages = {
        message.broadcast_recipient_id: message
        for message in session.scalars(
            select(WhatsAppMessage).where(
                WhatsAppMessage.broadcast_recipient_id.in_(
                    tuple(recipient.id for recipient in recipients)
                )
            )
        )
    }
    session.commit()
    for index, state in (
        (0, WhatsAppProviderState.READ),
        (1, WhatsAppProviderState.DELIVERED),
        (3, WhatsAppProviderState.FAILED),
    ):
        message = messages.get(recipients[index].id)
        if message is None or message.external_message_id is None:
            raise RuntimeError("Completed Broadcast recipient has no accepted message")
        if state is WhatsAppProviderState.READ:
            _record_status(
                session,
                message.external_message_id,
                WhatsAppProviderState.DELIVERED,
                anchor - timedelta(days=7, hours=20),
            )
        _record_status(
            session,
            message.external_message_id,
            state,
            anchor - timedelta(days=7, hours=19, minutes=index),
        )

    with session.begin():
        unknown_recipient = session.get(WhatsAppBroadcastRecipient, recipients[4].id)
        unknown_message = session.get(WhatsAppMessage, messages[recipients[4].id].id)
        blocked_recipient = session.get(WhatsAppBroadcastRecipient, recipients[5].id)
        blocked_message = session.get(WhatsAppMessage, messages[recipients[5].id].id)
        if any(
            item is None
            for item in (
                unknown_recipient,
                unknown_message,
                blocked_recipient,
                blocked_message,
            )
        ):
            raise RuntimeError("Completed Broadcast outcome data disappeared")
        assert unknown_recipient is not None
        assert unknown_message is not None
        assert blocked_recipient is not None
        assert blocked_message is not None
        unknown_message.external_message_id = None
        unknown_message.dispatch_state = WhatsAppDispatchState.UNKNOWN
        unknown_message.provider_state = None
        unknown_message.provider_error_code = "QA_ACCEPTANCE_UNKNOWN"
        unknown_message.provider_error_message = (
            "Aceptación del proveedor no confirmada"
        )
        unknown_message.accepted_at = None
        unknown_message.sent_at = None
        unknown_message.provider_status_at = None
        recompute_broadcast_recipient_projection(
            session,
            unknown_recipient,
            now=anchor - timedelta(days=7, hours=18),
        )
        session.delete(blocked_message)
        blocked_recipient.status = WhatsAppBroadcastRecipientStatus.BLOCKED
        blocked_recipient.reason_code = "CONSENT_OR_PHONE_CHANGED"
        blocked_recipient.safe_error_message = "Destinatario omitido antes del envío"
        blocked_recipient.updated_at = anchor - timedelta(days=7, hours=18)
        session.add(
            WhatsAppBroadcastAuditEvent(
                broadcast_id=broadcast_id,
                recipient_id=blocked_recipient.id,
                message_id=None,
                command_id=None,
                event_type=WhatsAppBroadcastAuditEventType.BLOCKED,
                reason_code="CONSENT_OR_PHONE_CHANGED",
                actor_user_id=None,
                affected_count=1,
                occurred_at=anchor - timedelta(days=7, hours=18),
            )
        )


def _count(session: Session, model: type[object]) -> int:
    value = session.scalar(select(func.count()).select_from(model))
    return int(value or 0)


def _print_summary(session: Session) -> None:
    counts = (
        ("users", _count(session, User)),
        ("products", _count(session, Product)),
        ("customers", _count(session, Customer)),
        ("opportunities", _count(session, Opportunity)),
        ("notifications", _count(session, Notification)),
        ("whatsapp_conversations", _count(session, WhatsAppConversation)),
        ("whatsapp_messages", _count(session, WhatsAppMessage)),
        ("whatsapp_broadcasts", _count(session, WhatsAppBroadcast)),
        ("whatsapp_recipients", _count(session, WhatsAppBroadcastRecipient)),
    )
    print("Visual QA dataset summary:")
    for label, count in counts:
        print(f"  {label}: {count}")
    print(f"  supervisor: {_SUPERVISOR_EMAIL}")
    print(f"  seller: {_SELLER_EMAIL}")


if __name__ == "__main__":
    raise SystemExit(main())
