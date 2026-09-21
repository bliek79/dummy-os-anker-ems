from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_STORAGE_VERSION = 1


class AnkerEmsLegacyAuthorityFence:
    """Single-writer fence for the legacy physical battery controller.

    OPEN preserves the existing Alpha76 behaviour. CLOSING blocks all new
    physical commands except zero-power/self-consumption safe-return writes.
    CLOSED blocks every physical write until an explicit rollback re-opens the
    legacy controller.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.authority_fence"
        )
        self._lock = asyncio.Lock()
        self._state: dict[str, Any] = {
            "status": "open",
            "authority_generation": 0,
            "inflight_calls": 0,
            "write_count": 0,
            "blocked_write_count": 0,
            "last_write_type": None,
            "last_write_at": None,
            "last_blocked_write_type": None,
            "last_blocked_write_at": None,
            "last_changed_at": None,
        }

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            for key in self._state:
                if key in stored:
                    self._state[key] = stored[key]
        # A restart during transfer must never reopen the writer. A transient
        # CLOSING state therefore restores fail-closed as CLOSED.
        if self._state.get("status") == "closing":
            self._state["status"] = "closed"
            self._state["inflight_calls"] = 0
            self._state["last_changed_at"] = dt_util.now().isoformat()
            await self._async_save()

    async def _async_save(self) -> None:
        await self._store.async_save(dict(self._state))

    @property
    def status(self) -> str:
        return str(self._state.get("status") or "closed")

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    @property
    def inflight_calls(self) -> int:
        return int(self._state.get("inflight_calls") or 0)

    @property
    def authority_generation(self) -> int:
        return int(self._state.get("authority_generation") or 0)

    def snapshot(self) -> dict[str, Any]:
        return {
            "legacy_write_fence": self.status,
            "legacy_physical_authority": self.is_open,
            "legacy_inflight_calls": self.inflight_calls,
            "legacy_authority_generation": self.authority_generation,
            "legacy_write_count": int(self._state.get("write_count") or 0),
            "legacy_blocked_write_count": int(
                self._state.get("blocked_write_count") or 0
            ),
            "legacy_last_write_type": self._state.get("last_write_type"),
            "legacy_last_write_at": self._state.get("last_write_at"),
            "legacy_last_blocked_write_type": self._state.get(
                "last_blocked_write_type"
            ),
            "legacy_last_blocked_write_at": self._state.get(
                "last_blocked_write_at"
            ),
            "legacy_authority_last_changed_at": self._state.get("last_changed_at"),
        }

    @staticmethod
    def _is_safe_return(
        domain: str, service: str, service_data: dict[str, Any] | None
    ) -> bool:
        data = service_data or {}
        if domain == "number" and service == "set_value":
            try:
                return float(data.get("value")) == 0.0
            except (TypeError, ValueError):
                return False
        if domain == "select" and service == "select_option":
            return str(data.get("option") or "") == "self_consumption"
        return False

    async def async_begin_dispatch(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None,
    ) -> tuple[int, str]:
        write_type = f"{domain}.{service}"
        async with self._lock:
            safe_return = self._is_safe_return(domain, service, service_data)
            allowed = self.status == "open" or (
                self.status == "closing" and safe_return
            )
            if not allowed:
                self._state["blocked_write_count"] = int(
                    self._state.get("blocked_write_count") or 0
                ) + 1
                self._state["last_blocked_write_type"] = write_type
                self._state["last_blocked_write_at"] = dt_util.now().isoformat()
                await self._async_save()
                raise HomeAssistantError(
                    "Dummy OS EMS physical authority is fenced closed"
                )
            generation = self.authority_generation
            self._state["inflight_calls"] = self.inflight_calls + 1
            await self._async_save()
            return generation, write_type

    async def async_end_dispatch(
        self, token: tuple[int, str], *, success: bool
    ) -> None:
        generation, write_type = token
        async with self._lock:
            self._state["inflight_calls"] = max(0, self.inflight_calls - 1)
            if success:
                self._state["write_count"] = int(
                    self._state.get("write_count") or 0
                ) + 1
                self._state["last_write_type"] = write_type
                self._state["last_write_at"] = dt_util.now().isoformat()
            if generation != self.authority_generation:
                self._state["last_blocked_write_type"] = (
                    f"stale_generation:{write_type}"
                )
                self._state["last_blocked_write_at"] = dt_util.now().isoformat()
            await self._async_save()

    async def async_begin_close(self) -> None:
        async with self._lock:
            if self.status == "closed":
                return
            self._state["status"] = "closing"
            self._state["authority_generation"] = self.authority_generation + 1
            self._state["last_changed_at"] = dt_util.now().isoformat()
            await self._async_save()

    async def async_complete_close(self) -> None:
        async with self._lock:
            if self.inflight_calls:
                raise HomeAssistantError(
                    "Legacy authority fence cannot close with in-flight writes"
                )
            self._state["status"] = "closed"
            self._state["last_changed_at"] = dt_util.now().isoformat()
            await self._async_save()

    async def async_open(self) -> None:
        async with self._lock:
            if self.inflight_calls:
                raise HomeAssistantError(
                    "Legacy authority fence cannot open with in-flight writes"
                )
            self._state["status"] = "open"
            self._state["authority_generation"] = self.authority_generation + 1
            self._state["last_changed_at"] = dt_util.now().isoformat()
            await self._async_save()
