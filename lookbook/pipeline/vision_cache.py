"""lookBOOK — Vision LLM Result Cache
JSON-based disk cache to avoid redundant API calls and save costs.
"""

import hashlib
import json
from pathlib import Path
from typing import Any


class VisionCache:
    """Simple JSON file cache keyed by image hash + prompt hash."""

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.cache_dir / "index.json"
        self._index: dict[str, str] = {}
        self._load_index()

    def _load_index(self):
        if self._index_path.exists():
            try:
                self._index = json.loads(self._index_path.read_text(encoding="utf-8"))
            except Exception:
                self._index = {}

    def _save_index(self):
        self._index_path.write_text(json.dumps(self._index, indent=2), encoding="utf-8")

    def _make_key(self, image_path: str | Path, prompt: str) -> str:
        """Hash image content + prompt to create a unique cache key."""
        img_path = Path(image_path)
        if img_path.exists():
            img_hash = hashlib.sha256(img_path.read_bytes()).hexdigest()[:16]
        else:
            img_hash = hashlib.sha256(str(image_path).encode()).hexdigest()[:16]
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        return f"{img_hash}_{prompt_hash}"

    def get(self, image_path: str | Path, prompt: str) -> dict[str, Any] | None:
        key = self._make_key(image_path, prompt)
        if key not in self._index:
            return None
        cache_file = self.cache_dir / self._index[key]
        if not cache_file.exists():
            return None
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def set(self, image_path: str | Path, prompt: str, result: dict[str, Any]) -> None:
        key = self._make_key(image_path, prompt)
        filename = f"{key}.json"
        cache_file = self.cache_dir / filename
        cache_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        self._index[key] = filename
        self._save_index()

    def clear(self) -> int:
        """Clear all cached entries. Returns count removed."""
        count = len(self._index)
        for filename in self._index.values():
            f = self.cache_dir / filename
            if f.exists():
                f.unlink()
        self._index.clear()
        self._save_index()
        return count

    def stats(self) -> dict[str, Any]:
        total_size = sum(
            (self.cache_dir / f).stat().st_size
            for f in self._index.values()
            if (self.cache_dir / f).exists()
        )
        return {
            "entries": len(self._index),
            "cache_dir": str(self.cache_dir),
            "total_size_bytes": total_size,
        }
