# 🌍 US Travel Advisory App

A Streamlit app that displays US State Department travel advisory levels for every country in the world — updated automatically from the official RSS feed.

## Features
- ✅ Live data from `travel.state.gov` official RSS feed
- ✅ Countries grouped by Level 1–4 (same as travelmaps.state.gov)
- ✅ Auto-refreshes every hour (cached)
- ✅ Filter by region, level, and search by country name
- ✅ Sort by name, level, or recency
- ✅ Tap "Details →" to go directly to the State Dept page
- ✅ iOS-inspired clean design, mobile-friendly

## Advisory Levels
| Level | Label | Color |
|-------|-------|-------|
| 1 | Exercise Normal Precautions | 🟢 Green |
| 2 | Exercise Increased Caution | 🟡 Yellow |
| 3 | Reconsider Travel | 🔴 Red |
| 4 | Do Not Travel | ⛔ Dark Red |

## Setup & Run Locally

```bash
# 1. Clone / download the files
# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

Then open http://localhost:8501 in your browser (works great on mobile too).

## Deploy to Streamlit Community Cloud (free)

1. Push this folder to a GitHub repo
2. Go to https://share.streamlit.io
3. Click **New app** → select your repo → set `app.py` as the main file
4. Click **Deploy** — done! Public URL generated automatically.

## Deploy to Other Platforms

**Heroku / Railway / Render:**
Add a `Procfile`:
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

**Docker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

## Data Source
Official RSS feed: https://travel.state.gov/_res/rss/TAsTWs.xml

Data is cached for 1 hour. Use the sidebar "Force refresh" button to reload immediately.

## Use on iPhone
Once deployed, open the URL in Safari → tap the Share button → **Add to Home Screen**.
You'll get a native app icon that opens the site full-screen like a real iOS app.
