"""
proxy-checker — async proxy validator
HTTP / SOCKS4 / SOCKS5 · anonymity detection · response time · export
"""

import asyncio
import time
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

try:
    import aiohttp
    import aiohttp_socks
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, MofNCompleteColumn
    from rich.panel import Panel
    from rich.prompt import Prompt, IntPrompt, Confirm
    from rich import box
except ImportError:
    print("Missing dependencies. Run:\n  pip install aiohttp aiohttp-socks rich")
    sys.exit(1)

console = Console()

HTTPBIN_URL = "http://httpbin.org/get"

# Fallback IP detection — tried in order until one succeeds
IP_SERVICES = [
    ("https://api.ipify.org?format=json",  lambda d: d.get("ip")),
    ("https://api.my-ip.io/ip.json",       lambda d: d.get("ip")),
    ("https://ip.seeip.org/json",          lambda d: d.get("ip")),
    ("https://ip-api.com/json",            lambda d: d.get("query")),
]

# Preset check targets
PRESET_TARGETS = {
    "httpbin":   (HTTPBIN_URL,                    "httpbin.org  (+ anonymity detection)"),
    "instagram": ("https://www.instagram.com",    "instagram.com"),
    "google":    ("https://www.google.com",       "google.com"),
    "telegram":  ("https://telegram.org",         "telegram.org"),
    "youtube":   ("https://www.youtube.com",      "youtube.com"),
    "twitter":   ("https://twitter.com",          "twitter.com"),
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def _fail(proxy: str, ptype: str, error: str) -> dict:
    return {"proxy": proxy, "type": ptype, "ok": False, "ms": None, "anon": None, "error": error}

def _make_connector(ptype: str, proxy: str):
    """Return (connector, extra_request_kwargs) for the given proxy type."""
    if ptype == "http":
        return aiohttp.TCPConnector(ssl=False), {"proxy": f"http://{proxy}"}
    connector = aiohttp_socks.ProxyConnector.from_url(
        f"{ptype}://{proxy}", ssl=False, rdns=True
    )
    return connector, {}

# ── Anonymity ─────────────────────────────────────────────────────────────────
def detect_anonymity(headers: dict, origin: str, real_ip: str) -> str:
    """
    Parse a single httpbin /get response for anonymity level.
    `origin` is the IP httpbin saw. `headers` are the forwarded request headers.
    """
    PROXY_HEADERS = {
        "x-forwarded-for", "x-real-ip", "via", "forwarded-for",
        "proxy-connection", "x-forwarded-host",
    }
    hdrs = {k.lower(): v for k, v in headers.items()}

    if real_ip and real_ip != "unknown":
        haystack = " ".join(str(v) for v in hdrs.values()) + " " + origin
        if real_ip in haystack:
            return "transparent"

    if any(h in hdrs for h in PROXY_HEADERS):
        return "anonymous"

    return "elite"

# ── Single proxy check ────────────────────────────────────────────────────────
async def check_proxy(proxy: str, ptype: str, timeout: int, real_ip: str, check_url: str) -> dict:
    is_httpbin = "httpbin.org" in check_url
    t0 = time.monotonic()

    try:
        connector, req_kwargs = _make_connector(ptype, proxy)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as s:
            async with s.get(check_url, **req_kwargs) as r:
                # For custom targets any response <500 means reachable
                ok_threshold = 300 if is_httpbin else 500
                if r.status >= ok_threshold:
                    return _fail(proxy, ptype, f"status {r.status}")

                ms = round((time.monotonic() - t0) * 1000)

                anon = None
                if is_httpbin:
                    try:
                        data = await r.json(content_type=None)
                        anon = detect_anonymity(
                            data.get("headers", {}),
                            data.get("origin", ""),
                            real_ip,
                        )
                    except Exception:
                        anon = "unknown"

        return {"proxy": proxy, "type": ptype, "ok": True, "ms": ms, "anon": anon, "error": None}

    except asyncio.TimeoutError:
        return _fail(proxy, ptype, "timeout")
    except ConnectionResetError:
        return _fail(proxy, ptype, "connection reset")
    except Exception as e:
        return _fail(proxy, ptype, str(e)[:60])

# ── Batch runner ──────────────────────────────────────────────────────────────
async def run_checks(proxies, ptype, timeout, concurrency, real_ip, check_url) -> list:
    results = []
    sem = asyncio.Semaphore(concurrency)

    if ptype == "all":
        tasks_input = [(p, t) for p in proxies for t in ("http", "socks4", "socks5")]
    else:
        tasks_input = [(p, ptype) for p in proxies]

    async def bounded(proxy, pt, progress, tid):
        async with sem:
            r = await check_proxy(proxy, pt, timeout, real_ip, check_url)
            results.append(r)
            progress.advance(tid)

    with Progress(
        SpinnerColumn(style="green"),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=28, style="dim", complete_style="bright_green"),
        MofNCompleteColumn(),
        TextColumn("·"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        tid = progress.add_task(f"Checking [{ptype.upper()}]", total=len(tasks_input))
        await asyncio.gather(*[bounded(p, t, progress, tid) for p, t in tasks_input])

    return results

# ── Real IP (with fallback chain) ─────────────────────────────────────────────
async def get_real_ip() -> str:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
        for url, extract in IP_SERVICES:
            try:
                async with s.get(url) as r:
                    data = await r.json(content_type=None)
                    ip = extract(data)
                    if ip:
                        return ip
            except Exception:
                continue
    return "unknown"

# ── Display ───────────────────────────────────────────────────────────────────
ANON_COLOR = {
    "elite":       "bright_green",
    "anonymous":   "yellow",
    "transparent": "red",
    "unknown":     "dim",
    None:          "dim",
}

def ms_color(ms: int) -> str:
    return "bright_green" if ms < 500 else "yellow" if ms < 1500 else "red"

def display_results(results: list, show_failed: bool = False, check_url: str = HTTPBIN_URL):
    working   = sorted([r for r in results if r["ok"]], key=lambda r: r["ms"] or 9999)
    failed    = [r for r in results if not r["ok"]]
    total     = len(results)
    pct       = round(len(working) / total * 100) if total else 0
    is_httpbin = "httpbin.org" in check_url

    console.print(Panel(
        f"[bright_green]◉ Working:[/] [bold]{len(working)}[/]  "
        f"[red]✕ Dead:[/] [bold]{len(failed)}[/]  "
        f"[dim]Total:[/] {total}  "
        f"[dim]Rate:[/] [bold]{pct}%[/]",
        border_style="bright_green",
        title="Results",
    ))

    if not working:
        console.print("[dim]No working proxies found.[/]")
        return

    t = Table(box=box.SIMPLE_HEAD, header_style="bold dim", border_style="dim", min_width=60)
    t.add_column("Proxy",  style="cyan",  no_wrap=True, min_width=22)
    t.add_column("Type",   style="dim",   width=8)
    t.add_column("Ping",   justify="right", width=9)
    if is_httpbin:
        t.add_column("Anonymity", width=14)

    for r in working:
        ms_s  = f"[{ms_color(r['ms'])}]{r['ms']} ms[/]"
        row   = [r["proxy"], r["type"], ms_s]
        if is_httpbin:
            row.append(f"[{ANON_COLOR.get(r['anon'], 'dim')}]{r['anon'] or '—'}[/]")
        t.add_row(*row)
    console.print(t)

    if show_failed and failed:
        ft = Table(box=box.SIMPLE, header_style="bold dim", border_style="dim",
                   title=f"Dead ({len(failed)})")
        ft.add_column("Proxy",  style="dim", min_width=22)
        ft.add_column("Type",   style="dim", width=8)
        ft.add_column("Reason", style="red")
        for r in failed[:100]:
            ft.add_row(r["proxy"], r["type"], r["error"] or "—")
        console.print(ft)

# ── Export ────────────────────────────────────────────────────────────────────
def export_results(results, ptype, fmt, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    working = [r for r in results if r["ok"]]

    if fmt in ("txt", "both"):
        types = ("http", "socks4", "socks5") if ptype == "all" else (ptype,)
        for t in types:
            subset = [r for r in working if r["type"] == t]
            if not subset:
                continue
            p = out_dir / f"working_{t}_{ts}.txt"
            p.write_text("\n".join(r["proxy"] for r in subset))
            console.print(f"[green]◉[/] {len(subset)} {t} → [cyan]{p}[/]")

    if fmt in ("json", "both"):
        p = out_dir / f"results_{ptype}_{ts}.json"
        p.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        console.print(f"[green]◉[/] JSON → [cyan]{p}[/]")

# ── Proxy list loaders ────────────────────────────────────────────────────────
def load_from_url(url: str) -> list[str]:
    import urllib.request
    with console.status("[dim]Downloading...[/]"):
        with urllib.request.urlopen(url, timeout=15) as r:
            lines = r.read().decode(errors="ignore").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]

def load_from_file(path: str) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]

# ── Entry point ───────────────────────────────────────────────────────────────
SOURCES = {
    "1": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "2": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
    "3": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
}

async def async_main():
    parser = argparse.ArgumentParser(description="Async proxy validator")
    parser.add_argument("--url",  help="Proxy list URL")
    parser.add_argument("--file", help="Local proxy list path")
    parser.add_argument("--type", choices=["http", "socks4", "socks5", "all"],
                        help="Protocol(s) to test")
    parser.add_argument("--target", choices=list(PRESET_TARGETS.keys()),
                        default="httpbin",
                        help="Preset site to check against (default: httpbin)")
    parser.add_argument("--check-url", dest="check_url",
                        help="Custom URL to check proxy against (overrides --target)")
    parser.add_argument("--limit",       type=int, default=0,
                        help="Max proxies to check (0 = all)")
    parser.add_argument("--timeout",     type=int, default=10,
                        help="Seconds per request")
    parser.add_argument("--concurrency", type=int, default=50,
                        help="Parallel coroutines")
    parser.add_argument("--export", choices=["txt", "json", "both", "none"],
                        default="txt")
    parser.add_argument("--out", default="./results",
                        help="Output directory")
    parser.add_argument("--show-failed", action="store_true",
                        help="Show dead proxies in results table")
    args = parser.parse_args()

    # Resolve check URL (CLI)
    check_url = args.check_url or PRESET_TARGETS[args.target][0]

    console.print(Panel(
        "[bold bright_green]PROXY CHECKER[/]  [dim]async · HTTP · SOCKS4 · SOCKS5[/]",
        border_style="green", padding=(0, 2),
    ))

    # ── Interactive mode ──────────────────────────────────────────────────────
    if not (args.url or args.file):

        # Source
        console.print("\n[bold]Source[/]  [dim]— where to get proxies[/]")
        console.print("  [dim]1[/]  TheSpeedX HTTP    [dim](~3k proxies)[/]")
        console.print("  [dim]2[/]  TheSpeedX SOCKS4")
        console.print("  [dim]3[/]  TheSpeedX SOCKS5")
        console.print("  [dim]4[/]  Custom URL")
        console.print("  [dim]5[/]  Local file\n")
        src = Prompt.ask("", choices=["1","2","3","4","5"], default="1")

        if src in ("1","2","3"):
            proxies   = load_from_url(SOURCES[src])
            auto_type = {"1":"http","2":"socks4","3":"socks5"}[src]
        elif src == "4":
            proxies   = load_from_url(Prompt.ask("URL"))
            auto_type = "http"
        else:
            proxies   = load_from_file(Prompt.ask("File path"))
            auto_type = "http"

        console.print(f"[dim]Loaded {len(proxies)} proxies[/]")

        # Protocol
        console.print(f"\n[bold]Protocol[/]")
        console.print(f"  [dim]1[/]  HTTP  [dim]2[/]  SOCKS4  [dim]3[/]  SOCKS5  [dim]4[/]  All three\n")
        type_map = {"1":"http","2":"socks4","3":"socks5","4":"all"}
        auto_num = {"http":"1","socks4":"2","socks5":"3"}.get(auto_type, "1")
        ptype = type_map[Prompt.ask("", choices=["1","2","3","4"], default=auto_num)]

        # Target
        console.print(f"\n[bold]Target[/]  [dim]— which site to check against[/]")
        console.print("  [dim]1[/]  httpbin      [dim](default — also detects anonymity level)[/]")
        console.print("  [dim]2[/]  instagram.com")
        console.print("  [dim]3[/]  google.com")
        console.print("  [dim]4[/]  telegram.org")
        console.print("  [dim]5[/]  youtube.com")
        console.print("  [dim]6[/]  Custom URL\n")
        tgt_map = {
            "1": HTTPBIN_URL,
            "2": "https://www.instagram.com",
            "3": "https://www.google.com",
            "4": "https://telegram.org",
            "5": "https://www.youtube.com",
        }
        tgt = Prompt.ask("", choices=["1","2","3","4","5","6"], default="1")
        check_url = tgt_map[tgt] if tgt != "6" else Prompt.ask("URL")

        # Options
        console.print()
        limit = IntPrompt.ask(f"[bold]Check how many?[/]  [dim]0 = all {len(proxies)}[/]", default=0)
        if limit and limit < len(proxies):
            proxies = proxies[:limit]
        timeout     = IntPrompt.ask("[bold]Timeout[/]  [dim]seconds[/]", default=10)
        concurrency = IntPrompt.ask("[bold]Concurrency[/]  [dim]parallel checks[/]", default=50)
        export_fmt  = Prompt.ask("[bold]Export[/]", choices=["txt","json","both","none"], default="txt")
        show_failed = Confirm.ask("[bold]Show dead proxies?[/]", default=False)
        out_dir     = Path("./results")

    # ── Non-interactive path ──────────────────────────────────────────────────
    else:
        proxies     = load_from_url(args.url) if args.url else load_from_file(args.file)
        ptype       = args.type or "http"
        limit       = args.limit
        timeout     = args.timeout
        concurrency = args.concurrency
        export_fmt  = args.export
        show_failed = args.show_failed
        out_dir     = Path(args.out)
        if limit and limit < len(proxies):
            proxies = proxies[:limit]

    # ── Run ───────────────────────────────────────────────────────────────────
    is_httpbin    = "httpbin.org" in check_url
    target_label  = "httpbin.org  (anonymity check)" if is_httpbin else check_url
    console.print(f"[dim]Target : {target_label}[/]")

    with console.status("[dim]Detecting your IP...[/]", spinner="dots"):
        real_ip = await get_real_ip()
    console.print(f"[dim]Your IP: {real_ip}[/]\n")

    t0      = time.monotonic()
    results = await run_checks(proxies, ptype, timeout, concurrency, real_ip, check_url)
    elapsed = time.monotonic() - t0
    console.print(f"\n[dim]Done in {elapsed:.1f}s[/]\n")

    display_results(results, show_failed=show_failed, check_url=check_url)

    if export_fmt != "none":
        export_results(results, ptype, export_fmt, out_dir)

    if ptype == "all":
        console.print()
        for t in ("http", "socks4", "socks5"):
            sub = [r for r in results if r["ok"] and r["type"] == t]
            if sub:
                avg = round(sum(r["ms"] for r in sub) / len(sub))
                console.print(f"  [dim]{t:8}[/]  [green]{len(sub)} live[/]  avg [yellow]{avg} ms[/]")


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped.[/]")
        sys.exit(0)


if __name__ == "__main__":
    main()