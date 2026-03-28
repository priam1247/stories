import os, json, time, random, requests, re, logging
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)

def log(msg):
    print(msg)
    logging.info(msg)

FB_TOKEN   = os.getenv("FB_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
GROQ_KEY   = os.getenv("GROQ_KEY")

for var, val in [("FB_TOKEN", FB_TOKEN), ("FB_PAGE_ID", FB_PAGE_ID), ("GROQ_KEY", GROQ_KEY)]:
    if not val:
        raise SystemExit(f"[ERROR] Missing environment variable: {var}")

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
        "Fossa", "Quokka", "Ocean sunfish", "Leafy sea dragon",
        "Pufferfish", "Hagfish", "Lamprey", "Piranha", "Arapaima",
        "Giant river otter", "Slow loris", "Tarsier", "Proboscis monkey",
        "Mandrill", "Geoduck", "Horseshoe crab", "Velvet worm",
        "Glaucus atlanticus", "Portuguese man o war", "Bobbit worm",
        "Draco lizard", "Flying snake", "Thorny dragon",
        "Frill-necked lizard", "Basilisk lizard", "Matamata",
        "Star-nosed mole", "Platypus", "Echidna", "Narwhal",
        "Beluga whale", "Orca", "Sperm whale", "Blue whale",
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
        "Benedetto Supino", "Natasha Demkina",
        "Erik Weihenmayer", "Hugh Herr", "Temple Grandin",
        "Derek Paravicini", "Tony Cicoria", "Jason Padgett",
        "Slavomir Rawicz", "Ernest Shackleton", "Louis Zamperini",
        "Mauro Prosperi", "Yossi Ghinsberg",
        "Anatoli Bugorski", "Harold Whittles",
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
        "Lobotomy", "Thalidomide", "Phrenology", "Eugenics",
        "Project MKNaomi", "Operation Sea-Spray",
        "Guatemalan syphilis experiments", "Willowbrook State School",
        "Dozier School for Boys", "Goiania accident",
        "Bhopal disaster", "Chernobyl disaster",
        "Love Canal", "Agent Orange",
        "Forced sterilization in the United States",
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
        "Cosmic web", "Observable universe",
        "Simulation hypothesis", "Blue hole",
        "Milky Way", "Andromeda Galaxy",
        "Gamma-ray burst", "Cosmic microwave background",
        "Spaghettification", "Time dilation",
        "Wormhole", "Hawking radiation",
        "Great Attractor", "Bloop",
        "Zone of silence", "Underwater waterfall",
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
        "Placebo effect", "Nocebo effect", "False memory",
        "Phantom limb", "Synesthesia", "Savant syndrome",
        "Near-death experience", "Lucid dreaming",
        "Human trafficking", "Blood diamonds", "Conflict minerals",
        "Shadow banking", "Tax haven", "Dark money",
        "Predictive policing", "Social credit system",
        "Surveillance capitalism", "Filter bubble",
        "Epigenetics", "Telomere", "CRISPR",
        "Brain-computer interface", "Transhumanism",
        "Factory farming", "Seed patent", "Fluoride controversy",
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

# ── Hashtags per category ─────────────────────────────────────────
HASHTAGS = {
    "animals_nature":  "#TheyNeverToldUs #Animals #Nature #Facts #DidYouKnow #Wildlife #Africa",
    "crazy_humans":    "#TheyNeverToldUs #CrazyHumans #Facts #DidYouKnow #Unbelievable #Africa",
    "dark_history":    "#TheyNeverToldUs #DarkHistory #Facts #History #HiddenTruth #Africa",
    "ocean_space":     "#TheyNeverToldUs #Space #Ocean #Facts #DidYouKnow #Universe #Africa",
    "world_news":      "#TheyNeverToldUs #WorldNews #Africa #Breaking #News #StayInformed",
    "shocking_facts":  "#TheyNeverToldUs #ShockingFacts #Facts #DidYouKnow #HiddenTruth #Africa",
}

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

# ── Groq AI with retry ────────────────────────────────────────────
def ask_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.9,
    }
    for attempt in range(3):
        try:
            r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=20)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            log(f"[GROQ] Error {r.status_code} attempt {attempt+1}: {r.text[:200]}")
        except Exception as e:
            log(f"[GROQ] Exception attempt {attempt+1}: {e}")
        time.sleep(5)
    return None

