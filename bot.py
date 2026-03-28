import os, json, time, random, requests, re
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

FB_TOKEN   = os.getenv("FB_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
GROQ_KEY   = os.getenv("GROQ_KEY")

FB_POST_URL  = f"https://graph.facebook.com/{FB_PAGE_ID}/feed"
FB_PHOTO_URL = f"https://graph.facebook.com/{FB_PAGE_ID}/photos"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
STATE_FILE   = "state.json"
PAGE_NAME    = "They Never Told Us"
POST_INTERVAL = 1800  # 30 minutes

# ── Categories ────────────────────────────────────────────────────
CATEGORIES = [
    "animals_nature",
    "crazy_humans",
    "dark_history",
    "ocean_space",
    "world_news",
    "shocking_facts",
]

CATEGORY_INFO = {
    "animals_nature": {"name": "Animals & Nature", "emoji": "🐾"},
    "crazy_humans":   {"name": "Crazy Humans",     "emoji": "😱"},
    "dark_history":   {"name": "Dark History",     "emoji": "💀"},
    "ocean_space":    {"name": "Ocean & Space",    "emoji": "🌊"},
    "world_news":     {"name": "World News",       "emoji": "🌍"},
    "shocking_facts": {"name": "Shocking Facts",   "emoji": "🤯"},
}

# ── Wikipedia topics per category ─────────────────────────────────
WIKI_TOPICS = {
    "animals_nature": [
        "Mantis shrimp", "Pistol shrimp", "Tardigrade", "Mimic octopus",
        "Bombardier beetle", "Platypus", "Goblin shark", "Archerfish",
        "Immortal jellyfish", "Axolotl", "Komodo dragon", "Cassowary",
        "Blue-ringed octopus", "Cone snail", "Irukandji jellyfish",
        "Hippopotamus", "Saltwater crocodile", "Inland taipan",
        "Box jellyfish", "Stonefish", "Venus flytrap", "Rafflesia",
        "Corpse flower", "Baobab tree", "Dragon blood tree",
        "Great white shark", "Black mamba", "Electric eel",
        "Honey badger", "Wolverine", "Tasmanian devil",
        "Aye-aye", "Naked mole rat", "Blobfish", "Anglerfish",
        "Vampire squid", "Giant squid", "Colossal squid",
        "Dung beetle", "Army ant", "Bullet ant", "Africanized bee",
        "Coconut crab", "Goliath birdeater", "Titan beetle",
        "Moose", "Capybara", "Pangolin", "Okapi", "Saiga antelope",
        "Shoebill", "Harpy eagle", "Andean condor", "Secretary bird",
    ],
    "crazy_humans": [
        "Robert Wadlow", "Michel Lotito", "Lina Medina",
        "Dean Karnazes", "Wim Hof", "Grigori Rasputin",
        "Charles Osborne", "Kim Peek", "Daniel Tammet",
        "Stephen Wiltshire", "Angus Barbieri", "Nicholas Alkemade",
        "Roy Sullivan", "Tsutomu Yamaguchi", "Vesna Vulovic",
        "Unusual deaths", "List of tallest people",
        "List of shortest people", "Human echolocation",
        "Feral children", "Mitsutaka Uchikoshi", "Stig Severinsen",
        "Tim Friede", "Juliane Koepcke", "Joe Simpson",
        "Aron Ralston", "Beck Weathers", "Phineas Gage",
        "Alexis St. Martin", "James Harrison",
    ],
    "dark_history": [
        "Black Death", "Unit 731", "Tanganyika laughter epidemic",
        "Dancing plague of 1518", "Great Molasses Flood",
        "Radium Girls", "Tulsa race massacre",
        "MKUltra", "Operation Paperclip",
        "Tuskegee syphilis experiment", "Stolen generations",
        "Emu War", "Holodomor", "Srebrenica massacre",
        "Rwandan genocide", "Triangle Shirtwaist Factory fire",
        "Jonestown", "Heaven's Gate",
        "Antikythera mechanism", "Voynich manuscript",
        "Wow! signal", "Dyatlov Pass incident",
        "Mary Celeste", "SS Ourang Medan",
        "Sodder children", "Tamam Shud case",
        "Lead poisoning in Rome", "Ergotism",
        "Great Pacific garbage patch", "Aral Sea",
    ],
    "ocean_space": [
        "Mariana Trench", "Challenger Deep", "Bioluminescence",
        "Hydrothermal vent", "Megalodon", "Bermuda Triangle",
        "Black hole", "Neutron star", "Magnetar",
        "Pale Blue Dot", "Voyager 1", "Fermi paradox",
        "Dark matter", "Dark energy", "Tunguska event",
        "Chelyabinsk meteor", "Great Oxygenation Event",
        "Permian-Triassic extinction event",
        "Chicxulub crater", "Oumuamua",
        "Dyson sphere", "Kardashev scale",
        "Great Red Spot", "Europa", "Enceladus",
        "Titan", "Io", "Triton",
        "Rogue planet", "Zombie star", "Quasar",
        "Fast radio burst", "Gravitational wave",
        "Event Horizon Telescope", "Sagittarius A*",
    ],
    "world_news": [],  # handled by BBC RSS
    "shocking_facts": [
        "Human microbiome", "Sleep paralysis",
        "Exploding head syndrome", "Cotard delusion",
        "Foreign accent syndrome", "Locked-in syndrome",
        "Mass hysteria", "Spontaneous human combustion",
        "Ball lightning", "Raining animals",
        "Biological warfare", "Chemical warfare",
        "Opium Wars", "Modern slavery",
        "Microplastics", "Forever chemicals",
        "Sugar industry", "Tobacco industry",
        "Opioid epidemic", "Panama Papers",
        "Cambridge Analytica", "Edward Snowden",
        "Area 51", "Bilderberg Group",
        "Food desert", "Organ trade",
        "Deep web", "Dark web",
        "Subliminal advertising", "Propaganda",
        "Gaslighting", "Stockholm syndrome",
        "Milgram experiment", "Stanford prison experiment",
        "Bystander effect", "Dunning-Kruger effect",
    ],
}

# ── Post starters ─────────────────────────────────────────────────
STARTERS = [
    "Did you know that",
    "Nobody told you this but",
    "They never told us that",
    "This is 100% real —",
    "Science cannot explain why",
    "Before you sleep tonight, read this —",
    "Only 1% of people know this —",
    "This actually happened and it will shock you —",
    "You will not believe this but",
    "God created this and scientists are still confused —",
    "This is the most shocking thing you will read today —",
    "The world never talks about this —",
    "Nobody is talking about this —",
    "Meet the most dangerous thing on Earth —",
    "This will change how you see the world —",
    "They tried to hide this from us —",
    "Most people go their whole life not knowing this —",
    "This is not a movie. This is real life —",
]

# ── BBC RSS ───────────────────────────────────────────────────────
BBC_RSS = "https://feeds.bbci.co.uk/news/rss.xml"

# ── State ─────────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                d = json.load(f)
                return (
                    d.get("last_post_time", 0),
                    d.get("category_index", 0),
                    d.get("posted_keys", {}),
                )
        except Exception:
            pass
    return 0, 0, {}

last_post_time, category_index, posted_keys = load_state()

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump({
            "last_post_time": last_post_time,
            "category_index": category_index,
            "posted_keys": posted_keys,
        }, f)

def is_posted(key):
    if key not in posted_keys:
        return False
    return (time.time() - posted_keys[key]) < (30 * 24 * 3600)

def mark_posted(key):
    posted_keys[key] = time.time()
    cutoff = time.time() - (31 * 24 * 3600)
    for k in [k for k, v in posted_keys.items() if v < cutoff]:
        del posted_keys[k]

# ── Groq AI ───────────────────────────────────────────────────────
def ask_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.9,
    }
    try:
        r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=20)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        print(f"[GROQ] Error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[GROQ] Exception: {e}")
    return None

