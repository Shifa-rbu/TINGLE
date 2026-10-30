"""The Spider-Sense HUD look: one block of CSS plus a small original emblem.

Everything is local: no external fonts, images, scripts or CDN files. The emblem is an original
octagonal web with a simple spider drawn from plain SVG shapes. It is not any official logo.
Class names start with "tgx-" (the evidence web, in evidence_web.py, uses "tg-").
"""

import streamlit as st

# Palette: deep navy background, electric-blue panels, red for warnings, near-white text.
CSS = """
:root{--tgx-bg:#050b1f;--tgx-panel:#0c1a3d;--tgx-panel2:#102450;--tgx-line:#2f6bff;--tgx-blue:#4aa8ff;
--tgx-red:#ff3b4e;--tgx-amber:#ffb020;--tgx-text:#f5f8ff;--tgx-muted:#b4c2e0;}

/* Page: navy with a faint web fanning out from the top-right corner. */
.stApp{color:var(--tgx-text);
background:
 repeating-conic-gradient(from 90deg at 100% 0,rgba(120,170,255,.08) 0 1deg,transparent 1deg 12deg),
 repeating-radial-gradient(circle at 100% 0,rgba(120,170,255,.07) 0 1px,transparent 1px 80px),
 radial-gradient(circle at 90% -10%,rgba(47,107,255,.35),transparent 45%),
 var(--tgx-bg);
background-attachment:fixed;}
[data-testid="stHeader"]{background:transparent;}
h1,h2,h3{letter-spacing:.01em;}
h1{text-shadow:0 0 18px rgba(74,168,255,.45);}
hr{border-color:rgba(74,168,255,.25) !important;}
a{color:var(--tgx-blue);}

/* Emblem next to the title area. */
.tgx-emblem{display:flex;align-items:center;gap:12px;margin:4px 0 -6px 0;}
.tgx-emblem svg{width:52px;height:52px;filter:drop-shadow(0 0 8px rgba(74,168,255,.6));}
.tgx-emblem span{font-size:.78rem;font-weight:700;letter-spacing:.18em;color:var(--tgx-blue);}

/* Inputs and buttons. */
[data-testid="stTextArea"] textarea,[data-baseweb="select"]>div,[data-testid="stFileUploaderDropzone"]{
background:var(--tgx-panel) !important;border:1px solid rgba(74,168,255,.45) !important;color:var(--tgx-text) !important;}
.stButton>button{border:1px solid var(--tgx-blue);background:var(--tgx-panel2);color:var(--tgx-text);font-weight:600;}
.stButton>button[kind="primary"]{background:linear-gradient(180deg,#ff4a5c,#c8182b);border-color:#ff7a88;
box-shadow:0 0 14px rgba(255,59,78,.45);}
.stButton>button:hover{box-shadow:0 0 14px rgba(74,168,255,.6);}

/* Keyboard focus must always be easy to see. */
:focus-visible{outline:3px solid #ffffff !important;outline-offset:2px !important;
box-shadow:0 0 0 5px var(--tgx-line) !important;}

/* Notices and banners: electric-blue panels, with the result banners in their own boxes. */
[data-testid="stAlert"]{border-radius:10px;}
[data-testid="stAlertContainer"]{color:var(--tgx-text) !important;border:1px solid rgba(74,168,255,.45);
background:rgba(16,36,80,.85) !important;}
[data-testid="stAlertContainer"] *{color:var(--tgx-text) !important;}
.st-key-tgx_notice [data-testid="stAlertContainer"]{border-left:6px solid var(--tgx-blue);}
.st-key-tgx_synthetic [data-testid="stAlertContainer"]{border:2px dashed var(--tgx-blue);}

/* Result banners. The border STYLE differs too (solid / dashed / dotted), so colour is never the only cue. */
.st-key-tgx_banner_stop [data-testid="stAlertContainer"]{background:rgba(120,12,30,.9) !important;
border:3px solid var(--tgx-red);border-left-width:10px;}
.st-key-tgx_banner_pause [data-testid="stAlertContainer"]{background:rgba(96,62,0,.9) !important;
border:3px dashed var(--tgx-amber);border-left:10px solid var(--tgx-amber);}
.st-key-tgx_banner_none [data-testid="stAlertContainer"]{background:rgba(16,36,80,.95) !important;
border:3px dotted var(--tgx-blue);border-left:10px solid var(--tgx-blue);}
.st-key-tgx_banner_error [data-testid="stAlertContainer"]{background:rgba(70,20,40,.95) !important;
border:2px solid var(--tgx-red);}
.st-key-tgx_banner_stop h3,.st-key-tgx_banner_pause h3,.st-key-tgx_banner_none h3{
text-transform:uppercase;letter-spacing:.06em;margin:0;}

/* The "tingle": a slow glow pulse on warning banners only. Off for people who prefer less motion. */
@keyframes tgx-pulse-red{0%,100%{box-shadow:0 0 6px rgba(255,59,78,.25);}50%{box-shadow:0 0 0 4px rgba(255,59,78,.15),0 0 26px rgba(255,59,78,.65);}}
@keyframes tgx-pulse-amber{0%,100%{box-shadow:0 0 6px rgba(255,176,32,.2);}50%{box-shadow:0 0 0 4px rgba(255,176,32,.12),0 0 22px rgba(255,176,32,.5);}}
.st-key-tgx_banner_stop [data-testid="stAlertContainer"]{animation:tgx-pulse-red 2.6s ease-in-out infinite;}
.st-key-tgx_banner_pause [data-testid="stAlertContainer"]{animation:tgx-pulse-amber 3.2s ease-in-out infinite;}
@media (prefers-reduced-motion:reduce){
 .st-key-tgx_banner_stop [data-testid="stAlertContainer"],.st-key-tgx_banner_pause [data-testid="stAlertContainer"]{animation:none;}
 *{scroll-behavior:auto !important;transition:none !important;}}

/* The "what could not be established" box. */
.st-key-tgx_unc{border:1px solid rgba(74,168,255,.5);border-left:6px solid var(--tgx-blue);
border-radius:10px;background:rgba(12,26,61,.9);padding:6px 14px;}
.st-key-tgx_unc [data-testid="stText"],.st-key-tgx_unc p{color:var(--tgx-text);}
/* Streamlit dims captions (60% opacity) and disabled boxes (40% text); for small text that is too faint. */
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] *{color:#c9d5ee !important;opacity:1 !important;}
[data-testid="stTextArea"] textarea:disabled{color:#d8e4ff !important;-webkit-text-fill-color:#d8e4ff !important;opacity:1 !important;}
"""

