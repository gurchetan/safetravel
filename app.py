import streamlit as st
import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone
import time

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
RSS_URL = "https://travel.state.gov/_res/rss/TAsTWs.xml"
CACHE_TTL = 3600  # 1 hour

LEVEL_CONFIG = {
    1: {
        "label": "Exercise Normal Precautions",
        "short": "Normal",
        "color": "#4CAF50",
        "bg": "#E8F5E9",
        "border": "#A5D6A7",
        "emoji": "🟢",
        "icon": "✈️",
    },
    2: {
        "label": "Exercise Increased Caution",
        "short": "Caution",
        "color": "#FF9800",
        "bg": "#FFF3E0",
        "border": "#FFCC80",
        "emoji": "🟡",
        "icon": "⚠️",
    },
    3: {
        "label": "Reconsider Travel",
        "short": "Reconsider",
        "color": "#F44336",
        "bg": "#FFEBEE",
        "border": "#EF9A9A",
        "emoji": "🔴",
        "icon": "🚫",
    },
    4: {
        "label": "Do Not Travel",
        "short": "Do Not Travel",
        "color": "#B71C1C",
        "bg": "#FCE4EC",
        "border": "#EF9A9A",
        "emoji": "⛔",
        "icon": "🚷",
    },
}

REGIONS = {
    "Africa": [
        "Algeria","Angola","Benin","Botswana","Burkina Faso","Burundi","Cabo Verde",
        "Cameroon","Central African Republic","Chad","Comoros","Congo","Côte d'Ivoire",
        "Democratic Republic of the Congo","Djibouti","Egypt","Equatorial Guinea",
        "Eritrea","Eswatini","Ethiopia","Gabon","Gambia","Ghana","Guinea",
        "Guinea-Bissau","Kenya","Lesotho","Liberia","Libya","Madagascar","Malawi",
        "Mali","Mauritania","Mauritius","Morocco","Mozambique","Namibia","Niger",
        "Nigeria","Rwanda","São Tomé and Príncipe","Senegal","Seychelles","Sierra Leone",
        "Somalia","South Africa","South Sudan","Sudan","Tanzania","Togo","Tunisia",
        "Uganda","Zambia","Zimbabwe",
    ],
    "Americas": [
        "Antigua and Barbuda","Argentina","Bahamas","Barbados","Belize","Bolivia",
        "Brazil","Canada","Chile","Colombia","Costa Rica","Cuba","Dominica",
        "Dominican Republic","Ecuador","El Salvador","Grenada","Guatemala","Guyana",
        "Haiti","Honduras","Jamaica","Mexico","Nicaragua","Panama","Paraguay","Peru",
        "Saint Kitts and Nevis","Saint Lucia","Saint Vincent and the Grenadines",
        "Suriname","Trinidad and Tobago","Uruguay","Venezuela",
    ],
    "East Asia & Pacific": [
        "Australia","Brunei","Burma (Myanmar)","Cambodia","China","Fiji","Indonesia",
        "Japan","Kiribati","Laos","Malaysia","Marshall Islands","Micronesia","Mongolia",
        "Nauru","New Zealand","North Korea","Palau","Papua New Guinea","Philippines",
        "Samoa","Singapore","Solomon Islands","South Korea","Taiwan","Thailand","Timor-Leste",
        "Tonga","Tuvalu","Vanuatu","Vietnam",
    ],
    "Europe & Eurasia": [
        "Albania","Andorra","Armenia","Austria","Azerbaijan","Belarus","Belgium",
        "Bosnia and Herzegovina","Bulgaria","Croatia","Cyprus","Czech Republic",
        "Denmark","Estonia","Finland","France","Georgia","Germany","Greece","Hungary",
        "Iceland","Ireland","Italy","Kazakhstan","Kosovo","Kyrgyzstan","Latvia",
        "Liechtenstein","Lithuania","Luxembourg","Malta","Moldova","Monaco","Montenegro",
        "Netherlands","North Macedonia","Norway","Poland","Portugal","Romania","Russia",
        "San Marino","Serbia","Slovakia","Slovenia","Spain","Sweden","Switzerland",
        "Tajikistan","Turkmenistan","Ukraine","United Kingdom","Uzbekistan","Vatican City",
    ],
    "Middle East & North Africa": [
        "Bahrain","Iran","Iraq","Israel","Jordan","Kuwait","Lebanon","Libya","Morocco",
        "Oman","Qatar","Saudi Arabia","Syria","Tunisia","United Arab Emirates","West Bank and Gaza","Yemen",
    ],
    "South & Central Asia": [
        "Afghanistan","Bangladesh","Bhutan","India","Maldives","Nepal","Pakistan","Sri Lanka",
    ],
}


