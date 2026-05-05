from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class GhostConfigError(RuntimeError):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _make_admin_token(admin_api_key: str) -> str:
    try:
        key_id, secret_hex = admin_api_key.split(":", 1)
    except ValueError as exc:  # pragma: no cover
        raise GhostConfigError("Admin API Key の形式が不正です（`id:secret` 形式）。") from exc

    try:
        secret = bytes.fromhex(secret_hex)
    except ValueError as exc:  # pragma: no cover
        raise GhostConfigError("Admin API Key の secret が不正です（hex形式）。") from exc

    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iat": now, "exp": now + 300, "aud": "/admin/"}
    signing_input = f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}.{_b64url(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(secret, signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}"


def _normalize_admin_api_base(api_url: str) -> str:
    base = api_url.strip().rstrip("/")
    if "/ghost/api/admin" in base:
        return base
    if base.endswith("/ghost"):
        return f"{base}/api/admin"
    return f"{base}/ghost/api/admin"


def _request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    request_headers = dict(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as exc:  # pragma: no cover - runtime safeguard
        raise RuntimeError(f"Ghost API 通信エラー: {exc}") from exc

    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:  # pragma: no cover
        return {"_raw": raw}


@dataclass(frozen=True)
class GhostClient:
    admin_api_url: str
    admin_api_key: str
    accept_version: str = "v5.0"

    @classmethod
    def from_streamlit_secrets(cls, secrets: Any) -> "GhostClient":
        admin_api_url = secrets.get("ghost_admin_api_url", "")
        admin_api_key = secrets.get("ghost_admin_api_key", "")
        accept_version = secrets.get("ghost_admin_api_version", "v5.0")

        if not admin_api_url:
            raise GhostConfigError("`ghost_admin_api_url` が Secrets に設定されていません。")
        if not admin_api_key:
            raise GhostConfigError("`ghost_admin_api_key` が Secrets に設定されていません。")

        return cls(
            admin_api_url=admin_api_url,
            admin_api_key=admin_api_key,
            accept_version=accept_version,
        )

    def _headers(self) -> dict[str, str]:
        token = _make_admin_token(self.admin_api_key)
        return {
            "Authorization": f"Ghost {token}",
            "Accept-Version": self.accept_version,
        }

    def _base(self) -> str:
        return _normalize_admin_api_base(self.admin_api_url)

    def _members_url(self) -> str:
        return f"{self._base()}/members/"

    def find_member_by_email(self, email: str) -> dict[str, Any] | None:
        quoted = f"email:'{email}'"
        query = urllib.parse.urlencode({"filter": quoted, "limit": "1"})
        url = f"{self._members_url()}?{query}"
        data = _request_json("GET", url, headers=self._headers())
        members = data.get("members") or []
        return members[0] if members else None

    def create_member(self, *, email: str, name: str, labels: list[str] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"members": [{"email": email, "name": name}]}
        if labels:
            payload["members"][0]["labels"] = labels
        return _request_json("POST", self._members_url(), headers=self._headers(), body=payload)

    def update_member(self, *, member_id: str, email: str | None = None, name: str | None = None) -> dict[str, Any]:
        member: dict[str, Any] = {"id": member_id}
        if email is not None:
            member["email"] = email
        if name is not None:
            member["name"] = name
        payload = {"members": [member]}
        url = f"{self._members_url()}{member_id}/"
        return _request_json("PUT", url, headers=self._headers(), body=payload)

