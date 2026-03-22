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

CHECK_URL = "http://httpbin.org/ip"
ANON_URL  = "http://httpbin.org/headers"

# ── Anonymity ─────────────────────────────────────────────────────────────────
def detect_anonymity(headers: dict, real_ip: str) -> str:
    proxy_headers = {"x-forwarded-for","x-real-ip","via","forwarded-for","proxy-connection","x-forwarded-host"}
    hdrs = {k.lower(): v for k, v in headers.items()}
    if any(real_ip in str(v) for v in hdrs.values()):
        return "transparent"
    if any(h in hdrs for h in proxy_headers):
        return "anonymous"
    return "elite"

# ── Single check ──────────────────────────────────────────────────────────────
async def check_proxy(proxy: str, ptype: str, timeout: int, real_ip: str) -> dict:
    t0    = time.monotonic()
    error = "unknown"
    try:
        if ptype == "http":
            conn = aiohttp.TCPConnector(ssl=False)
            proxy_url = f"http://{proxy}"
            async with aiohttp.ClientSession(
                connector=conn,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as s:
                async with s.get(CHECK_URL, proxy=proxy_url) as r:
                    if r.status != 200:
                        return {"proxy": proxy, "type": ptype, "ok": False, "ms": None, "anon": None, "error": f"status {r.status}"}
                    ms = round((time.monotonic() - t0) * 1000)
                try:
                    async with s.get(ANON_URL, proxy=proxy_url) as r2:
                        data = await r2.json()
                        anon = detect_anonymity(data.get("headers", {}), real_ip)
                except Exception:
                    anon = "unknown"
        else:
            connector = aiohttp_socks.ProxyConnector.from_url(
                f"{ptype}://{proxy}", ssl=False, rdns=True
            )
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as s:
                async with s.get(CHECK_URL) as r:
                    if r.status != 200:
                        return {"proxy": proxy, "type": ptype, "ok": False, "ms": None, "anon": None, "error": f"status {r.status}"}
                    ms = round((time.monotonic() - t0) * 1000)
                try:
                    async with s.get(ANON_URL) as r2:
                        data = await r2.json()
                        anon = detect_anonymity(data.get("headers", {}), real_ip)
                except Exception:
                    anon = "unknown"

        return {"proxy": proxy, "type": ptype, "ok": True, "ms": ms, "anon": anon, "error": None}

    except asyncio.TimeoutError:
        error = "timeout"
    except ConnectionResetError:
        error = "connection reset"
    except Exception as e:
        error = str(e)[:60]

    return {"proxy": proxy, "type": ptype, "ok": False, "ms": None, "anon": None, "error": error}

# ── Batch ─────────────────────────────────────────────────────────────────────
async def run_checks(proxies, ptype, timeout, concurrency, real_ip) -> list:
    results = []
    sem = asyncio.Semaphore(concurrency)

    tasks_input = []
    if ptype == "all":
        for p in proxies:
            for t in ("http", "socks4", "socks5"):
                tasks_input.append((p, t))
    else:
        tasks_input = [(p, ptype) for p in proxies]

    async def bounded(proxy, pt, progress, tid):
        async with sem:
            r = await check_proxy(proxy, pt, timeout, real_ip)
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

# ── Real IP ───────────────────────────────────────────────────────────────────
async def get_real_ip() -> str:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            async with s.get("https://api.ipify.org?format=json") as r:
                return (await r.json()).get("ip", "unknown")
    except Exception:
        return "unknown"

# ── Display ───────────────────────────────────────────────────────────────────
ANON_COLOR = {"elite":"bright_green","anonymous":"yellow","transparent":"red","unknown":"dim"}
def ms_color(ms): return "bright_green" if ms < 500 else "yellow" if ms < 1500 else "red"

def display_results(results: list, show_failed: bool = False):
    working = sorted([r for r in results if r["ok"]], key=lambda r: r["ms"] or 9999)
    failed  = [r for r in results if not r["ok"]]
    total   = len(results)
    pct     = round(len(working) / total * 100) if total else 0

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
    t.add_column("Proxy",     style="cyan",  no_wrap=True, min_width=22)
    t.add_column("Type",      style="dim",   width=8)
    t.add_column("Ping",      justify="right", width=9)
    t.add_column("Anonymity", width=14)

    for r in working:
        ms_s   = f"[{ms_color(r['ms'])}]{r['ms']} ms[/]"
        anon_s = f"[{ANON_COLOR.get(r['anon'],'dim')}]{r['anon'] or '—'}[/]"
        t.add_row(r["proxy"], r["type"], ms_s, anon_s)
    console.print(t)

    if show_failed and failed:
        ft = Table(box=box.SIMPLE, header_style="bold dim", border_style="dim", title=f"Dead ({len(failed)})")
        ft.add_column("Proxy", style="dim", min_width=22)
        ft.add_column("Type",  style="dim", width=8)
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
        types = ("http","socks4","socks5") if ptype == "all" else (ptype,)
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

# ── Load proxies ──────────────────────────────────────────────────────────────
def load_from_url(url: str) -> list[str]:
    import urllib.request
    with console.status(f"[dim]Downloading...[/]"):
        with urllib.request.urlopen(url, timeout=15) as r:
            lines = r.read().decode(errors="ignore").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.startswith("#")]