# ──────────────────────────────────────────────
# DATA FETCHING
# ──────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def fetch_advisories():
    """Fetch and parse the State Dept RSS feed."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TravelAdvisoryApp/1.0)"}
    resp = requests.get(RSS_URL, headers=headers, timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    ns = {"media": "http://search.yahoo.com/mrss/"}

    advisories = {}
    last_updated = None

    channel = root.find("channel")
    if channel is not None:
        pub_date_el = channel.find("lastBuildDate") or channel.find("pubDate")
        if pub_date_el is not None and pub_date_el.text:
            last_updated = pub_date_el.text.strip()

    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        pub_el = item.find("pubDate")

        if title_el is None or title_el.text is None:
            continue

        title = title_el.text.strip()
        # Parse: "Country Name - Level X: Description"
        match = re.match(
            r"^(.+?)\s*[-–]\s*Level\s*(\d)\s*[:\-–]?\s*(.*)?$",
            title,
            re.IGNORECASE,
        )
        if not match:
            continue

        country = match.group(1).strip()
        level = int(match.group(2))
        summary = match.group(3).strip() if match.group(3) else ""

        if level not in (1, 2, 3, 4):
            continue

        pub_date = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else "#"

        # Clean description HTML
        raw_desc = desc_el.text if desc_el is not None else ""
        clean_desc = re.sub(r"<[^>]+>", " ", raw_desc or "").strip()
        clean_desc = re.sub(r"\s+", " ", clean_desc)

        advisories[country] = {
            "country": country,
            "level": level,
            "summary": summary,
            "description": clean_desc[:400] + ("…" if len(clean_desc) > 400 else ""),
            "pub_date": pub_date,
            "link": link,
        }

    return advisories, last_updated


def get_region(country_name: str) -> str:
    for region, countries in REGIONS.items():
        for c in countries:
            if c.lower() == country_name.lower():
                return region
    return "Other"


# ──────────────────────────────────────────────
# PAGE SETUP
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="US Travel Advisories",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# CUSTOM CSS  (iOS-inspired clean look)
# ──────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

/* Reset & base */
* { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
    background: #F2F2F7;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1rem 1rem 3rem 1rem !important; max-width: 960px; margin: 0 auto; }

/* Top header bar */
.app-header {
    background: rgba(255,255,255,0.85);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 20px;
    padding: 20px 24px 16px;
    margin-bottom: 20px;
    border: 1px solid rgba(0,0,0,0.06);
    box-shadow: 0 2px 20px rgba(0,0,0,0.06);
}
.app-title {
    font-size: 28px;
    font-weight: 700;
    color: #1C1C1E;
    letter-spacing: -0.5px;
    margin: 0 0 4px;
}
.app-subtitle {
    font-size: 13px;
    color: #8E8E93;
    margin: 0 0 12px;
}
.app-updated {
    font-size: 11px;
    color: #AEAEB2;
    margin: 0;
}

/* Level banner cards */
.level-banner {
    border-radius: 16px;
    padding: 14px 18px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    border: 1.5px solid;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
}
.level-banner:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(0,0,0,0.1); }
.level-number {
    width: 36px; height: 36px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 17px; font-weight: 700; color: white;
    flex-shrink: 0;
}
.level-info { flex: 1; }
.level-title { font-size: 15px; font-weight: 600; color: #1C1C1E; margin: 0 0 2px; }
.level-count { font-size: 12px; color: #8E8E93; margin: 0; }
.level-chevron { color: #C7C7CC; font-size: 14px; }

/* Country cards */
.country-card {
    background: white;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 8px;
    border: 1px solid rgba(0,0,0,0.07);
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
    display: flex;
    align-items: flex-start;
    gap: 12px;
    transition: box-shadow 0.15s ease;
}
.country-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
.country-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    margin-top: 5px;
    flex-shrink: 0;
}
.country-body { flex: 1; min-width: 0; }
.country-name { font-size: 15px; font-weight: 600; color: #1C1C1E; margin: 0 0 3px; }
.country-region { font-size: 11px; color: #AEAEB2; margin: 0 0 4px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.4px; }
.country-desc { font-size: 13px; color: #636366; margin: 0; line-height: 1.4; }
.country-link {
    font-size: 12px; color: #007AFF; text-decoration: none;
    font-weight: 500; flex-shrink: 0; margin-top: 3px;
}
.country-link:hover { text-decoration: underline; }


/* Search bar */
.stTextInput input {
    border-radius: 12px !important;
    border: 1px solid rgba(0,0,0,0.12) !important;
    background: white !important;
    padding: 10px 16px !important;
    font-size: 15px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    /* Force text color to black */
    color: #1C1C1E !important; 
    -webkit-text-fill-color: #1C1C1E !important;
}

/* Ensure placeholder text remains visible but light */
.stTextInput input::placeholder {
    color: #8E8E93 !important;
    -webkit-text-fill-color: #8E8E93 !important;
}

/* Section header */
.section-header {
    font-size: 13px;
    font-weight: 600;
    color: #8E8E93;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin: 20px 0 10px;
    padding-left: 4px;
}

/* Stats row */
.stats-row {
    display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;
}
.stat-pill {
    background: white;
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    color: #1C1C1E;
    border: 1px solid rgba(0,0,0,0.08);
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    display: flex; align-items: center; gap: 6px;
}

/* Spinner override */
.stSpinner > div { color: #007AFF !important; }

/* Select boxes */
.stSelectbox select, .stMultiSelect div {
    border-radius: 12px !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: white !important;
    border-radius: 14px !important;
    border: 1px solid rgba(0,0,0,0.07) !important;
    font-weight: 600 !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────
# LOAD DATA
# ──────────────────────────────────────────────
with st.spinner("Fetching latest travel advisories…"):
    try:
        advisories, last_updated = fetch_advisories()
        data_ok = True
    except Exception as e:
        st.error(f"⚠️ Could not load data: {e}")
        advisories, last_updated = {}, None
        data_ok = False

# ──────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────
updated_str = ""
if last_updated:
    updated_str = f"Feed updated: {last_updated}"
else:
    updated_str = f"Loaded: {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')}"

st.markdown(
    f"""
