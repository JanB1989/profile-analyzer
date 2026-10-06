# Profile Analyzer

Turn Europa Universalis V profiler logs into an HTML report.

## Install

[Install uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```sh
uv tool install https://github.com/JanB1989/profile-analyzer/archive/refs/heads/main.zip
```

## Run

```sh
profile-analyzer "path/to/logs" --output "path/to/reports"
```

Open the generated `index.html` in your browser. Each run saves a new timestamped report.

The report opens with a **seconds per game year** chart for the session: wall-clock time between the game dates
in `performance_degradation.log` and the session's autosaves (the `save games` folder next to `logs`, or
`--saves`). Stretches far slower than their neighbours (pauses, menus) stay out of the average.

For the running game alone:

```sh
profile-analyzer speed "path/to/logs" --output "path/to/reports"
```
