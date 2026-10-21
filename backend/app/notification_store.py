"""Per-account in-memory notifications, triggered by queue mutations (A3 Module 5)."""

import threading
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal
from uuid import uuid4

NotificationKind = Literal["joined", "moved", "delayed", "almost-ready", "served", "left"]
_TITLES: dict[NotificationKind, str] = {
    "joined": "Queue joined", "moved": "Position updated", "delayed": "Queue delayed",
    "almost-ready": "Almost ready", "served": "Visit completed", "left": "Left queue",
}


@dataclass(frozen=True)
class Notification:
    id: str
    user_id: str
    entry_id: str
    ticket: str
    service_id: str
    service_name: str
    kind: NotificationKind
    category: Literal["queue", "status"]
    title: str
    message: str
    at: datetime
    read: bool = False


class NotificationStore:
    def __init__(self) -> None:
        self._items: dict[str, Notification] = {}
        self._lock = threading.Lock()

    def add(self, *, user_id: str, entry_id: str, ticket: str, service_id: str,
            service_name: str, kind: NotificationKind, message: str, at: datetime) -> Notification:
        item = Notification(
            id=str(uuid4()), user_id=user_id, entry_id=entry_id, ticket=ticket,
            service_id=service_id, service_name=service_name, kind=kind,
            category="queue" if kind in ("moved", "delayed") else "status",
            title=_TITLES[kind], message=f"{service_name}: {message}", at=at,
        )
        with self._lock:
            self._items[item.id] = item
        return item

    def for_user(self, user_id: str) -> list[Notification]:
        with self._lock:
            items = [item for item in reversed(list(self._items.values())) if item.user_id == user_id]
        return sorted(items, key=lambda item: item.at, reverse=True)

    def mark_read(self, user_id: str, notification_id: str, read: bool) -> Notification:
        with self._lock:
            item = self._items.get(notification_id)
            # The same response for nonexistent IDs and another student's notification.
            if item is None or item.user_id != user_id:
                raise KeyError(notification_id)
            updated = replace(item, read=read)
            self._items[item.id] = updated
            return updated

    def mark_all_read(self, user_id: str) -> None:
        with self._lock:
            for notification_id, item in self._items.items():
                if item.user_id == user_id and not item.read:
                    self._items[notification_id] = replace(item, read=True)

    def reset(self) -> None:
        with self._lock:
            self._items.clear()
