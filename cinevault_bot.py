import os
import json
import time
import random
import logging
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

# ============================================================
#  ██████╗██╗███╗   ██╗███████╗██╗   ██╗ █████╗ ██╗   ██╗██╗  ████████╗
# ██╔════╝██║████╗  ██║██╔════╝██║   ██║██╔══██╗██║   ██║██║  ╚══██╔══╝
# ██║     ██║██╔██╗ ██║█████╗  ██║   ██║███████║██║   ██║██║     ██║
# ██║     ██║██║╚██╗██║██╔══╝  ╚██╗ ██╔╝██╔══██║██║   ██║██║     ██║
# ╚██████╗██║██║ ╚████║███████╗ ╚████╔╝ ██║  ██║╚██████╔╝███████╗██║
#  ╚═════╝╚═╝╚═╝  ╚═══╝╚══════╝  ╚═══╝  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝
#  theynevertoldus Facebook Page Bot  v2.0  — Professional Edition
# ============================================================

load_dotenv()

TMDB_API_KEY    = os.getenv("TMDB_API_KEY")
FB_PAGE_ID      = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
PAGE_NAME       = os.getenv("PAGE_NAME", "theynevertoldus")
PAGE_HANDLE     = os.getenv("PAGE_HANDLE", "@theynevertoldusOfficial")
TIMEZONE        = os.getenv("TIMEZONE", "Africa/Blantyre")
TEST_MODE       = os.getenv("TEST_MODE", "false").lower() == "true"

BASE_DIR   = Path(__file__).parent
STATE_FILE = BASE_DIR / "state.json"
LOG_FILE   = BASE_DIR / "theynevertoldus.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger("theynevertoldus")

TMDB_BASE   = "https://api.themoviedb.org/3"
TMDB_IMG_HD = "https://image.tmdb.org/t/p/w1280"
FB_GRAPH    = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}"
TMDB_MOVIE  = "https://www.themoviedb.org/movie"
TMDB_TV     = "https://www.themoviedb.org/tv"

WEEKLY_PLAN = {
    0: {"label": "Trending Movies",       "fetch": "fetch_trending_movies"},
    1: {"label": "Trending Series",       "fetch": "fetch_trending_series"},
    2: {"label": "Top Rated Movies",      "fetch": "fetch_top_rated_movies"},
    3: {"label": "New Releases",          "fetch": "fetch_new_releases"},
    4: {"label": "Genre Spotlight",       "fetch": "fetch_genre_spotlight"},
    5: {"label": "Throwback Classics",    "fetch": "fetch_classics"},
    6: {"label": "Anime & Documentaries", "fetch": "fetch_anime_or_docs"},
}

GENRE_ROTATION = [
    {"id": 28,    "name": "Action"},
    {"id": 27,    "name": "Horror"},
    {"id": 35,    "name": "Comedy"},
    {"id": 53,    "name": "Thriller"},
    {"id": 878,   "name": "Sci-Fi"},
    {"id": 10749, "name": "Romance"},
    {"id": 80,    "name": "Crime"},
    {"id": 12,    "name": "Adventure"},
]

POST_TIMES = [
    "07:00", "09:00", "11:00", "13:00",
    "15:00", "17:00", "19:00", "21:00"
]

# ─── PERSISTENT STATE ────────────────────────────────────────

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                return {
                    "posted_ids":    set(data.get("posted_ids", [])),
                    "genre_index":   data.get("genre_index", 0),
                    "sunday_toggle": data.get("sunday_toggle", True),
                    "total_posts":   data.get("total_posts", 0),
                }
        except Exception as e:
            log.warning(f"Could not load state file: {e}. Starting fresh.")
    return {"posted_ids": set(), "genre_index": 0, "sunday_toggle": True, "total_posts": 0}


def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({
                "posted_ids":    list(state["posted_ids"]),
                "genre_index":   state["genre_index"],
                "sunday_toggle": state["sunday_toggle"],
                "total_posts":   state["total_posts"],
            }, f, indent=2)
    except Exception as e:
        log.error(f"Failed to save state: {e}")


state = load_state()

# ─── VALIDATION ──────────────────────────────────────────────

def validate_config():
    missing = [v for v in ["TMDB_API_KEY", "FB_PAGE_ID", "FB_ACCESS_TOKEN"] if not os.getenv(v)]
    if missing:
        log.error(f"Missing environment variables: {', '.join(missing)}")
        log.error("Please check your .env file.")
        raise SystemExit(1)
    log.info("✅  Config validated — all credentials loaded from .env")


def check_token():
    try:
        r = requests.get(
            "https://graph.facebook.com/v19.0/me",
            params={"access_token": FB_ACCESS_TOKEN},
            timeout=10
        )
        data = r.json()
        if "error" in data:
            log.error(f"⚠️  Facebook token error: {data['error']['message']}")
            log.error("   → Refresh your Page Access Token in Meta Developer Console.")
            return False
        log.info(f"✅  Token valid — connected as: {data.get('name', 'Unknown')}")
        return True
    except Exception as e:
        log.error(f"Token check failed: {e}")
        return False

