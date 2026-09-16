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
