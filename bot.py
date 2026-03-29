import os, json, time, random, requests, re, logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
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
PEXELS_KEY = os.getenv("PEXELS_KEY")

for var, val in [
    ("FB_TOKEN",   FB_TOKEN),
    ("FB_PAGE_ID", FB_PAGE_ID),
    ("GROQ_KEY",   GROQ_KEY),
    ("PEXELS_KEY", PEXELS_KEY),
]:
    if not val:
        raise SystemExit(f"[ERROR] Missing environment variable: {var}")

FB_POST_URL  = f"https://graph.facebook.com/{FB_PAGE_ID}/feed"
FB_PHOTO_URL = f"https://graph.facebook.com/{FB_PAGE_ID}/photos"
FB_VIDEO_URL = f"https://graph.facebook.com/{FB_PAGE_ID}/videos"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
PEXELS_URL   = "https://api.pexels.com/v1/search"
PEXELS_VID   = "https://api.pexels.com/videos/search"
STATE_FILE   = "state.json"
POST_INTERVAL = 3600  # 1 hour
AFRICA_TZ     = timezone(timedelta(hours=2))  # UTC+2
REEL_HOUR     = 19    # 7PM Africa time

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
    "crazy_humans":   "human athlete extreme sport",
    "dark_history":   "ancient history ruins monument",
    "ocean_space":    "ocean deep space stars galaxy",
    "world_news":     "world globe city people",
    "shocking_facts": "science discovery mind",
}

# ── Reel topics for Pexels videos ────────────────────────────────
REEL_TOPICS = [
    "ocean waves sunset", "wild animals Africa savanna",
    "deep sea creatures bioluminescence", "space galaxy milky way stars",
    "waterfall nature tropical", "lion hunting prey",
    "elephant herd walking", "whale underwater ocean",
    "coral reef colorful fish", "volcanic eruption lava",
    "northern lights aurora borealis", "cheetah running fast",
    "eagle flying mountains", "shark underwater blue ocean",
    "dolphins jumping ocean", "rainforest jungle green",
    "desert sand dunes sunset", "snow mountains peaks",
    "thunderstorm lightning dramatic", "river rapids waterfall",
    "birds of paradise dancing", "gorilla forest Africa",
    "polar bear arctic snow", "manta ray ocean diving",
    "jellyfish underwater glowing", "tornado storm dramatic",
    "meteor shower night sky", "hurricane aerial view",
    "giant waves surfing ocean", "fire flames dramatic",
]