# ─── HTTP HELPERS ────────────────────────────────────────────

def http_get_with_retry(url, params=None, retries=3, backoff=2):
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            log.warning(f"HTTP {r.status_code} attempt {attempt}/{retries}: {e}")
        except requests.exceptions.RequestException as e:
            log.warning(f"Request error attempt {attempt}/{retries}: {e}")
        if attempt < retries:
            sleep_time = backoff ** attempt + random.uniform(0, 1)
            log.info(f"  Retrying in {sleep_time:.1f}s...")
            time.sleep(sleep_time)
    return None


def http_post_with_retry(url, data=None, retries=3, backoff=2):
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(url, data=data, timeout=15)
            if r.status_code == 200:
                return r.json()
            err  = r.json().get("error", {})
            code = err.get("code", 0)
            msg  = err.get("message", r.text)
            if code == 190:
                log.error("🔑  Access token expired! Update FB_ACCESS_TOKEN in .env")
                return None
            if code == 32:
                log.warning("⏳  Rate limited. Waiting 60s...")
                time.sleep(60)
            else:
                log.warning(f"FB error attempt {attempt}: [{code}] {msg}")
        except requests.exceptions.RequestException as e:
            log.warning(f"Post error attempt {attempt}: {e}")
        if attempt < retries:
            time.sleep(backoff ** attempt + random.uniform(0, 1))
    return None

# ─── TMDB FETCHERS ───────────────────────────────────────────

def tmdb_get(endpoint, extra_params=None):
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}
    if extra_params:
        params.update(extra_params)
    data = http_get_with_retry(f"{TMDB_BASE}{endpoint}", params=params)
    if data is None:
        log.error(f"TMDb request failed: {endpoint}")
        return []
    return data.get("results", [])


def fetch_trending_movies():
    return tmdb_get("/trending/movie/day")

def fetch_trending_series():
    return tmdb_get("/trending/tv/day")

def fetch_top_rated_movies():
    return tmdb_get("/movie/top_rated")

def fetch_new_releases():
    combined = tmdb_get("/movie/now_playing")[:12] + tmdb_get("/tv/on_the_air")[:12]
    random.shuffle(combined)
    return combined

def fetch_genre_spotlight():
    genre = GENRE_ROTATION[state["genre_index"] % len(GENRE_ROTATION)]
    state["genre_index"] += 1
    results = tmdb_get("/discover/movie", {"with_genres": genre["id"], "sort_by": "popularity.desc"})
    for item in results:
        item["_genre_name"] = genre["name"]
    return results

def fetch_classics():
    return tmdb_get("/discover/movie", {
        "primary_release_date.lte": "2000-12-31",
        "sort_by": "vote_average.desc",
        "vote_count.gte": 1000
    })

def fetch_anime_or_docs():
    if state["sunday_toggle"]:
        results = tmdb_get("/discover/tv", {"with_genres": "16", "sort_by": "popularity.desc"})
        for r in results: r["_content_type"] = "Anime"
    else:
        results = tmdb_get("/discover/movie", {"with_genres": "99", "sort_by": "popularity.desc"})
        for r in results: r["_content_type"] = "Documentary"
    state["sunday_toggle"] = not state["sunday_toggle"]
    return results

# ─── CAPTION ─────────────────────────────────────────────────

