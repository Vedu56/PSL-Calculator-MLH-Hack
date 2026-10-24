"""Home page: dark editorial landing with a split-screen phone mockup on the side."""
import streamlit as st

import site_ui

SLIDE_SECONDS = 4  # how long each side image stays up when a slot has more than one


def _slot(images: list[str], slot: str) -> str:
    """One half of the phone screen. Several images cross-fade; none shows the 'YOU' scan slot."""
    if not images:
        return ('<div class="lp-you"><span class="lp-br tl"></span><span class="lp-br tr"></span>'
                '<span class="lp-br bl"></span><span class="lp-br br"></span>'
                '<span class="lp-you-label">YOU</span><div class="lp-scanline"></div></div>')
    n = len(images)
    imgs = "".join(
        f'<img class="lp-shot lp-shot-{slot}" src="{src}" alt="" style="animation-delay:{i * SLIDE_SECONDS}s">'
        for i, src in enumerate(images)
    )
    if n == 1:
        return imgs
    share = 100 / n  # each image is visible for 1/n of the cycle
    return (
        f"<style>.lp-shot-{slot}{{opacity:0;animation:lp-cycle-{slot} {n * SLIDE_SECONDS}s infinite}}"
        f"@keyframes lp-cycle-{slot}{{0%{{opacity:0}}{share * .12:.2f}%{{opacity:1}}"
        f"{share:.2f}%{{opacity:1}}{share * 1.12:.2f}%{{opacity:0}}100%{{opacity:0}}}}</style>" + imgs
    )


def _phone(images: list[str]) -> str:
    top, bottom = images[0::2], images[1::2]  # images alternate between the two halves
    return f"""
<div class="lp-phone" aria-hidden="true">
  <div class="lp-phone-screen">
    <div class="lp-half">{_slot(top, "a")}</div>
    <div class="lp-vs"><span>VS</span></div>
    <div class="lp-half">{_slot(bottom, "b")}</div>
    <div class="lp-notch"></div>
  </div>
</div>"""


def render():
    phone = _phone(site_ui.side_images())
    st.html(f"""
<div class="lp">
  <nav class="lp-nav" aria-label="Main">
    <a class="lp-logo" href="./" target="_self" aria-label="PSL Calculator home"><span>PSL</span><span>CALC</span></a>
    <div class="lp-links">
      <a href="?page=score" target="_self">PSL Score</a>
      <a href="?page=pvp" target="_self">PSL PvP</a>
    </div>
  </nav>

  <div class="lp-hero">
    <section class="lp-copy">
      <h1 class="lp-title">PSL Calculator</h1>
      <p class="lp-sub">What&rsquo;s your <em>PSL?</em></p>
      <p class="lp-kicker">The 10-second AI face scan</p>

      <div class="lp-ctas">
        <a class="lp-btn" href="?page=score" target="_self">
          <span class="lp-ico lp-ico-play" aria-hidden="true"></span>
          <span class="lp-btn-label">PSL Score</span>
          <span class="lp-chip"><i aria-hidden="true"></i>10s scan</span>
        </a>
        <a class="lp-btn" href="?page=pvp" target="_self">
          <span class="lp-ico lp-ico-vs" aria-hidden="true">VS</span>
          <span class="lp-btn-label">PSL PvP</span>
          <span class="lp-chip lp-chip-muted">Coming soon</span>
        </a>
      </div>
    </section>

    <section class="lp-side">{phone}</section>
  </div>
</div>
""")
