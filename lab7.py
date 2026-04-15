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

class Observer(Generic[T]):
    def __init__(self,
                 on_next: Callable[[T], None] = lambda _: None,
                 on_error: Callable[[Exception], None] = lambda e: None,
                 on_complete: Callable[[], None] = lambda: None):
        self.on_next = on_next
        self.on_error = on_error
        self.on_complete = on_complete
        self._closed = False

    def next(self, value: T) -> None:
        if not self._closed:
            self.on_next(value)

    def error(self, exc: Exception) -> None:
        if not self._closed:
            self._closed = True
            self.on_error(exc)

    def complete(self) -> None:
        if not self._closed:
            self._closed = True
            self.on_complete()

class Observable(Generic[T]):
    def __init__(self, subscribe_fn: Callable[[Observer[T]], Optional[Callable]]):
        self._subscribe_fn = subscribe_fn

    def subscribe(self,
                  on_next: Callable[[T], None] = lambda _: None,
                  on_error: Callable[[Exception], None] = lambda e: None,
                  on_complete: Callable[[], None] = lambda: None) -> Subscription:
        observer = Observer(on_next, on_error, on_complete)
        teardown = self._subscribe_fn(observer)

        def remove():
            observer._closed = True
            if callable(teardown):
                teardown()

        return Subscription(remove)

    def map(self, fn: Callable[[T], U]) -> "Observable[U]":
        source = self

        def subscribe_fn(observer: Observer[U]):
            return source.subscribe(
                on_next=lambda v: observer.next(fn(v)),
                on_error=observer.error,
                on_complete=observer.complete,
            )

        return Observable(subscribe_fn)

    def filter(self, predicate: Callable[[T], bool]) -> "Observable[T]":
        source = self

        def subscribe_fn(observer: Observer[T]):
            return source.subscribe(
                on_next=lambda v: observer.next(v) if predicate(v) else None,
                on_error=observer.error,
                on_complete=observer.complete,
            )

        return Observable(subscribe_fn)

    def pipe(self, *operators: Callable[["Observable"], "Observable"]) -> "Observable":
        result = self
        for op in operators:
            result = op(result)
        return result

    @staticmethod
    def from_iterable(iterable) -> "Observable":
        def subscribe_fn(observer: Observer):
            try:
                for item in iterable:
                    if observer._closed:
                        break
                    observer.next(item)
                observer.complete()
            except Exception as exc:
                observer.error(exc)

        return Observable(subscribe_fn)

    @staticmethod
    def merge(*observables: "Observable[T]") -> "Observable[T]":
        def subscribe_fn(observer: Observer[T]):
            subs = []
            completed = [0]
            total = len(observables)

            def on_complete():
                completed[0] += 1
                if completed[0] == total:
                    observer.complete()

            for obs in observables:
                subs.append(obs.subscribe(observer.next, observer.error, on_complete))

            return lambda: [s.unsubscribe() for s in subs]

        return Observable(subscribe_fn)