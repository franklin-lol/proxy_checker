<div align="center">

```
██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗
██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝
██████╔╝██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝ 
██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝  
██║     ██║  ██║╚██████╔╝██╔╝ ██╗   ██║   
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝  
        C H E C K E R
```

**Async proxy validator with a rich TUI.**  
HTTP · SOCKS4 · SOCKS5 · anonymity detection · custom targets · JSON/TXT export

---

[![Python](https://img.shields.io/badge/Python-3.10+-3572A5?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![asyncio](https://img.shields.io/badge/asyncio-powered-009688?style=flat-square)](https://docs.python.org/3/library/asyncio.html)
[![aiohttp](https://img.shields.io/badge/aiohttp-3.9-00BFA5?style=flat-square)](https://docs.aiohttp.org)
[![rich](https://img.shields.io/badge/rich-TUI-b44afb?style=flat-square)](https://github.com/Textualize/rich)
[![License: MIT](https://img.shields.io/badge/license-MIT-555?style=flat-square)](LICENSE)

</div>

---

## Overview

`proxy-checker` validates large proxy lists at high speed using fully async I/O. It measures response time, detects anonymity level, and lets you check proxies against any target — not just "is it alive?" but "does it reach Instagram / Telegram / Google?"

---

## ☁️ Run in Cloud (GitHub Actions)

You can run this checker directly on GitHub's servers without installing anything on your PC:

1. Go to the **[Actions](/../../actions/workflows/run_checker.yml)** tab.
2. Select **"Proxy Checker Cloud Run"** on the left.
3. Click **"Run workflow"** on the right.
4. Enter your proxy list URL (or use presets `1`, `2`, `3`) and adjust settings.
5. Once finished, download the results from the **Artifacts** section at the bottom of the run page.

---

## What's inside

| | Before | Now |
|---|---|---|
| **I/O model** | `requests` + threads | `asyncio` + `aiohttp` |
| **Concurrency** | 10 threads | 50 coroutines (configurable) |
| **Protocols** | one at a time | HTTP · SOCKS4 · SOCKS5 simultaneously |
| **Anonymity** | — | Elite / Anonymous / Transparent |
| **Check target** | httpbin only | httpbin · Instagram · Google · Telegram · custom URL |
| **IP detection** | ipify only | 4-service fallback chain |
| **Requests per proxy** | 2 (ip + headers) | 1 (unified `/get`) |
| **Export** | `.txt` only | `.txt`, `.json`, or both |
| **Interface** | `print()` | `rich` — progress bar, tables, panels |
| **CLI mode** | interactive only | full `--flag` non-interactive mode |
| **Platform** | Windows only | Linux · macOS · Windows |

---

## Install

```bash
git clone https://github.com/franklin-lol/proxy-checker
cd proxy-checker
pip install -r requirements.txt
```

> **Python 3.10+ required**

---

## Usage

### Interactive mode

```bash
python proxy_checker.py
```

Step-by-step prompts:

1. **Source** — public list, custom URL, or local file
2. **Protocol** — HTTP / SOCKS4 / SOCKS5 / All
3. **Target** — which site to check against (httpbin, Instagram, Google, Telegram, YouTube, custom)
4. **Limit** — how many proxies to check (`0` = all)
5. **Timeout & concurrency** — tune for speed vs accuracy
6. **Export** — format and output directory

### CLI mode

```bash
# Check HTTP proxies against Instagram
python proxy_checker.py \
  --url https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt \
  --type http \
  --target instagram \
  --timeout 10 \
  --concurrency 100 \
  --export txt

# Check all types from a local file against a custom URL, export JSON
python proxy_checker.py \
  --file proxies.txt \
  --type all \
  --check-url https://my-target-site.com \
  --limit 500 \
  --export json \
  --show-failed

# Full anonymity check (default httpbin target)
python proxy_checker.py \
  --url https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt \
  --type http \
  --target httpbin \
  --export both
```

### Flags reference

| Flag | Default | Description |
|------|---------|-------------|
| `--url` | — | Proxy list URL |
| `--file` | — | Local proxy list path |
| `--type` | interactive | `http` · `socks4` · `socks5` · `all` |
| `--target` | `httpbin` | Preset: `httpbin` · `instagram` · `google` · `telegram` · `youtube` · `twitter` |
| `--check-url` | — | Custom URL to check against (overrides `--target`) |
| `--limit` | `0` (all) | Max proxies to check |
| `--timeout` | `10` | Seconds per request |
| `--concurrency` | `50` | Parallel coroutines |
| `--export` | `txt` | `txt` · `json` · `both` · `none` |
| `--out` | `./results` | Output directory |
| `--show-failed` | off | Include dead proxies in results table |

---

## Anonymity levels

> Detected automatically when using `--target httpbin` (default).  
> Not available when checking against Instagram, Google, etc.

| Level | What it means |
|---|---|
| 🟢 **Elite** | Server sees no proxy headers and doesn't know your real IP |
| 🟡 **Anonymous** | Proxy headers present, but real IP is hidden |
| 🔴 **Transparent** | Your real IP is leaked via `X-Forwarded-For` or similar |

---

## Free proxy sources

```
# HTTP
https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt
https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt
https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt

# SOCKS4
https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt

# SOCKS5
https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt
```

---

## How to use your proxies

After checking, you get a `.txt` file with working proxies in `ip:port` format in `./results/`.  
Here's how to plug them into different platforms.

---

### 🖥️ Windows

**System-wide (all apps at once):**

1. Settings → Network & Internet → Proxy
2. Enable **Manual proxy setup**
3. Enter the IP and Port
4. Save

**Browser only:**

- **Chrome** — installs [Proxy SwitchyOmega](https://chrome.google.com/webstore/detail/proxy-switchyomega/padekgcemlokbadohgkifijomclgjgif), configure a profile with your proxy
- **Firefox** — Settings → Network Settings → Manual proxy configuration

**For scripts / automation:**

```cmd
:: HTTP proxy
set HTTP_PROXY=http://45.77.10.21:8080
set HTTPS_PROXY=http://45.77.10.21:8080
python your_script.py

:: SOCKS5 proxy
set HTTP_PROXY=socks5://45.77.10.21:1080
set HTTPS_PROXY=socks5://45.77.10.21:1080
python your_script.py
```

---

### 📱 iOS

**Per Wi-Fi network (HTTP proxies):**

1. Settings → Wi-Fi → tap **ⓘ** next to your network
2. Scroll to **HTTP Proxy** → Configure Proxy → **Manual**
3. Enter Server (IP) and Port
4. Save

> Applies only to that Wi-Fi network. Mobile data does not support system proxy on iOS.

**SOCKS5 / app-level routing:**  
iOS has no native SOCKS support system-wide. Use **Shadowrocket** or **Quantumult X** (App Store, paid) to route traffic through SOCKS5 proxies.

---

### 🤖 Android

**Per Wi-Fi network:**

1. Settings → Wi-Fi → long press your network → **Modify network**
2. Expand **Advanced options**
3. Proxy → **Manual** → enter IP and Port
4. Save

> Applies only to that Wi-Fi network.

**System-wide / SOCKS5:**  
Use **[Every Proxy](https://play.google.com/store/apps/details?id=com.gorillasoftware.everyproxy)** (free) or **[ProxyDroid](https://play.google.com/store/apps/details?id=org.proxydroid)** (requires root).

---

### 🐍 In your Python scripts

```python
import requests

proxy = "45.77.10.21:8080"

# HTTP proxy
r = requests.get("https://httpbin.org/ip", proxies={
    "http":  f"http://{proxy}",
    "https": f"http://{proxy}",
}, timeout=10)

# SOCKS5 proxy  (pip install requests[socks])
r = requests.get("https://httpbin.org/ip", proxies={
    "http":  "socks5://45.77.10.21:1080",
    "https": "socks5://45.77.10.21:1080",
}, timeout=10)

print(r.json())
```

---

## Package as an EXE (Windows)

You can bundle the script into a standalone `.exe` — useful for sharing with people who don't have Python.

```bash
pip install pyinstaller
pyinstaller --onefile --name proxy-checker proxy_checker.py
```

Output appears in `dist/proxy-checker.exe` (~15 MB). All interactive and CLI modes work as-is.

> **Note:** Windows Defender may flag fresh PyInstaller binaries (false positive).  
> Add `dist/` as an exclusion in Windows Security → Virus & threat protection → Exclusions.

---

## Project structure

```
proxy-checker/
├── proxy_checker.py   # main script — all logic in one file
├── requirements.txt   # aiohttp, aiohttp-socks, rich
└── results/           # output directory (auto-created)
    ├── working_http_*.txt
    ├── working_socks5_*.txt
    └── results_all_*.json
```

---

## Requirements

```
aiohttp==3.9.5
aiohttp-socks==0.8.4
rich==13.7.1
```

---

## License

MIT — do whatever you want with it.