# ── Safe Wikipedia topics ─────────────────────────────────────────
WIKI_TOPICS = {
    "animals_nature": [
        "Lyrebird", "Kakapo", "Frogfish", "Stonefish",
        "Mimic octopus", "Sea cucumber", "Crown-of-thorns starfish",
        "Mantis shrimp", "Snapping shrimp", "Giant clam",
        "Whale shark", "Basking shark", "Greenland shark",
        "Oarfish", "Frilled shark", "Goblin shark",
        "Dumbo octopus", "Firefly squid", "Japanese spider crab",
        "Flamingo", "Shoebill stork", "Sword-billed hummingbird",
        "Potoo bird", "Bowerbird", "Birds-of-paradise",
        "Sun bear", "Binturong", "Clouded leopard",
        "Serval", "Caracal", "Maned wolf",
        "African wild dog", "Aardvark", "Aardwolf",
        "Pygmy hippopotamus", "Irrawaddy dolphin", "Amazon river dolphin",
        "Sea otter", "Giant otter", "Walrus",
        "Leopard seal", "Quoll", "Numbat",
        "Glass frog", "Poison dart frog", "Purple frog",
        "Olm", "Chinese giant salamander",
        "Thorny devil", "Marine iguana", "Gharial",
        "Leatherback sea turtle", "Gaboon viper", "Boomslang",
        "Titan arum", "Welwitschia", "Bristlecone pine",
        "Rainbow eucalyptus", "Sandbox tree", "Manchineel tree",
        "Pistol shrimp", "Honey badger", "Wolverine",
        "Tasmanian devil", "Aye-aye", "Naked mole rat",
        "Blobfish", "Anglerfish", "Vampire squid",
        "Giant squid", "Colossal squid", "Bullet ant",
        "Goliath birdeater", "Coconut crab", "Titan beetle",
        "Capybara", "Pangolin", "Okapi", "Saiga antelope",
        "Harpy eagle", "Andean condor", "Secretary bird",
        "Cassowary", "Komodo dragon", "Immortal jellyfish",
        "Tardigrade", "Axolotl", "Platypus", "Archerfish",
        "Electric eel", "Bombardier beetle", "Army ant",
        "Dung beetle", "Africanized bee", "Trap-jaw ant",
        "Blue-ringed octopus", "Cone snail", "Box jellyfish",
        "Irukandji jellyfish", "Inland taipan", "Black mamba",
        "King cobra", "Reticulated python", "Green anaconda",
    ],
    "crazy_humans": [
        "Wim Hof", "Dean Karnazes", "Scott Jurek",
        "David Blaine", "Harry Houdini", "Michel Lotito",
        "Stig Severinsen", "Isao Machii", "Bob Munden",
        "Tim Cridland", "Etibar Elchiyev",
        "Slavomir Rawicz", "Hiroo Onoda", "Teruo Nakamura",
        "Hugh Glass", "John Colter", "Ada Blackjack",
        "Shackleton expedition", "Ernest Shackleton",
        "Benedikt Magnusson", "Zydrunas Savickas",
        "Mariusz Pudzianowski", "Brian Shaw",
        "Sultan Kosen", "Chandra Bahadur Dangi",
        "Robert Wadlow", "Jon Brower Minnoch",
        "Roy Sullivan", "Tsutomu Yamaguchi",
        "Vesna Vulovic", "Nicholas Alkemade",
        "Juliane Koepcke", "Aron Ralston",
        "Beck Weathers", "Phineas Gage",
        "Kim Peek", "Daniel Tammet", "Stephen Wiltshire",
        "Angus Barbieri", "Charles Osborne",
        "Prahlad Jani", "Mirin Dajo",
        "Lina Medina", "Walter Hudson",
        "Rolf Buchholz", "Lucky Diamond Rich",
        "Elaine Davidson", "Tom Leppard",
        "Erik Weihenmayer", "Diana Nyad",
        "Philippe Petit", "Alex Honnold",
        "Alain Robert", "Joe Simpson mountaineer",
        "Mauro Prosperi", "Yves Rossy",
        "Felix Baumgartner", "Natasha Demkina",
        "Leonid Stadnik", "He Pingping",
        "Mikel Ruffinelli", "Cathie Jung",
        "Pauly Unstoppable", "Harriet Tubman underground railroad",
        "Henry Box Brown", "Ellen Craft",
        "Oxana Malaya", "Genie Wiley",
        "Victor of Aveyron", "Wild Peter",
        "Kaspar Hauser", "Tim Friede",
        "Hugh Herr", "Nick Vujicic",
    ],
    "dark_history": [
        "Dancing plague of 1518", "Great Molasses Flood",
        "Radium Girls", "Triangle Shirtwaist Factory fire",
        "Emu War", "Tanganyika laughter epidemic",
        "Great Pacific garbage patch", "Aral Sea",
        "Bhopal disaster", "Chernobyl disaster",
        "Tunguska event", "Chelyabinsk meteor",
        "Pompeii", "Vesuvius eruption",
        "Black Death", "Spanish flu",
        "Great Smog of London", "Minamata disease",
        "Thalidomide", "Agent Orange",
        "Opium Wars", "East India Company",
        "Tulsa race massacre", "Rosewood massacre",
        "Jonestown", "Heaven's Gate",
        "Dyatlov Pass incident", "Mary Celeste",
        "SS Ourang Medan", "Tamam Shud case",
        "Voynich manuscript", "Antikythera mechanism",
        "Roanoke Colony", "Kaspar Hauser",
        "Bermuda Triangle", "Philadelphia Experiment",
        "Wow! signal", "Hessdalen lights",
        "Taos Hum", "Nazca Lines",
        "Baghdad Battery", "Sacsayhuaman",
        "Easter Island", "Stonehenge",
        "Great Zimbabwe", "Timbuktu",
        "Ancient Egypt mummies", "Terracotta Army",
        "Machu Picchu", "Angkor Wat",
        "Petra Jordan", "Carthage",
        "Roman concrete", "Greek fire",
        "Viking longships", "Mongol Empire",
        "Silk Road", "Spice trade",
        "Witch trials in the early modern period",
        "Children's Crusade",
        "Taiping Rebellion",
        "Transatlantic slave trade",
        "Congo Free State",
        "Leopold II of Belgium",
        "Herero and Namaqua genocide",
        "Armenian genocide",
        "Nanking Massacre",
        "Bataan Death March",
        "Operation Meetinghouse",
        "Dresden bombing",
        "Atomic bombings of Hiroshima and Nagasaki",
        "Korean War",
        "My Lai massacre",
        "Khmer Rouge",
        "Cambodian genocide",
        "Ethiopian famine",
        "Sierra Leone Civil War",
        "Lord's Resistance Army",
        "Blood diamonds",
        "Apartheid",
        "Sharpeville massacre",
        "Steve Biko",
        "COINTELPRO",
        "Iran-Contra affair",
        "Guatemalan genocide",
        "Operation Condor",
        "Banana massacre",
        "United Fruit Company",
        "Belgian Congo",
        "Comfort women",
        "Unit 731",
        "Aktion T4",
        "Night of the Long Knives",
        "Kristallnacht",
        "Sobibor extermination camp",
        "Treblinka extermination camp",
        "Majdanek concentration camp",
        "Rwandan genocide",
        "Srebrenica massacre",
        "Holodomor",
        "Great Leap Forward",
        "Tuskegee syphilis experiment",
        "MKUltra",
        "Operation Paperclip",
        "Stolen generations",
        "Oxana Malaya",
        "Feral children",
        "Wild Peter",
        "Victor of Aveyron",
        "Genie Wiley",
    ],
    "ocean_space": [
        "Io volcanic activity", "Europa ocean",
        "Enceladus water plumes", "Titan atmosphere",
        "Pluto geology", "Ceres dwarf planet",
        "Asteroid belt", "Kuiper belt", "Oort cloud",
        "Nebula", "Pillars of Creation",
        "Horsehead Nebula", "Orion Nebula",
        "Andromeda galaxy", "Local Group",
        "Virgo Supercluster", "Laniakea Supercluster",
        "Cosmic void", "Bootes void",
        "Big Bang", "Heat death of the universe",
        "White dwarf", "Brown dwarf",
        "Pulsar", "Magnetar", "Hypernova",
        "Kilonova", "Gravitational wave",
        "Black hole", "Event horizon",
        "Sagittarius A*", "Quasar",
        "Fast radio burst", "Fermi paradox",
        "Drake equation", "Dyson sphere",
        "Mariana Trench", "Challenger Deep",
        "Bioluminescence", "Hydrothermal vent",
        "Deep sea fish", "Megalodon",
        "Hadal zone", "Abyssal plain",
        "Underwater volcano", "Black smoker",
        "Brine pool", "Sargasso Sea",
        "Rogue wave", "Tsunami", "Megatsunami",
        "Antarctic Circumpolar Current",
        "Thermohaline circulation",
        "Great Barrier Reef", "Dead zone ocean",
        "Methane clathrate", "Ocean plastic",
        "Deepwater Horizon", "Titanic wreck",
        "Exoplanet", "Hot Jupiter", "Super-Earth",
        "Rogue planet", "Panspermia", "Extremophile",
        "Pale Blue Dot", "Voyager 1", "Oumuamua",
    ],
    "world_news": [],  # handled by BBC RSS
    "shocking_facts": [
        "Tarrare", "Charles Domery", "Pica disorder",
        "Capgras delusion", "Alice in Wonderland syndrome",
        "Alien hand syndrome", "Foreign accent syndrome",
        "Misophonia", "Mass psychogenic illness",
        "Dancing mania", "Fatal familial insomnia",
        "Prion disease", "Kuru disease",
        "Toxoplasma gondii", "Ophiocordyceps",
        "Zombie ant fungus", "Hairworm",
        "Cymothoa exigua", "Sacculina",
        "Jewel wasp", "Emerald cockroach wasp",
        "Human microbiome", "Sleep paralysis",
        "Exploding head syndrome",
        "Project MKULTRA", "Tuskegee syphilis experiment",
        "Radium jaw", "Phossy jaw",
        "Cavendish banana disease", "Colony collapse disorder",
        "Insect decline", "Sixth mass extinction",
        "Permafrost thaw", "Geoengineering",
        "HAARP", "Tsar Bomba", "Nuclear winter",
        "Stanford prison experiment", "Milgram experiment",
        "Bystander effect", "Dunning-Kruger effect",
        "Stockholm syndrome", "Gaslighting psychology",
        "Subliminal advertising", "Propaganda techniques",
        "Sugar industry history", "Tobacco industry",
        "Opioid epidemic", "Pharmaceutical industry",
        "Microplastics", "Forever chemicals",
        "Cambridge Analytica", "Edward Snowden",
        "Panama Papers", "Wikileaks",
        "Deep web", "Dark web",
        "Human trafficking statistics", "Modern slavery",
        "Food desert", "Water scarcity",
        "Cavendish banana extinction", "Seed bank",
        "Doomsday Clock", "Svalbard Global Seed Vault",
        "Dead hand nuclear", "Broken Arrow nuclear",
        "Cobalt bomb", "Neutron bomb",
        "Biological warfare history", "Chemical warfare history",
        "Bovine spongiform encephalopathy", "Chronic wasting disease",
        "Nodding disease", "Morgellons",
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
    "Did you know that the world has been hiding something that",
    "Do you know that every single day, millions of people walk past the truth about",
    "Did you know that one of the most shocking things ever discovered is",
    "Do you know that nature created something so unbelievable that",
    "Did you know that this actually happened and most people have no idea —",
    "Do you know that there is a real place on Earth where",
    "Did you know that the human body can do something that will completely shock you —",
    "Do you know that deep in the ocean, there exists something that",
    "Did you know that somewhere in space, there is a place where",
]

# ── Hashtags per category ─────────────────────────────────────────
HASHTAGS = {
    "animals_nature": "#TheyNeverToldUs #Animals #Nature #Facts #DidYouKnow #Wildlife #Africa",
    "crazy_humans":   "#TheyNeverToldUs #CrazyHumans #Facts #DidYouKnow #Unbelievable #Africa",
    "dark_history":   "#TheyNeverToldUs #DarkHistory #Facts #History #HiddenTruth #Africa",
    "ocean_space":    "#TheyNeverToldUs #Space #Ocean #Facts #DidYouKnow #Universe #Africa",
    "world_news":     "#TheyNeverToldUs #WorldNews #Africa #Breaking #News #StayInformed",
    "shocking_facts": "#TheyNeverToldUs #ShockingFacts #Facts #DidYouKnow #HiddenTruth #Africa",
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
                    d.get("reel_posted_date", ""),
                )
        except Exception:
            pass
    return 0, 0, {}, ""

last_post_time, category_index, posted_keys, reel_posted_date = load_state()

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump({
            "last_post_time":   last_post_time,
            "category_index":   category_index,
            "posted_keys":      posted_keys,
            "reel_posted_date": reel_posted_date,
        }, f)

def is_posted(key):
    if key not in posted_keys:
        return False
    return (time.time() - posted_keys[key]) < (30 * 24 * 3600)

def mark_posted(key):
    posted_keys[key] = time.time()
    cutoff = time.time() - (31 * 24 * 3600)
    for k in [k for k, v in list(posted_keys.items()) if v < cutoff]:
        del posted_keys[k]

# ── Africa time helper ────────────────────────────────────────────
def africa_now():
    return datetime.now(AFRICA_TZ)

# ── Groq AI with retry ────────────────────────────────────────────
def ask_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       "llama-3.3-70b-versatile",
        "messages":    [{"role": "user", "content": prompt}],
        "max_tokens":  900,
        "temperature": 0.85,
    }
    for attempt in range(3):
        try:
            r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=25)
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
        r = requests.get(api_url, headers={"User-Agent": "TheyNeverToldUs/1.0"}, timeout=15)
        if r.status_code != 200:
            return None
        pages = r.json().get("query", {}).get("pages", {})
        page  = next(iter(pages.values()))
        if "missing" in page:
            log(f"[WIKI] Page missing: {topic}")
            return None
        full_text = page.get("extract", "")

        # Image — strategy 1: summary API
        image_url = None
        sum_url = (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + requests.utils.quote(topic.replace(" ", "_"))
        )
        sr = requests.get(sum_url, headers={"User-Agent": "TheyNeverToldUs/1.0"}, timeout=10)
        if sr.status_code == 200:
            sd = sr.json()
            if "originalimage" in sd:
                image_url = sd["originalimage"]["source"]
            elif "thumbnail" in sd:
                image_url = re.sub(r'/\d+px-', '/1200px-', sd["thumbnail"]["source"])

        # Image — strategy 2: pageimages API
        if not image_url:
            pi_url = (
                "https://en.wikipedia.org/w/api.php"
                "?action=query&prop=pageimages&pithumbsize=1200"
                "&redirects=1&format=json&titles=" + requests.utils.quote(topic)
            )
            pr = requests.get(pi_url, headers={"User-Agent": "TheyNeverToldUs/1.0"}, timeout=10)
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

