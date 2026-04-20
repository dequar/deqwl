import requests
import re
import socket
import time
import json
import logging
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== НАСТРОЙКИ ====================
SOURCES = [
    "https://raw.githubusercontent.com/zieng2/wl/main/vless.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
         "https://t.me/s/urlsources",
    "https://t.me/s/LLxickVPN",
    "https://t.me/s/Unblock_Tech",
    "https://t.me/s/hiddifycode",
    "https://t.me/s/slashvpnfree",
    "https://t.me/s/FVNetVPN",
    "https://t.me/s/STR_BYPASS",
    "https://t.me/s/strbypass",
    "https://t.me/s/PAORIGANET",
    "https://t.me/s/WS_JuJuB01_vpn_keys",
    "https://t.me/s/cvedc_vpn",
    "https://t.me/s/ultimatewbypass",
    "https://t.me/s/vlesstrojan",
    "https://t.me/s/oneclickvpnkeys",
    "https://t.me/s/NotorVPN",
    "https://t.me/s/dns_tt",
    "https://t.me/s/Chan7r07u4r",
    "https://t.me/s/githubv2",
    "https://t.me/s/rjsxrd",
    "https://t.me/s/wlrustg",
    "https://t.me/s/bypassawm",
    "https://t.me/s/DESKVPN_RUSSIA",
    "https://t.me/s/YoutubeUnBlockRu",
    "https://t.me/s/AnonixVPNon",
    "https://t.me/s/KfWLRus",
    "https://t.me/s/northlandvpn",
    "https://t.me/s/AddaptVpn",
    "https://t.me/s/VlessTrogan",
    "https://t.me/s/configuraciivpn",
    "https://t.me/s/freeinternet_byMygalaru",
    "https://t.me/s/allvpntg",
    "https://t.me/s/FluxVPNOff",
    "https://t.me/s/tik7net_vpn",
    "https://t.me/s/tiknet_vpn",
    "https://t.me/s/Farah_Proxy",
    "https://t.me/s/Farah_VPN",
    "https://t.me/s/NormanV2ray",
    "https://t.me/s/ghachvpn",
    "https://t.me/s/restlyconnect",
    "https://t.me/s/V2RayTunSub",
    "https://t.me/s/vpn_obhod_glushilok",
    "https://t.me/s/obhodbelogolista67",
    "https://t.me/s/freekesha21",
    "https://t.me/s/bypassInterne",
    "https://t.me/s/PrivateVPNs",
    "https://t.me/s/EuServer",
    "https://t.me/s/VlessConfig",
    "https://t.me/s/horn_proxy",
    "https://t.me/s/v2rayNG_021",
    "https://t.me/s/stretten",
    "https://t.me/s/v2ray_shop",
    "https://t.me/s/vpn_free_one_day",
    "https://t.me/s/h110vpn",
    "https://t.me/s/VlessVpnFree",
    "https://t.me/s/openkeysfree",
    "https://t.me/s/delightvpn",
    "https://t.me/s/v2raytunkeys",
    "https://t.me/s/vpn451",
    "https://t.me/s/Vepeer_VPN",
    "https://t.me/s/Androidiha71",
    "https://t.me/s/V2rayVPN_WireGaurd",
    "https://t.me/s/h110vpnchat",
    "https://t.me/s/vless_free_keys",
    "https://t.me/s/vpn_amneziya_hiddify",
    "https://t.me/s/vpnv2rayNGv",
    "https://t.me/s/freeeirannet",
    "https://t.me/s/AXproxy",
    "https://t.me/s/v2rey_grum",
    "https://t.me/s/vpn_ioss",
    "https://t.me/s/Cyber_Ta",
    "https://t.me/s/ConfigV2rayNG",
    "https://t.me/s/v2ray_free_conf",
    "https://t.me/s/niyakwi",
    "https://t.me/s/forumYamVPN",
    "https://t.me/s/vpnruss1",
    "https://t.me/s/trojanconfigs",
    "https://t.me/s/FreeCFGHub",
    "https://t.me/s/KeyVless",
    "https://t.me/s/vpn_cat",
    "https://t.me/s/v2_happ",
    "https://t.me/s/shadbobr1",
]

