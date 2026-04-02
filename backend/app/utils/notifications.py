from typing import Any


async def send_notification(
    phone: str, message: str, metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "status": "queued",
        "phone": phone,
        "message": message,
        "metadata": metadata or {},
    }
