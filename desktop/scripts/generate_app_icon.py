#!/usr/bin/env python3
"""Generate VerityDesk macOS iconset PNGs without external dependencies."""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ICONSET = ASSETS / "veritydesk-icon.iconset"
ICNS = ASSETS / "veritydesk-icon.icns"

NAVY = (2, 6, 23, 255)
PANEL = (7, 17, 31, 255)
CYAN = (34, 211, 238, 255)
CYAN_SOFT = (34, 211, 238, 92)
LIME = (163, 230, 53, 255)
LIME_SOFT = (163, 230, 53, 92)
PINK = (244, 114, 182, 210)
WHITE = (248, 250, 252, 255)
STROKE = (29, 53, 88, 210)


def mix(a: tuple[int, int, int, int], b: tuple[int, int, int, int], t: float) -> tuple[int, int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(4))


def over(dst: tuple[int, int, int, int], src: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    sa = src[3] / 255
    da = dst[3] / 255
    out_a = sa + da * (1 - sa)
    if out_a <= 0:
        return (0, 0, 0, 0)
    return tuple(
        round((src[i] * sa + dst[i] * da * (1 - sa)) / out_a) for i in range(3)
    ) + (round(out_a * 255),)


class Canvas:
    def __init__(self, size: int) -> None:
        self.size = size
        self.pixels = [(0, 0, 0, 0)] * (size * size)

    def set(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if 0 <= x < self.size and 0 <= y < self.size:
            idx = y * self.size + x
            self.pixels[idx] = over(self.pixels[idx], color)

    def fill_rounded_rect(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        radius: float,
        color_fn,
    ) -> None:
        for y in range(math.floor(y0), math.ceil(y1)):
            for x in range(math.floor(x0), math.ceil(x1)):
                cx = min(max(x, x0 + radius), x1 - radius)
                cy = min(max(y, y0 + radius), y1 - radius)
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                    self.set(x, y, color_fn(x, y))

    def stroke_rounded_rect(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        radius: float,
        width: int,
        color: tuple[int, int, int, int],
    ) -> None:
        inset = width

        def contains(px: int, py: int, ax0: float, ay0: float, ax1: float, ay1: float, ar: float) -> bool:
            if not (ax0 <= px <= ax1 and ay0 <= py <= ay1):
                return False
            cx = min(max(px, ax0 + ar), ax1 - ar)
            cy = min(max(py, ay0 + ar), ay1 - ar)
            return (px - cx) ** 2 + (py - cy) ** 2 <= ar**2

        for y in range(math.floor(y0), math.ceil(y1)):
            for x in range(math.floor(x0), math.ceil(x1)):
                outer = contains(x, y, x0, y0, x1, y1, radius)
                inner = contains(
                    x,
                    y,
                    x0 + inset,
                    y0 + inset,
                    x1 - inset,
                    y1 - inset,
                    max(1, radius - inset),
                )
                if outer and not inner:
                    self.set(x, y, color)

    def line(self, x0: float, y0: float, x1: float, y1: float, width: float, color: tuple[int, int, int, int]) -> None:
        min_x = math.floor(min(x0, x1) - width)
        max_x = math.ceil(max(x0, x1) + width)
        min_y = math.floor(min(y0, y1) - width)
        max_y = math.ceil(max(y0, y1) + width)
        dx = x1 - x0
        dy = y1 - y0
        length_sq = dx * dx + dy * dy
        radius = width / 2
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if length_sq == 0:
                    t = 0
                else:
                    t = max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / length_sq))
                px = x0 + t * dx
                py = y0 + t * dy
                if (x - px) ** 2 + (y - py) ** 2 <= radius**2:
                    self.set(x, y, color)

    def circle(self, cx: float, cy: float, radius: float, color: tuple[int, int, int, int]) -> None:
        for y in range(math.floor(cy - radius), math.ceil(cy + radius) + 1):
            for x in range(math.floor(cx - radius), math.ceil(cx + radius) + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                    self.set(x, y, color)

    def polygon(self, points: list[tuple[float, float]], color: tuple[int, int, int, int]) -> None:
        min_x = math.floor(min(x for x, _ in points))
        max_x = math.ceil(max(x for x, _ in points))
        min_y = math.floor(min(y for _, y in points))
        max_y = math.ceil(max(y for _, y in points))
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                inside = False
                j = len(points) - 1
                for i in range(len(points)):
                    xi, yi = points[i]
                    xj, yj = points[j]
                    intersects = ((yi > y) != (yj > y)) and (
                        x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
                    )
                    if intersects:
                        inside = not inside
                    j = i
                if inside:
                    self.set(x, y, color)

    def png_bytes(self) -> bytes:
        raw = bytearray()
        for y in range(self.size):
            raw.append(0)
            for x in range(self.size):
                raw.extend(self.pixels[y * self.size + x])

        def chunk(kind: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data))
                + kind
                + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
            )

        header = struct.pack(">IIBBBBB", self.size, self.size, 8, 6, 0, 0, 0)
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")