TCP_TIMEOUT = 4          # секунды на TCP-проверку
FETCH_TIMEOUT = 25       # секунды на загрузку источника
MAX_WORKERS_FETCH = 5    # параллельных загрузок источников
MAX_WORKERS_TCP = 50     # параллельных TCP-проверок

VLESS_PATTERN = re.compile(r'vless://[A-Za-z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+')

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# ==================== КАРТА СТРАН ====================
COUNTRY_MAP = {
    "RU": "🇷🇺", "PL": "🇵🇱", "FI": "🇫🇮", "NL": "🇳🇱",
    "DE": "🇩🇪", "FR": "🇫🇷", "GB": "🇬🇧", "US": "🇺🇸",
    "TR": "🇹🇷", "IR": "🇮🇷", "UA": "🇺🇦", "AT": "🇦🇹",
    "CH": "🇨🇭", "SE": "🇸🇪", "NO": "🇳🇴", "BE": "🇧🇪",
    "ES": "🇪🇸", "IT": "🇮🇹", "CZ": "🇨🇿", "SK": "🇸🇰",
    "HU": "🇭🇺", "RO": "🇷🇴", "BG": "🇧🇬", "GR": "🇬🇷",
    "PT": "🇵🇹", "DK": "🇩🇰", "LT": "🇱🇹", "LV": "🇱🇻",
    "EE": "🇪🇪", "HR": "🇭🇷", "RS": "🇷🇸", "BA": "🇧🇦",
    "MD": "🇲🇩", "BY": "🇧🇾", "KZ": "🇰🇿", "UZ": "🇺🇿",
    "AE": "🇦🇪", "SG": "🇸🇬", "JP": "🇯🇵", "KR": "🇰🇷",
    "CN": "🇨🇳", "HK": "🇭🇰", "TW": "🇹🇼", "IN": "🇮🇳",
    "BR": "🇧🇷", "CA": "🇨🇦", "AU": "🇦🇺", "NZ": "🇳🇿",
    "MX": "🇲🇽", "AR": "🇦🇷", "ZA": "🇿🇦", "IL": "🇮🇱",
    "SA": "🇸🇦", "TH": "🇹🇭", "VN": "🇻🇳", "MY": "🇲🇾",
    "ID": "🇮🇩", "PH": "🇵🇭",
}

