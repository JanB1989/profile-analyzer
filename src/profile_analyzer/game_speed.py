"""Wall-clock seconds per game year for one EU5 session.

Two timestamped sources give (wall time, game date) points for the running session:

- ``performance_degradation.log``: elapsed seconds since launch and the game date, one row
  every few minutes. Its file time is the moment of the last row, which fixes the launch time.
- Autosaves: each save header carries ``date=`` and ``playthrough_id=``; the file time is when
  the save finished writing. Only saves written after the launch count, and only those of the
  playthrough the session is playing.

Consecutive points give segments (wall seconds / game years). A paused game keeps the wall clock
running, so pauses show as segments far slower than their neighbours; those are flagged as
outliers and left out of the clean average. Saving time stays in (the player waits for it too).
"""

from __future__ import annotations

import json
import os
import re
import statistics
from datetime import datetime
from pathlib import Path

PERF_LOG = "performance_degradation.log"
HEADER_BYTES = 4096
SAVE_DATE = re.compile(rb"\bdate=(\d+)\.(\d+)\.(\d+)")
SAVE_PLAYTHROUGH = re.compile(rb'\bplaythrough_id="([^"]+)"')
LOG_DATE = re.compile(r"^(\d+)_(\d+)_(\d+)$")
# Days before each month in the game's 365-day calendar.
MONTH_START = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
# A segment is a pause outlier when it is this much slower than the median of its neighbours.
OUTLIER_FACTOR = 1.6
NEIGHBOURS = 3


def game_years(year: int, month: int, day: int) -> float:
    return year + (MONTH_START[month - 1] + day - 1) / 365


def format_date(value: float) -> str:
    year = int(value)
    day = round((value - year) * 365)
    month = max(i for i, start in enumerate(MONTH_START) if start <= day)
    return f"{year}.{month + 1}.{day - MONTH_START[month] + 1}"


def log_points(rows: list[dict], log_mtime: float) -> tuple[float | None, list[dict]]:
    """Performance rows -> (launch time, points). Rows before the game starts carry 1_01_01."""
    if not rows:
        return None, []
    launch = log_mtime - rows[-1]["elapsed_seconds"]
    points = []
    for row in rows:
        match = LOG_DATE.match(str(row.get("date", "")))
        if not match:
            continue
        year, month, day = map(int, match.groups())
        if year <= 1:
            continue
        points.append({"wall": launch + row["elapsed_seconds"], "game": game_years(year, month, day),
                       "source": "log"})
    return launch, points


def read_save_header(path: Path) -> tuple[float, str | None] | None:
    try:
        with path.open("rb") as stream:
            head = stream.read(HEADER_BYTES)
    except OSError:
        return None
    date = SAVE_DATE.search(head)
    if not date:
        return None
    playthrough = SAVE_PLAYTHROUGH.search(head)
    return game_years(*map(int, date.groups())), playthrough.group(1).decode() if playthrough else None


