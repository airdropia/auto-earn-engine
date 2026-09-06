"""
mockup.py - P5 context mockup compositor (AUDIT.md P5).

Wraps a design's PNG in a simple context: white frame, optional wall
background. Pure stdlib (no Pillow, no SVG-to-PNG conversion) - works
by composing the design's pixel_fn with a frame overlay at the
pngio.write_png layer.

Why this approach (vs Pillow/SVG compositing):
- Project is stdlib-only per AGENTS.md (no install step, no extra deps)
- The design's pixel_fn is already in memory from the P3 PNG export;
  re-using it avoids re-decoding any raster
- Mockup = "bigger canvas + frame around the existing design" - simple
  to express as a composite pixel_fn

Available mockups (one per product type, chosen for the buyer's
visualization):
  - MOCKUP_WALL_ART: white frame on soft gray wall (mandala, layered)
  - MOCKUP_FABRIC: rectangular tile on warm fabric swatch (patterns)
  - MOCKUP_SOCIAL: portrait-orientation card with frame (quotes)
  - MOCKUP_NOTEPAD: A4-style pad on wood-grain color (planner)

Each function returns a pixel_fn(x, y) -> (r, g, b) suitable for
pngio.write_png.
"""
from __future__ import annotations

import pngio

# Standard mockup canvas sizes (slightly larger than design to fit frame).
WALL_ART_SIZE = 1200
FABRIC_SIZE = 1100
SOCIAL_W, SOCIAL_H = 1080, 1350
NOTEPAD_W, NOTEPAD_H = 1240, 1754  # A4 at ~150 dpi


def _wall_color() -> tuple[int, int, int]:
    return (240, 236, 230)  # soft warm gray


def _frame_color() -> tuple[int, int, int]:
    return (255, 255, 255)  # white


def _matte_color() -> tuple[int, int, int]:
    return (245, 245, 240)  # off-white matte behind frame


def _fabric_bg() -> tuple[int, int, int]:
    return (200, 180, 150)  # warm fabric tan


def _social_bg() -> tuple[int, int, int]:
    return (30, 30, 40)  # dark elegant background


def _notepad_bg() -> tuple[int, int, int]:
    return (180, 150, 110)  # wood desk color


def make_wallart_mockup(design_pixel_fn, design_size: int = 1000,
                        canvas_size: int = WALL_ART_SIZE,
                        frame_thickness: int = 60) -> callable:
    """White-framed wall art mockup: design centered in a white mat,
    framed against a soft warm wall. Returns a pixel_fn for the canvas.
    """
    wall = _wall_color()
    matte = _matte_color()
    frame = _frame_color()
    # Compute the offset to center the design
    offset = (canvas_size - design_size) // 2
    matte_pad = 30  # additional mat around design

    def pixel(x: int, y: int) -> tuple[int, int, int]:
        # Outer 20px = wall border (gives some "wall space")
        if x < 20 or y < 20 or x >= canvas_size - 20 or y >= canvas_size - 20:
            return wall
        # Frame = white border around the matte
        mat_left = offset - matte_pad
        mat_right = offset + design_size + matte_pad
        mat_top = offset - matte_pad
        mat_bottom = offset + design_size + matte_pad
        if (mat_left <= x < mat_left + frame_thickness
                or mat_right - frame_thickness <= x < mat_right
                or mat_top <= y < mat_top + frame_thickness
                or mat_bottom - frame_thickness <= y < mat_bottom):
            return frame
        # Matte surrounds the design
        if mat_left <= x < mat_right and mat_top <= y < mat_bottom:
            # Design region
            if offset <= x < offset + design_size and offset <= y < offset + design_size:
                return design_pixel_fn(x - offset, y - offset)
            return matte
        # Wall area between frame and outer border
        return wall
    return pixel