# Синонимы для определения страны по тексту ремарки
COUNTRY_KEYWORDS = {
    "RU": ["RUSSIA", "РОССИЯ", "РУС", "МОСКВА", "MOSCOW", "ПИТЕР", "SPBU", "SAINT PETER"],
    "PL": ["POLAND", "ПОЛЬША", "WARSAW", "ВАРШАВА"],
    "FI": ["FINLAND", "ФИНЛЯНДИЯ", "HELSINKI"],
    "NL": ["NETHERLANDS", "ГОЛЛАНДИЯ", "NEDERLAND", "AMSTERDAM"],
    "DE": ["GERMANY", "ГЕРМАНИЯ", "BERLIN", "FRANKFURT", "БЕРЛИН"],
    "FR": ["FRANCE", "ФРАНЦИЯ", "PARIS", "ПАРИЖ"],
    "GB": ["UK", "UNITED KINGDOM", "BRITAIN", "LONDON", "ЛОНДОН"],
    "US": ["USA", "AMERICA", "UNITED STATES", "NEW YORK", "CHICAGO", "LOS ANGELES"],
    "TR": ["TURKEY", "ТУРЦИЯ", "ISTANBUL", "СТАМБУЛ", "ANKARA"],
    "IR": ["IRAN", "ИРАН", "TEHRAN", "ТЕГЕРАН"],
    "UA": ["UKRAINE", "УКРАИНА", "KYIV", "KIEV", "ХАРЬКОВ"],
    "CH": ["SWITZERLAND", "ШВЕЙЦАРИЯ", "ZURICH", "ЦЮРИХ"],
    "SE": ["SWEDEN", "ШВЕЦИЯ", "STOCKHOLM"],
    "NO": ["NORWAY", "НОРВЕГИЯ", "OSLO"],
    "AT": ["AUSTRIA", "АВСТРИЯ", "VIENNA", "ВЕНА"],
    "BE": ["BELGIUM", "БЕЛЬГИЯ", "BRUSSELS"],
    "ES": ["SPAIN", "ИСПАНИЯ", "MADRID"],
    "IT": ["ITALY", "ИТАЛИЯ", "ROME", "MILAN", "РИМ"],
    "CZ": ["CZECH", "ЧЕХИЯ", "PRAGUE", "ПРАГА"],
    "HU": ["HUNGARY", "ВЕНГРИЯ", "BUDAPEST"],
    "RO": ["ROMANIA", "РУМЫНИЯ", "BUCHAREST"],
    "BG": ["BULGARIA", "БОЛГАРИЯ", "SOFIA"],
    "KZ": ["KAZAKHSTAN", "КАЗАХСТАН", "ALMATY", "АЛМА"],
    "BY": ["BELARUS", "БЕЛАРУСЬ", "MINSK", "МИНСК"],
    "AE": ["UAE", "EMIRATES", "ЭМИРАТЫ", "DUBAI", "ДУБАЙ", "ABU DHABI"],
    "SG": ["SINGAPORE", "СИНГАПУР"],
    "JP": ["JAPAN", "ЯПОНИЯ", "TOKYO", "ТОКИО", "OSAKA"],
    "KR": ["KOREA", "КОРЕЯ", "SEOUL", "СЕУЛ"],
    "CN": ["CHINA", "КИТАЙ", "BEIJING", "SHANGHAI", "ПЕКИН"],
    "HK": ["HONG KONG", "ГОНКОНГ", "HONGKONG"],
    "TW": ["TAIWAN", "ТАЙВАНЬ"],
    "IN": ["INDIA", "ИНДИЯ", "MUMBAI", "DELHI"],
    "BR": ["BRAZIL", "БРАЗИЛИЯ", "SAO PAULO"],
    "CA": ["CANADA", "КАНАДА", "TORONTO", "VANCOUVER"],
    "AU": ["AUSTRALIA", "АВСТРАЛИЯ", "SYDNEY", "MELBOURNE"],
    "ID": ["INDONESIA", "ИНДОНЕЗИЯ", "JAKARTA"],
    "TH": ["THAILAND", "ТАИЛАНД", "BANGKOK", "БАНГКОК"],
    "VN": ["VIETNAM", "ВЬЕТНАМ", "HANOI"],
    "MY": ["MALAYSIA", "МАЛАЙЗИЯ", "KUALA LUMPUR"],
}

# IP-диапазоны, которые НЕ принадлежат России
# Используются, чтобы не помечать зарубежные IP как RU
KNOWN_NON_RU_SUBNETS = []  # резерв для будущего расширения

# ==================== ЗАГРУЗКА ИСТОЧНИКОВ ====================
def fetch_url(url: str) -> list[str]:
    try:
        r = requests.get(url, timeout=FETCH_TIMEOUT)
        r.raise_for_status()
        found = VLESS_PATTERN.findall(r.text)
        log.info(f"  ✓ {url.split('/')[-1]}: {len(found)} конфигов")
        return found
    except Exception as e:
        log.warning(f"  ✗ {url.split('/')[-1]}: {e}")
        return []

def fetch_all(sources: list[str]) -> set[str]:
    configs = set()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_FETCH) as ex:
        futures = {ex.submit(fetch_url, url): url for url in sources}
        for future in as_completed(futures):
            configs.update(future.result())
    return configs

# ==================== ПАРСИНГ VLESS ====================
def parse_vless(vless_url: str) -> dict:
    """Разбирает VLESS-ссылку на составные части."""
    result = {
        "raw": vless_url,
        "uuid": "",
        "host": "",
        "port": 0,
        "remark": "",
        "params": {},
    }
    try:
        body = vless_url[len("vless://"):]
        remark = ""
        if "#" in body:
            body, remark = body.rsplit("#", 1)
            remark = unquote(remark)
        result["remark"] = remark

        params_str = ""
        if "?" in body:
            body, params_str = body.split("?", 1)

        # uuid@host:port
        uuid, hostport = body.rsplit("@", 1)
        result["uuid"] = uuid

        # IPv6 в квадратных скобках
        if hostport.startswith("["):
            bracket_end = hostport.index("]")
            result["host"] = hostport[1:bracket_end].lower()
            port_part = hostport[bracket_end + 1:]
            result["port"] = int(port_part.lstrip(":")) if ":" in port_part else 443
        else:
            parts = hostport.rsplit(":", 1)
            result["host"] = parts[0].lower()
            result["port"] = int(parts[1]) if len(parts) == 2 else 443

        # query-параметры
        result["params"] = {
            k: v[0] for k, v in parse_qs(params_str).items()
        }
    except Exception as e:
        log.debug(f"parse_vless error: {e} — {vless_url[:80]}")
    return result

