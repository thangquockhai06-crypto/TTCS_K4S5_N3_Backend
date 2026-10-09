from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.win_loss import WinLossReason

def headers(seed_data: dict, key: str) -> dict:
    return {"Authorization": f"Bearer {seed_data['tokens'][key]}"}


def add_lost_catalog(db_session: Session, code: str = "OTHER") -> WinLossReason:
    reason = WinLossReason(
        id=f"reason-{code.lower()}",
        result_type="LOST",
        code=code,
        reason=code.title(),
        is_active=True,
    )
    db_session.add(reason)
    db_session.commit()
    return reason


def test_close_won_requires_positive_value_and_signed_date(client: TestClient, seed_data: dict):
    deal_id = seed_data["deals"]["deal_a"].id
    auth = headers(seed_data, "emp_a")

    missing_value = client.post(
        f"/api/v1/opportunities/{deal_id}/close",
        json={"outcome": "WON", "signedDate": "2026-01-10"},
        headers=auth,
    )
    assert missing_value.status_code == 422

    negative = client.post(
        f"/api/v1/opportunities/{deal_id}/close",
        json={"outcome": "WON", "actualValue": "-1", "signedDate": "2026-01-10"},
        headers=auth,
    )
    assert negative.status_code == 422

    success = client.post(
        f"/api/v1/opportunities/{deal_id}/close",
        json={"outcome": "WON", "actualValue": "125000000.00", "signedDate": "2026-01-10"},
        headers=auth,
    )
    assert success.status_code == 200
    body = success.json()
    assert body["outcome"] == "WON"
    assert body["actualValue"] == "125000000.00"
    assert body["signedDate"] == "2026-01-10"


def test_close_lost_requires_active_reason_and_other_note(
    client: TestClient,
    seed_data: dict,
    db_session: Session,
):
    reason = add_lost_catalog(db_session)
    deal_id = seed_data["deals"]["deal_b"].id
    auth = headers(seed_data, "emp_b")

    missing = client.post(
        f"/api/v1/deals/{deal_id}/close",
        json={"outcome": "LOST"},
        headers=auth,
    )
    assert missing.status_code == 422

    without_note = client.post(
        f"/api/v1/deals/{deal_id}/close",
        json={"outcome": "LOST", "lostReasonId": reason.id},
        headers=auth,
    )
    assert without_note.status_code == 400
    assert "lostReasonNote" in without_note.json()["detail"]

    won_field = client.post(
        f"/api/v1/deals/{deal_id}/close",
        json={
            "outcome": "LOST",
            "lostReasonId": reason.id,
            "lostReasonNote": "No decision after final review",
            "actualValue": "10",
        },
        headers=auth,
    )
    assert won_field.status_code == 422

    success = client.post(
        f"/api/v1/deals/{deal_id}/close",
        json={
            "outcome": "LOST",
            "lostReasonId": reason.id,
            "lostReasonNote": "No decision after final review",
        },
        headers=auth,
    )
    assert success.status_code == 200
    assert success.json()["outcome"] == "LOST"


def test_closed_deal_is_immutable_and_duplicate_close_is_conflict(
    client: TestClient,
    seed_data: dict,
):
    deal_id = seed_data["deals"]["deal_a"].id
    auth = headers(seed_data, "emp_a")
    payload = {"outcome": "WON", "actualValue": "100", "signedDate": "2026-02-01"}
    assert client.post(f"/api/v1/deals/{deal_id}/close", json=payload, headers=auth).status_code == 200

    duplicate = client.post(f"/api/v1/deals/{deal_id}/close", json=payload, headers=auth)
    assert duplicate.status_code == 409

    update = client.patch(
        f"/api/v1/deals/{deal_id}",
        json={"title": "mutated"},
        headers=auth,
    )
    assert update.status_code == 409

    stage = client.patch(
        f"/api/v1/deals/{deal_id}/stage",
        json={"stage": "negotiation"},
        headers=auth,
    )
    assert stage.status_code == 409



