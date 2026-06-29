import json
import os
import smtplib
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Mapping, Optional


@dataclass(frozen=True)
class NotificationResult:
    channel: str
    sent: bool
    message: str


DEFAULT_PUSHPLUS_MAX_CHARS = 19000
DEFAULT_PUSHPLUS_MAX_BYTES = 18000
TRUNCATION_NOTICE = "\n\n[truncated: report was shortened to fit PushPlus size limit]"


def _post_json(url: str, payload, timeout: float) -> str:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _env_int(env: Mapping[str, str], key: str, default: int) -> int:
    try:
        return int(env.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def _clip_utf8_bytes(content: str, max_bytes: int) -> str:
    encoded = content.encode("utf-8")
    if len(encoded) <= max_bytes:
        return content
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def _truncate_content(content: str, max_chars: int, max_bytes: int) -> str:
    if (
        (max_chars <= 0 or len(content) <= max_chars)
        and (max_bytes <= 0 or len(content.encode("utf-8")) <= max_bytes)
    ):
        return content

    notice = TRUNCATION_NOTICE
    if max_bytes > 0:
        notice = _clip_utf8_bytes(notice, max_bytes)
    if max_chars > 0:
        notice = notice[:max_chars]

    max_head_chars = max_chars - len(notice) if max_chars > 0 else len(content)
    max_head_bytes = (
        max_bytes - len(notice.encode("utf-8"))
        if max_bytes > 0
        else len(content.encode("utf-8"))
    )
    if max_head_chars <= 0 or max_head_bytes <= 0:
        return notice

    head = content[:max_head_chars]
    head = _clip_utf8_bytes(head, max_head_bytes).rstrip()
    return head + notice


def _pushplus_result(body: str) -> NotificationResult:
    message = body[:500]
    try:
        parsed = json.loads(body)
    except (TypeError, ValueError):
        return NotificationResult("pushplus", False, message)
    code = parsed.get("code") if isinstance(parsed, dict) else None
    return NotificationResult("pushplus", str(code) == "200", message)


def _send_pushplus(title: str, content: str, env: Mapping[str, str]) -> NotificationResult:
    token = env.get("XUEQIU_PUSHPLUS_TOKEN")
    if not token:
        return NotificationResult("pushplus", False, "missing XUEQIU_PUSHPLUS_TOKEN")
    content = _truncate_content(
        content,
        _env_int(env, "XUEQIU_PUSHPLUS_MAX_CHARS", DEFAULT_PUSHPLUS_MAX_CHARS),
        _env_int(env, "XUEQIU_PUSHPLUS_MAX_BYTES", DEFAULT_PUSHPLUS_MAX_BYTES),
    )
    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": "markdown",
    }
    for env_key, payload_key in (
        ("XUEQIU_PUSHPLUS_TOPIC", "topic"),
        ("XUEQIU_PUSHPLUS_CHANNEL", "channel"),
        ("XUEQIU_PUSHPLUS_WEBHOOK", "webhook"),
    ):
        value = env.get(env_key)
        if value:
            payload[payload_key] = value
    url = env.get("XUEQIU_PUSHPLUS_URL", "https://www.pushplus.plus/send")
    body = _post_json(url, payload, float(env.get("XUEQIU_NOTIFY_TIMEOUT", "15")))
    return _pushplus_result(body)


def _send_webhook(title: str, content: str, env: Mapping[str, str]) -> NotificationResult:
    url = env.get("XUEQIU_WEBHOOK_URL")
    if not url:
        return NotificationResult("webhook", False, "missing XUEQIU_WEBHOOK_URL")
    body = _post_json(
        url,
        {"title": title, "content": content},
        float(env.get("XUEQIU_NOTIFY_TIMEOUT", "15")),
    )
    return NotificationResult("webhook", True, body[:500])


def _send_email(title: str, content: str, env: Mapping[str, str]) -> NotificationResult:
    host = env.get("XUEQIU_EMAIL_HOST")
    to_addr = env.get("XUEQIU_EMAIL_TO")
    if not host or not to_addr:
        return NotificationResult("email", False, "missing XUEQIU_EMAIL_HOST or XUEQIU_EMAIL_TO")

    security = env.get("XUEQIU_EMAIL_SECURITY", "starttls").lower()
    port = int(env.get("XUEQIU_EMAIL_PORT", "465" if security == "ssl" else "587"))
    user = env.get("XUEQIU_EMAIL_USER")
    password = env.get("XUEQIU_EMAIL_PASSWORD")
    from_addr = env.get("XUEQIU_EMAIL_FROM") or user or to_addr

    message = EmailMessage()
    message["Subject"] = title
    message["From"] = from_addr
    message["To"] = to_addr
    message.set_content(content)

    if security == "ssl":
        smtp = smtplib.SMTP_SSL(host, port, timeout=15)
    else:
        smtp = smtplib.SMTP(host, port, timeout=15)
    try:
        if security == "starttls":
            smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(message)
    finally:
        smtp.quit()
    return NotificationResult("email", True, "sent")


def _get_persistent_environment() -> Mapping[str, str]:
    if os.name != "nt":
        return {}
    try:
        import winreg
    except ImportError:
        return {}

    values = {}
    registry_locations = (
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        (winreg.HKEY_CURRENT_USER, "Environment"),
    )
    for root, path in registry_locations:
        try:
            with winreg.OpenKey(root, path) as key:
                index = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    values[name] = str(value)
                    index += 1
        except OSError:
            continue
    return values


def _current_environment() -> Mapping[str, str]:
    if os.name != "nt":
        return os.environ
    values = dict(_get_persistent_environment())
    values.update(os.environ)
    return values


def notify(
    title: str,
    content: str,
    env: Optional[Mapping[str, str]] = None,
) -> NotificationResult:
    current_env = env if env is not None else _current_environment()
    channel = current_env.get("XUEQIU_NOTIFY", "").strip().lower()
    if not channel or channel in ("none", "off", "0", "false"):
        return NotificationResult("none", False, "notification disabled")
    if channel == "pushplus":
        return _send_pushplus(title, content, current_env)
    if channel == "email":
        return _send_email(title, content, current_env)
    if channel == "webhook":
        return _send_webhook(title, content, current_env)
    return NotificationResult(channel, False, "unsupported XUEQIU_NOTIFY value")
