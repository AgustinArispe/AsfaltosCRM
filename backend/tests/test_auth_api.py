from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import JWT_ALGORITHM, get_jwt_secret
from app.core.security import create_access_token, hash_password, verify_password
from app.models import OpportunityStatusHistory, User, UserRole

SUPERVISOR_PASSWORD = "supervisor-test-password"
VENDOR_PASSWORD = "vendor-test-password"


def persist(db_session: Session, *entities: object) -> None:
    db_session.add_all(entities)
    db_session.commit()


def make_vendor(
    db_session: Session,
    *,
    email: str = "vendor-auth@faa.test",
) -> User:
    user = User(
        full_name="Vendedor autenticado",
        email=email,
        password_hash=hash_password(VENDOR_PASSWORD),
        role=UserRole.VENDEDOR,
    )
    persist(db_session, user)
    return user


def authenticate_as(client: TestClient, user: User) -> None:
    client.headers["Authorization"] = f"Bearer {create_access_token(user.id)}"


def login(client: TestClient, email: str, password: str) -> Response:
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


def test_password_hashing_and_verification() -> None:
    password = "a-safe-test-password"
    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2")
    assert verify_password(password, password_hash)
    assert not verify_password("incorrect-password", password_hash)
    assert not verify_password(password, "not-a-supported-hash")


def test_login_me_and_invalid_credentials(
    api_client: TestClient,
    supervisor_user: User,
) -> None:
    successful = login(
        api_client,
        "  SUPERVISOR-TESTS@FAA.TEST ",
        SUPERVISOR_PASSWORD,
    )

    assert successful.status_code == 200
    assert successful.json()["token_type"] == "bearer"
    assert successful.json()["expires_in"] == 3600

    api_client.headers["Authorization"] = f"Bearer {successful.json()['access_token']}"
    me = api_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == supervisor_user.id
    assert me.json()["role"] == "SUPERVISOR"
    assert "password_hash" not in me.json()

    wrong_password = login(
        api_client,
        supervisor_user.email,
        "wrong-password",
    )
    missing_email = login(
        api_client,
        "missing-user@faa.test",
        "wrong-password",
    )
    assert wrong_password.status_code == 401
    assert missing_email.status_code == 401
    assert (
        wrong_password.json()
        == missing_email.json()
        == {"detail": "Invalid email or password"}
    )


def test_inactive_user_and_invalid_tokens_are_rejected(
    api_client: TestClient,
    db_session: Session,
    supervisor_user: User,
) -> None:
    expired_token = create_access_token(
        supervisor_user.id,
        expires_delta=timedelta(seconds=-1),
    )
    api_client.headers["Authorization"] = f"Bearer {expired_token}"
    assert api_client.get("/api/auth/me").status_code == 401

    api_client.headers["Authorization"] = "Bearer malformed-token"
    assert api_client.get("/api/auth/me").status_code == 401

    api_client.headers.pop("Authorization")
    unauthorized = api_client.get("/api/customers")
    assert unauthorized.status_code == 401
    assert unauthorized.headers["www-authenticate"] == "Bearer"
    assert api_client.get("/health").status_code == 200

    db_session.execute(
        update(User).where(User.id == supervisor_user.id).values(is_active=False)
    )
    db_session.commit()
    assert (
        login(api_client, supervisor_user.email, SUPERVISOR_PASSWORD).status_code == 401
    )
    api_client.headers["Authorization"] = (
        f"Bearer {create_access_token(supervisor_user.id)}"
    )
    assert api_client.get("/api/auth/me").status_code == 401


def test_jwt_requires_expiration_positive_subject_and_fixed_algorithm(
    api_client: TestClient,
    supervisor_user: User,
) -> None:
    expires_at = datetime.now(UTC) + timedelta(minutes=5)
    invalid_tokens = [
        jwt.encode(
            {"sub": str(supervisor_user.id)},
            get_jwt_secret(),
            algorithm=JWT_ALGORITHM,
        ),
        jwt.encode(
            {"sub": "0", "exp": expires_at},
            get_jwt_secret(),
            algorithm=JWT_ALGORITHM,
        ),
        jwt.encode(
            {"sub": "not-an-id", "exp": expires_at},
            get_jwt_secret(),
            algorithm=JWT_ALGORITHM,
        ),
        jwt.encode(
            {"sub": str(supervisor_user.id), "exp": expires_at},
            key="",
            algorithm="none",
        ),
    ]

    for token in invalid_tokens:
        api_client.headers["Authorization"] = f"Bearer {token}"
        response = api_client.get("/api/auth/me")
        assert response.status_code == 401
        assert response.json() == {"detail": "Could not validate credentials"}


