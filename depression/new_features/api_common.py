"""Shared helpers for unified V1 API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from flask import jsonify, request


def _current_request_id() -> str:
    request_id = request.headers.get("X-Request-Id", "").strip()
    if request_id:
        return request_id
    return f"req-{uuid4()}"


def _current_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _build_payload(*, code: int, message: str, data: Any) -> Dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": data,
        "request_id": _current_request_id(),
        "timestamp": _current_timestamp(),
    }


def api_success(data: Optional[Any] = None, *, message: str = "ok", status_code: int = 200):
    payload = _build_payload(code=0, message=message, data={} if data is None else data)
    return jsonify(payload), status_code


def api_notice(
    code: int,
    message: str,
    *,
    data: Optional[Any] = None,
    status_code: int = 200,
):
    """Return a successful response that still carries a business advisory.

    This is intended for cases such as high-risk stratification where the request
    succeeds, but the payload should still remind the client to prioritize
    external help while optionally allowing the user to continue.
    """

    payload = _build_payload(code=code, message=message, data={} if data is None else data)
    return jsonify(payload), status_code


def api_error(
    code: int,
    message: str,
    *,
    status_code: int = 400,
    data: Optional[Any] = None,
):
    payload = _build_payload(code=code, message=message, data=data)
    return jsonify(payload), status_code


def api_health(
    *,
    status: str = "up",
    mode: str = "prod",
    model_loaded: bool = True,
    version: str = "v1",
    extra: Optional[Dict[str, Any]] = None,
):
    data = {
        "status": status,
        "mode": mode,
        "model_loaded": model_loaded,
        "version": version,
    }
    if extra:
        data.update(extra)
    return api_success(data)


def api_meta(
    *,
    module: str,
    capability: str,
    module_zh: str,
    capability_zh: str,
    version: str = "v1",
    owner: str = "team-platform",
    input_schema_version: str = "1.0.0",
    output_schema_version: str = "1.0.0",
    supports_mock: bool = True,
    extra: Optional[Dict[str, Any]] = None,
):
    data = {
        "module": module,
        "capability": capability,
        "module_zh": module_zh,
        "capability_zh": capability_zh,
        "version": version,
        "owner": owner,
        "input_schema_version": input_schema_version,
        "output_schema_version": output_schema_version,
        "supports_mock": supports_mock,
    }
    if extra:
        data.update(extra)
    return api_success(data)
