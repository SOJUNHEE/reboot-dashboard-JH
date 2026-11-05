"""시연(보기 전용) 모드 PUBLIC_DEMO=1 — 로그인 없이 입장 · 쓰기 잠금 (server/demo.py)."""
from conftest import make_app
from server.demo import DEMO_EMAIL
from server.models import User


def _demo_client(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, PUBLIC_DEMO=True)
    return app, app.test_client()


def test_demo_enters_without_login(tmp_path, monkeypatch):
    app, client = _demo_client(tmp_path, monkeypatch)
    assert client.get("/dashboard").status_code == 200
    assert client.get("/dashboard/compliance").status_code == 200
    me = client.get("/api/me")
    assert me.status_code == 200
    with app.app_context():
        viewer = User.query.filter_by(email=DEMO_EMAIL).one()
        assert not viewer.is_admin


def test_demo_login_page_goes_home(tmp_path, monkeypatch):
    _, client = _demo_client(tmp_path, monkeypatch)
    res = client.get("/login")
    assert res.status_code == 302 and res.headers["Location"].endswith("/")


def test_demo_blocks_every_write(tmp_path, monkeypatch):
    _, client = _demo_client(tmp_path, monkeypatch)
    client.get("/dashboard/home")
    res = client.post("/api/worklog", json={"text": "x"})
    assert res.status_code == 403 and res.get_json()["demo"] is True
    assert client.patch("/api/me", json={"name": "바꿈"}).status_code == 403
    assert client.post("/api/users", json={"email": "x@y.z", "password": "12345678"}).status_code == 403
    assert client.post("/logout").status_code == 302


def test_demo_viewer_is_not_admin(tmp_path, monkeypatch):
    _, client = _demo_client(tmp_path, monkeypatch)
    client.get("/dashboard/home")
    assert client.get("/api/users").status_code == 403


def test_demo_keeps_cron_job(tmp_path, monkeypatch):
    _, client = _demo_client(tmp_path, monkeypatch)
    res = client.post("/api/jobs/daily", headers={"X-Cron-Token": "test-cron-token"})
    assert res.status_code != 403 or "demo" not in (res.get_json() or {})


def test_without_demo_login_is_required(client):
    assert client.get("/dashboard").status_code == 302
    assert client.get("/api/me").status_code == 401
