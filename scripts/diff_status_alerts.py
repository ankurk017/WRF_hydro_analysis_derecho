#!/usr/bin/env python3
"""Diff two status.json files and report start/stop transitions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Entering these = "started"
START_STATUSES = {"running"}
# Leaving running for these = "stopped" (finished, failed short, or left queue-active)
STOP_FROM = {"running"}


def load(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text())
    return {m["member"]: m for m in data.get("members", [])}


def diff(prev: dict[str, dict], curr: dict[str, dict]) -> list[dict]:
    events: list[dict] = []
    for member, cur in sorted(curr.items()):
        old = prev.get(member)
        old_st = (old or {}).get("status")
        new_st = cur.get("status")
        if old_st == new_st:
            continue
        if new_st in START_STATUSES and old_st not in START_STATUSES:
            events.append(
                {
                    "kind": "started",
                    "member": member,
                    "from": old_st or "unknown",
                    "to": new_st,
                    "wrfout": f"{cur.get('wrfout_count', '?')}/{cur.get('expected', '?')}",
                }
            )
        elif old_st in STOP_FROM and new_st not in START_STATUSES:
            events.append(
                {
                    "kind": "stopped",
                    "member": member,
                    "from": old_st,
                    "to": new_st,
                    "wrfout": f"{cur.get('wrfout_count', '?')}/{cur.get('expected', '?')}",
                }
            )
    return events


def to_markdown(events: list[dict], generated: str | None) -> str:
    if not events:
        return ""
    lines = [
        "## Phase-1 WRF run alerts",
        "",
        f"Status snapshot: `{generated or 'unknown'}`",
        "",
    ]
    started = [e for e in events if e["kind"] == "started"]
    stopped = [e for e in events if e["kind"] == "stopped"]
    if started:
        lines.append("### Started")
        for e in started:
            lines.append(
                f"- **{e['member']}** · `{e['from']}` → `{e['to']}` · wrfout {e['wrfout']}"
            )
        lines.append("")
    if stopped:
        lines.append("### Stopped")
        for e in stopped:
            lines.append(
                f"- **{e['member']}** · `{e['from']}` → `{e['to']}` · wrfout {e['wrfout']}"
            )
        lines.append("")
    lines.append(
        "Dashboard: https://ankurk017.github.io/WRF_hydro_analysis_derecho/"
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("previous", type=Path)
    ap.add_argument("current", type=Path)
    ap.add_argument("--markdown-out", type=Path, default=None)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    if not args.previous.exists():
        print("no previous status; skip", file=sys.stderr)
        if args.json_out:
            args.json_out.write_text("[]\n")
        if args.markdown_out:
            args.markdown_out.write_text("")
        return 0

    prev = load(args.previous)
    curr_raw = json.loads(args.current.read_text())
    curr = {m["member"]: m for m in curr_raw.get("members", [])}
    events = diff(prev, curr)
    md = to_markdown(events, curr_raw.get("generated_cst"))

    if args.json_out:
        args.json_out.write_text(json.dumps(events, indent=2) + "\n")
    if args.markdown_out:
        args.markdown_out.write_text(md)

    if events:
        print(md)
        return 0
    print("no start/stop transitions", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
