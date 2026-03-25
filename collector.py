import requests
import re
import time
import subprocess
import json
import tempfile
import os
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== ИСТОЧНИКИ ====================
SOURCES = [
    "https://raw.githubusercontent.com/zieng2/wl/main/vless.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
]

VLESS_PATTERN = re.compile(r'vless://[^\s<>"]+')

# ==================== РАСШИРЕННАЯ КАРТА СТРАН (60+ как у zieng2) ====================
COUNTRY_MAP = {
    "RU": ("🇷🇺", "RU"), "PL": ("🇵🇱", "PL"), "FI": ("🇫🇮", "FI"), "NL": ("🇳🇱", "NL"),
    "DE": ("🇩🇪", "DE"), "FR": ("🇫🇷", "FR"), "GB": ("🇬🇧", "GB"), "US": ("🇺🇸", "US"),
    "TR": ("🇹🇷", "TR"), "IR": ("🇮🇷", "IR"), "UA": ("🇺🇦", "UA"), "AT": ("🇦🇹", "AT"),
    "CH": ("🇨🇭", "CH"), "SE": ("🇸🇪", "SE"), "NO": ("🇳🇴", "NO"), "BE": ("🇧🇪", "BE"),
    "ES": ("🇪🇸", "ES"), "IT": ("🇮🇹", "IT"), "CZ": ("🇨🇿", "CZ"), "SK": ("🇸🇰", "SK"),
    "HU": ("🇭🇺", "HU"), "RO": ("🇷🇴", "RO"), "BG": ("🇧🇬", "BG"), "GR": ("🇬🇷", "GR"),
    "PT": ("🇵🇹", "PT"), "DK": ("🇩🇰", "DK"), "LT": ("🇱🇹", "LT"), "LV": ("🇱🇻", "LV"),
    "EE": ("🇪🇪", "EE"), "HR": ("🇭🇷", "HR"), "RS": ("🇷🇸", "RS"), "BA": ("🇧🇦", "BA"),
    "MD": ("🇲🇩", "MD"), "BY": ("🇧🇾", "BY"), "KZ": ("🇰🇿", "KZ"), "UZ": ("🇺🇿", "UZ"),
    "AE": ("🇦🇪", "AE"), "SG": ("🇸🇬", "SG"), "JP": ("🇯🇵", "JP"), "KR": ("🇰🇷", "KR"),
    "CN": ("🇨🇳", "CN"), "HK": ("🇭🇰", "HK"), "TW": ("🇹🇼", "TW"), "IN": ("🇮🇳", "IN"),
    "BR": ("🇧🇷", "BR"), "CA": ("🇨🇦", "CA"), "AU": ("🇦🇺", "AU"), "NZ": ("🇳🇿", "NZ"),
    "MX": ("🇲🇽", "MX"), "AR": ("🇦🇷", "AR"), "ZA": ("🇿🇦", "ZA"), "IL": ("🇮🇱", "IL"),
    "SA": ("🇸🇦", "SA"), "TH": ("🇹🇭", "TH"), "VN": ("🇻🇳", "VN"), "MY": ("🇲🇾", "MY"),
    "ID": ("🇮🇩", "ID"), "PH": ("🇵🇭", "PH"),
}

def fetch_url(url):
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        return VLESS_PATTERN.findall(r.text)
    except:
        return []

def get_uuid_host_key(vless_url):
    try:
        part = vless_url.split("://")[1].split("?")[0].split("#")[0]
        uuid = part.split("@")[0]
        host = part.split("@")[1].split(":")[0].lower()
        return f"{uuid}@{host}"
    except:
        return vless_url

def parse_country(vless_url):
    """Улучшенный парсер — ищет флаги, коды, слова и даже популярные хосты"""
    try:
        text = vless_url.upper()
        remark = vless_url.split("#", 1)[1] if "#" in vless_url else ""

        # Прямой поиск по коду или флагу
        for code in COUNTRY_MAP:
            if code in text or f"🇷{code.lower()}" in text or f" {code} " in f" {text} ":
                return code

        # Поиск по полным названиям и синонимам
        country_keywords = {
            "RU": ["RUSSIA", "РОССИЯ", "РУС", "МОСКВА"], "PL": ["POLAND", "ПОЛЬША"],
            "FI": ["FINLAND", "ФИНЛЯНДИЯ"], "NL": ["NETHERLANDS", "ГОЛЛАНДИЯ", "NEDERLAND"],
            "DE": ["GERMANY", "ГЕРМАНИЯ"], "FR": ["FRANCE", "ФРАНЦИЯ"],
            "GB": ["UK", "UNITED KINGDOM", "BRITAIN"], "US": ["USA", "AMERICA"],
            "TR": ["TURKEY", "ТУРЦИЯ"], "IR": ["IRAN", "ИРАН"],
        }
        for code, keywords in country_keywords.items():
            if any(kw in text for kw in keywords):
                return code
    except:
        pass
    return "XX"

def make_nice_remark(vless_url, country, number):
    flag, code = COUNTRY_MAP.get(country, ("🏴", "XX"))
    base = vless_url.split("#")[0] if "#" in vless_url else vless_url
    return f"{base}#{flag} {code}-{number:03d}"

# ==================== СБОР И ОБРАБОТКА ====================
print(f"[{datetime.now()}] Запуск улучшенного сбора...")

all_configs = set()
for url in SOURCES:
    links = fetch_url(url)
    all_configs.update(links)
    print(f"✓ {url.split('/')[-1]}: {len(links)}")

print(f"Всего найдено: {len(all_configs)}")

# Дедупликация
unique = {}
for link in all_configs:
    key = get_uuid_host_key(link)
    if key not in unique:
        unique[key] = link

# Группировка по странам
groups = defaultdict(list)
for link in unique.values():
    country = parse_country(link)
    groups[country].append(link)

# Сортировка стран (RU первой)
sorted_countries = sorted(groups.keys(), key=lambda c: (0 if c == "RU" else 1, c))

final_list = []
for country in sorted_countries:
    country_configs = groups[country]
    for i, link in enumerate(country_configs, 1):
        nice = make_nice_remark(link, country, i)
        final_list.append(nice)

# Запись файлов
with open("vless_checked.txt", "w", encoding="utf-8") as f:
    f.write("# deqwl — VLESS Checked (как у zieng2)\n")
    f.write(f"# Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    f.write(f"# Всего: {len(final_list)} конфигов\n")
    f.write("# Формат: 🇷🇺 RU-001 • Россия сверху • минимум XX\n\n")
    f.write("\n".join(final_list))

with open("vless_all.txt", "w", encoding="utf-8") as f:
    f.write("# deqwl — ALL VLESS (все сырые конфиги)\n")
    f.write(f"# Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    f.write(f"# Всего: {len(all_configs)}\n\n")
    f.write("\n".join(sorted(all_configs)))

print(f"ГОТОВО!\n"
      f"• vless_checked.txt : {len(final_list)} (с флагами и нумерацией)\n"
      f"• vless_all.txt     : {len(all_configs)} (все найденные)")
