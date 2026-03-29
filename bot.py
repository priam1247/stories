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

FB_TOKEN      = os.getenv("FB_TOKEN")
FB_PAGE_ID    = os.getenv("FB_PAGE_ID")
GROQ_KEY      = os.getenv("GROQ_KEY")
PEXELS_KEY    = os.getenv("PEXELS_KEY")

for var, val in [
    ("FB_TOKEN",    FB_TOKEN),
    ("FB_PAGE_ID",  FB_PAGE_ID),
    ("GROQ_KEY",    GROQ_KEY),
    ("PEXELS_KEY",  PEXELS_KEY),
]:
    if not val:
        raise SystemExit(f"[ERROR] Missing environment variable: {var}")

FB_POST_URL   = f"https://graph.facebook.com/{FB_PAGE_ID}/feed"
FB_PHOTO_URL  = f"https://graph.facebook.com/{FB_PAGE_ID}/photos"
GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
PEXELS_URL    = "https://api.pexels.com/v1/search"
STATE_FILE    = "state.json"
POST_INTERVAL = 3600  # 1 hour

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

PEXELS_CATEGORY_FALLBACK = {
    "animals_nature": "wild animal nature",
    "crazy_humans":   "human crowd people",
    "dark_history":   "dark history war",
    "ocean_space":    "ocean space stars",
    "world_news":     "world news globe",
    "shocking_facts": "science discovery",
}