def test_only_team_lead_in_scope_can_reopen_and_history_is_preserved(
    client: TestClient,
    seed_data: dict,
):
    deal_id = seed_data["deals"]["deal_a"].id
    assert client.post(
        f"/api/v1/opportunities/{deal_id}/close",
        json={"outcome": "WON", "actualValue": "100", "signedDate": "2026-02-01"},
        headers=headers(seed_data, "emp_a"),
    ).status_code == 200

    forbidden = client.post(
        f"/api/v1/opportunities/{deal_id}/reopen",
        json={"reopenReason": "Need a new negotiation"},
        headers=headers(seed_data, "emp_b"),
    )
    assert forbidden.status_code == 403

    reopened = client.post(
        f"/api/v1/opportunities/{deal_id}/reopen",
        json={"reopenReason": "Need a new negotiation"},
        headers=headers(seed_data, "team_leader"),
    )
    assert reopened.status_code == 200
    body = reopened.json()
    assert body["outcome"] == "OPEN"
    assert body["stage"] == "proposal"
    assert body["actualValue"] is None
    assert len(body["history"]) == 2
    assert body["history"][0]["action"] == "CLOSED"
    assert body["history"][1]["action"] == "REOPENED"


def test_kpi_uses_signed_date_and_reopen_removes_value(
    client: TestClient,
    seed_data: dict,
):
    deal_id = seed_data["deals"]["deal_a"].id
    auth = headers(seed_data, "emp_a")
    close = client.post(
        f"/api/v1/opportunities/{deal_id}/close",
        json={"outcome": "WON", "actualValue": "123.45", "signedDate": "2026-03-31"},
        headers=auth,
    )
    assert close.status_code == 200

    kpi = client.get(
        "/api/v1/dashboard/kpi/won-value",
        params={"periodStart": "2026-03-01", "periodEnd": "2026-03-31"},
        headers=auth,
    )
    assert kpi.status_code == 200
    assert float(kpi.json()["wonValue"]) == 123.45

    reopened = client.post(
        f"/api/v1/opportunities/{deal_id}/reopen",
        json={"reopenReason": "Customer changed approval path"},
        headers=headers(seed_data, "team_leader"),
    )
    assert reopened.status_code == 200
    after_reopen = client.get(
        "/api/v1/dashboard/kpi/won-value",
        params={"periodStart": "2026-03-01", "periodEnd": "2026-03-31"},
        headers=auth,
    )
    assert after_reopen.status_code == 200
    assert float(after_reopen.json()["wonValue"]) == 0.0


def test_outcome_filters_respect_scope_and_signed_date(client: TestClient, seed_data: dict):
    deal_id = seed_data["deals"]["deal_a"].id
    auth = headers(seed_data, "emp_a")
    assert client.post(
        f"/api/v1/opportunities/{deal_id}/close",
        json={"outcome": "WON", "actualValue": "100", "signedDate": "2026-04-01"},
        headers=auth,
    ).status_code == 200

    response = client.get(
        "/api/v1/opportunities",
        params={"outcome": "WON", "signedFrom": "2026-04-01", "signedTo": "2026-04-01"},
        headers=auth,
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [deal_id]


def test_close_and_reopen_write_audit_records(
    client: TestClient,
    seed_data: dict,
    db_session: Session,
):
    deal_id = seed_data["deals"]["deal_a"].id
    assert client.post(
        f"/api/v1/opportunities/{deal_id}/close",
        json={"outcome": "WON", "actualValue": "100", "signedDate": "2026-05-01"},
        headers=headers(seed_data, "emp_a"),
    ).status_code == 200
    assert client.post(
        f"/api/v1/opportunities/{deal_id}/reopen",
        json={"reopenReason": "Rework the commercial proposal"},
        headers=headers(seed_data, "team_leader"),
    ).status_code == 200

    actions = [
        row.action
        for row in db_session.query(AuditLog)
        .filter(AuditLog.target_type == "opportunity", AuditLog.target_id == deal_id)
        .order_by(AuditLog.created_at.asc())
        .all()
    ]
    assert "OPPORTUNITY_CLOSED" in actions
    assert "OPPORTUNITY_REOPENED" in actions
