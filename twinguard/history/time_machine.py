"""Historical telemetry replay for TwinGuard Module 4."""

from datetime import datetime
from typing import Any

from state_store import StateStore


class TimeMachine:
    def __init__(self, store: StateStore):
        self.store = store

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime:
        return datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

    def get_run(self, run_id: str) -> list[dict[str, Any]]:
        return self.store.read_run(run_id)

    def get_range(
        self,
        run_id: str,
        start_time: str,
        end_time: str,
    ) -> list[dict[str, Any]]:
        start = self._parse_timestamp(start_time)
        end = self._parse_timestamp(end_time)

        if start > end:
            raise ValueError("start_time must not exceed end_time")

        return [
            record
            for record in self.get_run(run_id)
            if start <= self._parse_timestamp(record["timestamp"]) <= end
        ]

    def replay(
        self,
        run_id: str,
        start_time: str | None = None,
        end_time: str | None = None,
    ):
        if start_time is None and end_time is None:
            records = self.get_run(run_id)
        elif start_time is not None and end_time is not None:
            records = self.get_range(run_id, start_time, end_time)
        else:
            raise ValueError(
                "Provide both start_time and end_time, or neither."
            )

        yield from records