# Original emblem: three octagon "web" rings, eight spokes, and a small red spider in the middle.
EMBLEM_SVG = (
    '<svg viewBox="0 0 64 64" role="img" aria-label="TINGLE emblem: a web with a small spider">'
    '<g fill="none" stroke="#4aa8ff" stroke-width="1.4" stroke-linejoin="round">'
    '<polygon points="58.8,43.1 43.1,58.8 20.9,58.8 5.2,43.1 5.2,20.9 20.9,5.2 43.1,5.2 58.8,20.9"/>'
    '<polygon points="51.4,40.0 40.0,51.4 24.0,51.4 12.6,40.0 12.6,24.0 24.0,12.6 40.0,12.6 51.4,24.0" opacity=".8"/>'
    '<polygon points="44.0,37.0 37.0,44.0 27.0,44.0 20.0,37.0 20.0,27.0 27.0,20.0 37.0,20.0 44.0,27.0" opacity=".6"/>'
    '<path d="M32 32L58.8 43.1M32 32L43.1 58.8M32 32L20.9 58.8M32 32L5.2 43.1M32 32L5.2 20.9M32 32L20.9 5.2M32 32L43.1 5.2M32 32L58.8 20.9" opacity=".7"/>'
    '</g>'
    '<g fill="none" stroke="#ff3b4e" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M29 30L23 25L19 27M28.5 33L21 32L17 36M28.5 36L22 40L19 46M30 39L27 45L26 51"/>'
    '<path d="M35 30L41 25L45 27M35.5 33L43 32L47 36M35.5 36L42 40L45 46M34 39L37 45L38 51"/>'
    '</g>'
    '<ellipse cx="32" cy="35" rx="4" ry="5.5" fill="#ff3b4e"/>'
    '<circle cx="32" cy="28" r="2.8" fill="#ff3b4e"/>'
    '</svg>'
)


def apply_theme():
    """Add the HUD styles to the page. Call once, right after set_page_config."""
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def show_emblem():
    """The small web/spider emblem with the product name, shown above the title."""
    st.markdown(f'<div class="tgx-emblem">{EMBLEM_SVG}<span>SPIDER-SENSE CHECK</span></div>', unsafe_allow_html=True)