# ── Wikipedia fetch with image ────────────────────────────────────
def fetch_wikipedia(topic):
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + topic.replace(" ", "_")
        r = requests.get(url, headers={"User-Agent": "TheyNeverToldUs/1.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            image_url = None
            if "originalimage" in data:
                image_url = data["originalimage"]["source"]
            elif "thumbnail" in data:
                image_url = re.sub(r'/\d+px-', '/1200px-', data["thumbnail"]["source"])
            return {
                "title": data.get("title", topic),
                "summary": data.get("extract", ""),
                "image_url": image_url,
            }
    except Exception as e:
        log(f"[WIKI] Error fetching {topic}: {e}")
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
            log(f"[IMAGE] Downloaded {len(r.content)//1024}KB")
            return r.content
        log(f"[IMAGE] Failed: {r.status_code}")
    except Exception as e:
        log(f"[IMAGE] Exception: {e}")
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
                if title and len(title) > 10 and desc:
                    news.append({"title": title, "desc": desc})
            return news
    except Exception as e:
        log(f"[BBC] Error: {e}")
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
            log(f"[POSTED] {message[:80]}...")
            return True
        log(f"[FB ERROR] {r.status_code} {r.text[:300]}")
    except Exception as e:
        log(f"[FB ERROR] {e}")
    return False

# ── Write fact post with Groq ─────────────────────────────────────
def write_fact_post(category, topic, wiki_data):
    info    = CATEGORY_INFO[category]
    emoji   = info["emoji"]
    starter = random.choice(STARTERS)
    summary = wiki_data["summary"][:800]

    prompt = f"""You write Facebook posts for a page called "They Never Told Us".
Your audience is mostly African people. Use VERY simple English. Short sentences. Easy words. Maximum 15 words per sentence.

Topic: {topic}
Real facts to use: {summary}

Write a single Facebook post as plain flowing text. No titles. No headings. No numbers. No labels. No sections. Just the post text itself.

Start with "{starter}" then write the single most shocking fact about {topic}. Add {emoji} emoji on this first line.

Then write 5 to 6 short sentences about {topic}. Each sentence maximum 15 words. Simple English a 12 year old understands. Add emojis like 🔥😱💀🌊🧠⚡ on each line. Tell it like a story and build up the shock. Use ONLY real facts from the text above.

Then write one emotional sentence to close. Make the reader feel amazed or shocked. End with 🙏 or 😱 or 🤯

Then on a new line write exactly this:
🔔 Follow They Never Told Us — we post the craziest facts every single day.
Tag a friend who needs to see this 👇

Rules:
- Maximum 200 words total
- NO titles, NO headings, NO numbers, NO labels anywhere in the post
- No complex words
- No long sentences
- ONLY use facts from the real facts given above — do NOT invent anything
"""
    result = ask_groq(prompt)
    if result:
        return result + f"\n\n{HASHTAGS[category]}"
    return None

# ── Write news post with Groq ─────────────────────────────────────
def write_news_post(title, desc):
    starter = random.choice(STARTERS)
    prompt = f"""You write Facebook posts for a page called "They Never Told Us".
Your audience is mostly African people. Use VERY simple English. Short sentences. Easy words. Maximum 15 words per sentence.

Real news headline: {title}
Real news details: {desc}

Write a single Facebook post as plain flowing text. No titles. No headings. No numbers. No labels. No sections. Just the post text itself.

Start with "{starter}" then write the most important point of this news. Add 🌍 emoji on this first line.

Then write 5 short sentences explaining what is happening. Each sentence maximum 15 words. Very simple English like explaining to a friend. Explain why this matters for Africa and ordinary people. Add emojis on each line 🌍😱💰⚡🔥

Then write one sentence about what might happen next. End with 😳 or 🤔 or 💭

Then on a new line write exactly this:
🔔 Follow They Never Told Us — we explain world news in simple English every single day.
Tag someone who needs to understand what is happening 👇

Rules:
- Maximum 200 words total
- NO titles, NO headings, NO numbers, NO labels anywhere in the post
- No complex words
- No long sentences
- ONLY use facts from the headline and details above
"""
    result = ask_groq(prompt)
    if result:
        return result + f"\n\n{HASHTAGS['world_news']}"
    return None

# ── Main post function ────────────────────────────────────────────
def make_post():
    global last_post_time, category_index

    category = CATEGORIES[category_index % len(CATEGORIES)]
    info     = CATEGORY_INFO[category]
    log(f"\n[BOT] Category: {info['name']} {info['emoji']}")

    post_text   = None
    image_bytes = None
    post_key    = None

    if category == "world_news":
        news_items = fetch_bbc_news()
        random.shuffle(news_items)
        for item in news_items:
            key = re.sub(r'[^a-z0-9]', '', item["title"].lower())[:60]
            if not is_posted(key):
                log(f"[BOT] News: {item['title'][:60]}")
                post_text = write_news_post(item["title"], item["desc"])
                post_key  = key
                break

        if not post_key:
            log("[BOT] All news already posted. Moving to next category.")
            category_index += 1
            save_state()
            return False

    else:
        topics = WIKI_TOPICS[category].copy()
        random.shuffle(topics)
        for topic in topics:
            key = re.sub(r'[^a-z0-9]', '', topic.lower())[:60]
            if not is_posted(key):
                log(f"[BOT] Topic: {topic}")
                wiki_data = fetch_wikipedia(topic)
                if wiki_data and len(wiki_data["summary"]) > 100:
                    post_text   = write_fact_post(category, topic, wiki_data)
                    image_bytes = download_image(wiki_data.get("image_url"))
                    post_key    = key
                    break

        if not post_key:
            log(f"[BOT] All {category} topics posted recently. Moving on.")
            category_index += 1
            save_state()
            return False

    if not post_text:
        log("[BOT] Groq failed after 3 attempts. Moving to next category.")
        category_index += 1
        save_state()
        return False

    if post_to_facebook(post_text, image_bytes):
        mark_posted(post_key)
        last_post_time = time.time()
        category_index += 1
        save_state()
        next_cat = CATEGORIES[category_index % len(CATEGORIES)]
        log(f"[BOT] ✅ Posted! Next category: {CATEGORY_INFO[next_cat]['name']}")
        return True

    log("[BOT] Facebook post failed.")
    return False

# ── Run ───────────────────────────────────────────────────────────
def run():
    global last_post_time

    log("=" * 50)
    log("  They Never Told Us — Facebook Bot")
    log("=" * 50)
    log(f"Categories : {', '.join(CATEGORY_INFO[c]['name'] for c in CATEGORIES)}")
    log("Sources    : Wikipedia (with real photos) + BBC RSS")
    log("Writing    : Groq AI (llama-3.3-70b) — simple English for African audience")
    log("Images     : Wikipedia original photos")
    log("Interval   : Every 30 minutes")
    log("No repeats : 30 day cooldown per topic")
    log("")

    while True:
        try:
            now     = time.time()
            elapsed = now - last_post_time

            if elapsed >= POST_INTERVAL:
                log(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Time to post!")
                make_post()
            else:
                remaining = int((POST_INTERVAL - elapsed) / 60)
                log(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Next post in {remaining} mins.")

        except Exception as e:
            log(f"[ERROR] {e}")

        time.sleep(60)

if __name__ == "__main__":
    run()