def load_from_file(path: str) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.startswith("#")]

# ── Main ──────────────────────────────────────────────────────────────────────
SOURCES = {
    "1": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "2": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
    "3": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
}
SOURCE_LABELS = {
    "1": "TheSpeedX/http",
    "2": "TheSpeedX/socks4",
    "3": "TheSpeedX/socks5",
}

async def async_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url");  parser.add_argument("--file")
    parser.add_argument("--type",  choices=["http","socks4","socks5","all"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--export", choices=["txt","json","both","none"], default="txt")
    parser.add_argument("--out",  default="./results")
    parser.add_argument("--show-failed", action="store_true")
    args = parser.parse_args()

    console.print(Panel(
        "[bold bright_green]PROXY CHECKER[/]  [dim]async · HTTP · SOCKS4 · SOCKS5[/]",
        border_style="green", padding=(0, 2),
    ))

    # ── Step 1: source ────────────────────────────────────────────────────────
    if args.url or args.file:
        proxies = load_from_url(args.url) if args.url else load_from_file(args.file)
        ptype   = args.type or "http"
    else:
        console.print("\n[bold]Source[/]  [dim]— where to get proxies[/]")
        console.print("  [dim]1[/]  TheSpeedX HTTP list  [dim](public, ~3k proxies)[/]")
        console.print("  [dim]2[/]  TheSpeedX SOCKS4 list")
        console.print("  [dim]3[/]  TheSpeedX SOCKS5 list")
        console.print("  [dim]4[/]  Custom URL")
        console.print("  [dim]5[/]  Local file\n")
        src = Prompt.ask("", choices=["1","2","3","4","5"], default="1")

        if src in ("1","2","3"):
            proxies = load_from_url(SOURCES[src])
            # auto-select matching type but still allow override
            auto_type = {"1":"http","2":"socks4","3":"socks5"}[src]
        elif src == "4":
            url     = Prompt.ask("URL")
            proxies = load_from_url(url)
            auto_type = "http"
        else:
            path    = Prompt.ask("File path")
            proxies = load_from_file(path)
            auto_type = "http"

        console.print(f"[dim]Loaded {len(proxies)} proxies[/]")

        # ── Step 2: type ──────────────────────────────────────────────────────
        console.print(f"\n[bold]Protocol[/]  [dim]— what to test[/]")
        console.print(f"  [dim]1[/]  HTTP")
        console.print(f"  [dim]2[/]  SOCKS4")
        console.print(f"  [dim]3[/]  SOCKS5")
        console.print(f"  [dim]4[/]  All three\n")
        type_map = {"1":"http","2":"socks4","3":"socks5","4":"all"}
        auto_num = {"http":"1","socks4":"2","socks5":"3"}[auto_type]
        ptype = type_map[Prompt.ask("", choices=["1","2","3","4"], default=auto_num)]

        # ── Step 3: limit + speed (one line each) ─────────────────────────────
        console.print()
        limit = IntPrompt.ask(f"[bold]Check how many?[/]  [dim]0 = all {len(proxies)}[/]", default=0)
        if limit and limit < len(proxies):
            proxies = proxies[:limit]

        timeout     = IntPrompt.ask("[bold]Timeout[/]  [dim]seconds per proxy[/]", default=10)
        concurrency = IntPrompt.ask("[bold]Concurrency[/]  [dim]parallel checks[/]", default=50)
        export_fmt  = Prompt.ask("[bold]Export[/]", choices=["txt","json","both","none"], default="txt")
        show_failed = Confirm.ask("[bold]Show dead proxies?[/]", default=False)
        out_dir     = Path("./results")

    # ── non-interactive path ──────────────────────────────────────────────────
    if args.url or args.file:
        limit       = args.limit
        timeout     = args.timeout
        concurrency = args.concurrency
        export_fmt  = args.export
        show_failed = args.show_failed
        out_dir     = Path(args.out)
        if limit and limit < len(proxies):
            proxies = proxies[:limit]

    # ── Run ───────────────────────────────────────────────────────────────────
    with console.status("[dim]Detecting your IP...[/]", spinner="dots"):
        real_ip = await get_real_ip()
    console.print(f"[dim]Your IP: {real_ip}[/]\n")

    t0      = time.monotonic()
    results = await run_checks(proxies, ptype, timeout, concurrency, real_ip)
    elapsed = time.monotonic() - t0
    console.print(f"\n[dim]Done in {elapsed:.1f}s[/]\n")

    display_results(results, show_failed=show_failed)

    if export_fmt != "none":
        export_results(results, ptype, export_fmt, out_dir)

    # per-type summary for "all"
    if ptype == "all":
        console.print()
        for t in ("http","socks4","socks5"):
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
