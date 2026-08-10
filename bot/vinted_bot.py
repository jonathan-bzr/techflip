import time
import random
from curl_cffi import requests

# ==============================================================================
# CONFIGURATION
# ==============================================================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1536411605502525533/IjbjVIDChTlyz9kCY4qtJDNPAWnmjFkoD-AJCg8EQa_nSSn6Hl_16ZwBZVHlNJ37Ydvg"

SEARCH_QUERIES = [
    "pc portable hs",
    "pc portable lent",
    "tour pc hs",
    "ordinateur portable pieces",
    "lot pc portable"
]

MAX_PRICE = 100
CHECK_INTERVAL_SECONDS = 45

seen_item_ids = set()

def get_vinted_session():
    """ Initialise une session en imitant le comportement et le fingerprint de Chrome """
    session = requests.Session(impersonate="chrome120")
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    try:
        # Visite la page d'accueil pour récupérer le cookie de session officiel
        res = session.get("https://www.vinted.fr", headers=headers, timeout=10)
        if res.status_code == 200:
            print("[+] Session Vinted initialisée avec succès.")
        else:
            print(f"[-] Attention : statut {res.status_code} sur la page d'accueil Vinted.")
    except Exception as e:
        print(f"[-] Erreur lors de l'initialisation de la session : {e}")
    
    return session

def scrape_vinted_query(session, query):
    """ Interroge l'API Vinted """
    url = f"https://www.vinted.fr/api/v2/catalog/items?search_text={query}&price_to={MAX_PRICE}&order=newest_first&per_page=10"
    
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.vinted.fr/',
    }

    try:
        # On utilise l'option impersonate pour contourner la détection TLS/JA3
        response = session.get(url, headers=headers, impersonate="chrome120", timeout=10)
        
        if response.status_code == 403:
            print(f" [⚠️ 403] Bloqué par Vinted pour '{query}'. Pause et tentative de réinitialisation...")
            time.sleep(10)
            return

        if response.status_code != 200:
            print(f"[-] Erreur HTTP {response.status_code} pour la recherche : '{query}'")
            return

        data = response.json()
        items = data.get('items', [])

        for item in reversed(items):
            item_id = item.get('id')
            if item_id in seen_item_ids:
                continue

            title = item.get('title')
            price = item.get('price')
            item_url = item.get('url')
            photo_url = item.get('photos', [{}])[0].get('url', '') if item.get('photos') else ''

            seen_item_ids.add(item_id)
            send_discord_alert(title, price, item_url, photo_url, query)
            time.sleep(1)

    except Exception as e:
        print(f"[-] Erreur lors du scraping de '{query}': {e}")

def send_discord_alert(title, price, url, photo_url, query):
    embed = {
        "title": f"💻 Nouvelle Offre : {title}",
        "url": url,
        "color": 5814783,
        "fields": [
            {"name": "Prix", "value": f"**{price} €**", "inline": True},
            {"name": "Recherche", "value": f"`{query}`", "inline": True}
        ],
        "image": {"url": photo_url} if photo_url else {},
        "footer": {"text": "TechFlip Bot • Vinted Alert"}
    }

    payload = {"embeds": [embed]}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        print(f"[✅ DISCORD] Alerte envoyée : {title} ({price}€)")
    except Exception as e:
        print(f"[-] Erreur envoi Discord: {e}")

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    print("[*] Démarrage du Bot Vinted TechFlip (Mode TLS Impersonate)...")
    session = get_vinted_session()

    while True:
        for query in SEARCH_QUERIES:
            print(f"[+] Scan pour : '{query}' (Max {MAX_PRICE}€)...")
            scrape_vinted_query(session, query)
            time.sleep(random.randint(4, 8))

        print(f"[💤] Fin de cycle. Pause de {CHECK_INTERVAL_SECONDS}s...\n")
        time.sleep(CHECK_INTERVAL_SECONDS)