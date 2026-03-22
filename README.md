# proxy-checker

> Async proxy validator with rich TUI. HTTP · SOCKS4 · SOCKS5 · anonymity detection · response time · JSON/TXT export.

![Python](https://img.shields.io/badge/Python-3.10+-3572A5?style=flat-square&logo=python&logoColor=white)
![aiohttp](https://img.shields.io/badge/aiohttp-async-009688?style=flat-square)
![rich](https://img.shields.io/badge/rich-TUI-b44afb?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-555?style=flat-square)

---

## What's new vs the original

| Feature | Before | Now |
|---|---|---|
| Protocol | HTTP / SOCKS4 / SOCKS5 (one at a time) | All three simultaneously with `--type all` |
| I/O model | `concurrent.futures` + `requests` (blocking) | `asyncio` + `aiohttp` (fully async) |
| Concurrency | 10 threads | 50 coroutines (configurable) |
| Anonymity | — | Elite / Anonymous / Transparent detection |
| Response time | — | Measured per proxy, color-coded |
| Export | `.txt` only | `.txt`, `.json`, or both |
| Cross-platform | Windows only (`msvcrt`) | Linux / macOS / Windows |
| Interface | `print()` | `rich` — progress bar, tables, panels |
| CLI mode | Interactive only | Full `--flag` non-interactive mode |

---

## Install

```bash
git clone https://github.com/franklin-lol/proxy-checker
cd proxy-checker
pip install -r requirements.txt
```

**Python 3.10+ required.**

---

## Interactive mode

```bash
python proxy_checker.py
```

You'll be prompted step by step:
1. Protocol (HTTP / SOCKS4 / SOCKS5 / All)
2. Source — URL or local file
3. How many proxies to check (0 = all)
4. Timeout and concurrency
5. Export format and output directory

---

## CLI mode (non-interactive)

```bash
# Check HTTP proxies from URL, export TXT
python proxy_checker.py \
  --url https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt \
  --type http \
  --timeout 10 \
  --concurrency 100 \
  --export txt \
  --out ./results

# Check all types from local file, export JSON, show dead proxies
python proxy_checker.py \
  --file proxies.txt \
  --type all \
  --limit 500 \
  --export json \
  --show-failed
```

### All flags

| Flag | Default | Description |
|------|---------|-------------|
| `--url` | — | Proxy list URL |
| `--file` | — | Local proxy list path |
| `--type` | interactive | `http` / `socks4` / `socks5` / `all` |
| `--limit` | 0 (all) | Max proxies to check |
| `--timeout` | 10 | Seconds per request |
| `--concurrency` | 50 | Concurrent coroutines |
| `--export` | `txt` | `txt` / `json` / `both` / `none` |
| `--out` | `./results` | Output directory |
| `--show-failed` | off | Show dead proxies in results table |

---

## Anonymity levels

| Level | Meaning |
|---|---|
| **Elite** | Server sees no proxy headers and doesn't know your real IP |
| **Anonymous** | Proxy headers present but real IP is hidden |
| **Transparent** | Your real IP is leaked via `X-Forwarded-For` or similar |

Detection is done against `httpbin.org/headers` — the same request target used for the connection test.

---

## Output example

```
◉ Working: 42   ✕ Dead: 958   Total: 1000   Success rate: 4%

  Proxy                    Type     Ping    Anonymity   Status
  ─────────────────────────────────────────────────────────────
  45.77.10.21:8080         http     312 ms  elite       live
  103.149.130.38:80        http     489 ms  anonymous   live
  82.165.184.53:3128       http     921 ms  transparent live
  ...

◉ Saved 42 proxies → ./results/working_http_20240318_142300.txt
```

---

## Free proxy list sources

```
https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt
https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt
https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt
https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt
https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt
```

---

## License

MIT
