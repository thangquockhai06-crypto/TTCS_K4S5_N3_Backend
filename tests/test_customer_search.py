from sqlalchemy import event
from fastapi.testclient import TestClient

from app.models.customer import Contact


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_customer_search_normalizes_name_tax_and_contact_phone(client: TestClient, db_session, seed_data):
    customer = seed_data["customers"]["cust_a"]
    customer.tax_code = "031-234-567"
    db_session.add(
        Contact(
            id="contact-cust-a",
            customer_id=customer.id,
            full_name="Người liên hệ A",
            phone="+84 912 345 678",
            email="contact-a@test.com",
            is_primary=1,
        )
    )
    db_session.commit()

    headers = auth_header(seed_data["tokens"]["sales_director"])
    by_name = client.get("/api/v1/customers", params={"q": "cong ty a corp"}, headers=headers)
    by_tax = client.get("/api/v1/customers", params={"q": "031234"}, headers=headers)
    by_phone = client.get("/api/v1/customers", params={"q": "0912345678"}, headers=headers)
    wildcard = client.get("/api/v1/customers", params={"q": "%"}, headers=headers)

    assert [row["id"] for row in by_name.json()] == [customer.id]
    assert [row["id"] for row in by_tax.json()] == [customer.id]
    assert [row["id"] for row in by_phone.json()] == [customer.id]
    assert wildcard.json() == []
    assert by_phone.json()[0]["primaryContact"]["phone"] == "+84 912 345 678"


def test_customer_filters_owner_scope_paging_sort_and_total(client: TestClient, db_session, seed_data):
    customer = seed_data["customers"]["cust_a"]
    customer.industry = "TECH"
    customer.company_size = "SMB"
    customer.region = "Hanoi"
    db_session.commit()

    headers = auth_header(seed_data["tokens"]["emp_a"])
    response = client.get(
        "/api/v1/customers",
        params=[
            ("status", "active"),
            ("industry", "TECH"),
            ("companySize", "SMB"),
            ("region", "Hanoi"),
            ("owner", "me"),
            ("sort", "name"),
            ("descending", "false"),
            ("limit", "1"),
        ],
        headers=headers,
    )


    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "1"
    assert [row["id"] for row in response.json()] == [customer.id]

    invalid = client.get(
        "/api/v1/customers",
        params={"companySize": "INVALID"},
        headers=headers,
    )
    assert invalid.status_code == 422


def test_saved_filter_crud_apply_override_and_ownership(client: TestClient, seed_data):
    headers = auth_header(seed_data["tokens"]["emp_a"])
    create = client.post(
        "/api/v1/saved-filters",
        json={
            "name": "Active mine",
            "filterDefinition": {
                "status": ["active"],
                "owner": ["me"],
                "sort": "name",
                "descending": False,
            },
            "isDefault": True,
        },
        headers=headers,
    )
    assert create.status_code == 201
    saved = create.json()
    assert saved["filterDefinition"]["status"] == ["active"]
    assert saved["isDefault"] is True
    listed = client.get("/api/v1/saved-filters", headers=headers)
    fetched = client.get(f"/api/v1/saved-filters/{saved['id']}", headers=headers)
    assert listed.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["id"] == saved["id"]

    applied = client.get(
        "/api/v1/customers",
        params={"saved_filter_id": saved["id"]},
        headers=headers,
    )
    assert applied.status_code == 200
    assert [row["id"] for row in applied.json()] == [seed_data["customers"]["cust_a"].id]

    overridden = client.get(
        "/api/v1/customers",
        params={"saved_filter_id": saved["id"], "status": "prospect"},
        headers=headers,
    )
    assert overridden.status_code == 200
    assert overridden.json() == []

    duplicate = client.post(
        "/api/v1/saved-filters",
        json={"name": "active mine", "filterDefinition": {}},
        headers=headers,
    )
    assert duplicate.status_code == 409
    updated = client.patch(
        f"/api/v1/saved-filters/{saved['id']}",
        json={"name": "Active mine updated"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Active mine updated"

    other_user = client.get(
        "/api/v1/customers",
        params={"saved_filter_id": saved["id"]},
        headers=auth_header(seed_data["tokens"]["emp_b"]),
    )
    assert other_user.status_code == 404

    deleted = client.delete(f"/api/v1/saved-filters/{saved['id']}", headers=headers)
    assert deleted.status_code == 204


def test_customer_list_uses_bounded_query_count(client: TestClient, db_session, seed_data):
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", capture)
    try:
        response = client.get(
            "/api/v1/customers",
            headers=auth_header(seed_data["tokens"]["sales_director"]),
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture)

    assert response.status_code == 200
    assert len(statements) <= 5
