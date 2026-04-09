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