# ── Download image ────────────────────────────────────────────────
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

# ── Pexels photo fallback ─────────────────────────────────────────
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

# ── Pexels video for reel ─────────────────────────────────────────
def fetch_pexels_video(query):
    try:
        r = requests.get(
            PEXELS_VID,
            headers={"Authorization": PEXELS_KEY},
            params={
                "query":    query,
                "per_page": 10,
                "orientation": "portrait",  # vertical = better for reels
                "size":     "large",
            },
            timeout=15,
        )
        if r.status_code != 200:
            log(f"[PEXELS VIDEO] HTTP {r.status_code}")
            return None
        videos = r.json().get("videos", [])
        if not videos:
            log(f"[PEXELS VIDEO] No videos for: {query}")
            return None

        # Pick highest quality video file
        video = random.choice(videos[:5])
        video_files = video.get("video_files", [])
        # Sort by quality — prefer HD
        hd_files = [v for v in video_files if v.get("quality") in ("hd", "uhd")]
        if not hd_files:
            hd_files = video_files
        hd_files.sort(key=lambda x: x.get("width", 0), reverse=True)
        best = hd_files[0]
        video_url = best.get("link")
        if not video_url:
            return None

        log(f"[PEXELS VIDEO] Found: {video_url[:60]}...")
        # Download video
        vr = requests.get(video_url, timeout=120, stream=True)
        if vr.status_code != 200:
            log(f"[PEXELS VIDEO] Download failed: {vr.status_code}")
            return None
        video_bytes = b"".join(vr.iter_content(chunk_size=1024*1024))
        if len(video_bytes) < 50000:
            log("[PEXELS VIDEO] Too small")
            return None
        log(f"[PEXELS VIDEO] Downloaded {len(video_bytes)//1024//1024}MB")
        return video_bytes

    except Exception as e:
        log(f"[PEXELS VIDEO] Exception: {e}")
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