# ── FRESH Wikipedia topics — completely new, never posted ─────────
WIKI_TOPICS = {
    "animals_nature": [
        "Lyrebird", "Kakapo", "Frogfish", "Stonefish",
        "Mimic octopus", "Sea cucumber", "Crown-of-thorns starfish",
        "Mantis shrimp", "Snapping shrimp", "Giant clam",
        "Whale shark", "Basking shark", "Greenland shark",
        "Oarfish", "Frilled shark", "Goblin shark",
        "Dumbo octopus", "Firefly squid", "Japanese spider crab",
        "Yeti crab", "Flamingo", "Shoebill stork",
        "Marabou stork", "Sword-billed hummingbird",
        "Potoo", "Frogmouth", "Hoatzin", "Hoopoe",
        "Bowerbird", "Birds-of-paradise",
        "Wolverine", "Sun bear", "Binturong",
        "Clouded leopard", "Serval", "Caracal",
        "Maned wolf", "Bush dog", "African wild dog",
        "Aardvark", "Aardwolf", "Zorilla",
        "Pygmy hippo", "Forest elephant", "Pygmy elephant",
        "Irrawaddy dolphin", "Amazon river dolphin", "Vaquita",
        "Sea otter", "Giant otter", "Walrus",
        "Ribbon seal", "Leopard seal", "Weddell seal",
        "Quoll", "Numbat", "Thylacine",
        "Glass frog", "Poison dart frog", "Purple frog",
        "Olm", "Chinese giant salamander", "Hellbender",
        "Thorny devil", "Marine iguana", "Gharial",
        "Leatherback sea turtle", "Flatback turtle",
        "Gaboon viper", "Boomslang", "Tentacled snake",
        "Titan arum", "Welwitschia", "Bristlecone pine",
        "Rainbow eucalyptus", "Sandbox tree", "Manchineel",
    ],
    "crazy_humans": [
        "Stig Severinsen", "Tom Sietas", "Aleix Segura Vendrell",
        "Wim Hof", "Dean Karnazes", "Scott Jurek",
        "David Blaine", "Harry Houdini", "Mirin Dajo",
        "Michel Lotito", "Edward Hagert",
        "Natasha Demkina", "Lena Zagre",
        "Isao Machii", "Bob Munden",
        "Tim Cridland", "Murali", "Etibar Elchiyev",
        "Manoj Kumar Maharana",
        "Prahlad Jani", "Hira Ratan Manek",
        "Slavomir Rawicz", "Hiroo Onoda", "Teruo Nakamura",
        "Hugh Glass", "John Colter",
        "Ada Blackjack", "Shackleton expedition",
        "Roanoke Colony", "Kaspar Hauser",
        "Wild Peter", "Victor of Aveyron",
        "Genie Wiley", "Oxana Malaya",
        "Ellen Craft", "Henry Box Brown",
        "Harriet Tubman underground railroad",
        "Benedikt Magnusson", "Zydrunas Savickas",
        "Mariusz Pudzianowski", "Brian Shaw",
        "Leonid Stadnik", "Sultan Kosen",
        "Chandra Bahadur Dangi", "He Pingping",
        "Mikel Ruffinelli", "Cathie Jung",
        "Rolf Buchholz", "Lucky Diamond Rich",
        "Elaine Davidson", "Pauly Unstoppable",
    ],
    "dark_history": [
        "Witch trials in the early modern period",
        "Children's Crusade",
        "Taiping Rebellion",
        "Transatlantic slave trade",
        "Congo Free State",
        "Herero and Namaqua genocide",
        "Armenian genocide",
        "Nanking Massacre",
        "Bataan Death March",
        "Operation Meetinghouse",
        "Dresden bombing",
        "Hiroshima",
        "Nagasaki",
        "Atomic bombings of Hiroshima and Nagasaki",
        "Korean War",
        "Agent Orange",
        "My Lai massacre",
        "Khmer Rouge",
        "Cambodian genocide",
        "Ethiopian famine",
        "Sierra Leone Civil War",
        "Liberian Civil War",
        "Lord's Resistance Army",
        "Blood diamonds",
        "Apartheid",
        "Sharpeville massacre",
        "Steve Biko",
        "COINTELPRO",
        "Iran–Contra affair",
        "Guatemalan genocide",
        "Operation Condor",
        "Banana massacre",
        "United Fruit Company",
        "Belgian Congo",
        "Leopold II of Belgium",
        "Comfort women",
        "Unit 731",
        "Aktion T4",
        "Holocaust trains",
        "Sonderkommando",
        "Sobibor extermination camp",
        "Treblinka extermination camp",
        "Night of the Long Knives",
        "Kristallnacht",
        "Majdanek concentration camp",
        "Jasenovac concentration camp",
    ],
    "ocean_space": [
        "Io volcanic activity",
        "Europa ocean",
        "Enceladus water plumes",
        "Titan atmosphere",
        "Pluto geology",
        "Ceres dwarf planet",
        "Asteroid belt",
        "Kuiper belt",
        "Oort cloud",
        "Interstellar medium",
        "Nebula",
        "Pillars of Creation",
        "Horsehead Nebula",
        "Orion Nebula",
        "Crab Nebula",
        "Andromeda–Milky Way collision",
        "Local Group",
        "Virgo Supercluster",
        "Laniakea Supercluster",
        "Cosmic void",
        "Boötes void",
        "Cold spot",
        "Big Bang nucleosynthesis",
        "Inflation cosmology",
        "Heat death of the universe",
        "Big Rip",
        "Big Crunch",
        "White dwarf",
        "Brown dwarf",
        "Pulsar",
        "Magnetar",
        "Hypernova",
        "Pair-instability supernova",
        "Kilonova",
        "Gravitational microlensing",
        "Exoplanet",
        "Hot Jupiter",
        "Super-Earth",
        "Ocean planet",
        "Rogue planet",
        "Circumstellar habitable zone",
        "Panspermia",
        "Extremophile",
        "Thermophile",
        "Psychrophile",
        "Deep sea",
        "Hadal zone",
        "Abyssal plain",
        "Underwater volcano",
        "Black smoker",
        "Methane clathrate",
        "Brine pool",
        "Dead zone",
        "Sargasso Sea",
        "Antarctic Circumpolar Current",
        "Thermohaline circulation",
        "Rogue wave",
        "Tsunami",
        "Megatsunami",
    ],
    "world_news": [],
    "shocking_facts": [
        "Tarrare",
        "Charles Domery",
        "Pica disorder",
        "Autophagia",
        "Capgras delusion",
        "Fregoli delusion",
        "Alice in Wonderland syndrome",
        "Reduplicative paramnesia",
        "Alien hand syndrome",
        "Somatoparaphrenia",
        "Misophonia",
        "Morgellons",
        "Mass psychogenic illness",
        "Dancing mania",
        "Nodding disease",
        "Kuru disease",
        "Fatal familial insomnia",
        "Prion disease",
        "Bovine spongiform encephalopathy",
        "Chronic wasting disease",
        "Toxoplasma gondii",
        "Ophiocordyceps",
        "Zombie ant fungus",
        "Hairworm",
        "Cymothoa exigua",
        "Sacculina",
        "Jewel wasp",
        "Glyptapanteles",
        "Emerald cockroach wasp",
        "Ichneumon wasp",
        "Human experimentation in the United States",
        "Project MKULTRA",
        "Project Artichoke",
        "Operation Midnight Climax",
        "Edgewood Arsenal human experiments",
        "Holmesburg Prison",
        "Aversion Project",
        "CIA drug experiments",
        "Unethical human experimentation",
        "Radium jaw",
        "Phossy jaw",
        "Cavendish banana disease",
        "Panama disease",
        "Colony collapse disorder",
        "Insect decline",
        "Dead zones in the ocean",
        "Sixth mass extinction",
        "Permafrost thaw",
        "Methane bomb",
        "Geoengineering",
        "Solar geoengineering",
        "HAARP",
        "Scalar weapon",
        "Electronic warfare",
        "Directed-energy weapon",
        "Neutron bomb",
        "Cobalt bomb",
        "Tsar Bomba",
        "Nuclear winter",
    ],
}

