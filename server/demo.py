"""시연(보기 전용) 모드 — 포트폴리오 공개용.

환경변수 PUBLIC_DEMO=1 이면
- 로그인 화면 없이 '시연 방문자' 계정(관리자 아님)으로 자동 입장
- 쓰기 요청(POST·PUT·PATCH·DELETE)은 모두 막음 → 저장 · 메일/답장 발송 · AI 실행 · 키 변경 · 업로드가 일어나지 않음
  (예외: 외부 크론의 하루 1회 작업 core.jobs_daily — CRON_TOKEN으로 따로 보호)
- 관리자 전용 화면·API(계정 관리 등)는 원래 규칙대로 403
끄려면 PUBLIC_DEMO를 지우거나 0으로 두고 다시 배포 → 원래 로그인 방식으로 돌아감
"""
import secrets

from flask import jsonify, redirect, request
from flask_login import current_user, login_user

from .extensions import db
from .models import User
from .security import UNSAFE, is_api

DEMO_EMAIL = "demo-viewer@reboot.invalid"
DEMO_NAME = "시연 방문자"
WRITE_ALLOWED = {"core.jobs_daily"}
# 화면 상태 자동 저장(REBOOT.store): 저장하지 않고 성공만 돌려줌 → '저장하지 못했습니다' 알림 · 재시도가 생기지 않음
#   (방문자가 바꾼 화면 상태는 그 브라우저 화면에만 남고 다른 방문자에게는 보이지 않음)
FAKE_SAVE = {"core.store_put", "core.store_delete"}
# 파트 화면 파일(공개 저장소의 JS·CSS)과 상태 확인은 DB를 거치지 않음 → 첫 방문 때 파일 27개가 동시에 DB를 깨우다 실패하지 않게
NO_DB = {"core.part_file", "core.healthz"}
LOCKED_MSG = "시연(보기 전용) 모드라 저장 · 발송 · AI 실행은 잠겨 있어요."


def demo_user():
    """시연 방문자 계정 (없으면 만듦). 비밀번호는 아무도 모르는 임의 값이라 로그인 화면으로는 들어올 수 없음."""
    user = User.query.filter_by(email=DEMO_EMAIL).first()
    if user is None:
        user = User(email=DEMO_EMAIL, name=DEMO_NAME, title="포트폴리오 시연", is_admin=False)
        user.set_password(secrets.token_urlsafe(32))
        db.session.add(user)
        db.session.commit()
    return user


def register_demo(app):
    if not app.config.get("PUBLIC_DEMO"):
        return

    @app.before_request
    def _demo_guard():
        endpoint = request.endpoint or ""
        if endpoint == "static" or endpoint.endswith(".static") or endpoint in NO_DB:
            return None
        if request.method in UNSAFE and endpoint in FAKE_SAVE:
            return jsonify(ok=True, demo=True)
        if request.method in UNSAFE and endpoint not in WRITE_ALLOWED:
            if is_api():
                return jsonify(error=LOCKED_MSG, demo=True), 403
            return redirect("/")
        if endpoint == "core.jobs_daily":
            return None
        if not current_user.is_authenticated:
            login_user(demo_user(), remember=False)
        if endpoint == "auth.login":
            return redirect("/")
        return None
