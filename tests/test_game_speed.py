import os
from pathlib import Path

import pytest

from profile_analyzer import cli, game_speed

LOG_HEADER = ('"Total Time",\t\t "Average Delta",\t\t "MinDelta",\t\t "MaxDelta" ,"Audio Events:","Ecs entities",'
              '"Ecs entities capacity","GUI widgets","Game Data","Memory Usage (MB)","Memory Usage (Virtual) (MB)",'
              '"Old Entities:","Print Debug duration (ms)","Total number of Gfx units","Total number of Trade wagons"')
LAUNCH = 1_800_000_000.0


def write_log(logs: Path, rows):
    logs.mkdir(parents=True, exist_ok=True)
    lines = [LOG_HEADER] + [f'"{t}","0.03","0.01","0.2",4,8,48,329,{date},9000,13000,0,0,,0' for t, date in rows]
    path = logs / game_speed.PERF_LOG
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.utime(path, (LAUNCH + rows[-1][0],) * 2)


def write_save(saves: Path, name: str, date: str, wall: float, playthrough="game-a"):
    saves.mkdir(parents=True, exist_ok=True)
    path = saves / name
    path.write_bytes(b"SAV0300\nmetadata={\n\tdate=" + date.encode() +
                     b'\n\tplaythrough_id="' + playthrough.encode() + b'"\n}\n' + b"\0" * 64)
    os.utime(path, (LAUNCH + wall,) * 2)


@pytest.fixture
def session(tmp_path):
    logs, saves = tmp_path / "logs", tmp_path / "save games"
    write_log(logs, [(0.2, "1_01_01"), (20, "1337_04_01"), (270, "1347_04_01"), (520, "1357_04_01")])
    # 25 s per game year from autosaves; a 300 s pause between 1362 and 1367.
    for i, (date, wall) in enumerate([("1342.4.1", 145), ("1352.4.1", 395), ("1362.4.1", 645),
                                      ("1367.4.1", 1070), ("1372.4.1", 1195)]):
        write_save(saves, f"autosave_game-a_{i}.eu5", date, wall)
    write_save(saves, "autosave_old.eu5", "1500.1.1", -50)                      # before the launch
    write_save(saves, "autosave_game-b.eu5", "1400.1.1", 700, "game-b")         # another playthrough, older
    return logs, saves


def test_dates_and_calendar():
    assert game_speed.game_years(1337, 4, 1) == pytest.approx(1337 + 90 / 365)
    assert game_speed.format_date(game_speed.game_years(1392, 12, 31)) == "1392.12.31"


def test_session_merges_log_and_autosaves_and_drops_pause(session):
    logs, saves = session
    speed = game_speed.read_session(logs, saves)
    assert speed["playthrough"] == "game-a"
    assert all(p.get("file", "").startswith("autosave_game-a") for p in speed["points"] if p["source"] == "autosave")
    outliers = [s for s in speed["segments"] if s["outlier"]]
    assert len(outliers) == 1 and outliers[0]["start"] == pytest.approx(game_speed.game_years(1362, 4, 1))
    summary = speed["summary"]
    assert summary["clean_seconds_per_year"] == pytest.approx(25)
    assert summary["raw_seconds_per_year"] > 25
    assert summary["paused_seconds"] == pytest.approx(300)
    assert summary["first_date"] == "1337.4.1" and summary["last_date"] == "1372.4.1"
    assert all(d["seconds_per_year"] == pytest.approx(25) for d in speed["decades"])


def test_loaded_earlier_save_restarts_the_series():
    points = [{"wall": 0, "game": 1337, "source": "log"}, {"wall": 100, "game": 1341, "source": "log"},
              {"wall": 200, "game": 1338, "source": "autosave"}, {"wall": 300, "game": 1342, "source": "log"}]
    result = game_speed.segments(points)
    assert [(s["start"], s["end"]) for s in result] == [(1337, 1341), (1338, 1342)]


def test_same_date_twice_excludes_the_standstill():
    points = [{"wall": 0, "game": 1337, "source": "log"}, {"wall": 500, "game": 1337, "source": "log"},
              {"wall": 600, "game": 1341, "source": "log"}]
    assert [s["seconds"] for s in game_speed.segments(points)] == [100]


def test_speed_command_writes_report(session, tmp_path, capsys):
    logs, _ = session
    assert cli.main(["speed", str(logs), "--output", str(tmp_path / "out"), "--label", "run"]) == 0
    out = capsys.readouterr().out
    assert "Clean: 25.0 s per game year" in out
    page = next((tmp_path / "out").glob("run-*/index.html")).read_text(encoding="utf-8")
    assert "__SPEED" not in page and "renderSpeed" in page and '"playthrough": "game-a"' in page


def test_profiler_report_carries_speed(session, tmp_path):
    logs, _ = session
    (logs / "profiling.csv").write_text("File Location;Bottleneck Time;Call Count;Max Time;Min Time;Self Time;"
                                        "Total Time;Average Time (Inclusive);Average Time (Exclusive)\n"
                                        "trigger @ common/a.txt:1;0;10;0;0;2;5;0;0\n", encoding="utf-8")
    assert cli.main([str(logs), "--output", str(tmp_path / "out"), "--label", "cap"]) == 0
    report = next((tmp_path / "out").glob("cap-*"))
    page = (report / "index.html").read_text(encoding="utf-8")
    assert "__SPEED" not in page and (report / "inputs" / "speed.json").is_file()
    # An earlier report keeps its stored series (the autosaves may be gone by then).
    assert cli.main([str(report), "--output", str(tmp_path / "again"), "--label", "again"]) == 0
    assert (next((tmp_path / "again").glob("again-*")) / "inputs" / "speed.json").is_file()