<div class="app-header">
  <div class="app-title">🌍 US Travel Advisories</div>
  <div class="app-subtitle">U.S. Department of State · Official advisory levels for every country</div>
  <div class="app-updated">{updated_str}</div>
</div>
""",
    unsafe_allow_html=True,
)

if not data_ok or not advisories:
    st.warning("No advisory data available. Please try again later.")
    st.stop()

# ──────────────────────────────────────────────
# SIDEBAR FILTERS
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔧 Filters")
    selected_levels = st.multiselect(
        "Advisory Levels",
        options=[1, 2, 3, 4],
        default=[1, 2, 3, 4],
        format_func=lambda x: f"Level {x} – {LEVEL_CONFIG[x]['short']}",
    )

    region_options = ["All Regions"] + sorted(REGIONS.keys()) + ["Other"]
    selected_region = st.selectbox("Region", region_options)

    sort_by = st.radio(
        "Sort countries by",
        ["Country Name (A–Z)", "Level (highest first)", "Level (lowest first)", "Most Recently Updated"],
    )

    st.markdown("---")
    st.markdown(
        "**Source:** [travel.state.gov](https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html/)",
        unsafe_allow_html=True,
    )
    st.markdown("Data refreshes every hour.")
    if st.button("🔄 Force refresh"):
        st.cache_data.clear()
        st.rerun()

# ──────────────────────────────────────────────
# SEARCH
# ──────────────────────────────────────────────
search = st.text_input("🔍  Search country…", placeholder="e.g. Japan, Brazil, France…", label_visibility="collapsed")

# ──────────────────────────────────────────────
# FILTER & SORT DATA
# ──────────────────────────────────────────────
all_items = list(advisories.values())

# Enrich with region
for item in all_items:
    item["region"] = get_region(item["country"])

# Filter
filtered = [
    a for a in all_items
    if a["level"] in selected_levels
    and (selected_region == "All Regions" or a["region"] == selected_region)
    and (not search or search.lower() in a["country"].lower())
]

# Sort
if sort_by == "Country Name (A–Z)":
    filtered.sort(key=lambda x: x["country"])
elif sort_by == "Level (highest first)":
    filtered.sort(key=lambda x: (-x["level"], x["country"]))
elif sort_by == "Level (lowest first)":
    filtered.sort(key=lambda x: (x["level"], x["country"]))
elif sort_by == "Most Recently Updated":
    filtered.sort(key=lambda x: x["pub_date"], reverse=True)

# ──────────────────────────────────────────────
# STATS ROW
# ──────────────────────────────────────────────
counts = {1: 0, 2: 0, 3: 0, 4: 0}
for a in all_items:
    counts[a["level"]] = counts.get(a["level"], 0) + 1

pills_html = '<div class="stats-row">'
pills_html += f'<div class="stat-pill">🌐 <b>{len(all_items)}</b> countries</div>'
for lvl, cfg in LEVEL_CONFIG.items():
    pills_html += (
        f'<div class="stat-pill" style="border-left: 3px solid {cfg["color"]}">'
        f'{cfg["emoji"]} <b>{counts.get(lvl, 0)}</b> Level {lvl}'
        f"</div>"
    )
pills_html += "</div>"
st.markdown(pills_html, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# RESULTS COUNT
# ──────────────────────────────────────────────
if search or selected_region != "All Regions" or selected_levels != [1, 2, 3, 4]:
    st.markdown(
        f'<div style="font-size:13px;color:#8E8E93;margin-bottom:12px;">Showing <b>{len(filtered)}</b> of {len(all_items)} countries</div>',
        unsafe_allow_html=True,
    )

# ──────────────────────────────────────────────
# DISPLAY: Grouped by Level
# ──────────────────────────────────────────────
if not filtered:
    st.info("No countries match your filters.")
else:
    grouped = {1: [], 2: [], 3: [], 4: []}
    for a in filtered:
        grouped[a["level"]].append(a)

    for level in [1, 2, 3, 4]:
        group = grouped[level]
        if not group:
            continue

        cfg = LEVEL_CONFIG[level]

        with st.expander(
            f"{cfg['emoji']}  Level {level} — {cfg['label']}  ({len(group)} countries)",
            expanded=False,
        ):
            # Country cards
            cards_html = ""
            for a in group:
                dot_color = cfg["color"]
                cards_html += f"""
