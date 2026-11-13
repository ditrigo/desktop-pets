# Architecture

Desktop Pets separates shared runtime components (`Pet*`) from the first
character's artwork (`src/assets/duck*`, `art/flat/`, `art/blender/`). Version
1.0.0 ships one character, the duck, in three visual styles. The catalogue and
`pet-art` packs select model geometry, rendering and compatible clothing.
The current templates use the duck's joint and animation contract; additional
characters can supply compatible artwork, while different rigs or behaviors
require extending that contract. Multiple simultaneous pets are outside 1.0.0.

The repository root is the Omarchy installation unit. `manifest.json` points
to `src/BarWidget.qml` and `src/Service.qml`; a git clone works without building
art or running an installation hook. Built assets and generated metadata are committed.

| Area | Responsibility |
| --- | --- |
| `BarWidget.qml`, `PetWindow.qml`, `PetSettings.qml` | Bar lifecycle and user interface |
| `Service.qml` | Own-service facade, IPC, settings, memory and scene coordination |
| `PetModel.js`, `PetPolicy.js`, `WorldModel.js` | Pure simulation, action policy and compositor data normalization |
| `PetScene.qml`, `PetInput.qml` | Scene state, input capture, placement and one motion clock |
| `PetSprite.qml`, flat/atlas renderers | Model selection and joint-based presentation |
| `PetHit.js`, `PetSilhouette.qml` | Shared transformed geometry for reactions and input masks |
| `PetSettingsStore.qml`, `MemoryStore.qml` | Confirmed settings writes and checkpoint/backup persistence |
| `HyprlandAdapter.qml`, `HyprRequest.qml` | Bounded local IPC and recovery polling |
| `PetTranslations.qml`, `i18n/` | Plugin-owned live translations |
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
