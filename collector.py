import requests
import re
import socket
import time
import subprocess
import asyncio
import aiohttp
import os

from urllib.parse import urlparse, parse_qs, unquote
from concurrent.futures import ThreadPoolExecutor

# ==================== НАСТРОЙКИ ====================
SOURCES = [
    # GitHub источники
    "https://raw.githubusercontent.com/zieng2/wl/main/vless.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",

    # ==================== TELEGRAM КАНАЛЫ ====================
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

# Таймауты и настройки
TCP_TIMEOUT = 4
ICMP_TIMEOUT = 3
HTTP_TIMEOUT = 8
FETCH_TIMEOUT = 35

MAX_WORKERS_TCP = 50
MAX_WORKERS_ICMP = 40
MAX_WORKERS_HTTP = 25

HTTP_TEST_URL = "http://www.gstatic.com/generate_204"

VLESS_PATTERN = re.compile(r'vless://[A-Za-z0-9\-._\~:/?#\[\]@!$&\'()*+,;=%]+', re.IGNORECASE)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# ==================== КАРТА СТРАН ====================
COUNTRY_MAP = {
    "RU": "🇷🇺", "PL": "🇵🇱", "FI": "🇫🇮", "NL": "🇳🇱", "DE": "🇩🇪",
    "FR": "🇫🇷", "GB": "🇬🇧", "US": "🇺🇸", "TR": "🇹🇷", "IR": "🇮🇷",
    "UA": "🇺🇦", "AT": "🇦🇹", "CH": "🇨🇭", "SE": "🇸🇪", "NO": "🇳🇴",
    "BE": "🇧🇪", "ES": "🇪🇸", "IT": "🇮🇹", "CZ": "🇨🇿", "SK": "🇸🇰",
    "HU": "🇭🇺", "RO": "🇷🇴", "BG": "🇧🇬", "GR": "🇬🇷", "PT": "🇵🇹",
    "DK": "🇩🇰", "LT": "🇱🇹", "LV": "🇱🇻", "EE": "🇪🇪", "HR": "🇭🇷",
    "RS": "🇷🇸", "BA": "🇧🇦", "MD": "🇲🇩", "BY": "🇧🇾", "KZ": "🇰🇿",
    "UZ": "🇺🇿", "AE": "🇦🇪", "SG": "🇸🇬", "JP": "🇯🇵", "KR": "🇰🇷",
    "CN": "🇨🇳", "HK": "🇭🇰", "TW": "🇹🇼", "IN": "🇮🇳", "BR": "🇧🇷",
    "CA": "🇨🇦", "AU": "🇦🇺", "NZ": "🇳🇿", "MX": "🇲🇽", "AR": "🇦🇷",
    "ZA": "🇿🇦", "IL": "🇮🇱", "SA": "🇸🇦", "TH": "🇹🇭", "VN": "🇻🇳",
    "MY": "🇲🇾", "ID": "🇮🇩", "PH": "🇵🇭",
}

COUNTRY_KEYWORDS = {
    "RU": ["ru", "russia", "moscow", "spb", "saint-petersburg", "ekb", "novosibirsk", "rostov", "krasnodar", "samara", "ufa", "omsk", "perm", "vladivostok", "irkutsk", "yaroslavl", "tula", "kaliningrad", "sochi"],
    "PL": ["pl", "poland", "warsaw", "krakow", "wroclaw", "gdansk", "poznan", "lodz"],
    "FI": ["fi", "finland", "helsinki"],
    "NL": ["nl", "netherlands", "amsterdam", "rotterdam", "thehague", "denhaag"],
    "DE": ["de", "germany", "berlin", "frankfurt", "munich", "hamburg", "dusseldorf", "cologne", "koln", "stuttgart"],
    "FR": ["fr", "france", "paris", "lyon", "marseille"],
    "GB": ["gb", "uk", "unitedkingdom", "london", "manchester"],
    "US": ["us", "usa", "america", "newyork", "nyc", "losangeles", "la", "chicago", "dallas", "miami", "houston", "seattle", "sanfrancisco", "atlanta"],
    "TR": ["tr", "turkey", "istanbul", "ankara"],
    "IR": ["ir", "iran", "tehran"],
    "UA": ["ua", "ukraine", "kiev", "kyiv", "odessa", "kharkov"],
    "AT": ["at", "austria", "vienna"],
    "CH": ["ch", "switzerland", "zurich", "geneva"],
    "SE": ["se", "sweden", "stockholm"],
    "NO": ["no", "norway", "oslo"],
    "BE": ["be", "belgium", "brussels"],
    "ES": ["es", "spain", "madrid", "barcelona"],
    "IT": ["it", "italy", "rome", "milano", "naples"],
    "CZ": ["cz", "czech", "prague"],
    "SK": ["sk", "slovakia", "bratislava"],
    "HU": ["hu", "hungary", "budapest"],
    "RO": ["ro", "romania", "bucharest"],
    "BG": ["bg", "bulgaria", "sofia"],
    "GR": ["gr", "greece", "athens"],
    "PT": ["pt", "portugal", "lisbon"],
    "DK": ["dk", "denmark", "copenhagen"],
    "LT": ["lt", "lithuania", "vilnius"],
    "LV": ["lv", "latvia", "riga"],
    "EE": ["ee", "estonia", "tallinn"],
    "HR": ["hr", "croatia", "zagreb"],
    "RS": ["rs", "serbia", "belgrade"],
    "BA": ["ba", "bosnia"],
    "MD": ["md", "moldova"],
    "BY": ["by", "belarus", "minsk"],
    "KZ": ["kz", "kazakhstan", "almaty", "astana"],
    "UZ": ["uz", "uzbekistan", "tashkent"],
    "AE": ["ae", "emirates", "dubai", "abudhabi"],
    "SG": ["sg", "singapore"],
    "JP": ["jp", "japan", "tokyo"],
    "KR": ["kr", "korea", "seoul"],
    "CN": ["cn", "china", "beijing", "shanghai", "hongkong", "hk"],
    "HK": ["hk", "hongkong"],
    "TW": ["tw", "taiwan"],
    "IN": ["in", "india", "mumbai", "delhi"],
    "BR": ["br", "brazil", "sao paulo"],
    "CA": ["ca", "canada", "toronto", "montreal", "vancouver"],
    "AU": ["au", "australia", "sydney", "melbourne"],
    "NZ": ["nz", "newzealand"],
    "MX": ["mx", "mexico"],
    "AR": ["ar", "argentina", "buenosaires"],
    "ZA": ["za", "southafrica", "johannesburg"],
    "IL": ["il", "israel", "telaviv"],
    "SA": ["sa", "saudi", "riyadh"],
    "TH": ["th", "thailand", "bangkok"],
    "VN": ["vn", "vietnam", "hanoi", "hochiminh"],
    "MY": ["my", "malaysia", "kualalumpur"],
    "ID": ["id", "indonesia", "jakarta"],
    "PH": ["ph", "philippines", "manila"],
}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_dedup_key(config: dict) -> str:
    return f"{config['host']}:{config.get('port', '443')}:{config.get('uuid', '')}"


def parse_vless(link: str) -> dict | None:
    try:
        if not link.startswith("vless://"):
            return None
        
        url = urlparse(link)
        uuid = url.username
        host = url.hostname
        port = url.port or 443
        query = parse_qs(url.query)

        return {
            "uuid": uuid,
            "host": host,
            "port": str(port),
            "type": query.get("type", ["tcp"])[0],
            "security": query.get("security", ["none"])[0],
            "sni": query.get("sni", [host])[0] if query.get("sni") else host,
            "fp": query.get("fp", [""])[0],
            "alpn": query.get("alpn", [""])[0],
            "remarks": unquote(url.fragment) if url.fragment else "",
            "original": link
        }
    except Exception:
        return None


def build_remark(config: dict, is_perfect: bool = False) -> str:
    host_lower = config.get("host", "").lower()
    country_code = "??"
    for code, keywords in COUNTRY_KEYWORDS.items():
        if any(kw in host_lower for kw in keywords):
            country_code = code
            break
    flag = COUNTRY_MAP.get(country_code, "🌐")
    base = f"{flag} {config.get('host', 'unknown')}:{config.get('port', '443')}"
    return f"⭐ {base}" if is_perfect else base


def rebuild_vless(config: dict, new_remark: str) -> str:
    original = config["original"]
    base = original.split("#")[0] if "#" in original else original
    return f"{base}#{new_remark}"


# ==================== ПРОВЕРКИ (ICMP + HTTP + TCP) ====================

def icmp_check(host: str) -> bool:
    try:
        param = '-n' if os.name == 'nt' else '-c'
        timeout_param = '-w' if os.name == 'nt' else '-W'
        cmd = ['ping', param, '1', timeout_param, str(ICMP_TIMEOUT), host]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=ICMP_TIMEOUT + 2, shell=False)
        return result.returncode == 0
    except Exception:
        return False


