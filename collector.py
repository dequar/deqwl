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

# Регулярное выражение для разбора VLESS (UUID, Host:Port, Params, Remark)
VLESS_PATTERN = re.compile(r'vless://([A-Za-z0-9\-]+)@([A-Za-z0-9\-._~\[\]:]+)\?([A-Za-z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+)(?:#(.+))?')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Расширенная база для точного определения стран
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

# ==================== ЛОГИКА ====================

def get_country_code(host, old_remark):
    """Определяет страну по хосту или старой ремарке."""
    target = f"{host} {old_remark}".lower()
    
    # 1. Проверка субдоменов (напр. ru.server.com)
    host_parts = host.lower().split('.')
    for part in host_parts:
        if part.upper() in GEO_DB and len(part) == 2:
            return part.upper()
            
    # 2. Поиск по ключевым словам из базы
    for code, keywords in GEO_DB.items():
        if any(kw in target for kw in keywords):
            return code
            
    return "XX"

def process():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Сбор уникальных конфигов...")
    
    unique_configs = {} 
    
    for url in SOURCES:
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            
            # Ищем все ссылки vless:// в тексте
            raw_links = re.findall(r'vless://[^\s]+', response.text)
            
            for link in raw_links:
                match = VLESS_PATTERN.match(link)
                if match:
                    uuid = match.group(1)
                    host_port = match.group(2)
                    params = match.group(3)
                    old_remark = unquote(match.group(4)) if match.group(4) else ""
                    
                    # Ключ дедупликации (сервер + пользователь)
                    key = (uuid, host_port)
                    
                    if key not in unique_configs:
                        country = get_country_code(host_port.split(':')[0], old_remark)
                        unique_configs[key] = {
                            "base_url": f"vless://{uuid}@{host_port}?{params}",
                            "country": country
                        }
        except Exception as e:
            print(f"Пропуск источника {url}: {e}")

    # Сортировка: RU -> Остальные по алфавиту -> XX
    sorted_items = sorted(
        unique_configs.values(),
        key=lambda x: (
            0 if x['country'] == "RU" else (2 if x['country'] == "XX" else 1),
            x['country']
        )
    )

    # Формируем список ссылок с новыми именами
    final_links = []
    for index, data in enumerate(sorted_items, 1):
        new_name = f"{data['country']} #{index:03d}"
        final_links.append(f"{data['base_url']}#{new_name}")

    if not final_links:
        print("Конфиги не найдены!")
        return

    # Превращаем список в текст и кодируем в Base64 для v2rayNG
    raw_text = "\n".join(final_links)
    b64_data = base64.b64encode(raw_text.encode('utf-8')).decode('utf-8')

    # Запись в файл
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(b64_data)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Успех!")
    print(f"Создана подписка Base64 в '{OUTPUT_FILE}'")
    print(f"Всего уникальных серверов: {len(final_links)}")

if __name__ == "__main__":
    process()
    
