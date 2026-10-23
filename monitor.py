import csv
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

SOURCE_FILE = Path("surse_presa_constanta_seed.csv")
OUTPUT_FILE = Path("stiri_detectate.json")
USER_AGENT = "Mozilla/5.0 (compatible; NewsroomAI/1.0)"

def load_sources():
    with SOURCE_FILE.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def find_value(row, words):
    for key, value in row.items():
        if key and value and any(word in key.lower() for word in words):
            return value.strip()
    return ""

def google_news_feed(query):
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "ro",
        "gl": "RO",
        "ceid": "RO:ro"
    })
    return "https://news.google.com/rss/search?" + params

def read_feed(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read()
    root = ET.fromstring(data)
    articles = []
    for item in root.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        date = item.findtext("pubDate", "").strip()
        if title and link:
            articles.append({"titlu": title, "link": link, "data": date})
    return articles

def main():
    sources = load_sources()
    articles = []
    errors = []
    seen = set()
    for row in sources:
        name = find_value(row, ["nume", "name", "publicatie", "sursa"]) or "Sursa necunoscuta"
        domain = find_value(row, ["domeniu", "domain", "website", "site", "url"])
        feed = find_value(row, ["rss", "feed"])
        if not domain and not feed:
            errors.append({"sursa": name, "eroare": "Lipseste domeniul si RSS"})
            continue
        urls = []
        if feed.startswith("http"):
            urls.append(feed)
        if domain:
            host = urllib.parse.urlparse(domain if "://" in domain else "https://" + domain).netloc
            if host:
                urls.append(google_news_feed("site:" + host))
        success = False
        for url in dict.fromkeys(urls):
            try:
                results = read_feed(url)
                success = True
                for item in results:
                    if item["link"] not in seen:
                        seen.add(item["link"])
                        item["sursa"] = name
                        articles.append(item)
                if results:
                    break
            except Exception as exc:
                errors.append({"sursa": name, "feed": url, "eroare": str(exc)})
        if not success:
            print("Nu s-a putut citi:", name)
    output = {
        "generat_la": datetime.now(timezone.utc).isoformat(),
        "surse": len(sources),
        "articole": articles,
        "erori": errors
    }
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Surse:", len(sources))
    print("Articole identificate:", len(articles))
    print("Erori:", len(errors))

if __name__ == "__main__":
    main()
