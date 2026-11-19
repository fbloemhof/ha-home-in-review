"""Generate report documents from a live Home Assistant (development only).

    python dev/run.py 2026-10 [2026-09 ...]   -> dev/out/2026-10.json and dev/out/2026-10.html
"""
from __future__ import annotations

import asyncio
import importlib
import json
import sys
import types
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "custom_components" / "home_in_review"
OUT = Path(__file__).resolve().parent / "out"

# Load the integration's pure modules without importing Home Assistant (package __init__ is skipped).
pkg = types.ModuleType("hir")
pkg.__path__ = [str(PKG)]
sys.modules["hir"] = pkg
sys.path.insert(0, str(Path(__file__).resolve().parent))
collector = importlib.import_module("hir.collector")
render = importlib.import_module("hir.render")
# Outside Home Assistant the fonts come straight from the integration folder.
render.FONT_BASE = (ROOT / "custom_components" / "home_in_review" / "frontend" / "fonts").as_uri()
from ws_source import WsSource  # noqa: E402


async def main(months: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    cache_file = OUT / "cache.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    opts_file = OUT / "options.json"
    options = json.loads(opts_file.read_text()) if opts_file.exists() else {}
    async with aiohttp.ClientSession() as s, WsSource(s) as src:
        c = collector.Collector(src, options, cache)
        for ym in months:
            y, m = map(int, ym.split("-"))
            doc = await c.collect(y, m)
            if options.get("ai_task_entity") and "--ai" in sys.argv:
                story = importlib.import_module("hir.story")
                prompt = story.instructions(ym, {**{p.stem: json.loads(p.read_text()) for p in OUT.glob("????-??.json")}, ym: doc},
                                            "nl" if "--lang" not in sys.argv else sys.argv[sys.argv.index("--lang") + 1],
                                            options.get("ai_instructions"))
                text = await src.ai_generate(options["ai_task_entity"], prompt)
                if text:
                    doc["story"] = {"text": text.strip(), "entity": options["ai_task_entity"]}
            (OUT / f"{ym}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
            print("written", OUT / f"{ym}.json")
        cfg = await src.config()
    cache_file.write_text(json.dumps(cache))
    docs = {p.stem: json.loads(p.read_text()) for p in OUT.glob("????-??.json")}
    for ym in months:
        lang = sys.argv[sys.argv.index("--lang") + 1] if "--lang" in sys.argv else cfg["language"]
        html = render.render_month(ym, docs, lang=lang, home_name=cfg.get("location_name"),
                                   start_month=int(options.get("year_start_month", 1)), theme=options.get("default_theme", "auto"))
        (OUT / f"{ym}.html").write_text(html)
        print("written", OUT / f"{ym}.html")
    start = int(options.get("year_start_month", 1))
    for key in render.year_keys(docs, start):
        (OUT / f"year-{key}.html").write_text(render.render_year(key, docs, lang, cfg.get("location_name"), start))
    (OUT / "index.html").write_text(render.render_index(docs, lang, cfg.get("location_name"), cfg["currency"], start))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a[:2].isdigit()]
    asyncio.run(main(args))
