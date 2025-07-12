from flask import Flask, render_template, request, redirect, jsonify
from bs4 import BeautifulSoup
from datetime import datetime
import json, hashlib, os, requests
from flask_apscheduler import APScheduler  # ✅ Scheduler added

app = Flask(__name__)
scheduler = APScheduler()
scheduler.api_enabled = True

URLS_FILE = 'urls.json'
HEADERS = {'User-Agent': 'Mozilla/5.0'}


def load_urls():
    with open(URLS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_urls(urls):
    with open(URLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(urls, f, indent=2)


def get_session():
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def monitor_urls():
    urls = load_urls()
    session = get_session()
    for entry in urls:
        if entry.get("paused"):
            continue
        try:
            res = session.get(entry["url"], headers=HEADERS, timeout=10)
            soup = BeautifulSoup(res.content, 'html.parser')
            selected = soup.select_one(entry["selector"])
            if not selected:
                continue
            content = selected.decode_contents()
            content_hash = get_hash(content)

            if "hash_history" not in entry:
                entry["hash_history"] = []

            if not any(h["hash"] == content_hash for h in entry["hash_history"]):
                entry["hash_history"].append({
                    "hash": content_hash,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "content": content
                })
                entry["update_count"] = entry.get("update_count", 0) + 1
                entry["acknowledged"] = False

            # ✅ Always update last checked
            entry["last_checked"] = datetime.now().strftime("%d %b, %I:%M %p")

        except Exception as e:
            print(f"Error checking {entry['name']}: {e}")
    save_urls(urls)


@app.route('/')
def index():
    urls = load_urls()
    categories = sorted(set(u.get("category", "Uncategorized").capitalize() for u in urls))
    return render_template('index.html', urls=urls, categories=categories)


@app.route('/add', methods=['POST'])
def add():
    urls = load_urls()
    data = request.form
    name = data['name']
    url = data['url']
    selector = data['selector']
    category = data['category'].capitalize()

    session = get_session()
    try:
        res = session.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        selected = soup.select_one(selector)
        if not selected:
            return "Selector not found", 400
        content = selected.decode_contents()
        content_hash = get_hash(content)
    except:
        return "Failed to fetch URL or selector", 400

    entry = {
        "name": name,
        "url": url,
        "selector": selector,
        "category": category,
        "paused": False,
        "update_count": 0,
        "acknowledged": False,
        "last_checked": datetime.now().strftime("%d %b, %I:%M %p"),
        "hash_history": [{
            "hash": content_hash,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": content
        }]
    }
    urls.append(entry)
    save_urls(urls)
    return redirect('/')


@app.route('/acknowledge/<int:index>')
def acknowledge(index):
    urls = load_urls()
    urls[index]["acknowledged"] = True
    urls[index]["update_count"] = 0  # ✅ Reset count on acknowledge
    save_urls(urls)
    return redirect('/')


@app.route('/remove/<int:index>')
def remove(index):
    urls = load_urls()
    urls.pop(index)
    save_urls(urls)
    return redirect('/')


@app.route('/pause/<int:index>')
def pause(index):
    urls = load_urls()
    urls[index]["paused"] = not urls[index].get("paused", False)
    save_urls(urls)
    return redirect('/')


@app.route('/reset/<int:index>')
def reset(index):
    urls = load_urls()
    urls[index]["update_count"] = 0
    urls[index]["acknowledged"] = False
    save_urls(urls)
    return redirect('/')


@app.route('/reset_all', methods=['POST'])
def reset_all():
    urls = load_urls()
    for site in urls:
        site["update_count"] = 0
        site["acknowledged"] = False
    save_urls(urls)
    return jsonify({"status": "reset"})


@app.route('/updates/<int:index>')
def get_updates(index):
    urls = load_urls()
    return jsonify(urls[index].get("hash_history", []))


# ✅ Schedule background monitoring every 5 minutes
@scheduler.task('interval', id='monitor_task', minutes=5)
def scheduled_monitor():
    print(f"[{datetime.now()}] ⏲️ Scheduled monitoring triggered.")
    monitor_urls()


@app.route('/table-data')
def table_data():
    urls = load_urls()
    return render_template('table_body.html', urls=urls)
    # return render_template('table_body.html', urls=urls), 200, {'Content-Type': 'text/html'}


if __name__ == '__main__':
    scheduler.init_app(app)
    scheduler.start()
    app.run(debug=True)


