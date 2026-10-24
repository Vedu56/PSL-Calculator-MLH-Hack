"""Shared site UI: page routing, theme loading, the back button and the side images.

Presentation only - no PSL calculation logic lives here.
Theme files live in ./theme, side images in ./assets/side (drop more .png/.jpg files there
and the phone on the home page will cycle through them).
"""
from __future__ import annotations

import base64
import io
import re
from functools import lru_cache
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps

ROOT = Path(__file__).parent
THEME_DIR = ROOT / "theme"
SIDE_DIR = ROOT / "assets" / "side"
PAGES = ("home", "score", "pvp")

FONTS = ("@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1"
         "&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');")


# =====================================================================
# Routing (the page lives in the URL: ?page=score / ?page=pvp)
# =====================================================================
def current_page() -> str:
    page = st.query_params.get("page", "home")
    return page if page in PAGES else "home"


def go(page: str):
    """Button callback: switch page without reloading."""
    if page == "home":
        st.query_params.pop("page", None)
    else:
        st.query_params["page"] = page


# =====================================================================
# Theme
# =====================================================================
@lru_cache(maxsize=8)
def _theme_file(name: str) -> str:
    """Read a CSS file without its /* comments */. Streamlit's HTML sanitiser drops a whole
    style block if it sees something tag-like (a '<' followed by a letter); comments are
    where that tends to sneak in."""
    text = (THEME_DIR / name).read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def inject_theme(page: str):
    css = _theme_file("landing.css" if page == "home" else "pages.css")
    st.html(f"<style>{FONTS}\n{css}</style>")


# =====================================================================
# Components
# =====================================================================
def back_button():
    """Round icon button, pinned top-left, that returns to the home page.
    The word "Back" is only read out by screen readers (hidden visually by pages.css)."""
    with st.container(key="nav_backbar"):
        st.button("Back", key="nav_back", icon=":material/arrow_back:", on_click=go, args=("home",))


@lru_cache(maxsize=32)
def _image_data_uri(path: str, mtime: float) -> str:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img.thumbnail((720, 720))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def side_images() -> list[str]:
    """Every image in assets/side, as data URIs (sorted by file name)."""
    files = sorted(p for p in SIDE_DIR.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    return [_image_data_uri(str(p), p.stat().st_mtime) for p in files]
