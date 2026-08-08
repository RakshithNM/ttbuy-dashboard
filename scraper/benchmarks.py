import json
import os
import requests
from bs4 import BeautifulSoup

from scraper.core import TARGET_CURRENCIES, fetch_rendered_html

DATA_DIR = os.environ.get("TTBUY_DATA_DIR", "data")
BENCHMARKS_PATH = os.path.join(DATA_DIR, "benchmarks.json")

def fetch_mid_market_rates():
    rates = {}
    for currency in TARGET_CURRENCIES:
        if currency == "AED":
            continue

        try:
            res = requests.get(f"https://api.frankfurter.app/latest?from={currency}&to=INR", timeout=10)
            if res.status_code == 200:
                data = res.json()
                rates[currency] = data["rates"]["INR"]
            else:
                print(f"Failed to fetch {currency} from Frankfurter API: {res.status_code}")
        except Exception as e:
            print(f"Error fetching {currency} from Frankfurter API: {e}")

    return rates

def fetch_rbi_reference_rates():
    rates = {}
    print("Fetching FBIL reference rates using Playwright...")
    try:
        html = fetch_rendered_html("https://www.fbil.org.in/#/home", timeout_ms=30000, settle_ms=5000)
        soup = BeautifulSoup(html, "html.parser")

        currency_mapping = {
            "INR / 1 USD": "USD",
            "INR / 1 GBP": "GBP",
            "INR / 1 EUR": "EUR",
            "INR / 1 AED": "AED",
        }

        for table in soup.find_all("table"):
            text = table.get_text()
            if "USD" in text and "GBP" in text:
                for row in table.find_all("tr"):
                    cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                    if len(cells) >= 4:
                        pair = cells[2]
                        rate = cells[3]
                        if pair in currency_mapping:
                            curr = currency_mapping[pair]
                            if curr not in rates:
                                try:
                                    rates[curr] = float(rate)
                                except ValueError:
                                    pass
    except Exception as e:
        print(f"Error fetching FBIL reference rates: {e}")

    return rates

def update_benchmarks():
    print("Fetching Mid-Market Rates...")
    mid_market = fetch_mid_market_rates()

    print("\nFetching RBI Reference Rates...")
    rbi = fetch_rbi_reference_rates()

    os.makedirs(DATA_DIR, exist_ok=True)

    output = {}
    for curr in TARGET_CURRENCIES:
        output[curr] = {}
        if curr in mid_market:
            output[curr]["midMarket"] = mid_market[curr]
        if curr in rbi:
            output[curr]["rbiReference"] = rbi[curr]

    with open(BENCHMARKS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {BENCHMARKS_PATH}:")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    update_benchmarks()
