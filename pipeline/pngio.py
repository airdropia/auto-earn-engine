"""Minimal pure-stdlib PNG writer for small raster assets (no dependencies)."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path


def hex_rgb(color: str) -> tuple[int, int, int]:
    """Parse '#rrggbb' into an (r, g, b) tuple."""
    value = color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path: Path, width: int, height: int, pixel_fn) -> None:
    """Write an 8-bit RGB PNG. pixel_fn(x, y) must return (r, g, b) ints."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 per scanline
        for x in range(width):
            r, g, b = pixel_fn(x, y)
            raw += bytes((r & 255, g & 255, b & 255))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + _chunk(b"IEND", b"")
    )
    path.write_bytes(payload)
