import requests
import re
from urllib.parse import unquote
from datetime import datetime

# ==================== НАСТРОЙКИ ====================
SOURCES = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile-2.txt"
]

OUTPUT_FILE = "deray.txt"
# Паттерн для захвата vless ссылки и отделения параметров от ремарки
VLESS_PATTERN = re.compile(r'vless://([A-Za-z0-9\-]+)@([A-Za-z0-9\-._~\[\]:]+)\?([A-Za-z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+)(?:#(.+))?')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

GEO_DB = {
    "RU": ["ru", "russia", "moscow", "mow", "spb", "россия", "москва", "пб"],
    "DE": ["de", "germany", "frankfurt", "fra", "германия", "франкфурт"],
    "NL": ["nl", "netherlands", "amsterdam", "ams", "нидерланды", "амстердам"],
    "FI": ["fi", "finland", "helsinki", "финляндия", "хельсинки"],
    "US": ["us", "usa", "united states", "ny", "сша"],
    "KZ": ["kz", "kazakhstan", "казахстан", "алматы"],
    "TR": ["tr", "turkey", "istanbul", "турция", "стамбул"]
}

# ==================== ЛОГИКА ====================

def get_country_code(host, old_remark):
    target = f"{host} {old_remark}".lower()
    host_parts = host.lower().split('.')
    for part in host_parts:
        if part.upper() in GEO_DB and len(part) == 2:
            return part.upper()
    for code, keywords in GEO_DB.items():
        if any(kw in target for kw in keywords):
            return code
    return "XX"

def process():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Сбор конфигов начат...")
    
    unique_configs = {} 
    
    for url in SOURCES:
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            
            raw_links = re.findall(r'vless://[^\s]+', response.text)
            
            for link in raw_links:
                match = VLESS_PATTERN.match(link)
                if match:
                    uuid = match.group(1)
                    host_port = match.group(2)
                    params = match.group(3)
                    # Сохраняем старую ремарку только для определения страны
                    old_remark = unquote(match.group(4)) if match.group(4) else ""
                    
                    key = (uuid, host_port)
                    
                    if key not in unique_configs:
                        unique_configs[key] = {
                            "base_url": f"vless://{uuid}@{host_port}?{params}", # Ссылка без #ремарки
                            "host": host_port.split(':')[0],
                            "old_remark": old_remark
                        }
        except Exception as e:
            print(f"Ошибка при загрузке {url}: {e}")

    # Сортировка (RU -> Остальные -> XX)
    sorted_items = sorted(
        unique_configs.values(),
        key=lambda x: (
            0 if get_country_code(x['host'], x['old_remark']) == "RU" 
            else (2 if get_country_code(x['host'], x['old_remark']) == "XX" else 1)
        )
    )

    final_list = []
    for index, data in enumerate(sorted_items, 1):
        country = get_country_code(data['host'], data['old_remark'])
        # ПОЛНОЕ ПЕРЕИМЕНОВАНИЕ: приклеиваем новую ремарку к базовой ссылке
        new_name = f"{country} #{index:03d}"
        final_list.append(f"{data['base_url']}#{new_name}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_list))

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Готово!")
    print(f"Файл {OUTPUT_FILE} успешно обновлен. Всего конфигов: {len(final_list)}")

if __name__ == "__main__":
 
    process()