<div class="country-card">
  <div class="country-dot" style="background:{dot_color}"></div>
  <div class="country-body">
    <div class="country-name">{a['country']}</div>
    <div class="country-region">{a['region']}</div>
    <div class="country-desc">{a['description'] or a['summary']}</div>
  </div>
  <a class="country-link" href="{a['link']}" target="_blank">Details →</a>
</div>
"""
            st.markdown(cards_html, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# INTERACTIVE MAP (State Dept travelmaps.state.gov)
# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# INTERACTIVE MAP — full viewport, desktop only
# ──────────────────────────────────────────────
st.markdown(
    """
<style>
/* Desktop-only full-viewport map wrapper */
@media (min-width: 768px) {
    .map-section {
        display: block;
        position: relative;
        left: 50%;
        right: 50%;
        margin-left: -50vw;
        margin-right: -50vw;
        width: 100vw;
        height: 100vh;
        margin-top: 32px;
        margin-bottom: 0;
    }
    .map-label {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 600;
        color: #8E8E93;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        padding: 0 0 10px 4px;
        margin-top: 28px;
    }
    .map-iframe {
        width: 100%;
        height: 100%;
        border: none;
        display: block;
    }
}
/* Hide map entirely on mobile */
@media (max-width: 767px) {
    .map-section { display: none !important; }
    .map-label   { display: none !important; }
}
</style>

<div class="map-label">&#x1F5FA;&#xFE0F;&nbsp; Interactive Advisory Map &mdash; travelmaps.state.gov</div>
<div class="map-section">
  <iframe
    class="map-iframe"
    src="https://travelmaps.state.gov/TSGMap/"
    allowfullscreen
    loading="lazy">
  </iframe>
</div>
""",
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────
# DONATION + FOOTER
# ──────────────────────────────────────────────

# Inject CSS separately — no HTML comments in this block
st.markdown(
    """
