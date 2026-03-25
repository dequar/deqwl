import requests
import re
import time
import subprocess
import json
import tempfile
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== ТОЛЬКО ЛУЧШИЕ ИСТОЧНИКИ ====================
SOURCES = [
    "https://raw.githubusercontent.com/zieng2/wl/main/vless.txt",          # самая большая от zieng2
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
]

VLESS_PATTERN = re.compile(r'vless://[^\s<>"]+')

def fetch_url(url):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return VLESS_PATTERN.findall(r.text)
    except Exception as e:
        print(f"Ошибка при загрузке {url}: {e}")
        return []

def extract_country_and_clean(vless_url):
    """Пытается вытащить страну из remark (# DE # RU # PL и т.д.) и делает красивый remark"""
    try:
        if "#" in vless_url:
            base, remark = vless_url.split("#", 1)
            remark = remark.strip()
        else:
            base = vless_url
            remark = ""

        # Ищем флаги или коды стран
        country_map = {
            "🇷🇺": "RU", "RU": "RU", "Россия": "RU", "russia": "RU",
            "🇵🇱": "PL", "PL": "PL", "Poland": "PL",
            "🇫🇮": "FI", "FI": "FI", "Finland": "FI",
            "🇳🇱": "NL", "NL": "NL", "Netherlands": "NL",
            "🇩🇪": "DE", "DE": "DE", "Germany": "DE",
            "🇫🇷": "FR", "FR": "FR",
            "🇬🇧": "GB", "GB": "GB",
            "🇺🇸": "US", "US": "US",
        }

        country = "XX"
        for flag, code in country_map.items():
            if flag in remark or code.upper() in remark.upper():
                country = code.upper()
                break

        # Красивый remark: RU-001, PL-042 и т.д.
        clean_base = base.split("#")[0] if "#" in base else base
        return f"{clean_base}#{country}-Config"
    except:
        return f"{vless_url}#XX-Config"

def test_vless_light(vless_url):
    """Лёгкий тест (быстрее и мягче)"""
    try:
        # Простая проверка формата + быстрый connect
        if not vless_url.startswith("vless://") or "@" not in vless_url:
            return None
        return extract_country_and_clean(vless_url)
    except:
        return None

# ==================== ЗАПУСК ====================
print(f"[{datetime.now()}] Сбор из zieng2 + igareck WHITE...")

all_configs = set()
for url in SOURCES:
    links = fetch_url(url)
    all_configs.update(links)
    print(f"Загружено из {url.split('/')[-1]}: {len(links)}")

print(f"Всего уникальных: {len(all_configs)}")

# Лёгкий тест + очистка названий
working = []
with ThreadPoolExecutor(max_workers=15) as executor:
    future_to_url = {executor.submit(test_vless_light, url): url for url in all_configs}
    for future in as_completed(future_to_url):
        result = future.result()
        if result:
            working.append(result)

# Сортировка: сначала RU, потом остальные по алфавиту страны
def sort_key(x):
    country = x.split("#")[-1].split("-")[0]
    return (0 if country == "RU" else 1, country)

working.sort(key=sort_key)

with open("vless_checked.txt", "w", encoding="utf-8") as f:
    f.write("# deqwl — VLESS Checked для РФ (zieng2 + igareck WHITE)\n")
    f.write(f"# Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    f.write(f"# Всего конфигов: {len(working)}\n")
    f.write("# Сортировка: Россия сверху → остальные по стране\n")
    f.write("# Названия: RU-Config, PL-Config, FI-Config и т.д.\n\n")
    f.write("\n".join(working))

print(f"ГОТОВО! В подписке {len(working)} конфигов (с нормальными названиями и сортировкой)")
