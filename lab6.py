import asyncio
import csv
import io
import json
import random
import string
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

@dataclass
class Transaction:
    id: str
    user_id: str
    amount: float
    category: str
    timestamp: float

@dataclass
class StreamStats:
    total_records: int = 0
    total_amount: float = 0.0
    category_totals: dict = field(default_factory=lambda: defaultdict(float))
    max_amount: float = float("-inf")
    min_amount: float = float("inf")
    errors: int = 0

CATEGORIES = ["їжа", "транспорт", "здоров'я", "розваги", "комуналка"]

async def generate_csv_stream(total_rows: int = 1_000_000, chunk_size: int = 500) -> AsyncIterator[str]:
    header = "id,user_id,amount,category,timestamp\n"
    yield header

    rows_yielded = 0
    while rows_yielded < total_rows:
        batch = min(chunk_size, total_rows - rows_yielded)
        buffer = io.StringIO()
        for _ in range(batch):
            tx_id = "".join(random.choices(string.ascii_lowercase, k=8))
            user_id = f"юзер_{random.randint(1, 10_000)}"
            amount = round(random.uniform(0.5, 9_999.99), 2)
            cat = random.choice(CATEGORIES)
            ts = time.time() - random.uniform(0, 86_400 * 30)
            buffer.write(f"{tx_id},{user_id},{amount},{cat},{ts:.3f}\n")
        
        yield buffer.getvalue()
        rows_yielded += batch
        await asyncio.sleep(0)

async def parse_transactions(source: AsyncIterator[str], filter_min: Optional[float] = None, filter_max: Optional[float] = None) -> AsyncIterator[Transaction]:
    header_skipped = False
    leftover = ""

    async for chunk in source:
        lines = (leftover + chunk).split("\n")
        leftover = lines[-1]

        for line in lines[:-1]:
            if not header_skipped:
                header_skipped = True
                continue
            if not line.strip():
                continue
            try:
                tx_id, user_id, amount_str, category, ts_str = line.split(",")
                amount = float(amount_str)
                if filter_min is not None and amount < filter_min:
                    continue
                if filter_max is not None and amount > filter_max:
                    continue
                
                yield Transaction(
                    id=tx_id,
                    user_id=user_id,
                    amount=amount,
                    category=category,
                    timestamp=float(ts_str),
                )
            except (ValueError, AttributeError):
                pass

async def batch_processor(source: AsyncIterator[Transaction], batch_size: int = 1_000) -> AsyncIterator[list[Transaction]]:
    batch: list[Transaction] = []
    async for tx in source:
        batch.append(tx)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch

async def aggregate_stats(source: AsyncIterator[Transaction]) -> StreamStats:
    stats = StreamStats()
    async for tx in source:
        stats.total_records += 1
        stats.total_amount += tx.amount
        stats.category_totals[tx.category] += tx.amount
        if tx.amount > stats.max_amount:
            stats.max_amount = tx.amount
        if tx.amount < stats.min_amount:
            stats.min_amount = tx.amount
    return stats

async def detect_large_transactions(source: AsyncIterator[Transaction], threshold: float = 5_000.0) -> AsyncIterator[Transaction]:
    async for tx in source:
        if tx.amount >= threshold:
            yield tx