def star_rating(score):
    full  = int(score / 2)
    half  = 1 if (score / 2 - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + "½" * half + "☆" * empty


def build_caption(item, category):
    title    = item.get("title") or item.get("name", "Unknown Title")
    media    = "Movie" if item.get("title") else "Series"
    rating   = round(item.get("vote_average", 0), 1)
    overview = item.get("overview", "No description available.")
    release  = item.get("release_date") or item.get("first_air_date", "")
    year     = release[:4] if release else "N/A"
    votes    = f"{item.get('vote_count', 0):,}"
    genre    = item.get("_genre_name", "")
    ctype    = item.get("_content_type", media)
    tmdb_id  = item.get("id", "")
    link     = f"{TMDB_MOVIE}/{tmdb_id}" if media == "Movie" else f"{TMDB_TV}/{tmdb_id}"

    if len(overview) > 240:
        overview = overview[:240].rsplit(" ", 1)[0] + "…"

    clean_title = "#" + "".join(c for c in title if c.isalnum())
    genre_hash  = f"#{genre.replace(' ', '')}" if genre else ""
    day_theme   = category.replace(" ", "").replace("&", "And")

    hashtags = (
        f"{clean_title} {genre_hash} "
        f"#theynevertoldus #Cinema #FilmLovers #MustWatch "
        f"#NowStreaming #BingeWatch #{day_theme} "
        f"#Hollywood #Entertainment #MovieNight "
        f"#{'Movie' if media == 'Movie' else 'TVShow'} "
        f"#Popcorn #WeekendVibes #FilmRecommendation #IMDb "
        f"{'#Anime ' if ctype == 'Anime' else ''}"
        f"{'#Documentary' if ctype == 'Documentary' else ''}"
    ).strip()

    return f"""🎬  {title.upper()}  ({year})

{star_rating(rating)}  {rating}/10  ·  {votes} ratings

📖  {overview}

━━━━━━━━━━━━━━━━━━━━━━━
🗂  Category   :  {category}
📺  Type        :  {ctype}
🗓  Released  :  {year}
🔗  More Info  :  {link}
━━━━━━━━━━━━━━━━━━━━━━━

🍿  Follow {PAGE_NAME} for daily handpicked movies & series!
👉  {PAGE_HANDLE}  — Your Ultimate Cinema Guide

.
{hashtags}"""

# ─── FACEBOOK POST ────────────────────────────────────────────

def get_hd_poster(item):
    path = item.get("poster_path")
    return f"{TMDB_IMG_HD}{path}" if path else None

def get_tmdb_link(item):
    media = "Movie" if item.get("title") else "Series"
    tmdb_id = item.get("id", "")
    return f"{TMDB_MOVIE}/{tmdb_id}" if media == "Movie" else f"{TMDB_TV}/{tmdb_id}"


def post_to_facebook(image_url, caption, item):
    if TEST_MODE:
        title = item.get("title") or item.get("name", "?")
        log.info(f"  🧪  [TEST MODE] Would post: {title}")
        log.info(f"  📝  Caption preview:\n{caption[:200]}...")
        return True

    # Attempt photo post
    if image_url:
        result = http_post_with_retry(
            f"{FB_GRAPH}/photos",
            data={"url": image_url, "caption": caption, "access_token": FB_ACCESS_TOKEN}
        )
        if result and result.get("id"):
            log.info(f"  ✅  Photo posted  →  ID: {result['id']}")
            return True
        log.warning("  ⚠️  Photo post failed — trying link post fallback.")

    # Fallback: link post
    result = http_post_with_retry(
        f"{FB_GRAPH}/feed",
        data={"message": caption, "link": get_tmdb_link(item), "access_token": FB_ACCESS_TOKEN}
    )
    if result and result.get("id"):
        log.info(f"  ✅  Link post fallback  →  ID: {result['id']}")
        return True

    log.error("  ❌  All post attempts failed.")
    return False

# ─── MAIN JOB ────────────────────────────────────────────────

def run_post():
    now      = datetime.now()
    day      = now.weekday()
    plan     = WEEKLY_PLAN[day]
    category = plan["label"]
    fetcher  = globals()[plan["fetch"]]

    log.info(f"{'─'*52}")
    log.info(f"  🕐  {now.strftime('%A %d %b %Y  %H:%M')}")
    log.info(f"  📂  Category : {category}")
    log.info(f"{'─'*52}")

    items = fetcher()
    if not items:
        log.warning("  ⚠️  No items returned from TMDb. Skipping.")
        return

    item = next((i for i in items if i.get("id") not in state["posted_ids"]), None)
    if not item:
        log.info("  ♻️  All items seen — resetting history.")
        state["posted_ids"].clear()
        item = items[0]

    state["posted_ids"].add(item.get("id"))

    title  = item.get("title") or item.get("name", "?")
    poster = get_hd_poster(item)
    log.info(f"  🎬  Posting : {title}")

    if not poster:
        log.info("  🖼️  No poster available — will use link post.")

    caption = build_caption(item, category)
    success = post_to_facebook(poster, caption, item)

    if success:
        state["total_posts"] += 1
        log.info(f"  📊  Total posts this session: {state['total_posts']}")

    save_state(state)

# ─── SCHEDULER ───────────────────────────────────────────────

def start_bot():
    print(f"""
╔══════════════════════════════════════════════════╗
║       theynevertoldus Bot v2.0  —  Starting Up         ║
║     Your Ultimate Cinema Guide on Facebook       ║
╠══════════════════════════════════════════════════╣
║  Mode        : {"🧪 TEST (no real posts)         " if TEST_MODE else "🚀 LIVE                           "}║
║  Posts/day   : {len(POST_TIMES):<43}║
║  Posts/week  : {len(POST_TIMES) * 7:<43}║
║  Schedule    : Every 2 hrs  (7AM – 9PM)          ║
║  Timezone    : {TIMEZONE:<34}  ║
║  Total posts : {state["total_posts"]:<43}║
╚══════════════════════════════════════════════════╝
""")

    validate_config()
    check_token()

    scheduler = BlockingScheduler(timezone=TIMEZONE)
    for t in POST_TIMES:
        h, m = map(int, t.split(":"))
        scheduler.add_job(run_post, "cron", hour=h, minute=m)
        log.info(f"  ⏰  Scheduled post at  {t}")

    log.info(f"\n  🚀  Bot is live — waiting for next scheduled post...\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("\n  🛑  Bot stopped gracefully.")
        save_state(state)


if __name__ == "__main__":
    # To run a single test post immediately, uncomment:
    # run_post()
    start_bot()