# ── Post starters ─────────────────────────────────────────────────
STARTERS = [
    "Do you know that",
    "Did you know that",
    "Do you know that most people have never heard of",
    "Did you know that right now, as you read this,",
    "Do you know that somewhere on this planet,",
    "Did you know that for hundreds of years, people had no idea that",
    "Do you know that scientists still cannot fully explain",
    "Did you know that the thing you are about to read is completely real —",
    "Do you know that there is a creature on this Earth that",
    "Did you know that there is a true story that most schools never teach —",
    "Do you know that somewhere deep in history,",
    "Did you know that the world is hiding something that",
    "Do you know that every single day, millions of people walk past the truth about",
    "Did you know that one of the most shocking things ever discovered is",
    "Do you know that nature created something so unbelievable that",
    "Did you know that this actually happened and most people have no idea —",
    "Do you know that there is a real place on Earth where",
    "Did you know that the human body can do something that will completely shock you —",
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
            "posted_keys":    posted_keys,
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
        "Content-Type": "application/json",
    }
    payload = {
        "model":       "llama-3.3-70b-versatile",
        "messages":    [{"role": "user", "content": prompt}],
        "max_tokens":  900,
        "temperature": 0.85,
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

# ── Wikipedia fetch — full article + image ────────────────────────
def fetch_wikipedia(topic):
    try:
        api_url = (
            "https://en.wikipedia.org/w/api.php"
            "?action=query&prop=extracts&exintro=false&explaintext=true"
            "&redirects=1&format=json&titles=" + requests.utils.quote(topic)
        )
        r = requests.get(
            api_url, headers={"User-Agent": "TheyNeverToldUs/1.0"}, timeout=15
        )
        if r.status_code != 200:
            return None

        pages = r.json().get("query", {}).get("pages", {})
        page  = next(iter(pages.values()))
        if "missing" in page:
            log(f"[WIKI] Page missing: {topic}")
            return None
        full_text = page.get("extract", "")

        # Image strategy 1 — summary API
        image_url = None
        sum_url = (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + requests.utils.quote(topic.replace(" ", "_"))
        )
        sr = requests.get(
            sum_url, headers={"User-Agent": "TheyNeverToldUs/1.0"}, timeout=10
        )
        if sr.status_code == 200:
            sd = sr.json()
            if "originalimage" in sd:
                image_url = sd["originalimage"]["source"]
            elif "thumbnail" in sd:
                image_url = re.sub(r'/\d+px-', '/1200px-', sd["thumbnail"]["source"])

        # Image strategy 2 — pageimages API
        if not image_url:
            pi_url = (
                "https://en.wikipedia.org/w/api.php"
                "?action=query&prop=pageimages&pithumbsize=1200"
                "&redirects=1&format=json&titles=" + requests.utils.quote(topic)
            )
            pr = requests.get(
                pi_url, headers={"User-Agent": "TheyNeverToldUs/1.0"}, timeout=10
            )
            if pr.status_code == 200:
                pp    = next(iter(pr.json().get("query", {}).get("pages", {}).values()))
                thumb = pp.get("thumbnail", {})
                if thumb.get("source"):
                    image_url = thumb["source"]

        log(f"[WIKI] Image {'found' if image_url else 'not found'} for: {topic}")
        return {
            "title":     page.get("title", topic),
            "summary":   full_text[:3000],
            "image_url": image_url,
        }

    except Exception as e:
        log(f"[WIKI] Error fetching {topic}: {e}")
    return None

# ── Download and validate image ───────────────────────────────────
def download_image(image_url):
    if not image_url:
        return None
    try:
        r = requests.get(
            image_url,
            headers={"User-Agent": "TheyNeverToldUs/1.0"},
            timeout=20,
        )
        if r.status_code != 200:
            log(f"[IMAGE] HTTP {r.status_code}")
            return None
        content_type = r.headers.get("Content-Type", "")
        if "svg" in content_type.lower() or image_url.lower().endswith(".svg"):
            log("[IMAGE] Rejected SVG")
            return None
        if len(r.content) < 5000:
            log(f"[IMAGE] Too small ({len(r.content)} bytes)")
            return None
        log(f"[IMAGE] Downloaded {len(r.content)//1024}KB")
        return r.content
    except Exception as e:
        log(f"[IMAGE] Exception: {e}")
    return None

# ── Pexels image fallback ─────────────────────────────────────────
def fetch_pexels_image(query, category):
    def _search(q):
        try:
            r = requests.get(
                PEXELS_URL,
                headers={"Authorization": PEXELS_KEY},
                params={"query": q, "per_page": 15, "orientation": "landscape"},
                timeout=15,
            )
            if r.status_code != 200:
                log(f"[PEXELS] HTTP {r.status_code} for: {q}")
                return None
            photos = r.json().get("photos", [])
            if not photos:
                return None
            photo = random.choice(photos[:10])
            return photo.get("src", {}).get("large2x") or photo.get("src", {}).get("original")
        except Exception as e:
            log(f"[PEXELS] Exception for '{q}': {e}")
            return None

    url = _search(query)
    if not url:
        fallback = PEXELS_CATEGORY_FALLBACK.get(category, "nature")
        log(f"[PEXELS] No result for '{query}', trying fallback: '{fallback}'")
        url = _search(fallback)
    if not url:
        log("[PEXELS] No image found")
        return None
    return download_image(url)

# ── Get image: Wikipedia first, Pexels fallback ───────────────────
def get_image(wiki_image_url, topic, category):
    img = download_image(wiki_image_url)
    if img:
        log("[IMAGE] Using Wikipedia image")
        return img
    log(f"[IMAGE] Wikipedia failed, trying Pexels for: {topic}")
    img = fetch_pexels_image(topic, category)
    if img:
        log("[IMAGE] Using Pexels image")
        return img
    log(f"[IMAGE] No image found for: {topic}")
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
                timeout=30,
            )
        else:
            r = requests.post(
                FB_POST_URL,
                data={"message": message, "access_token": FB_TOKEN},
                timeout=15,
            )
        if r.status_code == 200:
            log(f"[POSTED] {'with image' if image_bytes else 'text only'} — {message[:80]}...")
            return True
        log(f"[FB ERROR] {r.status_code} {r.text[:300]}")
    except Exception as e:
        log(f"[FB ERROR] {e}")
    return False