# ── Post reel to Facebook ─────────────────────────────────────────
def post_reel_to_facebook(caption, video_bytes):
    try:
        r = requests.post(
            FB_VIDEO_URL,
            files={"source": ("reel.mp4", video_bytes, "video/mp4")},
            data={
                "description":  caption,
                "access_token": FB_TOKEN,
                "published":    "true",
            },
            timeout=180,
        )
        if r.status_code == 200:
            log(f"[REEL POSTED] {caption[:80]}...")
            return True
        log(f"[REEL ERROR] {r.status_code} {r.text[:300]}")
    except Exception as e:
        log(f"[REEL ERROR] {e}")
    return False

# ── Write reel caption with Groq ──────────────────────────────────
def write_reel_caption(topic):
    prompt = f"""You write captions for a Facebook Reels video for a page called "They Never Told Us". Your audience is mostly African people.

The video is about: {topic}

Write a short, punchy reel caption that:
- Opens with one shocking or amazing sentence about {topic}
- 2 to 3 more short sentences that build excitement
- Ends with this exact line: 🔔 Follow They Never Told Us for daily facts that will blow your mind.

Rules:
- Maximum 80 words total
- Simple English only
- Maximum 3 emojis in the whole caption
- No bullet points, no headings, no lists
- Make it feel urgent and exciting
- Add these hashtags at the end on a new line: #TheyNeverToldUs #Nature #Facts #Reels #Africa #DidYouKnow
"""
    return ask_groq(prompt)

