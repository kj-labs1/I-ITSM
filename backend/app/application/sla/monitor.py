"""
Scheduled SLA Background Monitor — Member 4.

Runs an asynchronous periodic task (default: every 60 seconds) during the
FastAPI application lifespan to evaluate active incidents against their SLA
deadlines and trigger warning / breach events automatically.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from app.application.sla.sla_service import SLAService

logger = logging.getLogger(__name__)

SLAServiceFactory = Callable[[], AbstractAsyncContextManager[SLAService]]


class SLAMonitorTask:
    """Managed background task that periodically evaluates active incident SLAs."""

    def __init__(
        self,
        sla_service_factory: SLAServiceFactory,
        interval_seconds: float = 60.0,
    ) -> None:
        self._sla_service_factory = sla_service_factory
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def run_once(self) -> int:
        """Execute a single SLA evaluation sweep and return number of records checked."""
        async with self._sla_service_factory() as sla_service:
            results = await sla_service.evaluate_active_slas()
            return len(results)

    async def _loop(self) -> None:
        logger.info(
            "SLAMonitorTask started (interval=%.1fs).",
            self._interval_seconds,
        )
        while not self._stop_event.is_set():
            try:
                checked = await self.run_once()
                logger.debug("SLAMonitorTask evaluated %d active SLA record(s).", checked)
            except Exception as exc:
                logger.exception("SLAMonitorTask sweep failed: %s", exc)

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._interval_seconds,
                )
            except TimeoutError:
                continue

        logger.info("SLAMonitorTask stopped cleanly.")

    def start(self) -> None:
        """Start the background SLA monitoring loop."""
        if self.is_running:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop(), name="sla-monitor-task")

    async def stop(self) -> None:
        """Signal the background SLA monitor to stop and await clean shutdown."""
        if self._task is None:
            return
        self._stop_event.set()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None