# ── Write fact post ───────────────────────────────────────────────
def write_fact_post(category, topic, wiki_data):
    info    = CATEGORY_INFO[category]
    emoji   = info["emoji"]
    starter = random.choice(STARTERS)
    summary = wiki_data["summary"]

    prompt = f"""You are a master storyteller writing for a Facebook page called "They Never Told Us". Your audience is mostly African people who love shocking, real stories told in simple English.

You have been given real facts about {topic}. Pick the most shocking, surprising and specific facts and turn them into a gripping story that feels like a wise friend whispering something incredible into your ear.

REAL FACTS ABOUT {topic.upper()}:
{summary}

Write the Facebook post following these instructions:

OPENING LINE: Start with "{starter}" then immediately give the single most shocking or surprising specific fact about {topic} — use a real number, size, speed, record, or event from the text above. Add {emoji} at the end of this line. This line must stop someone mid-scroll.

THE STORY: Write 4 to 5 sentences flowing naturally into each other like one connected story. Each sentence must introduce a completely NEW fact — never repeat or rephrase anything. Pull specific details — exact numbers, sizes, comparisons, records, events, behaviours, discoveries. Write like someone who cannot stop sharing the most incredible thing they just discovered.

THE CLOSER: One final sentence that leaves the reader amazed, unsettled or deeply grateful. No emoji. Make it land hard.

CALL TO ACTION — write exactly this on a new line:
🔔 Follow They Never Told Us — we post the craziest facts every single day.
Tag a friend who needs to see this 👇

STRICT RULES:
- Total length: 200 to 260 words
- Simple English only — a 13 year old must understand every word
- Maximum 2 emojis in the entire post
- No bullet points, no dashes, no numbered lines, no lists
- No titles, no headings, no section labels
- Every sentence must introduce NEW information — never repeat the same idea
- Only use facts from the text above — do not invent anything
- The opening starter must connect naturally and grammatically to the sentence
"""
    result = ask_groq(prompt)
    if result:
        return result + f"\n\n{HASHTAGS[category]}"
    return None

