"""
SVG → Animated GIF converter for ModBot custom emojis.

Uses a headless Chromium browser (via Playwright) to render SVG animations
exactly as a real browser does, then stitches screenshots into a looping GIF.

Tracks real wall-clock timing between frames so the GIF plays at the
exact same speed as the original SVG animation.

Requirements: playwright, imageio, Pillow
Setup:        pip install playwright imageio && playwright install chromium

Can also be run standalone:
    python scripts/convert_emoji_assets.py [--force] [--size 128] [--fps 30]
"""

from __future__ import annotations

import argparse
import asyncio
import io
import os
import sys
import time
from pathlib import Path
from typing import Optional

from PIL import Image

_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"

# All premium SVGs animate on a 2.5s loop
_ANIMATION_DURATION = 2.5


async def _render_svg_to_gif(
    svg_path: Path,
    gif_path: Path,
    *,
    size: int = 128,
    fps: int = 30,
    duration: float = _ANIMATION_DURATION,
) -> bool:
    """Render an animated SVG to a high-quality GIF using a headless browser."""
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        print(f"  Missing dependency: {e}. Run: pip install playwright && playwright install chromium")
        return False

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": size, "height": size})

            file_url = f"file:///{svg_path.resolve().as_posix()}"
            await page.goto(file_url)

            # Let the SVG fully parse before capturing
            await asyncio.sleep(0.2)

            frames: list[Image.Image] = []
            timestamps: list[float] = []
            total_frames = int(duration * fps)
            delay = 1.0 / fps

            start_time = time.monotonic()

            for _ in range(total_frames):
                timestamps.append(time.monotonic() - start_time)
                screenshot_bytes = await page.screenshot(omit_background=True)
                img = Image.open(io.BytesIO(screenshot_bytes)).convert("RGBA")
                frames.append(img)
                await asyncio.sleep(delay)

            total_elapsed = time.monotonic() - start_time
            await browser.close()

        if not frames or len(frames) < 2:
            return False

        # Calculate actual per-frame delay from real wall-clock timing.
        # This ensures the GIF plays at the same speed as the SVG.
        actual_frame_ms = int((total_elapsed / len(frames)) * 1000)
        # GIF minimum delay is 20ms (most renderers clamp below that)
        actual_frame_ms = max(20, actual_frame_ms)

        # Convert RGBA frames to palette mode with transparency
        gif_frames: list[Image.Image] = []
        for frame in frames:
            alpha = frame.getchannel("A")
            # Convert to RGB, then to palette
            rgb = frame.convert("RGB")
            p_frame = rgb.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
            # Set fully-transparent pixels to index 255
            mask = Image.eval(alpha, lambda a: 255 if a < 128 else 0)
            p_frame.paste(255, mask)
            gif_frames.append(p_frame)

        gif_frames[0].save(
            str(gif_path),
            format="GIF",
            save_all=True,
            append_images=gif_frames[1:],
            duration=actual_frame_ms,
            loop=0,
            transparency=255,
            disposal=2,
            optimize=True,
        )

        return gif_path.exists()

    except Exception as exc:
        print(f"  Error rendering {svg_path.name}: {exc}")
        import traceback
        traceback.print_exc()
        return False


def render_svg_sync(
    svg_path: Path,
    gif_path: Path,
    png_path: Optional[Path] = None,
    *,
    size: int = 128,
    fps: int = 30,
) -> bool:
    """
    Synchronous wrapper for the async renderer.
    Called by the bot's _auto_render_from_svg() function.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    _render_svg_to_gif(svg_path, gif_path, size=size, fps=fps),
                )
                return future.result(timeout=120)
        else:
            return loop.run_until_complete(
                _render_svg_to_gif(svg_path, gif_path, size=size, fps=fps)
            )
    except Exception as exc:
        print(f"  Sync render failed: {exc}")
        return False


async def convert_all(size: int = 128, fps: int = 30, force: bool = False) -> None:
    """Convert all emoji_*.svg files in assets/ to animated GIFs."""
    if not _ASSETS_DIR.exists():
        print(f"Assets directory not found: {_ASSETS_DIR}")
        sys.exit(1)

    svg_files = sorted(_ASSETS_DIR.glob("emoji_*.svg"))
    if not svg_files:
        print("No emoji_*.svg files found in assets/")
        return

    print(f"Converting {len(svg_files)} SVG(s) at {size}×{size}px, target {fps}fps...")
    print(f"Animation: {_ANIMATION_DURATION}s loop, transparent background")
    print(f"Frame delays will be set from actual capture timing")
    print(f"Assets dir: {_ASSETS_DIR}\n")

    for svg_path in svg_files:
        stem = svg_path.stem
        gif_path = _ASSETS_DIR / f"{stem}.gif"

        if gif_path.exists() and not force:
            print(f"  SKIP {stem} (exists, use --force)")
            continue

        print(f"  Rendering {stem}...")
        ok = await _render_svg_to_gif(svg_path, gif_path, size=size, fps=fps)
        if ok:
            gif_size = gif_path.stat().st_size
            kb = gif_size / 1024
            status = "✓" if gif_size <= 256 * 1024 else "⚠ OVER 256KB"
            print(f"    {status} {gif_path.name}: {kb:.1f} KB")
        else:
            print(f"    ✗ {gif_path.name}: FAILED")

    print("\nDone!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert ModBot emoji SVGs to animated GIFs")
    parser.add_argument("--size", type=int, default=128, help="Output size (default: 128)")
    parser.add_argument("--fps", type=int, default=30, help="Target frames per second (default: 30)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()
    asyncio.run(convert_all(size=args.size, fps=args.fps, force=args.force))