def make_fabric_mockup(design_pixel_fn, design_size: int = 1000,
                       canvas_size: int = FABRIC_SIZE) -> callable:
    """Fabric swatch mockup: a square tile of the design on a tan
    fabric background. Used for patterns (texture feel)."""
    bg = _fabric_bg()
    # Center the design, leave a fabric border around
    border = 50
    design_offset = (canvas_size - design_size) // 2
    # Slight fabric texture via low-amplitude noise (deterministic)
    def pixel(x: int, y: int) -> tuple[int, int, int]:
        if (design_offset <= x < design_offset + design_size
                and design_offset <= y < design_offset + design_size):
            return design_pixel_fn(x - design_offset, y - design_offset)
        # Subtle fabric texture: small variation in background
        if (x + y) % 17 == 0:
            return (bg[0] - 8, bg[1] - 6, bg[2] - 4)
        return bg
    return pixel


def make_social_mockup(design_pixel_fn, design_size: int = 1000) -> callable:
    """Instagram-style social card mockup: design as a 1080x1350 portrait
    with a subtle dark frame. Used for quote cards."""
    bg = _social_bg()
    # Design fills most of the canvas, with a small border for "card" feel
    border = 30
    inner_w = SOCIAL_W - 2 * border
    inner_h = SOCIAL_H - 2 * border
    # Scale design to fit inner area (keep aspect ratio: design is 1000x1000)
    scale = inner_w / design_size
    scaled_size = int(design_size * scale)
    offset_x = (SOCIAL_W - scaled_size) // 2
    offset_y = (SOCIAL_H - scaled_size) // 2

    def pixel(x: int, y: int) -> tuple[int, int, int]:
        if (offset_x <= x < offset_x + scaled_size
                and offset_y <= y < offset_y + scaled_size):
            src_x = int((x - offset_x) / scale)
            src_y = int((y - offset_y) / scale)
            return design_pixel_fn(src_x, src_y)
        return bg
    return pixel


def make_notepad_mockup(design_pixel_fn, design_size: int = 1000) -> callable:
    """Notepad/desk mockup: a planner sheet on a wood-grain background.
    A4 portrait orientation for natural planning print context."""
    bg = _notepad_bg()
    # Planner is already 1123x794 landscape, but we'll keep the 1000x1000
    # design and place it on a tall notepad
    inner_w = NOTEPAD_W - 2 * 60
    inner_h = NOTEPAD_H - 2 * 60
    scale = min(inner_w / design_size, inner_h / design_size)
    scaled_size = int(design_size * scale)
    offset_x = (NOTEPAD_W - scaled_size) // 2
    offset_y = (NOTEPAD_H - scaled_size) // 2
    # Pad color: cream
    pad = (250, 248, 240)
    def pixel(x: int, y: int) -> tuple[int, int, int]:
        if (offset_x <= x < offset_x + scaled_size
                and offset_y <= y < offset_y + scaled_size):
            src_x = int((x - offset_x) / scale)
            src_y = int((y - offset_y) / scale)
            return design_pixel_fn(src_x, src_y)
        # Pad area: white-ish with subtle edges
        if (offset_x - 30 <= x < offset_x + scaled_size + 30
                and offset_y - 30 <= y < offset_y + scaled_size + 30):
            return pad
        return bg
    return pixel


# Per-product-type mockup selection
MOCKUP_FOR_TYPE: dict[str, callable] = {
    "mandala": make_wallart_mockup,
    "layered-mandala": make_wallart_mockup,
    "patterns": make_fabric_mockup,
    "quotes": make_social_mockup,
    "planner": make_notepad_mockup,
}


def canvas_size_for(product_type: str) -> tuple[int, int]:
    """Return (width, height) for the given product type's mockup."""
    if product_type in ("mandala", "layered-mandala"):
        return WALL_ART_SIZE, WALL_ART_SIZE
    if product_type == "patterns":
        return FABRIC_SIZE, FABRIC_SIZE
    if product_type == "quotes":
        return SOCIAL_W, SOCIAL_H
    if product_type == "planner":
        return NOTEPAD_W, NOTEPAD_H
    return 1000, 1000
