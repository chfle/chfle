#!/usr/bin/env python3
"""Daily profile update: today's Daf Yomi, Hebrew date and parasha.

Rewrites the block between the DAILY markers in README.md and appends one
line to DAF_LOG.md, so every run produces a real change to commit.
Prints the commit subject on stdout.
"""
import datetime as dt
import json
import pathlib
import re
import sys
import urllib.request
from zoneinfo import ZoneInfo

TZ = "Europe/Zurich"
README = pathlib.Path("README.md")
LOG = pathlib.Path("DAF_LOG.md")
START, END = "<!-- DAILY:START -->", "<!-- DAILY:END -->"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-daily-daf"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def main():
    today = dt.datetime.now(ZoneInfo(TZ)).date()
    daf = parasha = daf_url = None
    hebrew = None
    try:
        cal = get_json(f"https://www.sefaria.org/api/calendars?timezone={TZ}")
        for item in cal.get("calendar_items", []):
            title = item["title"]["en"]
            if title == "Daf Yomi":
                daf = item["displayValue"]["en"]
                daf_url = "https://www.sefaria.org/" + item["url"]
            elif title == "Parashat Hashavua":
                parasha = item["displayValue"]["en"]
    except Exception as e:  # never fail the streak because an API hiccuped
        print(f"::warning::Sefaria lookup failed: {e}", file=sys.stderr)
    try:
        h = get_json(f"https://www.hebcal.com/converter?cfg=json&g2h=1&date={today}")
        hebrew = f"{h['hd']} {h['hm']} {h['hy']}"
    except Exception as e:
        print(f"::warning::Hebcal lookup failed: {e}", file=sys.stderr)

    # --- log -------------------------------------------------------------
    if not LOG.exists():
        LOG.write_text(
            "# Daf log\n\nOne line per day, written by "
            "[`daily.yml`](.github/workflows/daily.yml).\n\n"
            "| # | Date | Hebrew date | Daf Yomi | Parasha |\n|---|---|---|---|---|\n"
        )
    lines = LOG.read_text().splitlines()
    rows = [l for l in lines if re.match(r"^\| \d+ \|", l)]
    if any(f"| {today} |" in r for r in rows):
        n = len(rows)  # already ran today (manual re-run): don't double-count
    else:
        n = len(rows) + 1
        daf_cell = f"[{daf}]({daf_url})" if daf else "—"
        with LOG.open("a") as f:
            f.write(f"| {n} | {today} | {hebrew or '—'} | {daf_cell} | {parasha or '—'} |\n")

    # --- README block ----------------------------------------------------
    parts = []
    if daf:
        parts.append(f"📖 **[{daf}]({daf_url})**")
    if hebrew:
        parts.append(hebrew)
    if parasha:
        parts.append(f"Parashat {parasha}")
    parts.append(f"day **{n}** of the [log](./DAF_LOG.md)")
    block = (
        f"{START}\n"
        f"<!-- updated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC -->\n"
        f"{' &nbsp;·&nbsp; '.join(parts)}\n"
        f"{END}"
    )
    text = README.read_text()
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), block, text, flags=re.S)
    README.write_text(text)

    print(f"📖 {daf or 'daily'} · {today}")


if __name__ == "__main__":
    main()
