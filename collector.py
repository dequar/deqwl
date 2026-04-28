import requests
import re
import base64
from urllib.parse import unquote
from datetime import datetime

# ==================== НАСТРОЙКИ ====================
SOURCES = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile-2.txt"
]

OUTPUT_FILE = "deray.txt"

VLESS_PATTERN = re.compile(r'vless://([A-Za-z0-9\-]+)@([A-Za-z0-9\-._\~\[\]:]+)\?([A-Za-z0-9\-._\~:/?#\[\]@!$&\'()*+,;=%]+)(?:#(.+))?')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

GEO_DB = {
    "RU": ["ru", "russia", "moscow", "mow", "spb", "россия", "москва", "пб", "vdsina", "mcl"],
    "DE": ["de", "germany", "frankfurt", "fra", "германия", "франкфурт", "hetzner"],
    "NL": ["nl", "netherlands", "amsterdam", "ams", "нидерланды", "амстердам"],
    "FI": ["fi", "finland", "helsinki", "финляндия", "хельсинки"],
    "US": ["us", "usa", "united states", "ny", "сша", "new york"],
    "KZ": ["kz", "kazakhstan", "казахстан", "алматы", "almaty"],
    "TR": ["tr", "turkey", "istanbul", "турция", "стамбул"],
    "PL": ["pl", "poland", "warsaw", "польша", "варшава"]
}

FLAGS = {
    "RU": "🇷🇺", "DE": "🇩🇪", "NL": "🇳🇱", "FI": "🇫🇮",
    "US": "🇺🇸", "KZ": "🇰🇿", "TR": "🇹🇷", "PL": "🇵🇱", "XX": "🌍"
}

def get_country_code(host, old_remark=""):
    target = f"{host} {old_remark}".lower()
    for part in host.lower().split('.'):
        if part.upper() in GEO_DB and len(part) == 2:
            return part.upper()
    for code, keywords in GEO_DB.items():
        if any(kw in target for kw in keywords):
            return code
    return "XX"

def process():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск сбора...")

    unique_configs = {}

    for url in SOURCES:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            raw_links = re.findall(r'vless://[^\s]+', r.text)

            for link in raw_links:
                m = VLESS_PATTERN.match(link)
                if m:
                    uuid = m.group(1)
                    host_port = m.group(2)
                    params = m.group(3)
                    old_remark = unquote(m.group(4)) if m.group(4) else ""

                    key = (uuid, host_port)
                    if key not in unique_configs:
                        country = get_country_code(host_port.split(':')[0], old_remark)
                        # Сохраняем ТОЛЬКО чистую базу без ремарки
                        base = f"vless://{uuid}@{host_port}?{params}"
                        unique_configs[key] = {"base": base, "country": country}
        except Exception as e:
            print(f"Ошибка источника {url}: {e}")

    # Сортировка
    sorted_list = sorted(unique_configs.values(), 
                         key=lambda x: (0 if x['country'] == "RU" else (2 if x['country'] == "XX" else 1), x['country']))

    # Жёсткое формирование чистых имён
    final_links = []
    for i, item in enumerate(sorted_list, 1):
        flag = FLAGS.get(item['country'], "🌍")
        new_name = f"{flag} {item['country']} - {i:03d}"
        
        # Самая жёсткая очистка — берём только до первого #
        clean_base = item['base'].split('#')[0]
        final_links.append(f"{clean_base}#{new_name}")

    if not final_links:
        print("Ничего не собрано!")
        return

    # Base64
    text = "\n".join(final_links)
    b64 = base64.b64encode(text.encode()).decode()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(b64)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Готово!")
    print(f"Сохранено в {OUTPUT_FILE} — {len(final_links)} конфигов")
    print("Формат имён: 🇷🇺 RU - 001")

if __name__ == "__main__":
    process()
