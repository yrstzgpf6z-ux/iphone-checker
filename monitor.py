import json
import os
import sys
import time
import urllib.parse
import urllib.request

# ==========================================
# CONFIGURATION
# ==========================================
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "tucson-duo-restock-85718")
ZIP_CODE = "85718"
CHECK_INTERVAL = 30  # seconds

# Target SKUs: 256GB Duo (Star White & Night Sky)
TARGET_MODELS = {
    "MK1E4LL/A": "iPhone Duo 256GB - Star White",
    "MK1F4LL/A": "iPhone Duo 256GB - Night Sky",
}

# Stores: La Encantada (R086), Chandler (R026)
TARGET_STORES = {
    "R086": "Apple La Encantada (Tucson)",
    "R026": "Apple Chandler Fashion Center (Chandler)",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
}


def build_apple_url():
    base_url = "https://www.apple.com/shop/fulfillment-messages"
    params = [
        ("pl", "true"),
        ("mts.0", "regular"),
        ("mts.1", "compact"),
        ("location", ZIP_CODE),
    ]
    for idx, part in enumerate(TARGET_MODELS.keys()):
        params.append((f"parts.{idx}", part))
    return f"{base_url}?{urllib.parse.urlencode(params)}"


def send_iphone_push(model_name, store_name):
    """Dispatches a priority push notification to your iPhone."""
    payload = f"🔥 {model_name} is in stock for pickup at {store_name}!".encode(
        "utf-8"
    )
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=payload,
        headers={
            "Title": "🚨 IPHONE DUO IN STOCK! 🚨",
            "Priority": "urgent",  # Loud sound, bypasses DND
            "Tags": "iphone,tada,warning",
            "Click": "https://www.apple.com/shop/buy-iphone",  # Opens Apple checkout
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[PUSH SENT] Successfully dispatched alert to iPhone via ntfy.")
    except Exception as e:
        print(f"[PUSH ERROR] Failed to send iPhone notification: {e}")


def check_inventory(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        stores = (
            data.get("body", {})
            .get("content", {})
            .get("pickupMessage", {})
            .get("stores", [])
        )
        if not stores:
            stores = data.get("body", {}).get("stores", [])

        found = False
        for store in stores:
            store_id = store.get("storeNumber")
            if store_id not in TARGET_STORES:
                continue

            store_name = TARGET_STORES[store_id]
            parts = store.get("partsAvailability", {})

            for sku, details in parts.items():
                if sku in TARGET_MODELS:
                    status = details.get("pickupDisplay", "")
                    # 'available' or 'today' denotes active pickup eligibility
                    if status in ["available", "today"]:
                        print(
                            f"\n>>> IN STOCK FOUND: {TARGET_MODELS[sku]} at {store_name}! <<<"
                        )
                        send_iphone_push(TARGET_MODELS[sku], store_name)
                        found = True

        timestamp = time.strftime("%I:%M:%S %p MST")
        if not found:
            print(f"[{timestamp}] Polled La Encantada & Chandler: Sold out.")
        return found

    except Exception as e:
        timestamp = time.strftime("%I:%M:%S %p MST")
        print(f"[{timestamp}] Connection / Parsing error: {e}")
        return False


def main():
    print(
        f"Starting Apple Store tracker for {list(TARGET_STORES.values())}..."
    )
    url = build_apple_url()

    while True:
        hit = check_inventory(url)
        if hit:
            # Pause for 3 minutes after finding stock to avoid spamming alerts during checkout
            time.sleep(180)
        else:
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()