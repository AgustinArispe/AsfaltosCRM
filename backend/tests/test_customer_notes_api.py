from uuid import uuid4

from fastapi.testclient import TestClient


def test_customer_notes_create_edit_pin_and_archive(api_client: TestClient) -> None:
    customer = api_client.post(
        "/api/customers", json={"name": "Cliente de notas"}
    ).json()
    other = api_client.post(
        "/api/customers", json={"name": "Otro cliente de notas"}
    ).json()
    base = f"/api/customers/{customer['id']}/notes"
    other_base = f"/api/customers/{other['id']}/notes"
    payload = {"body": "  Prefiere mensajes por la tarde  ", "command_id": str(uuid4())}
    created = api_client.post(base, json=payload)
    assert created.status_code == 201
    note = created.json()
    assert note["body"] == "Prefiere mensajes por la tarde"
    assert note["author_name"] == "Supervisor de tests"
    assert api_client.post(base, json=payload).json()["id"] == note["id"]
    assert api_client.post(other_base, json=payload).status_code == 409
    assert api_client.get(other_base).json()["total"] == 0
    assert api_client.post(base, json={**payload, "body": " "}).status_code == 422

    newest = [
        api_client.post(
            base, json={"body": f"Dato {i}", "command_id": str(uuid4())}
        ).json()
        for i in range(3)
    ]
    for entry in [note, *newest[:2]]:
        data = {
            "body": f"{entry['body']} actualizado",
            "pinned": True,
            "expected_updated_at": entry["updated_at"],
        }
        target = f"{base}/{entry['id']}"
        pinned = api_client.put(target, json=data)
        assert pinned.status_code == 200
        assert pinned.json()["pinned"] is True
        assert pinned.json()["created_at"] == entry["created_at"]
        assert pinned.json()["author_name"] == entry["author_name"]
        assert api_client.put(target, json=data).status_code == 409
        assert (
            api_client.put(f"{other_base}/{entry['id']}", json=data).status_code == 404
        )
    last = newest[-1]
    last_data = {
        "body": last["body"],
        "pinned": True,
        "expected_updated_at": last["updated_at"],
    }
    assert api_client.put(f"{base}/{last['id']}", json=last_data).status_code == 409
    result = api_client.get(f"{base}?page_size=3").json()
    assert result["total"] == 4
    assert all(item["pinned"] for item in result["items"])
    assert api_client.delete(f"{base}/{note['id']}").status_code == 204
    assert api_client.put(f"{base}/{last['id']}", json=last_data).status_code == 200
    assert api_client.get(base).json()["total"] == 3
    assert api_client.delete(f"{base}/{note['id']}").status_code == 404
