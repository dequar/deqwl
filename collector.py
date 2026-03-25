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
from urllib.parse import urlparse

# ====================== МАКСИМАЛЬНЫЙ ПУЛ РЕСУРСОВ ======================
TG_CHANNELS = [
    "urlsources", "V2rayNG3", "VlessConfig", "v2Line", "VlessVpnFree", "v2ray_free_conf",
    "V2ray_Click", "v2rayngvpn", "V2rayTz", "vless_vmess", "free4allVPN", "alphav2ray",
    "NEW_MTProxi", "FilterShekanPRO", "MsV2ray", "DailyV2RY", "FreeVlessVpn",
    "vmess_vless_v2rayng", "configV2rayForFree", "FreeV2rays", "DigiV2ray",
    "iranvpnet", "V2RAY_NEW", "VPNCUSTOMIZE", "V2rayRootFree", "RealityV2ray",
    "vless_free", "v2rayng_vpn", "FreeV2rayNG", "VlessReality"
]

SUBSCRIPTION_LINKS = [
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/vless_configs.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/filtered/subs/vless.txt",
    "https://raw.githubusercontent.com/Farid-Karimi/Config-Collector/main/vless.txt",
    "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector_Py/main/sub/VLESS/vless.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/main/vless.txt",
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_lite.txt",
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
    """Создаёт минимальный JSON-конфиг Xray для теста (outbound + socks inbound)"""
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "port": 1080,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"udp": True}
        }],
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": "",
                    "port": 443,
                    "users": [{"id": "", "encryption": "none", "flow": ""}]
                }]
            },
            "streamSettings": {"network": "tcp", "security": "none"}
        }]
    }

    # Парсим vless://
    try:
        if "@" not in vless_url:
            return None
        part = vless_url.split("://")[1].split("?")[0]
        uuid, rest = part.split("@", 1)
        host_port = rest.split("#")[0] if "#" in rest else rest
        host, port = host_port.split(":", 1)
        port = int(port)

        params = {}
        if "?" in vless_url:
            query = vless_url.split("?")[1].split("#")[0]
            for p in query.split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = v

        config["outbounds"][0]["settings"]["vnext"][0]["address"] = host
        config["outbounds"][0]["settings"]["vnext"][0]["port"] = port
        config["outbounds"][0]["settings"]["vnext"][0]["users"][0]["id"] = uuid

        # Поддержка Reality / uTLS / flow
        if "reality" in vless_url.lower() or "security=reality" in vless_url:
            config["outbounds"][0]["streamSettings"]["security"] = "reality"
            config["outbounds"][0]["streamSettings"]["realitySettings"] = {
                "serverName": params.get("sni", host),
                "fingerprint": params.get("fp", "chrome"),
                "publicKey": params.get("pbk", ""),
                "shortId": params.get("sid", "")
            }
        elif "security" in params:
            config["outbounds"][0]["streamSettings"]["security"] = params["security"]

        if "flow" in params:
            config["outbounds"][0]["settings"]["vnext"][0]["users"][0]["flow"] = params["flow"]

        return config
    except:
        return None

def test_vless(vless_url):
    """Тест через реальный Xray: поднимаем socks5 и делаем запросы на ya.ru + vk.com + cloudflare"""
    config = create_test_config(vless_url)
    if not config:
        return None

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        config_path = f.name

    try:
        # Запускаем Xray
        process = subprocess.Popen(
            ["xray", "run", "-c", config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(3)  # даём время на запуск

        # Тест через socks5
        proxies = {"http": "socks5://127.0.0.1:1080", "https": "socks5://127.0.0.1:1080"}
        test_urls = ["https://ya.ru", "https://vk.com", "https://1.1.1.1"]
        success = False
        latency = 9999

        for url in test_urls:
            try:
                start = time.time()
                r = requests.get(url, proxies=proxies, timeout=8)
                if r.status_code == 200:
                    success = True
                    latency = min(latency, int((time.time() - start) * 1000))
                    break
            except:
                continue

        process.terminate()
        process.wait(timeout=5)

        if success:
            remark = vless_url.split("#")[-1] if "#" in vless_url else "RU-tested"
            return f"{vless_url.split('#')[0]}#{remark}-latency-{latency}ms"
        return None
    except:
        return None
    finally:
        try:
            os.unlink(config_path)
        except:
            pass

# ====================== ОСНОВНОЙ ЦИКЛ ======================
print(f"[{datetime.now()}] Сбор конфигов + Xray-тест для РФ...")

all_configs = set()

for ch in TG_CHANNELS:
    links = fetch_tg(ch)
    all_configs.update(links)
    print(f"  ✓ TG @{ch}: {len(links)}")

for sub in SUBSCRIPTION_LINKS:
    links = fetch_subscription(sub)
    all_configs.update(links)
    print(f"  ✓ Raw: {len(links)}")

print(f"Всего уникальных перед тестом: {len(all_configs)}")

# Параллельный тест (ограничиваем до 600-800 для скорости в Actions)
working = []
with ThreadPoolExecutor(max_workers=12) as executor:
    future_to_url = {executor.submit(test_vless, url): url for url in list(all_configs)[:700]}
    for future in as_completed(future_to_url):
        result = future.result()
        if result:
            working.append(result)

# Сортировка по latency
working.sort(key=lambda x: int(x.split('latency-')[-1].split('ms')[0]) if 'latency-' in x else 9999)

with open("vless_checked.txt", "w", encoding="utf-8") as f:
    f.write("# VLESS Checked — только рабочие после Xray-теста (оптимизировано под РФ DPI)\n")
    f.write(f"# Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    f.write(f"# Рабочих конфигов: {len(working)}\n")
    f.write("# Тест: ya.ru + vk.com + 1.1.1.1 через socks5 (имитирует белые списки РФ)\n\n")
    f.write("\n".join(working))

print(f"ГОТОВО! В подписке {len(working)} рабочих VLESS, проверенных под российские провайдеры.")
