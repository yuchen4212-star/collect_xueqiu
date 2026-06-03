import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ResponseKind(str, Enum):
    SUCCESS = "success"
    UNAUTHORIZED = "unauthorized"
    HTTP_FAILURE = "http_failure"
    EMPTY = "empty"
    MALFORMED_JSON = "malformed_json"


@dataclass(frozen=True)
class ClassifiedResponse:
    kind: ResponseKind
    message: str
    data: Optional[Any] = None


def _looks_like_login_error(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    error_code = str(data.get("error_code", ""))
    description = str(data.get("error_description", ""))
    login_words = ("login", "logged in", "登录", "重新登录")
    return error_code in {"400016", "401", "403"} or any(
        word in description.lower() for word in login_words
    )


def classify_response(status_code: int, body: str) -> ClassifiedResponse:
    if status_code in (401, 403):
        return ClassifiedResponse(
            ResponseKind.UNAUTHORIZED,
            "Xueqiu login is missing or expired; run xueqiu-collector auth again.",
        )
    if status_code < 200 or status_code >= 300:
        return ClassifiedResponse(
            ResponseKind.HTTP_FAILURE,
            "HTTP failure from Xueqiu: status {}".format(status_code),
        )
    if not body:
        return ClassifiedResponse(ResponseKind.EMPTY, "Empty response from Xueqiu.")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return ClassifiedResponse(
            ResponseKind.MALFORMED_JSON,
            "Received malformed JSON from Xueqiu.",
        )
    if _looks_like_login_error(data):
        return ClassifiedResponse(
            ResponseKind.UNAUTHORIZED,
            "Xueqiu login is missing or expired; run xueqiu-collector auth again.",
            data,
        )
    return ClassifiedResponse(ResponseKind.SUCCESS, "OK", data)
