import os, requests
from dotenv import load_dotenv

load_dotenv()

FB_TOKEN   = os.getenv("FB_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
GROQ_KEY   = os.getenv("GROQ_KEY")

def check_vars():
    print("Checking variables...\n")
    ok = True
    for name, val in [
        ("FB_TOKEN",   FB_TOKEN),
        ("FB_PAGE_ID", FB_PAGE_ID),
        ("GROQ_KEY",   GROQ_KEY),
    ]:
        if not val:
            print(f"❌ {name} NOT set")
            ok = False
        else:
            print(f"✅ {name} loaded")
    return ok

def test_groq():
    print("\n--- Groq AI ---")
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": "Say hello in one word."}],
        "max_tokens": 10
    }
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers=headers, json=payload, timeout=15)
    print("✅ Groq OK!" if r.status_code == 200 else f"❌ FAILED: {r.status_code} {r.text[:200]}")

def test_wikipedia():
    print("\n--- Wikipedia + Image ---")
    r = requests.get(
        "https://en.wikipedia.org/api/rest_v1/page/summary/Mantis_shrimp",
        headers={"User-Agent": "TheyNeverToldUs/1.0"}, timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"✅ Wikipedia OK! Got: {data.get('title','?')}")
        # Test image download
        image_url = None
        if "originalimage" in data:
            image_url = data["originalimage"]["source"]
        elif "thumbnail" in data:
            image_url = data["thumbnail"]["source"].replace("320px", "1200px")
        if image_url:
            img = requests.get(image_url, headers={"User-Agent": "TheyNeverToldUs/1.0"}, timeout=20)
            if img.status_code == 200 and len(img.content) > 1000:
                print(f"✅ Wikipedia Image OK! Size: {len(img.content)//1024}KB")
            else:
                print(f"❌ Image download failed: {img.status_code}")
        else:
            print("⚠️  No image found for this article")
    else:
        print(f"❌ FAILED: {r.status_code}")

def test_bbc():
    print("\n--- BBC RSS ---")
    r = requests.get("https://feeds.bbci.co.uk/news/rss.xml",
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    print("✅ BBC RSS OK!" if r.status_code == 200 else f"❌ FAILED: {r.status_code}")

def test_facebook():
    print("\n--- Facebook ---")
    r = requests.post(
        f"https://graph.facebook.com/{FB_PAGE_ID}/feed",
        data={"message": "🧪 They Never Told Us bot test — delete this post ✅",
              "access_token": FB_TOKEN}, timeout=10)
    print("✅ Facebook OK!" if r.status_code == 200 else f"❌ FAILED: {r.status_code} {r.text[:200]}")

if __name__ == "__main__":
    print("=" * 50)
    print("  They Never Told Us — Full Test")
    print("=" * 50 + "\n")
    if check_vars():
        test_groq()
        test_wikipedia()
        test_bbc()
        test_facebook()
        print("\n✅ All tests done! Push to GitHub → Railway auto-deploys.")
    else:
        print("\n❌ Fix your variables first.")