# Profile Analyzer

Turn Europa Universalis V script-profiler dumps into an interactive, offline HTML
report. Inspect hotspots, search source locations, follow inferred script
relationships, and compare captures. Python 3.11+; **no third-party runtime
dependencies**. [uv](https://docs.astral.sh/uv/getting-started/installation/) handles
the environment and command installation.

## Quick start

```sh
git clone https://github.com/JanB1989/profile-analyzer.git
cd profile-analyzer
uv run profile-analyzer /path/to/logs --output /path/to/reports
```

On Windows (PowerShell):

```powershell
uv run profile-analyzer "C:\path\to\logs" --output "C:\path\to\reports"
```

Open the `index.html` path printed by the command in a recent Chrome, Edge or
Firefox browser. The report embeds its data and works offline, including directly
from disk. No Node.js, web server, database, game installation, or Constructor
checkout is required for hotspot analysis.

Try the included **synthetic** example:

```sh
uv run profile-analyzer examples/sample --output reports --source example=examples/scripts
```

Optionally install the command once, then run it from any directory:

```sh
uv tool install git+https://github.com/JanB1989/profile-analyzer.git
profile-analyzer /path/to/logs --output /path/to/reports
```

## Inputs and outputs

Point the command at a folder containing either or both of:

- `profiling.csv`: summary locations.
- `profiling_roots.csv`: detailed locations.
- `performance_degradation.log`: optional frame-time/memory samples.

A single profiler CSV or a previous report directory also works. The command
reads only these known files, not every log in the directory. Input files are never
modified. Quoted Windows drive paths also work when running under WSL.

Every run creates a new folder, for example:

```text
reports/vanilla-20260916T123000.000000Z/
  index.html
  profile.json
  hotspots_summary.csv
  hotspots_detail.csv
  inputs/
```

`--output` selects the parent folder, and `--label vanilla` sets the capture name.
UTC timestamps with microseconds and collision suffixes prevent overwrites.
`inputs/` preserves the exact bytes used for analysis; file hashes are recorded in
the report. Only available measurement views have a hotspot CSV. When comparing,
the baseline inputs are also copied into `baseline_inputs/`.

Reports contain your input data, local paths, and supplied script excerpts. Keep
them local unless you intend to share that information. Generated reports, real
captures, and machine-specific paths are not part of this repository.

## Optional source graph

Profiler CSVs do **not** contain caller/callee IDs or recorded stacks. Hotspots
work with just the logs. To add source context and an **inferred** graph, point at
the exact game/mod scripts used to produce the capture:

```sh
uv run profile-analyzer /path/to/logs --output reports \
  --game-root /path/to/EuropaUniversalisV \
  --mod-root /path/to/a/mod
```

`--game-root` accepts an install directory, `game/`, or a script root.
Repeat `--mod-root` in load order. For custom layer labels, use
`--source 'my-mod=/path/to/mod'`; repeated named sources follow the game/mod roots,
and later roots override identical file paths. No mod naming convention is assumed.

The bundled structural indexer respects braces, comments, quoted text, operators,
typed blocks and local scripted declarations. Solid edges show enclosing script
blocks; dashed edges show literal scripted references; dotted edges associate
multiple measurements with one source entry. Graph nodes are interactive and
include nearby script lines. Unmeasured source nodes bridge structural gaps.

This is not a game interpreter: dynamic dispatch, event scheduling, and database
`REPLACE`/`INJECT` semantics are not reconstructed. References are limited to
unambiguous definitions in files represented in the capture. Unresolved files,
ambiguous same-line entries, and parse failures retain their timing measurements.
The report lists parse warnings instead of inventing edges.

## Compare a mod run against vanilla

```sh
uv run profile-analyzer /path/to/vanilla/logs --label vanilla --output reports
uv run profile-analyzer /path/to/modded/logs --label modded --output reports \
  --baseline /path/to/the/saved/vanilla-report
```

Use the actual report path printed by the first command. Baselines can also be
raw log folders or individual CSVs. Select **Self-share change vs baseline** in
the report. Matching uses exact profiler type + file + line in the same view;
line edits can invalidate matches. Compare equivalent scenarios: normalized
shares do not correct for different workloads, savegame dates, or run durations.

## Reading the numbers

- Summary and detail are separate views and are never added together.
- Inclusive times overlap; they cannot be summed into wall-clock time.
- Self-time shares use the selected view's self-time sum, not total game runtime.
- Duplicate locations aggregate within a view; their original caller contexts
  cannot be recovered. Max/min columns use maximum/minimum, not sums.
- Per-call costs are recomputed from totals and counts because exported averages
  are rounded. The engine's bottleneck column is preserved without assigning it
  an undocumented interpretation.
- The profiler CSV headers do not identify timing units. Values default to raw
  dump units. Use `--time-unit seconds`, `milliseconds` or `microseconds` only when
  independently known; this labels values without converting them.
- Performance-log frame times are shown in milliseconds and memory in MB. These
  session samples are not synchronized to script-profiler intervals. Empty or
  malformed samples are reported explicitly.

## Development and tests

```sh
uv sync --locked
uv run pytest
uv build
```

The test suite uses synthetic data. CI tests Python 3.11 and 3.14 on Linux and
Windows and checks the built wheel. The lockfile includes development
tooling; the installed application itself requires only Python's standard library.

The tool originated in the Prosper or Perish Constructor workspace. This repository
is standalone and does not import or depend on that workspace or its parser packages.

## License

MIT. See [LICENSE](LICENSE). Game and mod scripts are not distributed with this tool.