def get_dedup_key(parsed: dict) -> str:
    return f"{parsed['uuid']}@{parsed['host']}"

# ==================== ОПРЕДЕЛЕНИЕ ПРОТОКОЛА ====================
def detect_protocol(parsed: dict) -> str:
    """Возвращает метку типа: Reality, WS, gRPC, TCP и т.д."""
    p = parsed["params"]

    flow = p.get("flow", "")
    security = p.get("security", "").lower()
    sni = p.get("sni", p.get("serverName", "")).lower()
    fp = p.get("fp", "").lower()
    pbk = p.get("pbk", "")      # public key — признак Reality
    net = p.get("type", p.get("network", "tcp")).lower()

    if pbk or security == "reality":
        return "Reality"
    if security in ("tls", "xtls"):
        if net == "ws":
            return "WS+TLS"
            
        if net == "grpc":
            return "gRPC+TLS"
        return "TLS"
    if net == "ws":
        return "WS"
    if net == "grpc":
        return "gRPC"
    if net in ("tcp", "") or not net:
        return "TCP"
    return net.upper()

# ==================== ОПРЕДЕЛЕНИЕ СТРАНЫ ====================
def parse_country(parsed: dict) -> str:
    """
    Порядок приоритетов:
    1. Явный ISO-код в ремарке (ровно 2 буквы, отдельным словом или с разделителем)
    2. Поиск по синонимам в ремарке и хосте
    3. Поиск кода страны в ремарке (осторожно — избегаем ложных совпадений)
    4. XX — неизвестно
    """
    remark_raw = parsed.get("remark", "")
    host = parsed.get("host", "")

    remark = remark_raw.upper()
    host_up = host.upper()
    combined = f"{remark} {host_up}"

    # 1. Явный ISO-код в ремарке: отдельное слово, в начале, с разделителем
    #    Ищем паттерн вида RU-, -RU-, _RU_, [RU], (RU), "RU ", " RU "
    iso_pattern = re.compile(r'(?<![A-Z])([A-Z]{2})(?![A-Z])')
    for match in iso_pattern.finditer(remark):
        code = match.group(1)
        # Пропускаем слова, которые не являются кодами стран
        if code in COUNTRY_MAP:
            # Дополнительная проверка: не должно быть в середине обычного слова
            start = match.start()
            end = match.end()
            before = remark[start - 1] if start > 0 else " "
            after = remark[end] if end < len(remark) else " "
            if not before.isalpha() or not after.isalpha():
                return code

    # 2. Поиск по синонимам
    for code, keywords in COUNTRY_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return code

    # 3. Поиск кода страны в хосте (например, de.example.com, nl-server.vpn.io)
    host_parts = re.split(r'[\.\-_]', host_up)
    for part in host_parts:
        if len(part) == 2 and part in COUNTRY_MAP and part not in ("IS", "AS", "BY", "AM", "AN"):
            return part

    return "XX"

# ==================== TCP-ПРОВЕРКА ====================
def tcp_check(host: str, port: int, timeout: float = TCP_TIMEOUT) -> bool:
    """Проверяет, открыт ли TCP-порт. True = соединение установлено."""
    try:
        # Резолвим хост один раз
        addr_info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if not addr_info:
            return False
        family, socktype, proto, canonname, sockaddr = addr_info[0]
        with socket.socket(family, socktype) as s:
            s.settimeout(timeout)
            s.connect(sockaddr)
        return True
    except Exception:
        return False

