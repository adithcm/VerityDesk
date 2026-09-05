import asyncio
import logging
from contextlib import suppress

from app.db.session import SessionLocal
from app.services.ingestion_runner import run_due_daily_workflow


logger = logging.getLogger(__name__)
SCHEDULER_CHECK_SECONDS = 60


async def daily_scheduler_loop() -> None:
    while True:
        try:
            with SessionLocal() as session:
                run_due_daily_workflow(session)
        except Exception:
            logger.exception("Daily scheduler check failed")

        await asyncio.sleep(SCHEDULER_CHECK_SECONDS)


def start_daily_scheduler() -> asyncio.Task:
    return asyncio.create_task(daily_scheduler_loop())


async def stop_daily_scheduler(task: asyncio.Task | None) -> None:
    if task is None:
        return

    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