# ── Write news post ───────────────────────────────────────────────
def write_news_post(title, desc):
    starter = random.choice(STARTERS)

    prompt = f"""You are a master storyteller writing for a Facebook page called "They Never Told Us". Your audience is mostly African people. You write like a smart friend explaining important news in a gripping, clear and human way.

REAL NEWS HEADLINE: {title}
REAL NEWS DETAILS: {desc}

Write a Facebook post that reads like a short powerful story. Every sentence must add completely new information.

OPENING LINE: Start with "{starter}" then give the most shocking or important specific fact from this news. Add 🌍 at the end of this line. Make it impossible to stop reading.

THE STORY: Write 4 to 5 sentences explaining what happened, why it happened, who is affected, and why it matters for Africa and ordinary people. Each sentence must be completely new. Connect them naturally so the reader feels the full picture building.

THE CLOSER: One final powerful sentence about what this means or what might happen next. No emoji. Just weight.

CALL TO ACTION — write exactly this on a new line:
🔔 Follow They Never Told Us — we explain world news in simple English every single day.
Tag someone who needs to understand what is happening 👇

STRICT RULES:
- Total length: 200 to 260 words
- Simple English only — a 13 year old must understand every word
- Maximum 2 emojis in the entire post
- No bullet points, no dashes, no numbered lines, no lists
- No titles, no headings, no section labels
- Every sentence must introduce NEW information
- Only use facts from the headline and details above — do not invent anything
- The opening starter must connect naturally and grammatically to the sentence
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
                post_text   = write_news_post(item["title"], item["desc"])
                image_bytes = fetch_pexels_image(item["title"][:50], category)
                post_key    = key
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
                if wiki_data and len(wiki_data["summary"]) > 200:
                    post_text   = write_fact_post(category, topic, wiki_data)
                    image_bytes = get_image(wiki_data.get("image_url"), topic, category)
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
    log("Sources    : Wikipedia full extract + BBC RSS")
    log("Images     : Wikipedia → Pexels fallback")
    log("Writing    : Groq AI llama-3.3-70b — story style, real facts")
    log("Interval   : Every 1 hour")
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