def tcp_check_batch(parsed_list: list[dict]) -> dict[str, bool]:
    """Параллельная проверка всех конфигов. Возвращает {dedup_key: bool}."""
    results = {}

    def check_one(p):
        key = get_dedup_key(p)
        ok = tcp_check(p["host"], p["port"])
        return key, ok

    log.info(f"\n[TCP] Проверяю {len(parsed_list)} хостов (таймаут {TCP_TIMEOUT}с)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_TCP) as ex:
        futures = {ex.submit(check_one, p): p for p in parsed_list}
        done = 0
        for future in as_completed(futures):
            key, ok = future.result()
            results[key] = ok
            done += 1
            if done % 50 == 0 or done == len(parsed_list):
                log.info(f"  {done}/{len(parsed_list)}...")

    alive = sum(1 for v in results.values() if v)
    log.info(f"[TCP] Живых: {alive}/{len(parsed_list)}")
    return results

# ==================== ФОРМИРОВАНИЕ РЕМАРКИ ====================
def make_remark(parsed: dict, country: str, proto: str, number: int, alive: bool) -> str:
    flag = COUNTRY_MAP.get(country, "🏴")
    status = "✓" if alive else "✗"
    base = parsed["raw"].split("#")[0] if "#" in parsed["raw"] else parsed["raw"]
    return f"{base}#{status} {flag} {country}-{number:03d} [{proto}]"

# ==================== ГЛАВНЫЙ БЛОК ====================
if __name__ == "__main__":
    log.info(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Запуск сборщика VLESS...\n")

    # 1. Загрузка
    log.info("=== Загрузка источников ===")
    raw_configs = fetch_all(SOURCES)
    log.info(f"Всего найдено (с дублями): {len(raw_configs)}\n")

    # 2. Парсинг и дедупликация
    log.info("=== Парсинг и дедупликация ===")
    unique: dict[str, dict] = {}
    for raw in raw_configs:
        parsed = parse_vless(raw)
        if not parsed["host"]:
            continue
        key = get_dedup_key(parsed)
        if key not in unique:
            unique[key] = parsed
    log.info(f"Уникальных конфигов: {len(unique)}\n")

    # 3. TCP-проверка
    parsed_list = list(unique.values())
    tcp_results = tcp_check_batch(parsed_list)

    # 4. Определение страны и протокола
    log.info("\n=== Группировка по странам ===")
    groups: dict[str, list] = defaultdict(list)
    for p in parsed_list:
        country = parse_country(p)
        proto = detect_protocol(p)
        key = get_dedup_key(p)
        alive = tcp_results.get(key, False)
        groups[country].append((p, proto, alive))

    for country, items in sorted(groups.items()):
        alive_count = sum(1 for _, _, ok in items if ok)
        log.info(f"  {COUNTRY_MAP.get(country, '🏴')} {country}: {len(items)} ({alive_count} живых)")

    # 5. Сортировка: сначала RU, потом остальные; внутри страны — живые вперёд
    sorted_countries = sorted(
        groups.keys(),
        key=lambda c: (0 if c == "RU" else (1 if c != "XX" else 2), c)
    )

    checked_list = []   # только живые, с пометками
    all_list = []       # все (живые + мёртвые)

    for country in sorted_countries:
        items = groups[country]
        # Живые сначала
        items_sorted = sorted(items, key=lambda x: (0 if x[2] else 1))
        for i, (p, proto, alive) in enumerate(items_sorted, 1):
            remark = make_remark(p, country, proto, i, alive)
            all_list.append(remark)
            if alive:
                checked_list.append(remark)

    # 6. Запись файлов
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("vless_checked.txt", "w", encoding="utf-8") as f:
        f.write(f"# VLESS Checked — только живые конфиги\n")
        f.write(f"# Обновлено: {now_str}\n")
        f.write(f"# Всего живых: {len(checked_list)}\n")
        f.write("# Формат: ✓/✗ 🇷🇺 RU-001 [Reality]\n\n")
        f.write("\n".join(checked_list))

    with open("vless_all.txt", "w", encoding="utf-8") as f:
        f.write(f"# VLESS All — все конфиги (живые и мёртвые)\n")
        f.write(f"# Обновлено: {now_str}\n")
        f.write(f"# Всего: {len(all_list)} (живых: {len(checked_list)})\n\n")
        f.write("\n".join(all_list))

    log.info(f"\n=== ГОТОВО ===")
    log.info(f"• vless_checked.txt : {len(checked_list)} живых конфигов")
    log.info(f"• vless_all.txt     : {len(all_list)} всего")

