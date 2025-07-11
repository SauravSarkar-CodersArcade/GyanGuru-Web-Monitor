# Latest
from flask import Flask, render_template, jsonify, request
import requests, hashlib, json, urllib3
from bs4 import BeautifulSoup
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)
URLS_FILE = "urls.json"

# Disable SSL warnings (not recommended in production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Load URLs from file
def load_urls():
    with open(URLS_FILE, "r") as f:
        return json.load(f)


# Save URLs to file
def save_urls(urls):
    with open(URLS_FILE, "w") as f:
        json.dump(urls, f, indent=2)


# Generate SHA256 hash
def get_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# Extract FULL HTML content using selector
# def extract_content(html, selector):
#     soup = BeautifulSoup(html, "html.parser")
#     element = soup.select_one(selector)
#     return str(element) if element else ""

def extract_content(html, selector):
    soup = BeautifulSoup(html, "html.parser")
    elements = soup.select(selector)
    text = " ".join(el.get_text(strip=True) for el in elements)
    return text



# Retry-enabled requests session
def get_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# Core logic to check updates
def check_websites():
    urls = load_urls()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
    }
    session = get_session()

    for site in urls:
        if site.get("paused"):
            continue
        try:
            response = session.get(site["url"], timeout=10, headers=headers, verify=False)
            html = response.text
            target = extract_content(html, site.get("selector")) if site.get("selector") else html
            new_hash = get_hash(target)
            # print(f"\n[{site['name']}] Extracted content:\n{target}\nHash: {new_hash}\nOld Hash: {site.get('last_hash')}\n")

            if site.get("last_hash") and new_hash != site["last_hash"]:
                site["updated"] = True
                site["update_count"] = site.get("update_count", 0) + 1
            else:
                site["updated"] = False

            site["last_hash"] = new_hash
            site["last_checked"] = datetime.now().strftime("%d %b, %I:%M %p")
        except Exception as e:
            site["updated"] = False
            site["last_checked"] = "Error"
            print(f"Error checking {site['name']}: {e}")
    save_urls(urls)


# Reset all metadata
def reset_all_sites():
    urls = load_urls()
    for site in urls:
        site["last_hash"] = ""
        site["last_checked"] = ""
        site["updated"] = False
        site["update_count"] = 0
        site["updates"] = 0
        site["hash"] = ""
        site["last_change"] = ""
    save_urls(urls)


# Routes

@app.route("/reset_all", methods=["POST"])
def reset_all():
    reset_all_sites()
    return jsonify({"status": "reset"})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status")
def status():
    check_websites()
    return jsonify(load_urls())


@app.route("/add", methods=["POST"])
def add_site():
    data = request.get_json()
    urls = load_urls()
    urls.append({
        "name": data["name"],
        "url": data["url"],
        "selector": data.get("selector", ""),
        "category": data.get("category", ""),
        "last_hash": "",
        "last_checked": "",
        "updated": False,
        "update_count": 0,
        "paused": False
    })
    save_urls(urls)
    return jsonify({"status": "ok"})


@app.route("/acknowledge/<path:name>", methods=["POST"])
def acknowledge(name):
    urls = load_urls()
    for site in urls:
        if site["name"] == name:
            site["update_count"] = 0
    save_urls(urls)
    return jsonify({"status": "acknowledged"})


@app.route("/remove/<path:name>", methods=["POST"])
def remove_site(name):
    urls = load_urls()
    urls = [site for site in urls if site["name"] != name]
    save_urls(urls)
    return jsonify({"status": "removed"})


@app.route("/pause/<path:name>", methods=["POST"])
def toggle_pause(name):
    urls = load_urls()
    for site in urls:
        if site["name"] == name:
            site["paused"] = not site.get("paused", False)
    save_urls(urls)
    return jsonify({"status": "toggled"})


# Start the app
if __name__ == "__main__":
    app.run(debug=True)