async def async_http_check(host: str, port: int = 443) -> bool:
    try:
        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(HTTP_TEST_URL, allow_redirects=True) as resp:
                return resp.status in (200, 204, 301, 302)
    except Exception:
        return False


def http_check(host: str, port: int = 443) -> bool:
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(async_http_check(host, port))
        loop.close()
        return result
    except Exception:
        return False


def tcp_check(host: str, port: int = 443) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TCP_TIMEOUT)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def batch_check(parsed_list: list) -> dict:
    if not parsed_list:
        return {}
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_ICMP) as ex:
        futures = {get_dedup_key(p): ex.submit(icmp_check, p["host"]) 
                  for p in parsed_list if p.get("host")}
        for key, f in futures.items():
            results.setdefault(key, {})["icmp"] = f.result()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_HTTP) as ex:
        futures = {get_dedup_key(p): ex.submit(http_check, p["host"], int(p.get("port", 443))) 
                  for p in parsed_list if p.get("host")}
        for key, f in futures.items():
            results.setdefault(key, {})["http"] = f.result()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_TCP) as ex:
        futures = {get_dedup_key(p): ex.submit(tcp_check, p["host"], int(p.get("port", 443))) 
                  for p in parsed_list if p.get("host")}
        for key, f in futures.items():
            results.setdefault(key, {})["tcp"] = f.result()
    
    return results


# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================

def run_collection():
    log.info("🚀 Запуск сбора VLESS из GitHub + Telegram каналов...")

    all_links = set()

    for url in SOURCES:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"} if "t.me" in url else {}
            resp = requests.get(url, timeout=FETCH_TIMEOUT, headers=headers)
            resp.raise_for_status()
            text = resp.text

            found = VLESS_PATTERN.findall(text)
            all_links.update(found)

            source_name = url.split('/')[-1]
            log.info(f"✅ {source_name} → {len(found)} VLESS ссылок")
        except Exception as e:
            log.warning(f"❌ Ошибка загрузки {url}: {e}")

    log.info(f"Всего уникальных VLESS ссылок найдено: {len(all_links)}")

    # Парсинг
    parsed_list = []
    seen = set()
    for link in all_links:
        cfg = parse_vless(link)
        if not cfg or not cfg.get("host"):
            continue
        key = get_dedup_key(cfg)
        if key in seen:
            continue
        seen.add(key)
        parsed_list.append(cfg)

    log.info(f"Уникальных серверов после парсинга: {len(parsed_list)}")

    # Проверки
    log.info("🔍 Запуск проверок (ICMP + HTTP + TCP)... Это может занять время.")
    health = batch_check(parsed_list)

    # Формирование результатов
    checked = []
    all_configs = []
    perfect = 0
    any_passed = 0

    for cfg in parsed_list:
        key = get_dedup_key(cfg)
        h = health.get(key, {"icmp": False, "http": False, "tcp": False})

        passed_any = h["icmp"] or h["http"] or h["tcp"]
        passed_all = h["icmp"] and h["http"] and h["tcp"]

        if not passed_any:
            continue

        if passed_all:
            perfect += 1
        any_passed += 1

        remark = build_remark(cfg, passed_all)
        final = rebuild_vless(cfg, remark)

        checked.append(final)
        all_configs.append(final)

    # Сохранение файлов
    with open("vless_checked.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(checked))

    with open("vless_all.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(all_configs))

    log.info("🎉 Сбор и проверка завершены!")
    log.info(f"   Проверено серверов: {len(parsed_list)}")
    log.info(f"   Прошло хотя бы одну проверку: {any_passed}")
    log.info(f"   Идеальные (все 3 проверки) ⭐: {perfect}")
    log.info(f"   Сохранено в vless_checked.txt: {len(checked)}")
    log.info(f"   Сохранено в vless_all.txt: {len(all_configs)}")


if __name__ == "__main__":
    start = time.time()
    run_collection()
    log.info(f"Время выполнения: {time.time() - start:.1f} секунд")
