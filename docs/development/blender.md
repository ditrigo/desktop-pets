# Blender model sources

`art/blender/desktop-duck.blend` is the editable master for the voxel model.
Its original geometry and materials are MIT licensed.

- Coordinates: +X is the beak, -Y is the near wing, +Z is up.
- `DuckRig` has seven rigid bones. Hats and garments use armature modifiers.
- Enable one `hat.*` and one `outfit.*` collection at a time.
- The rig's `eyeState` selects open, closed or surprised eyes.
- Actions include Idle, Walk, Fly, Wave, Dance, Sleep, Eat, Drag, Love, Shake,
  Stretch and Land, with 24-frame cycles at 24 fps.

The runtime uses prebuilt PNG atlases and anchor metadata. Blender is only
needed when authoring or rebuilding the voxel artwork.

## Import an edited master

Use the studio from a source checkout:

```sh
./duck-art blender /path/to/my-duck.blend --key my-duck --label "My duck"
./duck-art preview my-duck
./duck-art build --install
```

The importer validates the rig, exports a separate custom pack and preserves
the input `.blend` file. See [ART-TOOL.md](../../ART-TOOL.md) for pack options.

## Rebuild the bundled model

For reproducible changes to the bundled geometry, edit
`art/blender/build_duck.py`, then run:

```sh
uv run --frozen python integration/build_blender_assets.py
./duck-art build
```

This regenerates the bundled master from the script. To render a manually
edited master without regenerating or saving it, pass `--blend /path/to/file.blend`.
`--pack-only` reuses existing raw renders. Raw frames go to
`art/blender/renders/`; `--raw /path/to/folder` selects a different location.
Generated animation previews go to `review/<manifest-version>/` and are excluded
from releases. Keep the Python environment outside the checkout as described in
[CONTRIBUTING.md](../../CONTRIBUTING.md).
