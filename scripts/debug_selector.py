# This script is for testing new URLs and CSS selectors manually.

import requests
from bs4 import BeautifulSoup
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load the URLs data from urls.json
with open('../urls.json', 'r', encoding='utf-8') as f:
    urls = json.load(f)

# Display all available site names
print("Available websites:")
for idx, site in enumerate(urls):
    print(f"{idx + 1}. {site['name']}")

# Ask user to choose a site
choice = input("\nEnter the number of the website you want to inspect (1 - {}): ".format(len(urls)))

# Validate input
try:
    idx = int(choice) - 1
    if idx < 0 or idx >= len(urls):
        print("Invalid selection.")
        exit()
except ValueError:
    print("Invalid input.")
    exit()

site = urls[idx]
url = site["url"]
selector = site.get("selector", "").strip()

print(f"\n🔍 Fetching content from: {url}")
print(f"📌 CSS Selector: {selector if selector else 'Entire Page'}\n")

try:
    response = requests.get(url, timeout=15, verify=False)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    if selector:
        elements = soup.select(selector)
        if elements:
            for i, el in enumerate(elements, 1):
                print(f"\n----- Element {i} -----")
                print(el.get_text(strip=True) or "[No visible text]")
                print("-----------------------")
        else:
            print("❌ No element found matching the given selector.")
    else:
        print("🌐 Full Page Content:")
        print(soup.get_text())

except requests.exceptions.RequestException as e:
    print("🚨 Error fetching content:", e)