# ── Write fact post with Groq ─────────────────────────────────────
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
- Maximum 2 emojis in the entire post — only the opening line emoji and the call to action emoji
- No bullet points, no dashes, no numbered lines, no lists
- No titles, no headings, no section labels — just flowing paragraphs
- Every sentence must introduce NEW information — never repeat the same idea twice
- Only use facts from the text above — do not invent anything
- The opening starter must connect naturally and grammatically to the sentence that follows it
"""
    result = ask_groq(prompt)
    if result:
        return result + f"\n\n{HASHTAGS[category]}"
    return None

# ── Write news post with Groq ─────────────────────────────────────
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
- No titles, no headings, no section labels — just flowing paragraphs
- Every sentence must introduce NEW information
- Only use facts from the headline and details above — do not invent anything
- The opening starter must connect naturally and grammatically to the sentence that follows it
"""
    result = ask_groq(prompt)
    if result:
        return result + f"\n\n{HASHTAGS['world_news']}"
    return None

# ── Daily reel handler ────────────────────────────────────────────
def handle_reel():
    global reel_posted_date
    today = africa_now().strftime("%Y-%m-%d")
    if reel_posted_date == today:
        return False

    log("\n[REEL] Time for daily reel!")
    topic = random.choice(REEL_TOPICS)
    log(f"[REEL] Topic: {topic}")

    video_bytes = fetch_pexels_video(topic)
    if not video_bytes:
        # Try another topic
        topic = random.choice(REEL_TOPICS)
        log(f"[REEL] Retrying with: {topic}")
        video_bytes = fetch_pexels_video(topic)

    if not video_bytes:
        log("[REEL] Could not get video. Skipping today.")
        return False

    caption = write_reel_caption(topic)
    if not caption:
        log("[REEL] Groq failed for caption.")
        return False

    if post_reel_to_facebook(caption, video_bytes):
        reel_posted_date = today
        save_state()
        log(f"[REEL] ✅ Daily reel posted! Topic: {topic}")
        return True

    return False

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
        log(f"[BOT] ✅ Posted! Next: {CATEGORY_INFO[next_cat]['name']}")
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
    log("Reels      : Daily at 7PM Africa time via Pexels HD video")
    log("Writing    : Groq llama-3.3-70b — story style, no headings")
    log("Interval   : Every 1 hour")
    log("No repeats : 30 day cooldown per topic")
    log("")

    while True:
        try:
            now      = time.time()
            elapsed  = now - last_post_time
            af_now   = africa_now()
            af_hour  = af_now.hour

            # Check reel time — 7PM Africa time
            if af_hour == REEL_HOUR:
                handle_reel()

            # Regular hourly post
            if elapsed >= POST_INTERVAL:
                log(f"[{af_now.strftime('%H:%M:%S')} Africa] Time to post!")
                make_post()
            else:
                remaining = int((POST_INTERVAL - elapsed) / 60)
                log(f"[{af_now.strftime('%H:%M:%S')} Africa] Next post in {remaining} mins.")

        except Exception as e:
            log(f"[ERROR] {e}")

        time.sleep(60)

if __name__ == "__main__":
    run()
