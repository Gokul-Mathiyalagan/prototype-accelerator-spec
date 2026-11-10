from conftest import token_for

from app.roles import has_role, roles_for_groups


def test_api_needs_a_token(client):
    response = client.get("/api/v1/teams/1/members")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"
    assert response.json()["error"]["request_id"]


def test_a_bad_token_is_rejected(client):
    response = client.get("/api/v1/teams/1/members", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_viewer_can_list_but_not_export(client):
    headers = {"Authorization": f"Bearer {token_for(['ti-viewers'], 'bob')}"}
    assert client.get("/api/v1/teams/1/members", headers=headers).status_code == 200
    response = client.get("/api/v1/teams/1/members.csv", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_analyst_can_export(client):
    headers = {"Authorization": f"Bearer {token_for(['ti-analysts'])}"}
    response = client.get("/api/v1/teams/1/members.csv", headers=headers)
    assert response.status_code == 200
    assert response.text.splitlines()[0] == "name,role,start_date"


def test_groups_map_to_roles():
    assert roles_for_groups(["ti-analysts", "other"]) == {"analyst"}
    assert has_role({"admin"}, "analyst")
    assert not has_role({"viewer"}, "analyst")
