from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.product import Product
from app.services.catalog_item_service import requires_discount_approval


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def catalog_payload(code: str = "CRM-STD-001") -> dict:
    return {
        "code": code,
        "name": "CRM Standard",
        "type": "ONE_TIME_PRODUCT",
        "unitOfMeasure": "license",
        "listPrice": "10000000.00",
        "floorPrice": "8000000.00",
        "costPrice": "5000000.00",
        "currency": "VND",
    }


def create_catalog_item(client: TestClient, token: str, code: str = "CRM-STD-001") -> dict:
    response = client.post(
        "/api/v1/catalog-items",
        json=catalog_payload(code),
        headers=auth_header(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_sales_director_can_manage_catalog_and_staff_cannot_see_cost(
    client: TestClient, seed_data: dict
):
    director_token = seed_data["tokens"]["sales_director"]
    created = create_catalog_item(client, director_token)
    assert float(created["costPrice"]) == 5000000.00
    assert float(created["listPrice"]) == 10000000.00

    director_list = client.get(
        "/api/v1/catalog-items", headers=auth_header(director_token)
    )
    assert director_list.status_code == 200
    assert "costPrice" in director_list.json()[0]

    staff_token = seed_data["tokens"]["emp_a"]
    staff_list = client.get(
        "/api/v1/catalog-items", headers=auth_header(staff_token)
    )
    assert staff_list.status_code == 200
    assert all("costPrice" not in item for item in staff_list.json())

    detail = client.get(
        f"/api/v1/catalog-items/{created['id']}", headers=auth_header(staff_token)
    )
    assert detail.status_code == 200
    assert "costPrice" not in detail.json()

    forbidden_create = client.post(
        "/api/v1/catalog-items",
        json=catalog_payload("STAFF-CREATE-001"),
        headers=auth_header(staff_token),
    )
    assert forbidden_create.status_code == 403

    forbidden_update = client.put(
        f"/api/v1/catalog-items/{created['id']}",
        json={"costPrice": "4000000.00"},
        headers=auth_header(staff_token),
    )
    assert forbidden_update.status_code == 403


def test_catalog_validation_and_case_insensitive_duplicate(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]
    create_catalog_item(client, token, "Case-Code")

    duplicate = client.post(
        "/api/v1/catalog-items",
        json=catalog_payload("case-code"),
        headers=auth_header(token),
    )
    assert duplicate.status_code == 409

    negative = catalog_payload("NEGATIVE-001")
    negative["listPrice"] = "-1"
    assert client.post(
        "/api/v1/catalog-items", json=negative, headers=auth_header(token)
    ).status_code == 422

    invalid_order = catalog_payload("ORDER-001")
    invalid_order["floorPrice"] = "11000000"
    assert client.post(
        "/api/v1/catalog-items", json=invalid_order, headers=auth_header(token)
    ).status_code == 422

    invalid_type = catalog_payload("TYPE-001")
    invalid_type["type"] = "MISC"
    assert client.post(
        "/api/v1/catalog-items", json=invalid_type, headers=auth_header(token)
    ).status_code == 422


def test_unused_item_can_be_deleted(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]
    item = create_catalog_item(client, token, "DELETE-001")
    response = client.delete(
        f"/api/v1/catalog-items/{item['id']}", headers=auth_header(token)
    )
    assert response.status_code == 200
    assert client.get(
        f"/api/v1/catalog-items/{item['id']}", headers=auth_header(token)
    ).status_code == 404


def test_used_item_cannot_be_deleted_and_quote_keeps_price_snapshots(
    client: TestClient, seed_data: dict, db_session: Session
):
    token = seed_data["tokens"]["sales_director"]
    item = create_catalog_item(client, token, "QUOTED-001")
    customer_id = seed_data["customers"]["cust_a"].id
    quote_response = client.post(
        "/api/v1/quotations",
        json={
            "quoteNumber": "Q-CATALOG-001",
            "title": "Catalog quote",
            "customerId": customer_id,
            "items": [
                {"productId": item["id"], "quantity": "2", "unitPrice": "7500000.00"}
            ],
        },
        headers=auth_header(token),
    )
    assert quote_response.status_code == 201, quote_response.text
    quote = quote_response.json()
    assert quote["requiresDiscountApproval"] is True
    assert float(quote["items"][0]["listPriceSnapshot"]) == 10000000.00
    assert float(quote["items"][0]["floorPriceSnapshot"]) == 8000000.00
    assert "costPrice" not in quote["items"][0]

    delete_response = client.delete(
        f"/api/v1/catalog-items/{item['id']}", headers=auth_header(token)
    )
    assert delete_response.status_code == 409

    discontinued = client.post(
        f"/api/v1/catalog-items/{item['id']}/discontinue",
        headers=auth_header(token),
    )
    assert discontinued.status_code == 200
    assert discontinued.json()["status"] == "DISCONTINUED"

    blocked_quote = client.post(
        "/api/v1/quotations",
        json={
            "quoteNumber": "Q-CATALOG-002",
            "title": "Blocked quote",
            "customerId": customer_id,
            "items": [{"productId": item["id"], "quantity": "1"}],
        },
        headers=auth_header(token),
    )
    assert blocked_quote.status_code == 409

    updated = client.put(
        f"/api/v1/catalog-items/{item['id']}",
        json={"listPrice": "12000000.00", "floorPrice": "9000000.00"},
        headers=auth_header(token),
    )
    assert updated.status_code == 200

    historical = client.get(
        f"/api/v1/quotations/{quote['id']}", headers=auth_header(token)
    )
    assert historical.status_code == 200
    assert float(historical.json()["items"][0]["listPriceSnapshot"]) == 10000000.00
    assert float(historical.json()["items"][0]["floorPriceSnapshot"]) == 8000000.00

    audit_rows = db_session.query(AuditLog).filter(
        AuditLog.target_type == "catalog_item", AuditLog.target_id == item["id"]
    ).all()
    assert {row.field_name for row in audit_rows} >= {"list_price", "floor_price", "cost_price", "status"}


def test_discount_approval_boundaries(db_session: Session):
    item = Product(list_price=Decimal("100.00"), floor_price=Decimal("80.00"))
    assert requires_discount_approval(Decimal("79.99"), item) is True
    assert requires_discount_approval(Decimal("80.00"), item) is False
    assert requires_discount_approval(Decimal("100.00"), item) is False
