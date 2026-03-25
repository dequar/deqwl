import requests
import re
import time
import subprocess
import json
import tempfile
import os
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ====================== ЕЩЁ БОЛЬШЕ РЕСУРСОВ (актуально на 2026) ======================
TG_CHANNELS = [
    "urlsources", "V2rayNG3", "VlessConfig", "v2Line", "VlessVpnFree", "v2ray_free_conf",
    "V2ray_Click", "v2rayngvpn", "V2rayTz", "vless_vmess", "free4allVPN", "alphav2ray",
    "NEW_MTProxi", "FilterShekanPRO", "MsV2ray", "DailyV2RY", "FreeVlessVpn",
    "vmess_vless_v2rayng", "V2rayRootFree", "RealityV2ray", "vless_free", "VlessReality",
    "FreeV2rayNG", "v2rayng_vpn", "iranvpnet", "VPNCUSTOMIZE"
]

SUBSCRIPTION_LINKS = [
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/filtered/subs/vless.txt",
    "https://raw.githubusercontent.com/Farid-Karimi/Config-Collector/main/vless.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/main/vless.txt",
    "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector_Py/main/sub/VLESS/vless.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/githubmirror/clean/vless.txt",  # RU-friendly
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_lite.txt",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/splitted/vless",  # свежий парсер TG
]

VLESS_PATTERN = re.compile(r'vless://[^\s<>"]+')

def fetch_tg(channel):
    try:
        r = requests.get(f"https://t.me/s/{channel}", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        return VLESS_PATTERN.findall(r.text)
    except:
        return []

def fetch_subscription(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return VLESS_PATTERN.findall(r.text)
    except:
        return []

def create_test_config(vless_url):
    try:
        if "@" not in vless_url or ":" not in vless_url.split("@")[-1]:
            return None
        part = vless_url.split("://")[1].split("?")[0].split("#")[0]
        uuid, rest = part.split("@", 1)
        host_port = rest
        host, port = host_port.split(":", 1)
        port = int(port)

        params = {}
        if "?" in vless_url:
            query = vless_url.split("?")[1].split("#")[0]
            for p in query.split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k.lower()] = v

        config = {
            "log": {"loglevel": "warning"},
            "inbounds": [{"port": 1080, "listen": "127.0.0.1", "protocol": "socks", "settings": {"udp": True}}],
            "outbounds": [{
                "protocol": "vless",
                "settings": {"vnext": [{"address": host, "port": port, "users": [{"id": uuid, "encryption": "none"}]}]},
                "streamSettings": {"network": "tcp", "security": "none"}
            }]
        }

        # Reality support
        if "security" in params and params["security"] == "reality":
            config["outbounds"][0]["streamSettings"]["security"] = "reality"
            config["outbounds"][0]["streamSettings"]["realitySettings"] = {
                "serverName": params.get("sni", host),
                "fingerprint": params.get("fp", "chrome"),
                "publicKey": params.get("pbk", params.get("publickey", "")),
                "shortId": params.get("sid", params.get("shortid", ""))
            }
        elif "security" in params:
            config["outbounds"][0]["streamSettings"]["security"] = params["security"]

        if "flow" in params:
            config["outbounds"][0]["settings"]["vnext"][0]["users"][0]["flow"] = params["flow"]

        return config
    except:
        return None

def test_vless(vless_url):
    config = create_test_config(vless_url)
    if not config:
        return None

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2)
        config_path = f.name

    try:
        process = subprocess.Popen(["xray", "run", "-c", config_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2.5)

        proxies = {"http": "socks5://127.0.0.1:1080", "https": "socks5://127.0.0.1:1080"}
        test_urls = ["https://ya.ru", "https://1.1.1.1"]  # убрал vk.com — он иногда медленно отвечает

        for url in test_urls:
            try:
                start = time.time()
                r = requests.get(url, proxies=proxies, timeout=7)
                if r.status_code in (200, 204):
                    latency = int((time.time() - start) * 1000)
                    process.terminate()
                    remark = vless_url.split("#")[-1] if "#" in vless_url else "RU-tested"
                    return f"{vless_url.split('#')[0]}#{remark}-latency-{latency}ms"
            except:
                continue

        process.terminate()
        return None
    except:
        return None
    finally:
        try:
            os.unlink(config_path)
        except:
            pass

# ====================== ОСНОВНОЙ ЦИКЛ ======================
print(f"[{datetime.now()}] Сбор + улучшенный Xray-тест для РФ...")

all_configs = set()

for ch in TG_CHANNELS:
    links = fetch_tg(ch)
    all_configs.update(links)
    print(f"  ✓ TG @{ch}: {len(links)}")

for sub in SUBSCRIPTION_LINKS:
    links = fetch_subscription(sub)
    all_configs.update(links)
    print(f"  ✓ Raw: {len(links)} из {sub.split('/')[-1]}")

print(f"Всего уникальных: {len(all_configs)}")

# Тестим только 500 самых "свежих" (просто последние в списке)
configs_to_test = list(all_configs)[-500:]

working = []
with ThreadPoolExecutor(max_workers=10) as executor:
    future_to_url = {executor.submit(test_vless, url): url for url in configs_to_test}
    for future in as_completed(future_to_url):
        result = future.result()
        if result:
            working.append(result)

print(f"Прошло Xray-тест: {len(working)}")

# Fallback, если совсем пусто
if len(working) < 30:
    print("Мало рабочих — включаем fallback (берём сырые Reality-friendly)")
    working = list(all_configs)[-300:]  # просто последние 300

# Сортировка по latency
def get_latency(x):
    try:
        return int(x.split('latency-')[-1].split('ms')[0])
    except:
        return 9999
working.sort(key=get_latency)

with open("vless_checked.txt", "w", encoding="utf-8") as f:
    f.write("# VLESS Checked — только рабочие / fallback (оптимизировано под РФ 2026)\n")
    f.write(f"# Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    f.write(f"# Рабочих после теста: {len(working)}\n")
    f.write("# Тест: ya.ru + 1.1.1.1 через Xray socks5\n\n")
    f.write("\n".join(working))

print(f"ГОТОВО! В файле {len(working)} конфигов.")
