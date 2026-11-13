# Desktop Duck art studio

[Русский](docs/ru/ART-TOOL.md)

`duck-art` is one entry point for custom models, hats, clothes and preset looks:
**template → artwork → validation → preview → installation**. Packs are data-only
folders under `art/packs/`; the studio generates the catalogue, settings keys,
interaction contours and compatibility lists without manual QML edits.

The studio is included in the source release. It needs Python 3.11+, uv and
`rsvg-convert`; previews need Quickshell, and Blender import needs Blender.
`./duck-art doctor` checks the tools. Python dependencies live outside the
plugin directory in the user's cache.

## Create clothes

```sh
./duck-art new hat my-cap --label "My cap" --template santa
./duck-art new outfit my-coat --label "My coat" --template raincoat
./duck-art new look my-look --label "My look" --hat my-cap --outfit my-coat
./duck-art preview my-look --guides
```

Edit the SVG/PNG files and the single `pack.json` in each new folder. By default,
clothing templates include classic and pixel variants. Their labels are your
content and are not translated by the plugin.

```sh
./duck-art fit my-cap --model pixel --part hat --rect -30 -64 64 32
./duck-art preview my-look --models vector,pixel --guides
./duck-art watch my-look --guides
./duck-art build --install
```

`fit` sets `X Y width height` in logical units. It applies to every view unless
`--view side`, `--view threeQuarter` or `--view front` is specified. Roles are
`hat`, `neck`, `body` and `sleeve`; sleeves use their side/front source parts.
The image and its input contour use the same placement.

`preview` writes `review/art-tool/<key>.png` using the actual QML renderer:
three views and plumages, idle, walking, sleeping, eating, flying and carrying.
`--guides` overlays interaction contours; `--live` opens a window. `watch`
updates the PNG when pack files change and retains the last working catalogue
while an edit is invalid. Add `--install` to apply each successful edit.

## Create a model

```sh
./duck-art new model my-duck --label "My duck" --base vector
./duck-art new outfit my-vest --label "My vest" --template sailor --models my-duck,pixel
./duck-art preview my-duck
```

The base can be `vector`, `pixel`, `voxel` or an existing custom model. A flat
model template contains 52 parts: standing/resting bodies, covered/uncovered
heads, wings, eyes and feet for the supported plumages and views. It appears
as a separate model card in Appearance after a successful build.

`geometry` overrides base-model anchors and dimensions. `wardrobeBase` chooses
which model's clothes may be inherited; an empty string disables inheritance.
Clothes for a different silhouette need their own variant and artwork.

```json
{
  "schemaVersion": 1,
  "kind": "model",
  "key": "my-duck",
  "label": "My duck",
  "base": "vector",
  "directory": "model",
  "wardrobeBase": "vector",
  "geometry": {"hatOffset": [-30, -66]}
}
```

Models use the existing animation rig: a **120×112** logical canvas, three
views and three plumages. Pixel sources use half-resolution RGBA PNGs with
binary alpha: body 60×56, head 32×29 and hat 32×16. Templates document the
other dimensions. SVG uses a zero-origin viewBox, ordinary shapes/paths and
gradients. External resources, scripts, CSS and runtime `clipPath` are rejected.

## Blender

```sh
./duck-art blender ~/models/my-duck.blend --key my-3d-duck --label "My 3D duck"
./duck-art preview my-3d-duck
./duck-art blender ~/models/my-duck.blend --key my-3d-duck --label "My 3D duck" --update
```

Import requires the compatible seven-bone `DuckRig`, part collections, materials
and Actions described in the [Blender guide](docs/development/blender.md).
The selected master is not overwritten. Additional `hat.<key>` and
`outfit.<key>` collections are registered automatically; a collection's
`duck_label` property supplies its UI label. Only required part frames are
rendered, not demonstration animations.

For an editable atlas accessory template:

```sh
./duck-art new hat my-3d-hat --label "My 3D hat" --template explorer --models voxel
```

Its folder contains a PNG atlas and `manifest.json`. Atlas placement uses
`x`, `y`, `width` and `height` there; `fit` is for flat assets. The studio
rebuilds contours from the image rather than trusting supplied hulls.

## Exchange and removal

```sh
./duck-art export my-cap --output ~/my-cap.zip
./duck-art check ~/my-cap.zip
./duck-art import ~/my-cap.zip
./duck-art remove my-cap
```

Import accepts a directory or ZIP with `pack.json` at its root. It validates
before registering and does not replace an existing key. Required custom base
models and clothes must already exist in the receiving library. Removal backs
up sources under `.cache/duck-art/removed/` and is cancelled if another pack
still depends on the removed resource.

## Build and install

```sh
./duck-art check
./duck-art build
./duck-art build --rebuild-flat
./duck-art install
```

`art/catalog.json` is the built-in source catalogue. Generated runtime files
are under `src/`: `DuckCatalog.js`, `DuckLooks.js`, settings keys in
`DuckModel.js` and `assets/custom/`. Do not hand-edit them.

Unchanged files reuse cached contours. Identical builds do not rewrite generated
files; changed assets receive content-addressed paths. Failed builds preserve
the last working outputs. `--rebuild-flat` rebuilds original vector/pixel
artwork and geometry in a separate staging tree before publishing the result.

Installation backs up the prior plugin and preserves settings and personal
looks. An external studio checkout cannot replace a git-managed install;
run the studio from that installed checkout or keep snapshot-based development
separate. Native git updates may require exporting local packs and restoring
generated files before a clean fast-forward. No Python process, Blender
process or image analysis is used by the running duck.