def render(size: int) -> Canvas:
    c = Canvas(size)
    s = size / 1024

    def bg(x: int, y: int) -> tuple[int, int, int, int]:
        t = (x + y) / (2 * size)
        base = mix(PANEL, NAVY, t)
        glow_c = max(0, 1 - math.dist((x, y), (720 * s, 240 * s)) / (430 * s))
        glow_l = max(0, 1 - math.dist((x, y), (300 * s, 760 * s)) / (390 * s))
        color = mix(base, CYAN, glow_c * 0.22)
        return mix(color, LIME, glow_l * 0.14)

    c.fill_rounded_rect(64 * s, 64 * s, 960 * s, 960 * s, 214 * s, bg)

    grid = max(1, round(64 * s))
    for pos in range(round(64 * s), round(960 * s), grid):
        c.line(pos, 64 * s, pos, 960 * s, max(1, 2 * s), (34, 211, 238, 22))
        c.line(64 * s, pos, 960 * s, pos, max(1, 2 * s), (34, 211, 238, 22))

    c.stroke_rounded_rect(82 * s, 82 * s, 942 * s, 942 * s, 196 * s, max(2, round(18 * s)), (34, 211, 238, 170))
    c.stroke_rounded_rect(118 * s, 118 * s, 906 * s, 906 * s, 168 * s, max(1, round(6 * s)), STROKE)

    c.line(226 * s, 322 * s, 798 * s, 322 * s, max(2, 8 * s), (34, 211, 238, 44))
    c.line(226 * s, 704 * s, 798 * s, 704 * s, max(2, 8 * s), (163, 230, 53, 44))

    c.fill_rounded_rect(262 * s, 293 * s, 762 * s, 688 * s, 48 * s, lambda _x, _y: (2, 6, 23, 220))
    c.stroke_rounded_rect(262 * s, 293 * s, 762 * s, 688 * s, 48 * s, max(2, round(10 * s)), CYAN_SOFT)

    c.polygon([(338 * s, 390 * s), (421 * s, 390 * s), (512 * s, 574 * s), (603 * s, 390 * s), (686 * s, 390 * s), (537 * s, 674 * s), (487 * s, 674 * s)], CYAN)
    c.polygon([(487 * s, 674 * s), (512 * s, 574 * s), (537 * s, 674 * s)], LIME)
    c.line(345 * s, 724 * s, 679 * s, 724 * s, max(8, 34 * s), LIME)
    c.line(414 * s, 781 * s, 610 * s, 781 * s, max(5, 20 * s), (34, 211, 238, 190))

    c.circle(716 * s, 306 * s, 34 * s, LIME)
    c.circle(716 * s, 306 * s, 10 * s, WHITE)
    c.circle(309 * s, 306 * s, 13 * s, CYAN)
    c.circle(309 * s, 648 * s, 13 * s, PINK)
    c.circle(715 * s, 648 * s, 13 * s, (34, 211, 238, 190))
    return c


def write_png(size: int, name: str) -> None:
    (ICONSET / name).write_bytes(render(size).png_bytes())


def write_icns() -> None:
    chunks = [
        ("icp4", ICONSET / "icon_16x16.png"),
        ("icp5", ICONSET / "icon_32x32.png"),
        ("icp6", ICONSET / "icon_32x32@2x.png"),
        ("ic07", ICONSET / "icon_128x128.png"),
        ("ic08", ICONSET / "icon_256x256.png"),
        ("ic09", ICONSET / "icon_512x512.png"),
        ("ic10", ICONSET / "icon_512x512@2x.png"),
    ]
    body = bytearray()
    for chunk_type, file_path in chunks:
        data = file_path.read_bytes()
        body.extend(chunk_type.encode("ascii"))
        body.extend(struct.pack(">I", len(data) + 8))
        body.extend(data)

    ICNS.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)


def main() -> None:
    ICONSET.mkdir(parents=True, exist_ok=True)
    for old_file in ICONSET.glob("*.png"):
        old_file.unlink()

    write_png(16, "icon_16x16.png")
    write_png(32, "icon_16x16@2x.png")
    write_png(32, "icon_32x32.png")
    write_png(64, "icon_32x32@2x.png")
    write_png(128, "icon_128x128.png")
    write_png(256, "icon_128x128@2x.png")
    write_png(256, "icon_256x256.png")
    write_png(512, "icon_256x256@2x.png")
    write_png(512, "icon_512x512.png")
    write_png(1024, "icon_512x512@2x.png")

    write_icns()
    print(ICNS)


if __name__ == "__main__":
    main()
