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
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

# ==================== НАСТРОЙКИ ====================
SOURCES = [
    "https://raw.githubusercontent.com/zieng2/wl/main/vless.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
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

# ==================== GUI ====================

class GuiLogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__(level=logging.INFO)
        self.callback = callback

    def emit(self, record):
        msg = self.format(record)
        self.callback(msg)


class CollectorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VLESS Collector GUI")
        self.geometry("920x720")
        self.resizable(True, True)

        self._log_handler = None
        self.create_widgets()

    def create_widgets(self):
        sources_frame = ttk.LabelFrame(self, text="SOURCES — добавленные ссылки")
        sources_frame.pack(fill="both", expand=False, padx=10, pady=8)

        list_frame = ttk.Frame(sources_frame)
        list_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.sources_listbox = tk.Listbox(list_frame, selectmode="single", activestyle="dotbox")
        self.sources_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.sources_listbox.yview)
        scrollbar.pack(side="left", fill="y")
        self.sources_listbox.config(yscrollcommand=scrollbar.set)

        for source in SOURCES:
            self.sources_listbox.insert(tk.END, source)

        add_frame = ttk.Frame(sources_frame)
        add_frame.pack(fill="x", padx=6, pady=4)

        add_button = ttk.Button(add_frame, text="Добавить ссылку", command=self.add_source)
        add_button.pack(side="left", padx=4)

        delete_button = ttk.Button(add_frame, text="Удалить ссылку", command=self.delete_source)
        delete_button.pack(side="left", padx=4)

        clear_button = ttk.Button(add_frame, text="Удалить все ссылки", command=self.clear_sources)
        clear_button.pack(side="left", padx=4)

        self.run_button = ttk.Button(self, text="Запустить проверку", command=self.on_run_clicked)
        self.run_button.pack(fill="x", padx=10, pady=4)

        self.status_label = ttk.Label(self, text="Готов к запуску", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=(0, 8))

        log_frame = ttk.LabelFrame(self, text="Лог выполнения")
        log_frame.pack(fill="both", expand=True, padx=10, pady=0)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=18, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

    def add_source(self):
        try:
            url = self.clipboard_get().strip()
        except tk.TclError:
            messagebox.showwarning("Буфер пуст", "В буфере нет текста для вставки.")
            return
        if not url:
            messagebox.showwarning("Пустая ссылка", "Буфер не содержит URL.")
            return
        if url in self.sources_listbox.get(0, tk.END):
            messagebox.showinfo("Уже добавлено", "Эта ссылка уже присутствует в списке.")
            return
        self.sources_listbox.insert(tk.END, url)

    def delete_source(self):
        selected = self.sources_listbox.curselection()
        if not selected:
            messagebox.showwarning("Ничего не выбрано", "Выберите ссылку для удаления.")
            return
        self.sources_listbox.delete(selected[0])

    def clear_sources(self):
        if messagebox.askyesno("Удалить все ссылки", "Точно удалить все ссылки из списка?"):
            self.sources_listbox.delete(0, tk.END)

    def get_sources(self) -> list[str]:
        return list(self.sources_listbox.get(0, tk.END))

    def on_run_clicked(self):
        sources = self.get_sources()
        if not sources:
            messagebox.showwarning("Нет источников", "Добавьте хотя бы один URL в список SOURCES.")
            return
        self.run_button.config(state="disabled")
        self.status_label.config(text="Выполняется проверка... Пожалуйста, подождите.")
        self.append_log("=== Запуск проверки SOURCES ===")
        threading.Thread(target=self.run_collection_thread, args=(sources,), daemon=True).start()

    def run_collection_thread(self, sources: list[str]):
        self.attach_log_handler()
        try:
            checked_count, all_count = run_collection(sources)
            self.after(0, lambda: self.on_collection_done(checked_count, all_count))
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Произошла ошибка:\n{exc}"))
            self.append_log(f"Ошибка выполнения: {exc}")
        finally:
            self.detach_log_handler()

    def attach_log_handler(self):
        if self._log_handler is None:
            self._log_handler = GuiLogHandler(lambda msg: self.after(0, lambda: self.append_log(msg)))
            self._log_handler.setFormatter(logging.Formatter("%(message)s"))
            log.addHandler(self._log_handler)

    def detach_log_handler(self):
        if self._log_handler is not None:
            log.removeHandler(self._log_handler)
            self._log_handler = None

    def append_log(self, message: str):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def on_collection_done(self, checked_count: int, all_count: int):
        self.status_label.config(text=f"Готово. Живых: {checked_count}, всего: {all_count}")
        self.run_button.config(state="normal")
        self.append_log("=== Завершено ===")


def run_collection(sources: list[str]) -> tuple[int, int]:
    log.info(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Запуск сборщика VLESS...\n")

    log.info("=== Загрузка источников ===")
    raw_configs = fetch_all(sources)
    log.info(f"Всего найдено (с дублями): {len(raw_configs)}\n")

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

    parsed_list = list(unique.values())
    tcp_results = tcp_check_batch(parsed_list)

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

    sorted_countries = sorted(
        groups.keys(),
        key=lambda c: (0 if c == "RU" else (1 if c != "XX" else 2), c)
    )

    checked_list = []
    all_list = []
    for country in sorted_countries:
        items = groups[country]
        items_sorted = sorted(items, key=lambda x: (0 if x[2] else 1))
        for i, (p, proto, alive) in enumerate(items_sorted, 1):
            remark = make_remark(p, country, proto, i, alive)
            all_list.append(remark)
            if alive:
                checked_list.append(remark)

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

    return len(checked_list), len(all_list)


if __name__ == "__main__":
    app = CollectorGUI()
    app.mainloop()
