"""
Resume scanning animation shown while the backend analyzes an upload.

Rendered as a self-contained HTML component (not st.spinner) so the beam
sweep, phase text and progress track stay on screen for the full request
instead of Streamlit's default spinner glyph.
"""

import json

import streamlit.components.v1 as components

# Phases roughly mirror the real backend pipeline so the status text is
# honest about what's happening rather than decorative filler.
_PHASES = [
    "Extracting text",
    "Parsing sections",
    "Reading skills and experience",
    "Comparing against the job description",
    "Scoring",
]

_HTML = """
<div class="scan-stage">
  <div class="doc">
    <div class="doc-line head"></div>
    <div class="doc-line sub"></div>
    <div class="doc-line sec1"></div>
    <div class="doc-line l1"></div>
    <div class="doc-line l2"></div>
    <div class="doc-line l3"></div>
    <div class="doc-line sec2"></div>
    <div class="doc-line l4"></div>
    <div class="doc-line l5"></div>
    <div class="doc-line l6"></div>
    <div class="doc-line sec3"></div>
    <div class="doc-line l7"></div>
    <div class="beam"></div>
    <div class="corner tl"></div><div class="corner tr"></div>
    <div class="corner bl"></div><div class="corner br"></div>
  </div>
  <div class="filename">__FILENAME__</div>
  <div class="status" id="scan-status">Extracting text</div>
  <div class="track"><div class="track-fill"></div></div>
</div>

<style>
  .scan-stage {
    display: flex; flex-direction: column; align-items: center; gap: 14px;
    padding: 30px 20px; font-family: 'Inter', sans-serif;
  }
  .doc {
    position: relative; width: 190px; height: 250px;
    background: #12151A; border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px; overflow: hidden;
    box-shadow: 0 18px 50px rgba(0,0,0,0.55);
  }
  .doc-line { position: absolute; left: 18px; height: 6px; border-radius: 3px; background: rgba(255,255,255,0.10); }
  .doc-line.head { top: 22px; width: 84px; height: 9px; background: rgba(255,255,255,0.22); }
  .doc-line.sub  { top: 40px; width: 116px; height: 5px; }
  .doc-line.sec1 { top: 68px; width: 60px; background: rgba(110,231,183,0.45); }
  .doc-line.l1   { top: 84px; width: 150px; }
  .doc-line.l2   { top: 96px; width: 132px; }
  .doc-line.l3   { top: 108px; width: 146px; }
  .doc-line.sec2 { top: 134px; width: 52px; background: rgba(167,139,250,0.45); }
  .doc-line.l4   { top: 150px; width: 140px; }
  .doc-line.l5   { top: 162px; width: 120px; }
  .doc-line.l6   { top: 174px; width: 150px; }
  .doc-line.sec3 { top: 200px; width: 46px; background: rgba(110,231,183,0.45); }
  .doc-line.l7   { top: 216px; width: 128px; }

  .beam {
    position: absolute; left: 0; right: 0; height: 2px;
    background: #6EE7B7; box-shadow: 0 0 14px 3px rgba(110,231,183,0.75);
    animation: sweep 2.4s ease-in-out infinite;
  }
  .beam::after {
    content: ''; position: absolute; left: 0; right: 0; top: 1px; height: 46px;
    background: linear-gradient(to bottom, rgba(110,231,183,0.18), transparent);
  }
  @keyframes sweep {
    0%   { top: -6px; opacity: 0; }
    8%   { opacity: 1; }
    92%  { opacity: 1; }
    100% { top: 100%; opacity: 0; }
  }

  .corner { position: absolute; width: 14px; height: 14px; border-color: #6EE7B7; border-style: solid; opacity: 0.55; }
  .corner.tl { top: 7px; left: 7px;  border-width: 1px 0 0 1px; }
  .corner.tr { top: 7px; right: 7px; border-width: 1px 1px 0 0; }
  .corner.bl { bottom: 7px; left: 7px;  border-width: 0 0 1px 1px; }
  .corner.br { bottom: 7px; right: 7px; border-width: 0 1px 1px 0; }

  .filename {
    font-family: 'IBM Plex Mono', monospace; font-size: 12px;
    color: rgba(231, 233, 230, 0.55); max-width: 260px; text-align: center;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .filename:empty { display: none; }

  .status {
    font-family: 'IBM Plex Mono', monospace; font-size: 13px;
    color: #6EE7B7; min-height: 18px;
  }
  .track { width: 230px; height: 3px; background: rgba(255,255,255,0.07); border-radius: 2px; overflow: hidden; }
  .track-fill {
    height: 100%; width: 38%;
    background: linear-gradient(90deg, transparent, #6EE7B7, transparent);
    animation: slide 1.6s ease-in-out infinite;
  }
  @keyframes slide {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(360%); }
  }

  @media (prefers-reduced-motion: reduce) {
    .beam, .track-fill { animation: none; }
    .beam { top: 45%; }
  }
</style>

<script>
  const phases = __PHASES__;
  let i = 0;
  const el = document.getElementById('scan-status');
  setInterval(() => {
    i = (i + 1) % phases.length;
    el.textContent = phases[i];
  }, 2600);
</script>
"""


def render_scan_animation(filename: str = "", height: int = 420) -> None:
    """
    Draw the scanning animation. Call inside a placeholder (st.empty()) so it
    can be cleared once the backend response arrives.

    Args:
        filename: optional resume filename shown under the document mockup.
        height: iframe height in px.
    """
    html = _HTML.replace("__PHASES__", json.dumps(_PHASES))
    html = html.replace("__FILENAME__", filename or "")
    components.html(html, height=height)