<style>
.donate-card {
    background: linear-gradient(135deg, #1C1C1E 0%, #2C2C2E 100%);
    border-radius: 20px;
    padding: 28px 24px 24px;
    margin: 32px 0 20px;
    text-align: center;
    box-shadow: 0 8px 32px rgba(0,0,0,0.18);
    position: relative;
    overflow: hidden;
}
.donate-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #007AFF, #5AC8FA, #34C759, #FF9F0A, #FF375F);
}
.donate-title {
    font-size: 20px; font-weight: 700; color: #FFFFFF;
    margin: 0 0 6px; letter-spacing: -0.3px;
}
.donate-subtitle {
    font-size: 13px; color: #8E8E93; margin: 0 0 22px; line-height: 1.5;
}
.donate-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 10px;
    margin-bottom: 4px;
}
.donate-btn {
    display: flex; align-items: center; justify-content: center; gap: 7px;
    padding: 12px 10px;
    border-radius: 12px;
    text-decoration: none !important;
    font-size: 13px; font-weight: 600;
    transition: transform 0.12s ease, box-shadow 0.12s ease;
    cursor: pointer;
    border: none; outline: none;
}
.donate-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.3); }
.donate-btn:active { transform: translateY(0); }
.btn-paypal  { background: #003087; color: #fff; }
.btn-stripe  { background: #635BFF; color: #fff; }
.btn-cashapp { background: #00D632; color: #fff; }
.btn-venmo   { background: #3D95CE; color: #fff; }
.btn-apple   { background: #fff;    color: #000; }
.btn-zelle   { background: #6D1ED4; color: #fff; }
.btn-icon { font-size: 16px; flex-shrink: 0; }
.creator-bar {
    display: flex; align-items: center; justify-content: center; gap: 8px;
    background: white;
    border-radius: 14px;
    padding: 12px 20px;
    margin-bottom: 16px;
    border: 1px solid rgba(0,0,0,0.07);
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
}
.creator-avatar {
    width: 34px; height: 34px;
    border-radius: 50%;
    background: linear-gradient(135deg, #007AFF, #5AC8FA);
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; font-weight: 700; color: white;
    flex-shrink: 0;
}
.creator-text { text-align: left; }
.creator-name { font-size: 14px; font-weight: 600; color: #1C1C1E; margin: 0 0 1px; }
.creator-role { font-size: 11px; color: #8E8E93; margin: 0; }
.footer-note {
    text-align: center; color: #AEAEB2; font-size: 11px;
    margin-top: 20px; padding-top: 14px;
    border-top: 1px solid rgba(0,0,0,0.06);
    line-height: 1.7;
}
</style>
""",
    unsafe_allow_html=True,
)

# Creator credit — rendered separately from the CSS block
st.markdown(
    """
<div class="creator-bar">
  <div class="creator-avatar">G</div>
  <div class="creator-text">
    <div class="creator-name">Gurchetan Singh</div>
    <div class="creator-role">Created this app &middot; US Travel Advisory Tracker</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Donation card — no HTML comments, properly closed divs
st.markdown(
    """
<div class="donate-card">
  <div class="donate-title">&#9749; Support This App</div>
  <div class="donate-subtitle">
    Built and maintained by Gurchetan Singh.<br>
    If this tool helped your travel planning, consider buying me a coffee!
  </div>
  <div class="donate-grid">
    <a class="donate-btn btn-paypal"
       href="https://www.paypal.com/donate/?business=456SKVHVRT29N&no_recurring=0&item_name=Thank+you+for+your+support+&currency_code=USD"
       target="_blank" rel="noopener">
      <span class="btn-icon">&#x1F1F5;</span> PayPal
    </a>
    <a class="donate-btn btn-stripe"
       href="https://buy.stripe.com/YOUR_STRIPE_LINK"
       target="_blank" rel="noopener">
      <span class="btn-icon">&#x1F4B3;</span> Card / Stripe
    </a>
    <a class="donate-btn btn-cashapp"
       href="https://cash.app/$gurchetan"
       target="_blank" rel="noopener">
      <span class="btn-icon">&#x1F4B5;</span> Cash App
    </a>
    <a class="donate-btn btn-venmo"
       href="https://venmo.com/GurchetanSingh"
       target="_blank" rel="noopener">
      <span class="btn-icon">&#x270C;&#xFE0F;</span> Venmo
    </a>
    <a class="donate-btn btn-apple"
       href="https://buy.stripe.com/YOUR_STRIPE_LINK"
       target="_blank" rel="noopener">
      <span class="btn-icon">&#xF8FF;</span> Apple Pay
    </a>
    <a class="donate-btn btn-zelle"
       href="https://enroll.zellepay.com/qr-codes?data=eyJuYW1lIjoiR1VSQ0hFVEFOIiwiYWN0aW9uIjoicGF5bWVudCIsInRva2VuIjoiMzYwMjI0NTk2MCJ9"
       target="_blank" rel="noopener">
      <span class="btn-icon">&#x26A1;</span> Zelle
    </a>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Footer note — separate block
st.markdown(
    """
<div class="footer-note">
  Data sourced from the
  <a href="https://travel.state.gov" target="_blank" style="color:#007AFF">U.S. Department of State</a>.<br>
  For informational purposes only. Always verify with official sources before travel.
</div>
""",
    unsafe_allow_html=True,
)
