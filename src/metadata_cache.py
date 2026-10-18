"""Persistent, provider-scoped cache for external metadata responses."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Optional, Union

_VERSION = 1
_LOCKS: dict[Path, asyncio.Lock] = {}
_MISSING = object()


def _default_config() -> dict[str, Any]:
    try:
        from data.config import config

        return config if isinstance(config, dict) else {}
    except ImportError:
        return {}


def _project_root() -> Path:
    """Locate the configured checkout independently of the current directory."""
    try:
        import data.config as config_module

        config_file = getattr(config_module, "__file__", None)
        if config_file:
            return Path(config_file).resolve().parent.parent
    except ImportError:
        pass
    return Path.cwd()


class MetadataCache:
    """JSON cache with hashed keys and per-entry expiry."""

    def __init__(self, base_dir: Union[str, Path] = "", config: Optional[dict[str, Any]] = None) -> None:
        config = config or _default_config()
        default_value = config.get("DEFAULT", config) if isinstance(config, dict) else {}
        default = default_value if isinstance(default_value, dict) else {}
        self.enabled = bool(default.get("metadata_cache_enabled", True))
        configured_dir = str(default.get("metadata_cache_dir", "data/cache/metadata")).strip()
        root = Path(base_dir) if base_dir else _project_root()
        cache_dir = Path(configured_dir or "data/cache/metadata")
        self.root = cache_dir if cache_dir.is_absolute() else root / cache_dir
        try:
            self.default_ttl = max(0, int(default.get("metadata_cache_default_ttl_hours", 168))) * 3600
        except (TypeError, ValueError):
            self.default_ttl = 168 * 3600
        try:
            self.negative_ttl = max(0, int(default.get("metadata_cache_negative_ttl_minutes", 60))) * 60
        except (TypeError, ValueError):
            self.negative_ttl = 60 * 60
        services = default.get("metadata_cache_services", {})
        self.services = services if isinstance(services, dict) else {}

    def _service_settings(self, provider: str) -> dict[str, Any]:
        value = self.services.get(provider, {})
        return value if isinstance(value, dict) else {}

    def is_enabled(self, provider: str) -> bool:
        return self.enabled and bool(self._service_settings(provider).get("enabled", True))

    def ttl(self, provider: str, resource: str, negative: bool = False) -> int:
        if negative:
            return self.negative_ttl
        settings = self._service_settings(provider)
        resource_ttl = settings.get(f"{resource}_ttl_hours", settings.get("ttl_hours", self.default_ttl // 3600))
        try:
            return max(0, int(resource_ttl)) * 3600
        except (TypeError, ValueError):
            return self.default_ttl

    def _path(self, provider: str, resource: str, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        safe_provider = "".join(char for char in provider.lower() if char.isalnum() or char in "_-")
        safe_resource = "".join(char for char in resource.lower() if char.isalnum() or char in "_-")
        return self.root / safe_provider / safe_resource / f"{digest}.json"

    async def get(self, provider: str, resource: str, key: str) -> Any:
        if not self.is_enabled(provider):
            return _MISSING
        path = self._path(provider, resource, key)
        try:
            raw = await asyncio.to_thread(path.read_text, encoding="utf-8")
            entry = json.loads(raw)
            if not isinstance(entry, dict) or entry.get("version") != _VERSION or float(entry.get("expires_at", 0)) < time.time():
                return _MISSING
            return entry.get("value", _MISSING)
        except (OSError, ValueError, TypeError):
            return _MISSING

    async def set(self, provider: str, resource: str, key: str, value: Any, *, negative: bool = False) -> None:
        if not self.is_enabled(provider):
            return
        ttl = self.ttl(provider, resource, negative)
        if ttl <= 0:
            return
        path = self._path(provider, resource, key)
        now = time.time()
        entry = {"version": _VERSION, "fetched_at": now, "expires_at": now + ttl, "value": value}
        try:
            serialized = json.dumps(entry, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return
        lock = _LOCKS.setdefault(path, asyncio.Lock())
        async with lock:
            try:
                await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
                temporary = path.with_suffix(f".tmp.{os.getpid()}")
                await asyncio.to_thread(temporary.write_text, serialized, encoding="utf-8")
                await asyncio.to_thread(temporary.replace, path)
            except OSError:
                return


def cache_for(base_dir: Union[str, Path] = "", config: Optional[dict[str, Any]] = None) -> MetadataCache:
    return MetadataCache(base_dir, config)


def is_cache_miss(value: Any) -> bool:
    return value is _MISSING
