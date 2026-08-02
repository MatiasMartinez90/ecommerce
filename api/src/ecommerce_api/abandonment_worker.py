"""Durable cart-abandonment marker for the scheduled dev worker.

This job only transitions eligible carts and leaves the resulting rows in
PostgreSQL for a delivery worker to evaluate against consent, quiet hours and
channel availability. It is deliberately separate from HTTP request traffic.
"""

import asyncio
import logging

from .config import get_settings
from .database import create_pool
from .repository import mark_abandoned_carts

logger = logging.getLogger("ecommerce.abandonment")


async def run() -> None:
    settings = get_settings()
    pool = await create_pool(settings)
    try:
        rows = await mark_abandoned_carts(
            pool,
            idle_minutes=settings.abandonment_idle_minutes,
            limit=settings.abandonment_batch_size,
        )
        logger.info("abandoned carts marked=%d", len(rows))
    finally:
        await pool.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
