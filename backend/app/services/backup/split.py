from __future__ import annotations

from pathlib import Path


def split_file(path: Path, *, max_bytes: int) -> list[Path]:
    """Розбиває файл на частини ≤ max_bytes. Якщо файл менший — повертає [path]."""
    size = path.stat().st_size
    if size <= max_bytes:
        return [path]

    parts: list[Path] = []
    with path.open("rb") as src:
        index = 1
        while True:
            chunk = src.read(max_bytes)
            if not chunk:
                break
            part_path = path.with_name(f"{path.name}.part{index:03d}")
            part_path.write_bytes(chunk)
            parts.append(part_path)
            index += 1
    return parts
