from conftest import token_for

HEADERS = {"Authorization": f"Bearer {token_for(['ti-viewers'])}"}


def test_members_are_paginated_without_emails(client):
    body = client.get("/api/v1/teams/1/members?page_size=2", headers=HEADERS).json()
    assert body["total"] == 3 and body["page"] == 1 and len(body["items"]) == 2
    assert set(body["items"][0]) == {"name", "role", "start_date"}


def test_unknown_team_uses_the_error_envelope(client):
    response = client.get("/api/v1/teams/99/members", headers=HEADERS)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_summary_goes_through_the_llm_gateway(client):
    body = client.get("/api/v1/teams/1/summary", headers=HEADERS).json()
    assert body["summary"].startswith("[fake summary of")


def test_request_ids_are_echoed(client):
    response = client.get("/healthz", headers={"x-request-id": "abc123"})
    assert response.headers["x-request-id"] == "abc123"
