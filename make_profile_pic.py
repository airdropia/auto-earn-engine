"""Generate VectorForge Daily profile picture (512x512 PNG, stdlib only)."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "pipeline"))
from pngio import write_png

W = H = 512
CX = CY = 255.5
BG_TOP = (0x1A, 0x1E, 0x2E)
BG_BOT = (0x2D, 0x32, 0x50)
GREEN = (0x7E, 0xE7, 0x87)
DARK = (0x1A, 0x1E, 0x2E)
RING_W = 6.0


def pixel_fn(x: int, y: int):
    dx = x - CX
    dy = y - CY
    d = math.hypot(dx, dy)
    t = y / (H - 1)
    px = round(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
    pg = round(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
    pb = round(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
    ang_deg = (math.degrees(math.atan2(dy, dx)) + 360) % 360
    spoke_off = abs(((ang_deg + 22.5) % 45) - 22.5)
    on_ring = abs(d - 150) <= RING_W or abs(d - 110) <= RING_W
    on_spoke = 110 < d < 150 and spoke_off < 1.6
    on_hub = d <= 58
    on_center = d <= 22
    if on_center:
        return DARK
    if on_hub or on_ring or on_spoke:
        return GREEN
    return (px, pg, pb)


out = Path(__file__).parent / "patreon_profile_pic.png"
write_png(out, W, H, pixel_fn)
print(f"written: {out}")
