"""
CareerForge -- Streamlit front end.

UI layer only. The answer path is the SAME one main.py uses:

    build_index() -> VectorRetriever -> Generator -> Conversation.ask(question)

Nothing in the retrieval / prompting / rewriting / citation logic is
re-implemented here. Run from the project root with:

    streamlit run app.py
"""
from __future__ import annotations

import html
import logging
import re
import sys
import uuid
from pathlib import Path

import streamlit as st

# --------------------------------------------------------------------------- #
# Paths (same convention as main.py: modules import as `config`, `generation`..)
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
for _p in (str(PROJECT_ROOT), str(SRC_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

log = logging.getLogger("careerforge.ui")

st.set_page_config(
    page_title="CareerForge | AI Career Assistant",
    page_icon=":material/auto_awesome:",
    layout="wide",
    initial_sidebar_state="auto",
)

PLACEHOLDER = "Ask CareerForge anything about your career..."
FRIENDLY_ERROR = "Something went wrong while processing your request. Please try again."
UNAVAILABLE = "CareerForge is temporarily unavailable. Please try again in a moment."

EXAMPLES = [
    ("description", "How should I analyze a job description?"),
    ("person", "How can I improve my resume?"),
    ("forum", "How should I answer behavioral interview questions?"),
    ("code", "How should I prepare for a technical interview?"),
    ("payments", "How can I approach salary negotiation?"),
    ("badge", "How can I build my professional brand?"),
]

# --------------------------------------------------------------------------- #
# Inline icons (Feather-style strokes)
# --------------------------------------------------------------------------- #
_ICONS = {
    "spark": '<path d="M12 2l2.2 6.3L21 10l-6.8 1.7L12 18l-2.2-6.3L3 10l6.8-1.7z"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "bulb": '<path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.3h6c0-1 .4-1.8 1-2.3A7 7 0 0 0 12 2z"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "arrow": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "down": '<line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>',
    "rocket": '<path d="M4.5 16.5c-1.5 1.3-2 5-2 5s3.7-.5 5-2c.7-.8.7-2.1-.1-2.9a2.1 2.1 0 0 0-2.9-.1z"/><path d="M12 15l-3-3a22 22 0 0 1 2-3.9A12.9 12.9 0 0 1 22 2c0 2.7-.8 7.5-6 11a22 22 0 0 1-4 2z"/><path d="M9 12H4s.6-3 2-4c1.6-1.1 5 0 5 0"/><path d="M12 15v5s3-.6 4-2c1.1-1.6 0-5 0-5"/>',
}


def icon(name: str, size: int = 20) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{_ICONS[name]}</svg>'
    )


# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root{
  --cf-ink:#12163a; --cf-muted:#6b7194; --cf-line:#e4e8f7; --cf-soft:#f4f6fd;
  --cf-primary:#5b3df5; --cf-primary-2:#7c5cff; --cf-blue:#3b6cf6;
  --cf-grad:linear-gradient(90deg,#b14ff0 0%,#6a4cf6 50%,#3b82f6 100%);
  --cf-shadow:0 10px 30px -12px rgba(60,55,160,.22);
}
html, body, [class*="css"], .stApp, button, input, textarea{
  font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif !important;
}
.stApp{
  background:
    radial-gradient(900px 500px at 85% -10%, rgba(124,92,255,.10), transparent 60%),
    radial-gradient(700px 500px at 10% 0%, rgba(59,130,246,.07), transparent 60%),
    #f5f7fe;
  color:var(--cf-ink);
}

/* --- hide Streamlit chrome --- */
#MainMenu, footer, [data-testid="stToolbarActions"], [data-testid="stMainMenu"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], .stDeployButton, [data-testid="stAppDeployButton"]{ display:none !important; }
[data-testid="stExpandSidebarButton"]{ color:#4a3fd6; }
header[data-testid="stHeader"]{ background:transparent !important; height:2.5rem; }

.block-container{ max-width:1320px; padding:1.4rem 2rem 9rem 2rem !important; }

/* --- scrollbar --- */
*::-webkit-scrollbar{ width:10px; height:10px; }
*::-webkit-scrollbar-thumb{ background:#cfd4ee; border-radius:10px; border:2px solid transparent; background-clip:content-box; }
*::-webkit-scrollbar-thumb:hover{ background:#b4bce6; background-clip:content-box; }

/* ================= SIDEBAR ================= */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#080b24 0%,#0c1240 55%,#161a66 100%) !important;
  border-right:0;
}
[data-testid="stSidebar"] *{ color:#e8ebff; }
[data-testid="stSidebar"] .block-container, [data-testid="stSidebarUserContent"]{ padding-top:1.2rem !important; }
.cf-brand{ display:flex; align-items:center; gap:.85rem; padding:.3rem .2rem 1.6rem; }
.cf-brand svg{ flex:none; }
.cf-wordmark{ font-size:1.55rem; font-weight:700; letter-spacing:-.02em; line-height:1.1; color:#fff; }
.cf-wordmark b{ background:linear-gradient(90deg,#b58bff,#6f8cff); -webkit-background-clip:text; background-clip:text; color:transparent; font-weight:700; }
.cf-tag{ font-size:.78rem; color:#b9c0ee; margin-top:.2rem; }

[data-testid="stSidebar"] .stButton>button{
  width:100%; justify-content:flex-start; gap:.7rem; background:transparent; border:0;
  color:#e8ebff; font-size:1.02rem; font-weight:500; padding:.85rem 1rem; border-radius:14px;
  transition:background .18s ease, transform .18s ease;
}
[data-testid="stSidebar"] .stButton>button:hover{ background:rgba(255,255,255,.07); color:#fff; }
[data-testid="stSidebar"] .stButton>button:focus-visible{ outline:2px solid #8f7cff; outline-offset:2px; }
[data-testid="stSidebar"] .stButton>button[kind="primary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]{
  background:linear-gradient(90deg,#3a35c9,#5648e8); box-shadow:0 8px 22px -8px rgba(86,72,232,.8);
}
[data-testid="stSidebar"] .stButton>button p{ font-size:1.02rem; }
[data-testid="stSidebar"] .stButton>button>div, [class*="st-key-ex_"] .stButton>button>div{ width:100%; justify-content:flex-start; }
[data-testid="stSidebar"] .stButton>button span[data-has-shortcut], [class*="st-key-ex_"] .stButton>button span[data-has-shortcut]{
  display:flex; align-items:center; justify-content:flex-start; width:100%; gap:.8rem; }
[class*="st-key-ex_"] .stButton>button span[data-has-shortcut]{ padding-left:.35rem; gap:1rem; }
[data-testid="stSidebar"] .stButton>button [data-testid="stIconMaterial"]{ color:#c9ceff; font-size:1.4rem; }
.st-key-hist_list .stButton>button{ font-size:.86rem !important; padding:.5rem .9rem .5rem 2.4rem !important; color:#c6ccf5 !important; }
.st-key-hist_list .stButton>button p{ font-size:.86rem !important; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.cf-rule{ height:1px; margin:1.4rem .3rem; background:linear-gradient(90deg,transparent,rgba(120,130,255,.6),transparent); }
.cf-side-promo{ margin:2.2rem .4rem 0; }
.cf-side-promo svg{ color:#7c8dff; }
.cf-side-promo h4{ margin:.7rem 0 .6rem; font-size:1.18rem; line-height:1.3; font-weight:600; color:#fff; }
.cf-side-promo p{ font-size:.92rem; line-height:1.65; color:#c3c9f0; margin:0; }
.cf-profile{ display:flex; align-items:center; gap:.75rem; margin:4.5rem .3rem 0; padding-top:1.1rem; border-top:1px solid rgba(255,255,255,.1); }
.cf-avatar{ width:42px; height:42px; border-radius:50%; background:linear-gradient(135deg,#8f6bff,#5b3df5); display:grid; place-items:center; font-weight:700; color:#fff; position:relative; }
.cf-avatar::after{ content:""; position:absolute; right:0; bottom:0; width:10px; height:10px; border-radius:50%; background:#3ddc84; border:2px solid #101554; }
.cf-profile b{ display:block; font-size:.9rem; font-weight:600; color:#fff; }
.cf-profile span{ font-size:.75rem; color:#aab2e6; }

/* ================= TOP BAR ================= */
.cf-top{ display:flex; align-items:center; gap:.9rem; padding:.7rem 1.1rem; background:#fff; border:1px solid var(--cf-line);
  border-radius:16px; box-shadow:var(--cf-shadow); margin-bottom:1.3rem; }
.cf-top .ic{ color:var(--cf-primary); display:grid; place-items:center; width:32px; height:32px; border-radius:10px; background:#eeebff; }
.cf-top b{ font-size:.92rem; font-weight:600; }
.cf-top span{ font-size:.9rem; color:#8a90b5; padding-left:.9rem; border-left:1px solid var(--cf-line); }

/* ================= HERO ================= */
.cf-hero{ position:relative; overflow:hidden; border-radius:26px; padding:2.1rem 2.2rem 1.6rem; border:1px solid var(--cf-line);
  background:linear-gradient(120deg,#f6f4ff 0%,#eef1ff 55%,#e6ecff 100%); box-shadow:var(--cf-shadow); }
.cf-hero::before{ content:""; position:absolute; right:-80px; top:-80px; width:420px; height:420px; border-radius:50%;
  background:radial-gradient(circle,rgba(160,130,255,.35),transparent 65%); }
.cf-hero-grid{ position:relative; display:grid; grid-template-columns:1.15fr 1fr; gap:1rem; align-items:center; }
.cf-pill{ display:inline-flex; align-items:center; gap:.45rem; padding:.35rem .8rem; border-radius:999px; background:#e9e6ff; color:#4a3fd6;
  font-size:.72rem; font-weight:700; letter-spacing:.06em; }
.cf-pill svg{ width:14px; height:14px; }
.cf-h1{ font-size:clamp(2.2rem,4.2vw,3.5rem); line-height:1.06; font-weight:800; letter-spacing:-.035em; margin:1rem 0 1rem; color:var(--cf-ink); }
.cf-h1 em{ font-style:normal; background:var(--cf-grad); -webkit-background-clip:text; background-clip:text; color:transparent; }
.cf-lead{ font-size:1.02rem; line-height:1.75; color:#4a5078; max-width:34ch; margin:0; }
.cf-art{ display:grid; place-items:center; }
.cf-art svg{ width:100%; max-width:430px; height:auto; filter:drop-shadow(0 24px 30px rgba(60,50,160,.25)); }
.cf-props{ position:relative; display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin-top:1.5rem; }
.cf-prop{ display:flex; align-items:center; gap:.75rem; }
.cf-prop .ic{ flex:none; width:46px; height:46px; border-radius:50%; display:grid; place-items:center; background:#ebe8ff; color:#5b3df5; }
.cf-prop b{ display:block; font-size:.86rem; font-weight:600; }
.cf-prop span{ font-size:.75rem; color:#6b7194; }

.cf-section{ display:flex; align-items:center; gap:.6rem; font-size:1.12rem; font-weight:600; margin:1.9rem .3rem 1rem; }
.cf-section svg{ color:var(--cf-primary); }

/* --- example cards (real buttons) --- */
[class*="st-key-ex_"] .stButton>button{
  width:100%; min-height:82px; justify-content:flex-start; text-align:left; gap:1rem; padding:1rem 3.2rem 1rem 1rem;
  background:linear-gradient(180deg,#fff,#f8f9ff); border:1px solid var(--cf-line); border-radius:18px; color:#2a2f55;
  box-shadow:0 6px 18px -14px rgba(60,55,160,.4); position:relative; transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
}
[class*="st-key-ex_"] .stButton>button>div, [class*="st-key-ex_"] .stButton>button p, [class*="st-key-ex_"] [data-testid="stMarkdownContainer"]{
  white-space:normal !important; overflow:visible !important; text-overflow:clip !important; }
[class*="st-key-ex_"] .stButton>button p{ font-size:.93rem; font-weight:500; line-height:1.4; text-align:left; margin:0; }
[class*="st-key-ex_"] .stButton>button [data-testid="stIconMaterial"]{ font-size:1.3rem; color:#5b3df5; background:#ece9ff; border-radius:50%;
  width:42px; height:42px; display:grid; place-items:center; flex:none; }
[class*="st-key-ex_"] .stButton>button::after{ content:"\\2192"; position:absolute; right:1.3rem; top:50%; transform:translateY(-50%); font-size:1.15rem; color:#5b3df5; transition:transform .18s ease; }
[class*="st-key-ex_"] .stButton>button:hover{ transform:translateY(-2px); border-color:#b9adff; box-shadow:0 14px 26px -14px rgba(91,61,245,.5); color:#1d2150; }
[class*="st-key-ex_"] .stButton>button:hover::after{ transform:translate(4px,-50%); }
[class*="st-key-ex_"] .stButton>button:focus-visible{ outline:2px solid #7c5cff; outline-offset:2px; }

/* ================= RIGHT RAIL ================= */
.cf-quote{ position:relative; overflow:hidden; border-radius:26px; min-height:400px; padding:1.6rem; color:#12163a; box-shadow:var(--cf-shadow);
  background:linear-gradient(180deg,#a9c2ff 0%,#d6c9ff 38%,#ffd2b8 70%,#f7a98d 100%); }
.cf-quote .q{ width:38px; height:38px; border-radius:50%; background:#ece9ff; color:#5b3df5; display:grid; place-items:center; font-weight:800; font-size:1.6rem; line-height:1; padding-top:.35rem; }
.cf-quote h3{ font-size:1.5rem; line-height:1.28; font-weight:700; letter-spacing:-.02em; margin:1rem 0 .8rem; position:relative; z-index:2; max-width:11em; }
.cf-quote h3 em{ font-style:normal; color:#5b3df5; }
.cf-quote p{ font-size:.85rem; color:#4d537a; margin:0; position:relative; z-index:2; line-height:1.5; }
.cf-quote svg.land{ position:absolute; left:0; bottom:0; width:100%; height:55%; }
.cf-tips{ margin-top:1.2rem; padding:1.3rem 1.3rem 1rem; background:#fff; border:1px solid var(--cf-line); border-radius:22px; box-shadow:var(--cf-shadow); }
.cf-tips-h{ display:flex; align-items:center; gap:.7rem; font-size:1.12rem; font-weight:600; margin-bottom:.9rem; }
.cf-tips-h .ic{ width:40px; height:40px; border-radius:50%; display:grid; place-items:center; background:#efecff; color:#5b3df5; }
.cf-tip{ display:flex; gap:.75rem; padding:.55rem 0; }
.cf-tip .ck{ flex:none; width:24px; height:24px; border-radius:50%; background:#5b3df5; color:#fff; display:grid; place-items:center; margin-top:.1rem; }
.cf-tip .ck svg{ width:13px; height:13px; stroke-width:3; }
.cf-tip b{ display:block; font-size:.86rem; font-weight:600; }
.cf-tip span{ font-size:.77rem; color:#6b7194; }
.cf-cta{ display:flex; align-items:center; gap:.9rem; margin-top:1.2rem; padding:1.2rem; border-radius:22px; border:1px solid #ddd6ff;
  background:linear-gradient(135deg,#efeaff,#dcd4ff); box-shadow:var(--cf-shadow); }
.cf-cta .ic{ flex:none; width:48px; height:48px; border-radius:50%; background:#fff; color:#4a3fd6; display:grid; place-items:center; }
.cf-cta b{ display:block; font-size:1rem; font-weight:600; }
.cf-cta span{ font-size:.8rem; color:#5f6590; }
.cf-cta .go{ margin-left:auto; flex:none; width:44px; height:44px; border-radius:50%; background:linear-gradient(135deg,#6a4cf6,#4a3fd6); color:#fff; display:grid; place-items:center; }

/* ================= CHAT ================= */
.cf-chat-head{ display:flex; align-items:center; gap:.6rem; margin:.2rem .2rem 1rem; color:#6b7194; font-size:.85rem; }
[data-testid="stChatMessage"]{ background:transparent; padding:.55rem 0; gap:.9rem; align-items:flex-start; justify-content:flex-start; }
[data-testid="stChatMessageContent"] [data-testid="stVerticalBlock"]{ gap:0; }
[data-testid="stChatMessage"] [data-testid^="stChatMessageAvatar"]{ width:38px; height:38px; border-radius:50%; flex:none; border:0; }
[data-testid="stChatMessage"] [data-testid^="stChatMessageAvatar"] *{ color:#fff !important; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid^="stChatMessageAvatar"]{ background:#12163a !important; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid^="stChatMessageAvatar"]{ background:linear-gradient(135deg,#8f6bff,#4a3fd6) !important; }
[data-testid="stChatMessageContent"]{ font-size:.98rem; line-height:1.7; width:auto; flex:0 1 auto; margin:0 !important; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]){ flex-direction:row-reverse; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageContent"]{
  background:linear-gradient(135deg,#5b3df5,#7c5cff); color:#fff; padding:.85rem 1.15rem; border-radius:20px 20px 6px 20px;
  max-width:min(75%,640px); box-shadow:0 12px 24px -14px rgba(91,61,245,.7);
}
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageContent"] *{ color:#fff; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"]{
  background:#fff; border:1px solid var(--cf-line); padding:1rem 1.3rem; border-radius:20px 20px 20px 6px; box-shadow:var(--cf-shadow); max-width:min(88%,820px);
}
[data-testid="stChatMessageContent"] [data-testid="stMarkdownContainer"]{ margin-bottom:0 !important; }
[data-testid="stChatMessageContent"] p{ margin:0 0 .6rem; } [data-testid="stChatMessageContent"] p:last-child{ margin-bottom:0; }
[data-testid="stChatMessageContent"] ul, [data-testid="stChatMessageContent"] ol{ padding-left:1.3rem; margin:.3rem 0 .6rem; }
[data-testid="stChatMessageContent"] li{ margin:.25rem 0; }

.cf-cite{ display:inline-flex; align-items:center; gap:.4rem; margin:.1rem .15rem; padding:.12rem .6rem; border-radius:999px; vertical-align:baseline;
  background:#f1efff; border:1px solid #ddd8ff; font-size:.72rem; font-weight:500; color:#4a3fd6; line-height:1.5; white-space:normal; }
.cf-cite::before{ content:""; width:6px; height:6px; border-radius:50%; background:#7c5cff; flex:none; }
.cf-cite i{ font-style:normal; color:#8a86c9; }

.cf-think{ display:flex; align-items:center; gap:.7rem; color:#6b7194; font-size:.95rem; }
.cf-dots{ display:inline-flex; gap:5px; }
.cf-dots span{ width:8px; height:8px; border-radius:50%; background:#7c5cff; animation:cf-b 1.2s infinite ease-in-out; }
.cf-dots span:nth-child(2){ animation-delay:.15s; } .cf-dots span:nth-child(3){ animation-delay:.3s; }
@keyframes cf-b{ 0%,80%,100%{ transform:translateY(0); opacity:.4 } 40%{ transform:translateY(-6px); opacity:1 } }
.cf-err{ color:#8a4b1f; }

/* ================= CHAT INPUT ================= */
[data-testid="stBottom"], [data-testid="stBottom"]>div{ background:transparent !important; }
[data-testid="stChatInput"]{ max-width:980px; margin:0 auto; background:#fff !important; border:1px solid var(--cf-line); border-radius:22px;
  box-shadow:0 18px 40px -20px rgba(60,55,160,.35); padding:.2rem; transition:box-shadow .2s ease, border-color .2s ease; }
[data-testid="stChatInput"] > div{ border:0 !important; box-shadow:none !important; outline:0 !important; }
[data-testid="stChatInput"]:focus-within{ border-color:#9b86ff; box-shadow:0 0 0 4px rgba(124,92,255,.14), 0 18px 40px -20px rgba(60,55,160,.4); }
[data-testid="stChatInput"] div, [data-testid="stChatInput"] textarea{ background:transparent !important; }
[data-testid="stChatInput"] textarea{ font-size:.98rem; }
[data-testid="stChatInput"] button:disabled{ opacity:.45; }
.st-key-home_layout [data-testid="stChatInput"]{ max-width:none; margin-top:1.6rem; }
[data-testid="stChatInput"] button{ background:linear-gradient(135deg,#6a4cf6,#4a3fd6) !important; border-radius:14px !important; color:#fff !important; }
[data-testid="stChatInput"] button:hover{ filter:brightness(1.08); }


/* ================= READABILITY (independent of the viewer's light/dark system theme) ================= */
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"],
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] :is(p,li,ol,ul,div,td,th,blockquote,em){ color:#1f2347 !important; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] :is(h1,h2,h3,h4,h5,h6,strong,b){ color:#12163a !important; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] a{ color:#4a3fd6 !important; text-decoration:underline; text-underline-offset:2px; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] code{ color:#3b2fb8 !important; background:#f1efff !important; border-radius:6px; padding:.1rem .35rem; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] pre, [data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] pre code{ background:#f4f6fd !important; color:#1f2347 !important; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] table{ border-collapse:collapse; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] :is(td,th){ border:1px solid var(--cf-line); padding:.4rem .6rem; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] blockquote{ opacity:1 !important; border-left:3px solid #b9adff; background:#f8f7ff; padding:.4rem .9rem; border-radius:0 10px 10px 0; margin:.4rem 0 .8rem; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] blockquote *{ opacity:1 !important; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] .cf-cite{ color:#3f34c4 !important; background:#f1efff !important; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] .cf-cite i{ color:#6c67b8 !important; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] .cf-err{ color:#8a4b1f !important; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] .cf-think{ color:#6b7194 !important; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageContent"], [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageContent"] *{ color:#fff !important; }
[data-testid="stChatInput"] textarea{ color:#1f2347 !important; -webkit-text-fill-color:#1f2347; caret-color:#5b3df5; }
[data-testid="stChatInput"] textarea::placeholder{ color:#8a90b5 !important; -webkit-text-fill-color:#8a90b5; opacity:1; }
[data-testid="stMarkdownContainer"] .cf-hero, .cf-h1, .cf-top b{ color:var(--cf-ink); }
[class*="st-key-ex_"] .stButton>button, [class*="st-key-ex_"] .stButton>button p{ color:#2a2f55 !important; }
[class*="st-key-ex_"] .stButton>button:hover, [class*="st-key-ex_"] .stButton>button:hover p{ color:#1d2150 !important; }
[class*="st-key-ex_"] .stButton>button [data-testid="stIconMaterial"]{ color:#5b3df5 !important; }

/* ================= RESPONSIVE ================= */
@media (max-width:1100px){
  .cf-hero-grid{ grid-template-columns:1fr; } .cf-art{ display:none; } .cf-lead{ max-width:none; }
  .st-key-home_layout [data-testid="stHorizontalBlock"]:first-child{ flex-wrap:wrap; }
  .st-key-home_layout [data-testid="stHorizontalBlock"]:first-child>[data-testid="stColumn"]{ min-width:100% !important; }
}
@media (max-width:760px){
  .block-container{ padding:1rem 1rem 8rem 1rem !important; }
  .cf-props{ grid-template-columns:1fr; } .cf-hero{ padding:1.4rem 1.2rem; } .cf-top span{ display:none; }
  [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageContent"]{ max-width:85%; }
  [data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"]{ max-width:100%; }
  [data-testid="stChatMessage"] [data-testid^="stChatMessageAvatar"]{ display:none; }
}
@media (prefers-reduced-motion:reduce){ *{ animation:none !important; transition:none !important; } }
</style>
"""

LOGO_SVG = """
<svg width="52" height="52" viewBox="0 0 64 64" aria-hidden="true"><defs>
<linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#a855f7"/><stop offset="1" stop-color="#3b6cf6"/></linearGradient></defs>
<path d="M32 6C17 6 6 17 6 32s11 26 26 26c8 0 14-3 18-8l-9-7c-2 2-5 3-9 3-8 0-14-6-14-14s6-14 14-14c5 0 9 2 11 6l10-4C51 12 43 6 32 6z" fill="url(#lg)"/>
<path d="M34 30h24v6H46l-8 22-8-6 6-16h-2z" fill="url(#lg)" opacity=".92"/></svg>
"""

HERO_ART = """
<svg viewBox="0 0 440 300" aria-hidden="true"><defs>
<linearGradient id="scr" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1f2a86"/><stop offset="1" stop-color="#3a2fb8"/></linearGradient>
<linearGradient id="bs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e9ecf8"/><stop offset="1" stop-color="#c9cee6"/></linearGradient></defs>
<path d="M70 250c60-10 240-10 320 0l-20 14H90z" fill="#c9cee6" opacity=".6"/>
<path d="M120 60l190-14 30 150-215 20z" fill="url(#scr)" stroke="#dfe3f6" stroke-width="6" stroke-linejoin="round"/>
<text x="176" y="98" font-family="Georgia,serif" font-style="italic" font-size="22" fill="#f1f0ff" transform="rotate(-8 176 98)">Better</text>
<text x="166" y="124" font-family="Georgia,serif" font-style="italic" font-size="22" fill="#f1f0ff" transform="rotate(-8 166 124)">Skills</text>
<text x="176" y="150" font-family="Georgia,serif" font-style="italic" font-size="22" fill="#f1f0ff" transform="rotate(-8 176 150)">Bigger</text>
<text x="156" y="176" font-family="Georgia,serif" font-style="italic" font-size="22" fill="#f1f0ff" transform="rotate(-8 156 176)">Opportunities</text>
<path d="M92 214l248-20 40 26-250 26z" fill="url(#bs)" stroke="#bfc5e3"/>
<path d="M112 222l200-17 22 14-205 18z" fill="#aab1d6" opacity=".55"/>
<path d="M60 130c-18 6-30 26-22 44 6-16 18-28 34-32z" fill="#4fbf9f" opacity=".85"/>
<path d="M62 132c4-28 20-50 30-58 2 26-4 48-24 70z" fill="#38a88a"/>
<path d="M40 178h44l-5 34H46z" fill="#fff" stroke="#dfe3f6"/><circle cx="62" cy="194" r="9" fill="#8a5cf6"/>
</svg>
"""

LANDSCAPE_SVG = """
<svg class="land" viewBox="0 0 400 220" preserveAspectRatio="none" aria-hidden="true">
<path d="M0 150l60-50 45 35 70-70 85 80 60-40 80 60v55H0z" fill="#7a72c9" opacity=".65"/>
<path d="M0 175l70-45 60 40 90-60 80 55 100-30v85H0z" fill="#4e4aa8" opacity=".9"/>
<path d="M0 205l90-35 100 20 90-25 120 30v25H0z" fill="#262d76"/>
<g fill="#2a3170"><rect x="240" y="120" width="8" height="45"/><rect x="252" y="100" width="10" height="65"/><rect x="266" y="130" width="8" height="35"/></g>
<g><circle cx="332" cy="98" r="6" fill="#3a2f7a"/><path d="M322 106h20l4 34h-6l-2 22h-6l-1-16-1 16h-6l-2-22h-6z" fill="#3a2f7a"/><rect x="336" y="108" width="10" height="20" rx="3" fill="#e0558f"/></g>
</svg>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Backend (built once per server process; the SAME construction as main.main())
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner="Getting CareerForge ready...")
def load_backend():
    from config import LLM_MODEL, TOP_K, load_api_key
    from main import build_index
    from retrieval.vector_retriever import VectorRetriever
    from generation.generator import Generator

    api_key = load_api_key()
    embedder, store = build_index()
    retriever = VectorRetriever(embedder=embedder, store=store)
    generator = Generator(api_key=api_key, model=LLM_MODEL)
    return retriever, generator, TOP_K


def make_session() -> dict:
    """A fresh UI session with its OWN backend Conversation (own history)."""
    from generation.conversation import Conversation

    retriever, generator, top_k = load_backend()
    return {
        "id": uuid.uuid4().hex,
        "title": None,
        "messages": [],  # [{"role": "user"|"assistant", "content": str, "error": bool}]
        "busy": None,  # question currently being answered by this session's Conversation, if any
        "conv": Conversation(retriever=retriever, generator=generator, top_k=top_k),
    }


# --------------------------------------------------------------------------- #
# State helpers
# --------------------------------------------------------------------------- #
def active() -> dict:
    for s in st.session_state.sessions:
        if s["id"] == st.session_state.active_id:
            return s
    raise KeyError("no active session")


def cb_new_chat() -> None:
    """Open a brand-new, empty CHAT (not Home) with its own Conversation (shared cached backend)."""
    cur = active()
    fresh = make_session()
    # A chat that has messages -- or an answer still being generated -- is kept in history.
    if cur["messages"] or cur["busy"]:
        st.session_state.sessions.append(fresh)
    else:
        # Current chat is empty: swap it for a clean one instead of piling up empty sessions.
        # A NEW object (not a reset) so a stale, still-running answer can never land in it.
        st.session_state.sessions = [fresh if x is cur else x for x in st.session_state.sessions]
    st.session_state.active_id = fresh["id"]
    st.session_state.page = "chat"
    st.session_state.show_history = False
    st.session_state.pending = None


def cb_home() -> None:
    st.session_state.page = "home"
    st.session_state.show_history = False


def cb_toggle_history() -> None:
    st.session_state.show_history = not st.session_state.show_history


def cb_open(session_id: str) -> None:
    st.session_state.active_id = session_id
    st.session_state.page = "chat"
    st.session_state.pending = None


def route_question(question: str) -> None:
    """A question asked from Home (example card or Home input) always opens a chat.

    If the active session already has a conversation, start a fresh one -- otherwise the
    question would silently continue an old chat the user is not looking at.
    """
    cur = active()
    if cur["messages"] or cur["busy"]:
        fresh = make_session()
        st.session_state.sessions.append(fresh)
        st.session_state.active_id = fresh["id"]
    st.session_state.page = "chat"
    st.session_state.pending = question


def cb_ask(question: str) -> None:
    route_question(question)


def short_title(text: str, n: int = 38) -> str:
    t = re.sub(r"[*_`#\[\]<>]", "", text).strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "..."


# --------------------------------------------------------------------------- #
# Answer rendering: citations -> subtle source chips (text is NOT altered)
# --------------------------------------------------------------------------- #
_CITE = re.compile(r"\[Source:\s*(?P<title>[^,]+),\s*(?P<lab>Pages?)\s*(?P<a>\d+)(?:-(?P<b>\d+))?\]")


def render_answer(text: str) -> str:
    out, last = [], 0
    for m in _CITE.finditer(text):
        out.append(text[last:m.start()].replace("<", "&lt;"))
        pages = m.group("a") + (f"-{m.group('b')}" if m.group("b") else "")
        out.append(
            f'<span class="cf-cite">{html.escape(m.group("title").strip())}'
            f'<i>{html.escape(m.group("lab"))} {pages}</i></span>'
        )
        last = m.end()
    out.append(text[last:].replace("<", "&lt;"))
    return "".join(out)


THINKING = '<div class="cf-think"><span class="cf-dots"><span></span><span></span><span></span></span>Thinking...</div>'


def show_message(msg: dict) -> None:
    if msg["role"] == "user":
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar=":material/auto_awesome:"):
            if msg.get("error"):
                st.markdown(f'<span class="cf-err">{html.escape(msg["content"])}</span>', unsafe_allow_html=True)
            else:
                st.markdown(render_answer(msg["content"]), unsafe_allow_html=True)


def answer_question(sess: dict, question: str) -> None:
    """Send the question through the existing Conversation.ask()."""
    user_msg = {"role": "user", "content": question}
    show_message(user_msg)
    sess["busy"] = question

    with st.chat_message("assistant", avatar=":material/auto_awesome:"):
        slot = st.empty()
        slot.markdown(THINKING, unsafe_allow_html=True)
        try:
            turn = sess["conv"].ask(question)
            reply = {"role": "assistant", "content": turn.answer, "error": False}
        except Exception:  # UI boundary: never leak internals to the client
            log.exception("Conversation.ask failed")
            reply = {"role": "assistant", "content": FRIENDLY_ERROR, "error": True}
        # Commit the question and its reply together, BEFORE any further Streamlit call.
        # If the user clicked New Chat while this was running, Streamlit stops this script at
        # the next st.* call -- so the session can never keep a question without its answer,
        # and the UI stays in step with the Conversation's own history.
        sess["messages"] += [user_msg, reply]
        if sess["title"] is None:
            sess["title"] = short_title(question)
        sess["busy"] = None
        if reply["error"]:
            slot.markdown(f'<span class="cf-err">{html.escape(reply["content"])}</span>', unsafe_allow_html=True)
        else:
            slot.markdown(render_answer(reply["content"]), unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Layout pieces
# --------------------------------------------------------------------------- #
def sidebar(page: str, chat_is_empty: bool) -> None:
    with st.sidebar:
        st.markdown(
            f'<div class="cf-brand">{LOGO_SVG}<div><div class="cf-wordmark">Career<b>Forge</b></div>'
            f'<div class="cf-tag">Your Career, Our Knowledge</div></div></div>',
            unsafe_allow_html=True,
        )
        st.button("Home", key="nav_home", icon=":material/home:", on_click=cb_home,
                  type="primary" if page == "home" else "secondary", use_container_width=True)
        st.button("New Chat", key="nav_new", icon=":material/chat_bubble:", on_click=cb_new_chat,
                  type="primary" if (page == "chat" and chat_is_empty) else "secondary", use_container_width=True)
        st.button("Chat History", key="nav_hist", icon=":material/history:", on_click=cb_toggle_history,
                  type="primary" if st.session_state.show_history else "secondary", use_container_width=True)

        if st.session_state.show_history:
            with st.container(key="hist_list"):
                past = [s for s in st.session_state.sessions if s["messages"]]
                if not past:
                    st.markdown('<p style="font-size:.85rem;color:#aab2e6;padding:.2rem 1rem;">No conversations yet.</p>',
                                unsafe_allow_html=True)
                for i, s in enumerate(reversed(past[-10:])):
                    st.button(s["title"] or "Conversation", key=f"hist_{i}", on_click=cb_open, args=(s["id"],),
                              use_container_width=True)

        st.markdown('<div class="cf-rule"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="cf-side-promo">{icon("spark", 30)}<h4>Better Questions<br>Brighter Opportunities</h4>'
            f'<p>Get practical career guidance and clear next steps to build the future you want.</p></div>'
            f'<div class="cf-profile"><div class="cf-avatar">C</div><div><b>Career Assistant</b>'
            f'<span>Always here for you</span></div></div>',
            unsafe_allow_html=True,
        )


def top_bar() -> None:
    st.markdown(
        f'<div class="cf-top"><div class="ic">{icon("spark", 18)}</div><b>Smart Career Guidance</b>'
        f'<span>Ask anything about your career journey...</span></div>',
        unsafe_allow_html=True,
    )


def hero() -> None:
    props = [("layers", "Focused Guidance", "Answers with sources"),
             ("bulb", "Practical Advice", "Clear, usable next steps"),
             ("target", "Your Goals", "Your priority")]
    p = "".join(
        f'<div class="cf-prop"><div class="ic">{icon(i, 22)}</div><div><b>{t}</b><span>{d}</span></div></div>'
        for i, t, d in props
    )
    st.markdown(
        f'<div class="cf-hero"><div class="cf-hero-grid"><div>'
        f'<div class="cf-pill">{icon("spark")}AI CAREER ASSISTANT</div>'
        f'<h1 class="cf-h1">Welcome to<br><em>CareerForge</em></h1>'
        f'<p class="cf-lead">Get practical, focused guidance for your resume, interviews, career growth, and more.</p>'
        f'</div><div class="cf-art">{HERO_ART}</div></div><div class="cf-props">{p}</div></div>',
        unsafe_allow_html=True,
    )


def examples() -> None:
    st.markdown(f'<div class="cf-section">{icon("spark", 20)}Try asking about...</div>', unsafe_allow_html=True)
    for row in range(0, len(EXAMPLES), 2):
        cols = st.columns(2, gap="medium")
        for col, (ic, q) in zip(cols, EXAMPLES[row:row + 2]):
            with col:
                st.button(q, key=f"ex_{row}_{ic}", icon=f":material/{ic}:", on_click=cb_ask, args=(q,),
                          use_container_width=True)


def right_rail() -> None:
    tips = [("Be specific in your questions", "The more details, the better advice."),
            ("Ask about your unique situation", "Get guidance that fits you."),
            ("Explore different perspectives", "Build a well-rounded view.")]
    t = "".join(f'<div class="cf-tip"><div class="ck">{icon("check")}</div><div><b>{a}</b><span>{b}</span></div></div>'
                for a, b in tips)
    st.markdown(
        f'<div class="cf-quote"><div class="q">&ldquo;</div>'
        f'<h3>The right guidance today can lead to your <em>dream career</em> tomorrow.</h3>'
        f'<p>Your goals.<br>Our mission.</p>{LANDSCAPE_SVG}</div>'
        f'<div class="cf-tips"><div class="cf-tips-h"><div class="ic">{icon("bulb", 20)}</div>Quick Tips</div>{t}</div>'
        f'<div class="cf-cta"><div class="ic">{icon("rocket", 24)}</div><div><b>Ready to take the next step?</b>'
        f'<span>Ask your first question below.</span></div><div class="go">{icon("down", 20)}</div></div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    inject_css()

    try:
        if "sessions" not in st.session_state:
            first = make_session()
            st.session_state.sessions = [first]
            st.session_state.active_id = first["id"]
            st.session_state.show_history = False
            st.session_state.pending = None
            st.session_state.page = "home"  # "home" = landing page, "chat" = a conversation (may be empty)
    except Exception:
        log.exception("Backend initialisation failed")
        st.markdown(f'<div class="cf-top"><b>CareerForge</b><span>{html.escape(UNAVAILABLE)}</span></div>',
                    unsafe_allow_html=True)
        st.stop()

    sess = active()
    pending = st.session_state.pending
    st.session_state.pending = None
    page = st.session_state.page  # explicit navigation state -- NOT inferred from messages

    sidebar(page=page, chat_is_empty=not sess["messages"])
    top_bar()

    if page == "chat":
        # Pinned to the bottom of the page while in a conversation (new/empty ones included).
        prompt = st.chat_input(PLACEHOLDER)
        if prompt and prompt.strip():
            pending = prompt.strip()
        if not sess["messages"] and not pending:
            st.markdown(
                f'<div class="cf-chat-head">{icon("spark", 18)}New conversation &middot; '
                f'ask CareerForge anything about your career below.</div>',
                unsafe_allow_html=True,
            )
        for m in sess["messages"]:
            show_message(m)
        if pending:
            answer_question(sess, pending)
    else:
        with st.container(key="home_layout"):
            left, right = st.columns([3.1, 1.15], gap="large")
            with left:
                hero()
                examples()
                # Inline on the welcome screen (matches the reference layout).
                prompt = st.chat_input(PLACEHOLDER)
                if prompt and prompt.strip():
                    route_question(prompt.strip())
                    st.rerun()
            with right:
                right_rail()


main()
