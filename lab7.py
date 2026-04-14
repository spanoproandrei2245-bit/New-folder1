import asyncio
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Optional, TypeVar
from uuid import uuid4

T = TypeVar("T")
U = TypeVar("U")

class Subscription:
    def __init__(self, remove_fn: Callable[[], None]):
        self._remove = remove_fn
        self.active = True

    def unsubscribe(self) -> None:
        if self.active:
            self._remove()
            self.active = False

    def __enter__(self): return self
    def __exit__(self, *_): self.unsubscribe()

class EventEmitter:
    def __init__(self):
        self._handlers: dict[str, dict[str, Callable]] = defaultdict(dict)

    def on(self, event: str, handler: Callable) -> Subscription:
        sub_id = str(uuid4())
        self._handlers[event][sub_id] = handler

        def remove():
            self._handlers[event].pop(sub_id, None)

        return Subscription(remove)

    def once(self, event: str, handler: Callable) -> Subscription:
        sub: Optional[Subscription] = None

        def wrapper(payload):
            handler(payload)
            if sub:
                sub.unsubscribe()

        sub = self.on(event, wrapper)
        return sub

    def emit(self, event: str, payload: Any = None) -> int:
        handlers = list(self._handlers[event].values())
        for h in handlers:
            h(payload)
        return len(handlers)

    def off(self, event: str) -> None:
        self._handlers[event].clear()

    def listener_count(self, event: str) -> int:
        return len(self._handlers[event])