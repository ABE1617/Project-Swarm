"""API tests through the full FastAPI stack (auth, workflows, runs, isolation)."""

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

VALID_DEFINITION = {
    "nodes": [
        {
            "id": "manual_trigger_1",
            "type": "manual_trigger",
            "position": {"x": 1, "y": 2},
            "config": {"payload": '{"n": 1}'},
        },
        {
            "id": "set_variable_1",
            "type": "set_variable",
            "position": {"x": 100, "y": 2},
            "config": {"variables": "{\"doubled\": {{ input['n'] * 2 }}}"},
        },
    ],
    "edges": [
        {
            "source": "manual_trigger_1",
            "target": "set_variable_1",
            "sourceHandle": "out",
            "targetHandle": "in",
        }
    ],
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def logged_in(client):
    response = client.post(
        "/api/auth/register",
        json={"username": "tester", "email": "tester@example.com", "password": "secret123"},
    )
    assert response.status_code == 200, response.text
    return client


# ---------- auth ----------


def test_me_requires_auth(client):
    fresh = TestClient(app)
    assert fresh.get("/api/auth/me").status_code == 401


def test_register_rejects_duplicates(logged_in):
    response = logged_in.post(
        "/api/auth/register",
        json={"username": "tester", "email": "other@example.com", "password": "secret123"},
    )
    assert response.status_code == 409


def test_register_rejects_invalid_email(client):
    response = client.post(
        "/api/auth/register",
        json={"username": "bademail", "email": "not-an-email", "password": "secret123"},
    )
    assert response.status_code == 422


def test_login_wrong_password(logged_in):
    fresh = TestClient(app)
    response = fresh.post("/api/auth/login", json={"username": "tester", "password": "wrong"})
    assert response.status_code == 401


def test_me_returns_user(logged_in):
    data = logged_in.get("/api/auth/me").json()
    assert data["user"]["username"] == "tester"


# ---------- nodes ----------


def test_nodes_require_auth(client):
    fresh = TestClient(app)
    assert fresh.get("/api/nodes").status_code == 401


def test_nodes_lists_builtins(logged_in):
    data = logged_in.get("/api/nodes").json()
    types = {n["type"] for n in data["nodes"]}
    assert {"manual_trigger", "if_condition", "http_request"} <= types
    assert "load_errors" in data


# ---------- workflows ----------


def test_workflow_crud_roundtrip(logged_in):
    created = logged_in.post(
        "/api/workflows", json={"name": "crud test", "definition": VALID_DEFINITION}
    )
    assert created.status_code == 200
    wf_id = created.json()["workflow"]["id"]

    listed = logged_in.get("/api/workflows").json()["workflows"]
    assert any(w["id"] == wf_id for w in listed)

    fetched = logged_in.get(f"/api/workflows/{wf_id}").json()["workflow"]
    assert fetched["definition"]["nodes"][0]["position"] == {"x": 1, "y": 2}
    assert fetched["definition"]["edges"][0]["sourceHandle"] == "out"

    updated = logged_in.put(
        f"/api/workflows/{wf_id}", json={"name": "renamed", "definition": VALID_DEFINITION}
    )
    assert updated.status_code == 200
    assert logged_in.get(f"/api/workflows/{wf_id}").json()["workflow"]["name"] == "renamed"

    assert logged_in.delete(f"/api/workflows/{wf_id}").status_code == 200
    assert logged_in.get(f"/api/workflows/{wf_id}").status_code == 404


def test_workflow_save_validates_shape(logged_in):
    bad = {"nodes": [{"id": "a", "type": "x"}], "edges": [{"source": "a"}]}  # edge missing target
    response = logged_in.post("/api/workflows", json={"name": "bad", "definition": bad})
    assert response.status_code == 422


def test_workflows_isolated_between_users(logged_in):
    created = logged_in.post(
        "/api/workflows", json={"name": "private", "definition": VALID_DEFINITION}
    )
    wf_id = created.json()["workflow"]["id"]

    other = TestClient(app)
    other.post(
        "/api/auth/register",
        json={"username": "intruder", "email": "intruder@example.com", "password": "secret123"},
    )
    assert other.get(f"/api/workflows/{wf_id}").status_code == 404
    assert other.delete(f"/api/workflows/{wf_id}").status_code == 404


# ---------- runs ----------


def test_run_executes_and_persists(logged_in):
    started = logged_in.post(
        "/api/run", json={"definition": VALID_DEFINITION, "workflow_name": "api run"}
    )
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    for _ in range(50):
        run = logged_in.get(f"/api/runs/{run_id}").json()["run"]
        if run["status"] != "running":
            break
        time.sleep(0.1)
    assert run["status"] == "success"
    assert run["result"]["outputs"]["set_variable_1"]["doubled"] == 2

    executions = logged_in.get("/api/executions").json()["executions"]
    assert any(e["id"] == run_id and e["status"] == "success" for e in executions)

    detail = logged_in.get(f"/api/executions/{run_id}").json()["execution"]
    assert detail["summary"]["node_statuses"]["set_variable_1"] == "success"


def test_run_with_unknown_node_type_reports_error(logged_in):
    definition = {
        "nodes": [{"id": "a", "type": "does_not_exist", "config": {}}],
        "edges": [],
    }
    started = logged_in.post("/api/run", json={"definition": definition})
    run_id = started.json()["run_id"]
    for _ in range(50):
        run = logged_in.get(f"/api/runs/{run_id}").json()["run"]
        if run["status"] != "running":
            break
        time.sleep(0.1)
    assert run["status"] == "error"
    assert "Unknown node types" in run["result"]["error"]


def test_runs_isolated_between_users(logged_in):
    started = logged_in.post("/api/run", json={"definition": VALID_DEFINITION})
    run_id = started.json()["run_id"]

    other = TestClient(app)
    other.post("/api/auth/login", json={"username": "intruder", "password": "secret123"})
    assert other.get(f"/api/runs/{run_id}").status_code == 404