def test_supervisor_manages_users_and_passwords(
    api_client: TestClient,
    db_session: Session,
) -> None:
    created = api_client.post(
        "/api/users",
        json={
            "full_name": "Vendedor API",
            "email": "Vendor.Users@FAA.test",
            "password": VENDOR_PASSWORD,
            "role": "VENDEDOR",
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]
    assert created.json()["email"] == "vendor.users@faa.test"
    assert "password_hash" not in created.json()

    duplicate = api_client.post(
        "/api/users",
        json={
            "full_name": "Duplicado",
            "email": "  VENDOR.USERS@FAA.TEST ",
            "password": VENDOR_PASSWORD,
            "role": "VENDEDOR",
        },
    )
    assert duplicate.status_code == 409
    assert api_client.get(f"/api/users/{user_id}").status_code == 200
    assert any(user["id"] == user_id for user in api_client.get("/api/users").json())
    assert (
        login(api_client, "vendor.users@faa.test", VENDOR_PASSWORD).status_code == 200
    )

    changed_password = api_client.put(
        f"/api/users/{user_id}/password",
        json={"password": "replacement-password"},
    )
    assert changed_password.status_code == 200
    assert (
        login(api_client, "vendor.users@faa.test", VENDOR_PASSWORD).status_code == 401
    )
    assert (
        login(api_client, "vendor.users@faa.test", "replacement-password").status_code
        == 200
    )

    deactivated = api_client.patch(
        f"/api/users/{user_id}",
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert (
        login(api_client, "vendor.users@faa.test", "replacement-password").status_code
        == 401
    )
    persisted_user = db_session.get(User, user_id)
    assert persisted_user is not None
    assert persisted_user.password_hash != "replacement-password"
    assert verify_password("replacement-password", persisted_user.password_hash)


def test_vendor_cannot_manage_users(
    api_client: TestClient,
    db_session: Session,
) -> None:
    vendor = make_vendor(db_session)
    authenticate_as(api_client, vendor)

    assert api_client.get("/api/users").status_code == 403
    assert (
        api_client.post(
            "/api/users",
            json={
                "full_name": "Sin permiso",
                "email": "forbidden@faa.test",
                "password": VENDOR_PASSWORD,
                "role": "VENDEDOR",
            },
        ).status_code
        == 403
    )


def test_customer_permissions_by_role(
    api_client: TestClient,
    db_session: Session,
    supervisor_user: User,
) -> None:
    vendor = make_vendor(db_session)
    authenticate_as(api_client, vendor)

    created = api_client.post("/api/customers", json={"name": "Cliente vendedor"})
    assert created.status_code == 201
    customer_id = created.json()["id"]
    assert api_client.get("/api/customers").status_code == 200
    assert (
        api_client.patch(
            f"/api/customers/{customer_id}",
            json={"phone": "1123456789"},
        ).status_code
        == 200
    )
    assert (
        api_client.patch(
            f"/api/customers/{customer_id}",
            json={"legendary_historical_override": True},
        ).status_code
        == 403
    )
    assert (
        api_client.post(
            "/api/customers",
            json={
                "name": "Legendario prohibido",
                "legendary_historical_override": False,
            },
        ).status_code
        == 403
    )
    assert api_client.delete(f"/api/customers/{customer_id}").status_code == 403

    authenticate_as(api_client, supervisor_user)
    override = api_client.patch(
        f"/api/customers/{customer_id}",
        json={"legendary_historical_override": True},
    )
    assert override.status_code == 200
    assert override.json()["legendary_historical_override"] is True


def test_product_permissions_by_role(
    api_client: TestClient,
    db_session: Session,
    supervisor_user: User,
) -> None:
    vendor = make_vendor(db_session)
    authenticate_as(api_client, supervisor_user)
    product = api_client.post("/api/products", json={"name": "Producto permisos"})
    assert product.status_code == 201

    authenticate_as(api_client, vendor)
    assert api_client.get("/api/products").status_code == 200
    assert (
        api_client.get(
            "/api/products",
            params={"include_inactive": True},
        ).status_code
        == 403
    )
    assert (
        api_client.post("/api/products", json={"name": "Prohibido"}).status_code == 403
    )
    assert (
        api_client.patch(
            f"/api/products/{product.json()['id']}",
            json={"is_active": False},
        ).status_code
        == 403
    )

    authenticate_as(api_client, supervisor_user)
    assert (
        api_client.patch(
            f"/api/products/{product.json()['id']}",
            json={"is_active": False},
        ).status_code
        == 200
    )


def test_vendor_opportunity_flow_uses_authenticated_actor(
    api_client: TestClient,
    db_session: Session,
    supervisor_user: User,
) -> None:
    vendor = make_vendor(db_session)
    authenticate_as(api_client, supervisor_user)
    product = api_client.post("/api/products", json={"name": "Producto auditoría"})
    assert product.status_code == 201

    authenticate_as(api_client, vendor)
    customer = api_client.post("/api/customers", json={"name": "Cliente auditoría"})
    opportunity = api_client.post(
        "/api/opportunities",
        json={"customer_id": customer.json()["id"], "source": "WEB"},
    )
    assert opportunity.status_code == 201
    opportunity_id = opportunity.json()["id"]

    spoofed_actor = api_client.post(
        f"/api/opportunities/{opportunity_id}/quote",
        json={
            "products": [{"product_id": product.json()["id"], "quantity_kg": 1000}],
            "changed_by_user_id": supervisor_user.id,
        },
    )
    assert spoofed_actor.status_code == 422

    quoted = api_client.post(
        f"/api/opportunities/{opportunity_id}/quote",
        json={"products": [{"product_id": product.json()["id"], "quantity_kg": 1000}]},
    )
    assert quoted.status_code == 200
    negotiation = api_client.post(
        f"/api/opportunities/{opportunity_id}/move-to-negotiation",
        json={},
    )
    assert negotiation.status_code == 200
    won = api_client.post(f"/api/opportunities/{opportunity_id}/win", json={})
    assert won.status_code == 200

    second_opportunity = api_client.post(
        "/api/opportunities",
        json={"customer_id": customer.json()["id"], "source": "WHATSAPP"},
    )
    second_id = second_opportunity.json()["id"]
    assert (
        api_client.put(
            f"/api/opportunities/{second_id}/assignee",
            json={"assigned_user_id": vendor.id},
        ).status_code
        == 403
    )
    assert (
        api_client.post(
            "/api/opportunities",
            json={
                "customer_id": customer.json()["id"],
                "source": "WEB",
                "assigned_user_id": vendor.id,
            },
        ).status_code
        == 403
    )

    authenticate_as(api_client, supervisor_user)
    assigned = api_client.put(
        f"/api/opportunities/{second_id}/assignee",
        json={"assigned_user_id": vendor.id},
    )
    assert assigned.status_code == 200
    assert assigned.json()["assigned_user"]["id"] == vendor.id

    history = db_session.scalars(
        select(OpportunityStatusHistory)
        .where(OpportunityStatusHistory.opportunity_id == opportunity_id)
        .order_by(OpportunityStatusHistory.changed_at)
    ).all()
    assert [entry.changed_by_user_id for entry in history] == [vendor.id] * 4


def test_openapi_declares_bearer_security(api_client: TestClient) -> None:
    document = api_client.get("/openapi.json").json()
    schemes = document["components"]["securitySchemes"]

    assert any(
        scheme.get("type") == "http" and scheme.get("scheme") == "bearer"
        for scheme in schemes.values()
    )
    assert document["paths"]["/api/auth/login"]["post"].get("security") is None
    assert document["paths"]["/api/customers"]["get"]["security"]
