# Contributing

Use a separate source checkout for development. Do not edit packaged Omarchy
files under `/usr/share/omarchy/`. Preserve `ditrigo.desktop-duck` and existing
settings keys so upgrades retain pet state and personal looks.

## Layout and tools

[Architecture](docs/development/architecture.md) explains component boundaries.
Runtime code belongs in `src/`; original art in `art/`; build utilities in
`tools/`; fixtures and checks in `tests/` and `integration/`.

- Python 3.11+, uv and Node are needed for development checks.
- `rsvg-convert` validates SVG and builds alpha contours.
- Quickshell and Qt Test run renderer checks.
- The full suite also needs Omarchy's QML modules and Blender.

`duck-art` installs its Python environment in the user's cache. If invoking
uv directly, set `UV_PROJECT_ENVIRONMENT` outside the checkout: Omarchy rejects
symlinks anywhere in a plugin directory, including a virtual environment.

## Checks

```sh
node --test tests/model.test.cjs
uv run --frozen --group dev ruff check tools install.py tests integration art/flat
uv run --frozen --group dev ruff format --check tools install.py tests integration art/flat
uv run --frozen python -m unittest discover -s tests -p 'test_*.py'
```

Set an external `UV_PROJECT_ENVIRONMENT` before these commands. CI does this
automatically. Renderer-specific unit cases skip when Qt Test is unavailable;
the full Omarchy verification suite requires and runs them:

```sh
python integration/verify.py
```

Run `python integration/check_lint.py` for QML lint alone. It checks each file
in a fresh process with `--max-warnings 0`, ignores user lint settings and reads
JSON diagnostics so warnings cannot disappear behind shared import analysis.
Only the two `PanelWindow` roots have a line-specific `uncreatable-type`
exception: Quickshell's metadata describes an abstract interface while its
platform factory creates the actual windows. The runtime checks exercise them.

The full suite checks a clean first launch, actual settings and service behavior, delayed persistence,
input contours, three renderers, English/Russian switching, asset validation,
Blender source preservation and QML lint. Live compositor input probes are
opt-in with `--live`.

## Making changes

- Keep simulation and policy logic independent of QML and translated text.
- Use stable identifiers in saved state and IPC, and translate at the UI boundary.
- Keep user-visible strings in `src/i18n/en.json` and `ru.json` with matching keys.
- Use `Text.PlainText` for plugin-owned text. Escape markup before host-owned
  tooltip sinks; add regression coverage for untrusted text.
- Do not hand-edit generated catalogue or geometry files. Run `./duck-art build`
  or `./duck-art build --rebuild-flat` after changing source metadata/artwork.
- Keep subprocess arguments as arrays and asset packs data-only.
- Add targeted tests for behavior changes and review screenshots for visual changes.

Python is formatted with Ruff. Existing QML components are grouped by role and
use explicit IDs, properties and small helpers; avoid introducing a second
animation timer or a runtime image-analysis process.

## Pull requests and releases

Describe the concrete trigger and resulting behavior, list relevant validation,
and include before/after captures for visual changes. Do not include private
state, diagnostic logs, local paths, virtual environments or review directories.

Build releases with `python tools/release.py`. The builder validates clean
staging trees, excludes development state and normalizes archive metadata.
See [RELEASING.md](docs/publishing/RELEASING.md).