def save_points(saves_dir: Path, since: float | None) -> tuple[str | None, list[dict]]:
    """Autosaves of the session's playthrough written after the launch."""
    found = []
    for path in saves_dir.glob("autosave*.eu5"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if since is not None and mtime < since:
            continue
        header = read_save_header(path)
        if header:
            found.append((mtime, header[0], header[1], path.name))
    if not found:
        return None, []
    # The newest autosave belongs to the game being played now.
    playthrough = max(found)[2]
    points = [{"wall": mtime, "game": game, "source": "autosave", "file": name}
              for mtime, game, pid, name in found if pid == playthrough]
    return playthrough, points


def segments(points: list[dict]) -> list[dict]:
    """Merge points in wall order into segments; a date jump backwards (a loaded save) restarts."""
    ordered = sorted(points, key=lambda p: (p["wall"], p["game"]))
    result = []
    previous = None
    for point in ordered:
        if previous is not None:
            years = point["game"] - previous["game"]
            seconds = point["wall"] - previous["wall"]
            if years < 0:
                previous = point
                continue
            if years > 0 and seconds > 0:
                result.append({"start": previous["game"], "end": point["game"], "years": years,
                               "seconds": seconds, "per_year": seconds / years,
                               "wall_start": previous["wall"], "wall_end": point["wall"],
                               "sources": f"{previous['source']}>{point['source']}"})
        # Same date twice: the game stood still in between, so the next segment starts at the later one.
        previous = point
    flag_outliers(result)
    return result


def flag_outliers(result: list[dict]) -> None:
    for i, segment in enumerate(result):
        window = [s["per_year"] for j, s in enumerate(result)
                  if j != i and abs(j - i) <= NEIGHBOURS]
        reference = statistics.median(window) if window else segment["per_year"]
        segment["reference"] = reference
        segment["outlier"] = bool(window) and segment["per_year"] > OUTLIER_FACTOR * reference


def summary(result: list[dict]) -> dict:
    kept = [s for s in result if not s["outlier"]]
    def rate(items):
        years = sum(s["years"] for s in items)
        return sum(s["seconds"] for s in items) / years if years else None
    first = result[0]["start"] if result else None
    last = result[-1]["end"] if result else None
    return {"segments": len(result), "outliers": len(result) - len(kept),
            "clean_seconds_per_year": rate(kept), "raw_seconds_per_year": rate(result),
            "first_date": format_date(first) if first is not None else None,
            "last_date": format_date(last) if last is not None else None,
            "game_years": (last - first) if result else 0,
            "paused_seconds": sum(s["seconds"] - s["years"] * s["reference"] for s in result if s["outlier"])}


def by_decade(result: list[dict]) -> list[dict]:
    """Clean seconds per game year per decade; a segment's time splits by its years in each decade."""
    buckets: dict[int, list[float]] = {}
    for s in result:
        if s["outlier"]:
            continue
        start = s["start"]
        while start < s["end"]:
            decade = int(start // 10 * 10)
            stop = min(s["end"], decade + 10)
            share = (stop - start) / s["years"]
            bucket = buckets.setdefault(decade, [0.0, 0.0])
            bucket[0] += s["seconds"] * share
            bucket[1] += stop - start
            start = stop
    return [{"decade": d, "years": y, "seconds_per_year": sec / y}
            for d, (sec, y) in sorted(buckets.items()) if y > 0.5]


def read_session(logs_dir: Path, saves_dir: Path | None, performance: dict | None = None) -> dict | None:
    """Speed data for the session whose performance log is in ``logs_dir``."""
    log = logs_dir / PERF_LOG
    if performance is None:
        if not log.is_file():
            return None
        from profile_analyzer.analyzer import read_performance
        performance = read_performance(log)
        performance.pop("_raw_bytes", None)
    log_mtime = log.stat().st_mtime if log.is_file() else None
    launch, points = log_points(performance["rows"], log_mtime) if log_mtime else (None, [])
    playthrough, saves = (save_points(saves_dir, launch) if saves_dir and saves_dir.is_dir() else (None, []))
    points += saves
    result = segments(points)
    return {"launch": datetime.fromtimestamp(launch).isoformat(timespec="seconds") if launch else None,
            "playthrough": playthrough, "points": sorted(points, key=lambda p: p["wall"]),
            "segments": result, "summary": summary(result), "decades": by_decade(result),
            "outlier_factor": OUTLIER_FACTOR, "log": str(log), "saves": str(saves_dir) if saves_dir else None}


def default_saves_dir(logs_dir: Path) -> Path | None:
    candidate = logs_dir.parent / "save games"
    return candidate if candidate.is_dir() else None


def text_report(speed: dict) -> str:
    s = speed["summary"]
    lines = [f"Session launched {speed['launch']}, playthrough {speed['playthrough'] or '-'}",
             f"{s['first_date']} -> {s['last_date']} ({s['game_years']:.1f} game years, {s['segments']} segments, "
             f"{s['outliers']} pause outliers removed, {s['paused_seconds']:.0f} s)"]
    if s["clean_seconds_per_year"] is not None:
        lines.append(f"Clean: {s['clean_seconds_per_year']:.1f} s per game year (raw {s['raw_seconds_per_year']:.1f})")
    for d in speed["decades"]:
        lines.append(f"  {d['decade']}s  {d['seconds_per_year']:6.1f} s/yr  ({d['years']:.1f} yr)")
    return os.linesep.join(lines)


SPEED_CSS = (
    ".speed-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}"
    ".speed-stat{padding:12px 14px;background:#10161d;border-radius:8px}.speed-stat strong{display:block;font-size:22px;font-weight:550}"
    ".speed-stat span{color:var(--muted);font-size:12px}.speed-chart svg{width:100%;display:block}"
    ".speed-chart text{fill:var(--muted);font:11px system-ui,sans-serif}.speed-grid{stroke:var(--line)}"
    ".speed-seg rect{fill:var(--accent);opacity:.85}.speed-seg:hover rect{opacity:1}"
    ".speed-out rect{fill:#5d6b79;opacity:.45}.speed-out text{fill:var(--muted)}"
    ".speed-mean{stroke:var(--warm);stroke-width:1.5;stroke-dasharray:6 4}.speed-chart text.speed-mean-label{fill:var(--warm)}"
    ".speed-note{font-size:12px}.speed-table{border-collapse:collapse;margin-top:10px;font-variant-numeric:tabular-nums}"
    ".speed-table th,.speed-table td{padding:6px 14px;border-bottom:1px solid var(--line);text-align:right}"
    ".speed-table th:first-child,.speed-table td:first-child{text-align:left}"
    "@media(max-width:800px){.speed-stats{grid-template-columns:repeat(2,1fr)}}"
)


def inline_assets(template: str) -> str:
    script = Path(__file__).with_name("speed_chart.js").read_text(encoding="utf-8")
    return template.replace("/*__SPEED_CSS__*/", SPEED_CSS).replace("/*__SPEED_CHART_JS__*/", script)


def write_speed_report(speed: dict, label: str, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    payload = dict(speed, label=label, generated=datetime.now().isoformat(timespec="seconds"))
    serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    (output / "speed.json").write_text(serialized, encoding="utf-8")
    template = inline_assets(Path(__file__).with_name("speed_report.html").read_text(encoding="utf-8"))
    page = output / "index.html"
    page.write_text(template.replace("__SPEED_JSON__", serialized.replace("</", "<\\/")), encoding="utf-8")
    return page
