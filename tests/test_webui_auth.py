from __future__ import annotations

from astrbot_plugin_update_manager.core.adapters.storage import AtomicJsonStore
from astrbot_plugin_update_manager.core.webui_auth import WebUIAuth, WebUIAuthError


def auth(tmp_path):
    return WebUIAuth(AtomicJsonStore(tmp_path))


def test_first_admin_is_owner_and_password_is_not_persisted(tmp_path):
    service = auth(tmp_path)
    created = service.create_admin("owner", "correct horse", "admin")
    assert created["role"] == "owner"
    raw = (tmp_path / "webui-admins.json").read_text(encoding="utf-8")
    assert "correct horse" not in raw
    assert "digest" in raw and "salt" in raw


def test_multiple_admins_and_session_revoke(tmp_path):
    service = auth(tmp_path)
    owner = service.create_admin("owner", "owner-pass", "owner")
    admin = service.create_admin("operator", "operator-pass", "admin")
    assert {item["username"] for item in service.list_admins()} == {"owner", "operator"}
    session = service.authenticate("operator", "operator-pass")
    assert service.session(session.token) is not None
    updated = service.change_admin(admin["id"], password="new-pass")
    assert updated["enabled"] is True
    assert service.session(session.token) is None
    assert service.authenticate("operator", "new-pass").username == "operator"
    assert owner["role"] == "owner"


def test_last_owner_cannot_be_disabled(tmp_path):
    service = auth(tmp_path)
    owner = service.create_admin("owner", "owner-pass", "owner")
    try:
        service.change_admin(owner["id"], enabled=False)
    except WebUIAuthError as error:
        assert str(error) == "LAST_OWNER_PROTECTED"
    else:
        raise AssertionError("最后一个 owner 不应被禁用")
    try:
        service.change_admin(owner["id"], role="viewer")
    except WebUIAuthError as error:
        assert str(error) == "LAST_OWNER_PROTECTED"
    else:
        raise AssertionError("最后一个 owner 不应被降级")


def test_login_failures_are_rate_limited_without_secret_details(tmp_path):
    service = auth(tmp_path)
    service.create_admin("owner", "owner-pass", "owner")
    try:
        service.authenticate("owner", "wrong-pass")
    except WebUIAuthError as error:
        assert str(error) == "INVALID_CREDENTIALS"
    else:
        raise AssertionError("错误密码应失败")
    try:
        service.authenticate("owner", "wrong-pass")
    except WebUIAuthError as error:
        assert str(error) in {"LOGIN_RATE_LIMITED", "INVALID_CREDENTIALS"}
    else:
        raise AssertionError("连续错误登录应失败")
