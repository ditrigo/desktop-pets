# Architecture

The repository root is the Omarchy installation unit. `manifest.json` points
to `src/BarWidget.qml` and `src/Service.qml`; a git clone works without building
art or running an installation hook. Built assets and generated metadata are committed.

| Area | Responsibility |
| --- | --- |
| `BarWidget.qml`, `DuckWindow.qml`, `DuckSettings.qml` | Bar lifecycle and user interface |
| `Service.qml` | Own-service facade, IPC, settings, memory and scene coordination |
| `DuckModel.js`, `DuckPolicy.js`, `WorldModel.js` | Pure simulation, action policy and compositor data normalization |
| `DuckScene.qml`, `DuckInput.qml` | Scene state, input capture, placement and one motion clock |
| `DuckSprite.qml`, flat/atlas renderers | Model selection and joint-based presentation |
| `DuckHit.js`, `DuckSilhouette.qml` | Shared transformed geometry for reactions and input masks |
| `DuckSettingsStore.qml`, `MemoryStore.qml` | Confirmed settings writes and checkpoint/backup persistence |
| `HyprlandAdapter.qml`, `HyprRequest.qml` | Bounded local IPC and recovery polling |
| `DuckTranslations.qml`, `i18n/` | Plugin-owned live translations |
| `tools/artlib.py`, `art/catalog.json`, `art/packs/` | Pack validation and catalogue compilation |

Rendering consumes cached textures and precomputed contours. It does not start
Blender, read back pixels or create another animation clock. Unsupported clothes
are hidden for the selected model while the saved selection remains available.

The pure model returns stable state and mood identifiers. Translation happens
at the presentation boundary. User names, saved look names and custom asset
labels are never translated or interpreted as markup.

The snapshot installer packages a whitelisted runtime tree under a content hash,
backs up the previous install and retains unrelated shell configuration during
rollback. Git-managed installs use Omarchy's native add/update/remove commands;
an external snapshot install cannot replace their `.git` history.

Release archives are built from explicit file sets. Runtime and source artifacts
both contain a valid root manifest; only the source artifact includes the art
studio, artist sources, tests and development configuration.
