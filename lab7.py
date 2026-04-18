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

class Subject(Generic[T]):
    def __init__(self):
        self._observers: dict[str, Observer[T]] = {}
        self._closed = False

    def next(self, value: T) -> None:
        if not self._closed:
            for obs in list(self._observers.values()):
                obs.next(value)

    def error(self, exc: Exception) -> None:
        if not self._closed:
            self._closed = True
            for obs in list(self._observers.values()):
                obs.error(exc)

    def complete(self) -> None:
        if not self._closed:
            self._closed = True
            for obs in list(self._observers.values()):
                obs.complete()
            self._observers.clear()

    def subscribe(self,
                  on_next: Callable[[T], None] = lambda _: None,
                  on_error: Callable[[Exception], None] = lambda e: None,
                  on_complete: Callable[[], None] = lambda: None) -> Subscription:
        sub_id = str(uuid4())
        observer = Observer(on_next, on_error, on_complete)
        self._observers[sub_id] = observer

        def remove():
            self._observers.pop(sub_id, None)

        return Subscription(remove)

    def as_observable(self) -> Observable[T]:
        subject = self

        def subscribe_fn(observer: Observer[T]):
            sub_id = str(uuid4())
            subject._observers[sub_id] = observer
            return lambda: subject._observers.pop(sub_id, None)

        return Observable(subscribe_fn)

@dataclass
class SensorReading:
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: float = field(default_factory=time.time)

    def __str__(self):
        return f"[{self.sensor_type.upper():>11}] {self.sensor_id}: {self.value:>6.1f} {self.unit}"

def demo_event_emitter():
    print("Демо 1: Розумна халупа на базі EventEmitter")

    hub = EventEmitter()
    log: list[str] = []

    def security_handler(r: SensorReading):
        msg = f"Охорона <- {r}"
        print(msg)
        log.append(msg)

    sub_security = hub.on("рух", security_handler)

    def lighting_handler(r: SensorReading):
        msg = f"Світло <- {r}"
        print(msg)
        log.append(msg)

    sub_lighting = hub.on("рух", lighting_handler)

    def hvac_handler(r: SensorReading):
        action = "ОХОЛОДЖЕННЯ" if r.value > 25 else "ОБІГРІВ"
        msg = f"{action} клімату <- {r}"
        print(msg)
        log.append(msg)

    hub.on("температура", hvac_handler)

    def chime_handler(r: SensorReading):
        msg = f"Дзвінок <- двері відчинено (спрацює раз)"
        print(msg)
        log.append(msg)

    hub.once("двері", chime_handler)

    readings = [
        SensorReading("PIR-01", "рух", 1.0, "виявлено"),
        SensorReading("TMP-01", "температура", 27.3, "C"),
        SensorReading("DOR-01", "двері", 1.0, "відкрито"),
        SensorReading("DOR-01", "двері", 1.0, "відкрито"),
        SensorReading("PIR-02", "рух", 1.0, "виявлено"),
        SensorReading("TMP-02", "температура", 19.5, "C"),
    ]

    for r in readings:
        print(f"\nвідправка '{r.sensor_type}' -> слухачів: {hub.listener_count(r.sensor_type)}")
        hub.emit(r.sensor_type, r)

    print("\nСвітло відписали від подій руху")
    sub_lighting.unsubscribe()

    r = SensorReading("PIR-03", "рух", 1.0, "виявлено")
    print(f"\nвідправка 'рух' -> слухачів: {hub.listener_count('рух')}")
    hub.emit("рух", r)

    print(f"\nДемо EventEmitter завершено (реакцій: {len(log)})\n")

def demo_observable():
    print("-" * 40)
    print("Демо 2: Обробка потоків через Observable")
    print("-" * 40)

    readings = [
        SensorReading("TMP-01", "температура", v, "C")
        for v in [18.0, 22.5, 26.1, 30.4, 24.8, 19.2, 35.0, 28.3]
    ]

    source = Observable.from_iterable(readings)

    alerts = (
        source
        .filter(lambda r: r.value > 25.0)
        .map(lambda r: f"ТРИВОГА: темп={r.value}C на {r.sensor_id}")
    )

    print("\nПотік А - попередження (>25C):")
    with alerts.subscribe(on_next=lambda msg: print(f"  {msg}")):
        pass

    normalized = source.map(lambda r: round((r.value - 18) / (35 - 18), 3))

    collected: list[float] = []
    print("\nПотік Б - нормалізація [0..1]:")
    with normalized.subscribe(on_next=collected.append):
        pass
    print(f"  {collected}")

    smoke_readings = Observable.from_iterable([
        SensorReading("SMK-01", "дим", 0.02, "ppm"),
        SensorReading("SMK-02", "дим", 0.45, "ppm"),
    ])
    motion_readings = Observable.from_iterable([
        SensorReading("PIR-01", "рух", 1.0, "виявлено"),
        SensorReading("PIR-02", "рух", 1.0, "виявлено"),
    ])

    merged = Observable.merge(smoke_readings, motion_readings)
    print("\nПотік В - об'єднані дані диму і руху:")
    merged.subscribe(on_next=lambda r: print(f"  {r}"),
                     on_complete=lambda: print("  [потік закрито]"))
    print()

def demo_subject():
    print("-" * 40)
    print("Демо 3: Трансляція в реальному часі (Subject)")
    print("-" * 40)

    sensor_bus: Subject[SensorReading] = Subject()

    received: dict[str, list] = {"dashboard": [], "logger": [], "alert_system": []}

    sub_dash = sensor_bus.subscribe(
        on_next=lambda r: (
            received["dashboard"].append(r),
            print(f"Панель керування <- {r}")
        )[0]
    )

    sub_log = sensor_bus.subscribe(
        on_next=lambda r: (
            received["logger"].append(r),
            print(f"Логер <- {r.sensor_type}={r.value}")
        )[0]
    )

    sub_alert = sensor_bus.subscribe(
        on_next=lambda r: (
            None if r.sensor_type != "дим" else (
                received["alert_system"].append(r),
                print(f"Система тривоги <- ВИЯВЛЕНО ДИМ: {r.value} ppm!")
            )
        )
    )

    live_data = [
        SensorReading("TMP-01", "температура", 23.1, "C"),
        SensorReading("PIR-01", "рух", 1.0, "виявлено"),
        SensorReading("SMK-01", "дим", 0.38, "ppm"),
        SensorReading("TMP-02", "температура", 19.8, "C"),
    ]

    print()
    for r in live_data:
        print(f"надсилаємо: {r}")
        sensor_bus.next(r)
        print()

    print("Панель відключилась\n")
    sub_dash.unsubscribe()

    late_data = [
        SensorReading("PIR-02", "рух", 1.0, "виявлено"),
        SensorReading("SMK-02", "дим", 0.55, "ppm"),
    ]
    for r in late_data:
        print(f"надсилаємо: {r}")
        sensor_bus.next(r)
        print()

    print("Статистика по підписниках:")
    for name, items in received.items():
        print(f"  {name:<15}: {len(items)} записів")

    sensor_bus.complete()
    print("[генерацію завершено - всі підписники в курсі]\n")