# ── Wikipedia fetch with image ────────────────────────────────────
def fetch_wikipedia(topic):
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + topic.replace(" ", "_")
        r = requests.get(url, headers={"User-Agent": "TheyNeverToldUs/1.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            # Get best quality image URL
            image_url = None
            if "originalimage" in data:
                image_url = data["originalimage"]["source"]
            elif "thumbnail" in data:
                image_url = data["thumbnail"]["source"].replace("320px", "1200px")
            return {
                "title": data.get("title", topic),
                "summary": data.get("extract", ""),
                "image_url": image_url,
            }
    except Exception as e:
        print(f"[WIKI] Error fetching {topic}: {e}")
    return None

# ── Download Wikipedia image ──────────────────────────────────────
def download_image(image_url):
    if not image_url:
        return None
    try:
        r = requests.get(
            image_url,
            headers={"User-Agent": "TheyNeverToldUs/1.0"},
            timeout=20
        )
        if r.status_code == 200 and len(r.content) > 1000:
            print(f"[IMAGE] Downloaded {len(r.content)//1024}KB")
            return r.content
        print(f"[IMAGE] Failed: {r.status_code}")
    except Exception as e:
        print(f"[IMAGE] Exception: {e}")
    return None

# ── BBC RSS fetch ─────────────────────────────────────────────────
def fetch_bbc_news():
    try:
        r = requests.get(BBC_RSS, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            tree  = ET.fromstring(r.content)
            items = tree.findall(".//item")
            news  = []
            for item in items[:20]:
                title_el = item.find("title")
                desc_el  = item.find("description")
                title = (title_el.text or "").strip() if title_el is not None else ""
                desc  = (desc_el.text or "").strip() if desc_el is not None else ""
                desc  = re.sub(r'<[^>]+>', '', desc).strip()
                if title and len(title) > 10:
                    news.append({"title": title, "desc": desc})
            return news
    except Exception as e:
        print(f"[BBC] Error: {e}")
    return []

# ── Post to Facebook ──────────────────────────────────────────────
def post_to_facebook(message, image_bytes=None):
    try:
        if image_bytes:
            r = requests.post(
                FB_PHOTO_URL,
                files={"source": ("image.jpg", image_bytes, "image/jpeg")},
                data={"caption": message, "access_token": FB_TOKEN},
                timeout=30
            )
        else:
            r = requests.post(
                FB_POST_URL,
                data={"message": message, "access_token": FB_TOKEN},
                timeout=15
            )
        if r.status_code == 200:
            print(f"[POSTED] {message[:80]}...")
            return True
        print(f"[FB ERROR] {r.status_code} {r.text[:300]}")
    except Exception as e:
        print(f"[FB ERROR] {e}")
    return False

# ── Write fact post with Groq ─────────────────────────────────────
def write_fact_post(category, topic, wiki_data):
    info    = CATEGORY_INFO[category]
    emoji   = info["emoji"]
    starter = random.choice(STARTERS)
    summary = wiki_data["summary"][:800]

    prompt = f"""You write Facebook posts for a page called "They Never Told Us".
Your audience is mostly African people — use VERY simple English. Short sentences. Easy words. Maximum 15 words per sentence.

Topic: {topic}
Real facts to use: {summary}

Write the Facebook post in this EXACT structure:

1. HOOK LINE
Start with: "{starter}" — then write the single most shocking fact about {topic}.
Add {emoji} emoji. Make it impossible to scroll past.

2. THE FACTS
Write 5 to 6 short sentences. Each sentence maximum 15 words.
Use simple English a 12 year old understands.
Add relevant emojis on each line 🔥😱💀🌊🧠⚡🙏
Tell it like a story — build up the shock.
Use ONLY real facts from the text above.

3. THE CLOSER
One emotional sentence. Make the reader feel amazed, shocked or grateful.
End with 🙏 or 😱 or 🤯

4. FOLLOW TRIGGER — write EXACTLY this:
🔔 Follow They Never Told Us — we post the craziest facts every single day.
Tag a friend who needs to see this 👇

Rules:
- Maximum 200 words total
- No complex words — use simple ones
- No long sentences — keep them short
- Use lots of emojis throughout
- Make it feel like a friend whispering a secret to you
- ONLY use facts from the real facts given above — do NOT invent anything
"""
    return ask_groq(prompt)

# ── Write news post with Groq ─────────────────────────────────────
def write_news_post(title, desc):
    starter = random.choice(STARTERS)
    prompt = f"""You write Facebook posts for a page called "They Never Told Us".
Your audience is mostly African people — use VERY simple English. Short sentences. Easy words. Maximum 15 words per sentence.

Real news headline: {title}
Real news details: {desc}

Write the Facebook post in this EXACT structure:

1. HOOK LINE
Start with "{starter}" — then the most important point of this news.
Add 🌍 emoji. Make it impossible to scroll past.

2. THE STORY
Explain what is happening in 5 short sentences. Maximum 15 words each.
Use very simple English — like explaining to a friend.
Explain WHY this matters for Africa and ordinary people.
Add emojis on each line 🌍😱💰⚡🔥

3. THE CLOSER
One sentence about what might happen next.
Add 😳 or 🤔 or 💭

4. FOLLOW TRIGGER — write EXACTLY this:
🔔 Follow They Never Told Us — we explain world news in simple English every single day.
Tag someone who needs to understand what is happening 👇

Rules:
- Maximum 200 words total
- No complex words
- No long sentences
- Make it feel like a smart friend explaining the news to you
- ONLY use facts from the headline and details above
- Add relevant emojis throughout
"""
    return ask_groq(prompt)

# ── Main post function ────────────────────────────────────────────
def make_post():
    global last_post_time, category_index

    category = CATEGORIES[category_index % len(CATEGORIES)]
    info     = CATEGORY_INFO[category]
    print(f"\n[BOT] Category: {info['name']} {info['emoji']}")

    post_text   = None
    image_bytes = None
    post_key    = None

    if category == "world_news":
        # BBC News
        news_items = fetch_bbc_news()
        random.shuffle(news_items)
        for item in news_items:
            key = re.sub(r'[^a-z0-9]', '', item["title"].lower())[:60]
            if not is_posted(key):
                print(f"[BOT] News: {item['title'][:60]}")
                post_text = write_news_post(item["title"], item["desc"])
                post_key  = key
                # No image for news — post text only
                break

        if not post_key:
            print("[BOT] All news already posted. Moving to next category.")
            category_index += 1
            save_state()
            return False

    else:
        # Wikipedia fact
        topics = WIKI_TOPICS[category].copy()
        random.shuffle(topics)
        for topic in topics:
            key = re.sub(r'[^a-z0-9]', '', topic.lower())[:60]
            if not is_posted(key):
                print(f"[BOT] Topic: {topic}")
                wiki_data = fetch_wikipedia(topic)
                if wiki_data and len(wiki_data["summary"]) > 100:
                    post_text   = write_fact_post(category, topic, wiki_data)
                    image_bytes = download_image(wiki_data.get("image_url"))
                    post_key    = key
                    break

        if not post_key:
            print(f"[BOT] All {category} topics posted recently. Moving on.")
            category_index += 1
            save_state()
            return False

    if not post_text:
        print("[BOT] Groq failed. Moving to next category.")
        category_index += 1
        save_state()
        return False

    # Post to Facebook
    if post_to_facebook(post_text, image_bytes):
        mark_posted(post_key)
        last_post_time = time.time()
        category_index += 1
        save_state()
        next_cat = CATEGORIES[category_index % len(CATEGORIES)]
        print(f"[BOT] ✅ Posted! Next category: {CATEGORY_INFO[next_cat]['name']}")
        return True

    print("[BOT] Facebook post failed.")
    return False

# ── Run ───────────────────────────────────────────────────────────
def run():
    global last_post_time

    print("=" * 50)
    print("  They Never Told Us — Facebook Bot")
    print("=" * 50)
    print(f"Categories : {', '.join(CATEGORY_INFO[c]['name'] for c in CATEGORIES)}")
    print("Sources    : Wikipedia (with real photos) + BBC RSS")
    print("Writing    : Groq AI — simple English for African audience")
    print("Images     : Wikipedia original photos")
    print("Interval   : Every 30 minutes")
    print("No repeats : 30 day cooldown per topic")
    print()

    while True:
        try:
            now     = time.time()
            elapsed = now - last_post_time

            if elapsed >= POST_INTERVAL:
                print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Time to post!")
                make_post()
            else:
                remaining = int((POST_INTERVAL - elapsed) / 60)
                print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Next post in {remaining} mins.")

        except Exception as e:
            print(f"[ERROR] {e}")

        time.sleep(300)

if __name__ == "__main__":
    run()
