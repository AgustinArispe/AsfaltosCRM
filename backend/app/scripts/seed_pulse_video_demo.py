"""Seed the isolated PULSE video database. Never run against a shared database."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from os import environ
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from app.core.config import (
    RuntimeEnvironment,
    get_app_environment,
    get_database_url,
    get_whatsapp_provider_name,
)
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Customer,
    LeadIntake,
    LeadSource,
    LossReason,
    Notification,
    NotificationRecipient,
    NotificationType,
    Opportunity,
    OpportunityNote,
    OpportunityNoteRevision,
    OpportunityStatus,
    Product,
    User,
    UserRole,
    WhatsAppAttachment,
    WhatsAppBroadcast,
    WhatsAppConversation,
    WhatsAppConversationOpportunity,
    WhatsAppConversationResolution,
    WhatsAppDirection,
    WhatsAppDispatchState,
    WhatsAppMessage,
    WhatsAppMessageOrigin,
    WhatsAppMessageType,
    WhatsAppOpportunityLinkSource,
    WhatsAppProviderState,
    WhatsAppStorageStatus,
)
from app.services.opportunity_service import OpportunityService, QuoteProductInput
from app.services.whatsapp_projection_service import recompute_response_projection
from app.whatsapp.media_storage import FilesystemMediaStorage, MediaPutRequest

NS = UUID("7ee03063-35b8-424f-9af1-0d9639af8658")
USERS = (("Martina López", "demo@pulse.test", UserRole.SUPERVISOR),
         ("Tomás García", "tomas@pulse-demo.invalid", UserRole.VENDEDOR),
         ("Sofía Fernández", "sofia@pulse-demo.invalid", UserRole.VENDEDOR))
PRODUCTS = ("Plan Business", "Plan Enterprise", "Implementación inicial", "Soporte Premium",
            "Capacitación de equipo", "Integración personalizada")
CUSTOMERS = (
    ("Clara Ríos", "NovaTech", "Buenos Aires"), ("Mateo Gil", "Estudio Norte", "Buenos Aires"),
    ("Julia Paz", "Grupo Prisma", "Córdoba"), ("Ramiro Serra", "Delta Digital", "Santa Fe"),
    ("Paula Luna", "Nexo Solutions", "Mendoza"), ("Diego Vera", "Horizonte Comercial", "Buenos Aires"),
    ("Lara Pinto", "Urbania", "Neuquén"), ("Bruno Costa", "Vértice", "Entre Ríos"),
    ("Elena Torres", "Atlas Group", "Buenos Aires"), ("Iván Castro", "Punto Sur", "Santa Fe"),
    ("Mara Vidal", "Cima Labs", "Córdoba"), ("Nicolás Paz", "Aula Uno", "Mendoza"),
    ("Olivia Rey", "Lumen Studio", "Buenos Aires"), ("Felipe Sosa", "Surco Data", "Neuquén"),
    ("Camila Núñez", "Puerto Nube", "Río Negro"), ("Andrés Molina", "Marea Retail", "Buenos Aires"),
)
# customer index, source, final status, age in days, product index, seller index, optional loss reason
OPPS = (
    (0, LeadSource.WEB, OpportunityStatus.NEGOCIACION, 21, 1, 0, None),
    (1, LeadSource.INSTAGRAM, OpportunityStatus.COTIZADA, 12, 0, 1, None),
    (2, LeadSource.REFERIDO, OpportunityStatus.NEGOCIACION, 18, 5, 2, None),
    (3, LeadSource.WEB, OpportunityStatus.NUEVA, 4, 2, 1, None),
    (4, LeadSource.WHATSAPP, OpportunityStatus.COTIZADA, 9, 0, 2, None),
    (5, LeadSource.WEB, OpportunityStatus.COTIZADA, 14, 3, 0, None),
    (6, LeadSource.INSTAGRAM, OpportunityStatus.NUEVA, 2, 4, 1, None),
    (7, LeadSource.REFERIDO, OpportunityStatus.NUEVA, 6, 0, 2, None),
    (8, LeadSource.REFERIDO, OpportunityStatus.GANADA, 77, 1, 0, None),
    (9, LeadSource.WEB, OpportunityStatus.GANADA, 65, 2, 1, None),
    (10, LeadSource.WHATSAPP, OpportunityStatus.GANADA, 54, 0, 2, None),
    (11, LeadSource.INSTAGRAM, OpportunityStatus.GANADA, 28, 4, 1, None),
    (12, LeadSource.WHATSAPP, OpportunityStatus.GANADA, 19, 3, 0, None),
    (13, LeadSource.REFERIDO, OpportunityStatus.PERDIDA, 59, 1, 2, LossReason.PRECIO),
    (14, LeadSource.WHATSAPP, OpportunityStatus.PERDIDA, 46, 5, 0, LossReason.COMPETENCIA),
    (15, LeadSource.INSTAGRAM, OpportunityStatus.PERDIDA, 21, 0, 1, LossReason.PROYECTO_CANCELADO),
)


def stable(label: str) -> UUID:
    return uuid5(NS, label)


def guard() -> None:
    url = make_url(get_database_url())
    forbidden = any(key.startswith("RAILWAY_") for key in environ) or any(
        environ.get(key) for key in ("META_ACCESS_TOKEN", "META_APP_SECRET", "META_VERIFY_TOKEN",
                                     "META_WEBHOOK_VERIFY_TOKEN", "META_PHONE_NUMBER_ID", "META_WABA_ID")
    )
    if not (
        environ.get("PULSE_DEMO_GIT_BRANCH") == "demo/pulse-video"
        and get_app_environment() is RuntimeEnvironment.DEVELOPMENT
        and get_whatsapp_provider_name() == "fake"
        and url.drivername == "postgresql+psycopg"
        and url.host == "db" and url.port == 5432
        and url.database == "pulse_demo" and url.username == "pulse_demo"
        and environ.get("WHATSAPP_MEDIA_STORAGE") == "filesystem"
        and environ.get("WHATSAPP_MEDIA_STORAGE_ROOT") == "/var/lib/pulse-crm/whatsapp-media"
        and not forbidden
    ):
        raise SystemExit("Refused: this seed only runs on demo/pulse-video in the isolated local pulse_demo stack.")


def count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def inventory(session) -> dict[str, int]:
    return {name: count(session, model) for name, model in (
        ("users", User), ("customers", Customer), ("products", Product),
        ("opportunities", Opportunity), ("conversations", WhatsAppConversation),
        ("notifications", Notification), ("attachments", WhatsAppAttachment),
        ("broadcasts", WhatsAppBroadcast))}


def owned(session) -> bool:
    emails = set(session.scalars(select(User.email)))
    names = set(session.scalars(select(Customer.name)))
    products = set(session.scalars(select(Product.name)))
    phones = set(session.scalars(select(WhatsAppConversation.external_phone)))
    expected_phones = {phone(i) for i in (1, 3, 4, 6, 7)}
    expected_opps = {(CUSTOMERS[i][0], source) for i, source, *_ in OPPS}
    existing_opps = list(session.execute(
        select(Customer.name, Opportunity.source).join(Opportunity, Opportunity.customer_id == Customer.id)
    ))
    message_ids = list(session.scalars(select(WhatsAppMessage.external_message_id)))
    return (emails <= {entry[1] for entry in USERS}
            and names <= {entry[0] for entry in CUSTOMERS}
            and products <= set(PRODUCTS)
            and phones <= expected_phones
            and len(existing_opps) <= len(OPPS)
            and set(existing_opps) <= expected_opps
            and all(value and value.startswith("pulse-demo-") for value in message_ids)
            and count(session, WhatsAppBroadcast) == 0
            and set(session.scalars(select(LeadIntake.external_submission_id))) <= {"pulse-video-web-0", "pulse-video-web-3"})


def phone(index: int) -> str:
    return f"+549110055{index:04d}"


def reset(session) -> None:
    if not owned(session):
        raise SystemExit("Reset refused: unrelated data is present in the demo database.")
    session.rollback()
    with session.begin():
        session.execute(text("TRUNCATE TABLE users, products, customers, whatsapp_conversations RESTART IDENTITY CASCADE"))


def seed_base(session, anchor: datetime, password: str):
    with session.begin():
        users = [User(full_name=name, email=email, password_hash=hash_password(password), role=role)
                 for name, email, role in USERS]
        products = [Product(name=name) for name in PRODUCTS]
        customers = [Customer(name=name, company=company, province=province,
                              email=f"contacto{i:02d}@pulse-demo.invalid", phone=phone(i),
                              created_at=anchor-timedelta(days=age+1),
                              updated_at=anchor-timedelta(days=age+1))
                     for i, ((name, company, province), (_, _, _, age, _, _, _)) in enumerate(zip(CUSTOMERS, OPPS, strict=True))]
        session.add_all(users + products + customers)
        session.flush()
    return users, products, customers


def seed_opportunities(session, anchor, users, products, customers):
    result = []
    service = OpportunityService(session)
    for customer_idx, source, status, age, product_idx, seller_idx, reason in OPPS:
        start = anchor-timedelta(days=age)
        seller = users[seller_idx]
        opp = service.create_opportunity(customer_id=customers[customer_idx].id, source=source,
                                         assigned_user_id=seller.id, changed_by_user_id=seller.id,
                                         occurred_at=start)
        if status is not OpportunityStatus.NUEVA:
            service.quote_opportunity(opp.id, [QuoteProductInput(products[product_idx].id, Decimal("1"))],
                                      changed_by_user_id=seller.id, occurred_at=start+timedelta(days=1))
        if status in (OpportunityStatus.NEGOCIACION, OpportunityStatus.GANADA):
            service.move_to_negotiation(opp.id, changed_by_user_id=seller.id,
                                        occurred_at=start+timedelta(days=2))
        if status is OpportunityStatus.GANADA:
            service.mark_as_won(opp.id, changed_by_user_id=seller.id,
                                occurred_at=start+timedelta(days=8))
        if status is OpportunityStatus.PERDIDA:
            service.mark_as_lost(opp.id, reason, changed_by_user_id=seller.id,
                                 occurred_at=start+timedelta(days=5))
        result.append(opp)
    with session.begin():
        for i, message in ((0, "Buscamos ordenar el seguimiento comercial de tres equipos y tener reportes por responsable."),
                           (3, "Queremos conocer los pasos de implementación y los tiempos de puesta en marcha.")):
            customer = customers[i]
            session.add(LeadIntake(source=LeadSource.WEB, external_submission_id=f"pulse-video-web-{i}",
                                   submitted_name=customer.name, submitted_company=customer.company,
                                   submitted_email=customer.email, submitted_phone=customer.phone,
                                   submitted_province=customer.province, message=message,
                                   opportunity_id=result[i].id, received_at=result[i].created_at))
        notes = ((0, "Prioridad: unificar consultas de los tres equipos. Próxima reunión: revisar el flujo de aprobación y la integración con reportes.", True),
                 (2, "Llegó por recomendación. Julia pidió una demostración para dirección comercial y un cronograma de implementación.", True),
                 (4, "Enviar alcance del Plan Business y confirmar responsables para la capacitación inicial.", False),
                 (8, "Aprobación final recibida. Coordinar inicio y acceso de los usuarios.", False),
                 (13, "El cliente pausó la decisión por presupuesto; mantener contacto para el siguiente trimestre.", False))
        for i, body, pinned in notes:
            moment = result[i].created_at + timedelta(days=1)
            note = OpportunityNote(opportunity_id=result[i].id, author_user_id=users[OPPS[i][5]].id,
                                   created_at=moment)
            session.add(note)
            session.flush()
            session.add(OpportunityNoteRevision(note_id=note.id, revision_number=1, body=body,
                                                is_pinned=pinned, actor_user_id=users[OPPS[i][5]].id,
                                                command_id=stable(f"note-{i}"), created_at=moment))
    return result


def seed_whatsapp(session, anchor, users, customers, opps):
    storage = FilesystemMediaStorage(Path("/var/lib/pulse-crm/whatsapp-media"))
    media_root = Path(__file__).resolve().parents[1] / "demo_media"
    # Inbound offsets relative to anchor. 23h30m and 27h show both window states.
    cases = (
        (4, 2, ((-7, "IN", "Hola, ¿me pueden pasar detalles del plan Business?", None),
                (-6, "OUT", "Hola Paula, sí. Te comparto el alcance y coordinamos una llamada.", None),
                (-4, "IN", "Perfecto, ¿podemos verlo esta semana?", None),
                (-3, "OUT", "Claro, te propongo el jueves a las 11.", None))),
        (3, 1, ((-10, "IN", "Adjunto una idea del flujo que necesitamos.", "workflow.png"),
                 (-8, "OUT", "Gracias, lo revisamos y preparamos una propuesta.", None),
                 (-5, "IN", "También comparto la vista de indicadores.", "analytics.png"),
                 (-2, "OUT", "Recibido. Te enviamos un borrador para comentar.", "propuesta-demo.pdf"))),
        (6, 1, ((-5, "IN", "Les dejo una nota de voz con el contexto.", "nota-de-voz.ogg"),
                 (-1, "IN", "Quedo atenta a su respuesta.", None))),
        (1, 1, ((-23.5, "IN", "¿Podemos conversar sobre la capacitación del equipo?", None),)),
        (7, 2, ((-28, "IN", "Quisiera retomar esta consulta la semana próxima.", None),)),
    )
    with session.begin():
        for ci, seller_idx, specs in cases:
            customer = customers[ci]
            first_at = anchor + timedelta(hours=specs[0][0])
            last_at = anchor + timedelta(hours=specs[-1][0])
            inbound_at = max(anchor+timedelta(hours=offset) for offset, direction, _, _ in specs if direction == "IN")
            conversation = WhatsAppConversation(customer_id=customer.id, external_phone=customer.phone,
                phone_match_key=customer.phone.removeprefix("+"), display_name=customer.name,
                resolution_status=WhatsAppConversationResolution.RESOLVED, last_message_at=last_at,
                last_inbound_at=inbound_at, window_expires_at=inbound_at+timedelta(hours=24),
                unread_count=sum(1 for _, direction, _, _ in specs if direction == "IN"),
                created_at=first_at, updated_at=last_at)
            session.add(conversation)
            session.flush()
            session.add(WhatsAppConversationOpportunity(conversation_id=conversation.id,
                opportunity_id=opps[ci].id, linked_at=first_at,
                linked_by_user_id=users[seller_idx].id,
                link_source=WhatsAppOpportunityLinkSource.MANUAL))
            first_inbound = None
            for j, (offset, direction, body, filename) in enumerate(specs):
                at = anchor+timedelta(hours=offset)
                outbound = direction == "OUT"
                kind = {"png": WhatsAppMessageType.IMAGE, "pdf": WhatsAppMessageType.DOCUMENT,
                        "ogg": WhatsAppMessageType.AUDIO}.get(filename.rsplit(".", 1)[-1] if filename else "", WhatsAppMessageType.TEXT)
                msg = WhatsAppMessage(conversation_id=conversation.id,
                    external_message_id=f"pulse-demo-in-{ci}-{j}" if not outbound else f"pulse-demo-out-{ci}-{j}",
                    client_generated_id=stable(f"wa-{ci}-{j}") if outbound else None,
                    direction=WhatsAppDirection.OUTBOUND if outbound else WhatsAppDirection.INBOUND,
                    message_type=kind, origin=WhatsAppMessageOrigin.HUMAN, body=body,
                    sent_by_user_id=users[seller_idx].id if outbound else None,
                    dispatch_state=WhatsAppDispatchState.ACCEPTED if outbound else None,
                    provider_state=WhatsAppProviderState.READ if outbound else WhatsAppProviderState.RECEIVED,
                    provider_message_at=at, accepted_at=at if outbound else None,
                    sent_at=at if outbound else None, delivered_at=at+timedelta(seconds=5) if outbound else None,
                    read_at=at+timedelta(seconds=30) if outbound else None,
                    provider_status_at=at+timedelta(seconds=30) if outbound else at,
                    created_at=at, updated_at=at)
                session.add(msg)
                session.flush()
                if first_inbound is None and not outbound:
                    first_inbound = msg.id
                if filename:
                    kind_to_mime = {"png": "image/png", "pdf": "application/pdf", "ogg": "audio/ogg"}
                    data = (media_root/filename).read_bytes()
                    stored = storage.put(MediaPutRequest(media_ref=stable(f"media-{filename}"), content=data,
                        media_type=kind, mime_type=kind_to_mime[filename.rsplit(".",1)[1]], filename=filename))
                    session.add(WhatsAppAttachment(message_id=msg.id, media_type=kind,
                        provider_media_id=f"pulse-demo-media-{ci}-{j}", mime_type=stored.mime_type,
                        filename=filename, size_bytes=stored.size_bytes, storage_key=stored.storage_key,
                        storage_status=WhatsAppStorageStatus.AVAILABLE, created_at=at, updated_at=at))
            if opps[ci].source is LeadSource.WHATSAPP:
                opps[ci].initial_whatsapp_message_id = first_inbound
            session.flush()
            recompute_response_projection(session, conversation, now=anchor)


def seed_notifications(session, anchor, users, opps):
    with session.begin():
        session.execute(text("DELETE FROM notification_recipients"))
        session.execute(text("DELETE FROM notifications"))
        for j, (opp_idx, type_, seller_idx, read) in enumerate((
            (3, NotificationType.NEW_LEAD, 0, False),
            (6, NotificationType.NEW_LEAD, 1, False),
            (7, NotificationType.NEW_LEAD, 2, False),
            (0, NotificationType.OPPORTUNITY_STALE, 0, True),
            (2, NotificationType.OPPORTUNITY_STALE, 2, True),
            (5, NotificationType.NEW_LEAD, 0, True),
        )):
            at = anchor-timedelta(hours=2+j*4)
            notification = Notification(type=type_, opportunity_id=opps[opp_idx].id,
                                        created_at=at, read_at=at+timedelta(minutes=20) if read else None)
            session.add(notification)
            session.flush()
            session.add(NotificationRecipient(notification_id=notification.id,
                user_id=users[seller_idx].id, created_at=at,
                read_at=at+timedelta(minutes=20) if read else None))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="replace only recognized PULSE demo data")
    args = parser.parse_args()
    guard()
    password = environ.get("PULSE_DEMO_PASSWORD", "")
    if not 12 <= len(password) <= 128:
        raise SystemExit("PULSE_DEMO_PASSWORD must be 12-128 characters.")
    anchor = datetime.now(UTC).replace(microsecond=0)
    with SessionLocal() as session:
        before = inventory(session)
        if args.reset:
            reset(session)
        elif any(before.values()):
            if not owned(session):
                raise SystemExit("Seed refused: unrelated data is present.")
            if all(before[k] == n for k, n in (("users", 3), ("customers", 16), ("products", 6),
                                                ("opportunities", 16), ("conversations", 5),
                                                ("notifications", 6), ("attachments", 4))):
                print("PULSE demo already complete; no writes performed.")
                print(inventory(session))
                return
            raise SystemExit("Seed refused: partial demo data. Inspect it, then use --reset if owned.")
        users, products, customers = seed_base(session, anchor, password)
        opps = seed_opportunities(session, anchor, users, products, customers)
        seed_whatsapp(session, anchor, users, customers, opps)
        seed_notifications(session, anchor, users, opps)
        print("Seeded isolated PULSE video demo:")
        print(inventory(session))


if __name__ == "__main__":
    main()
