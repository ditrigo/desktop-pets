# Asset provenance and dependencies

The vector and pixel artwork, generated flat parts, Blender duck model and
rendered atlases were authored for Desktop Pets and are covered by the MIT
license at the repository root. The bundled quack WAV is generated locally;
no downloaded asset pack, stock character or proprietary model is required.

| Resource | Editable source | Built output |
| --- | --- | --- |
| Classic duck | `art/flat/classic.py` | `src/assets/duck2d/vector/` |
| Pixel duck | `art/flat/build_skins.py` | `src/assets/duck2d/pixel/` |
| Flat clothes | `art/flat/wardrobe.py` and build helpers | `src/assets/duck2d/` |
| Voxel model | `art/blender/desktop-duck.blend`, `build_duck.py` | `src/assets/duck3d/` |
| Effects and audio | Bundled local SVG/WAV files | `src/assets/duck/`, `src/assets/quack.wav` |
| Metadata | `art/catalog.json`, `src/assets/duck-contract.json` | Generated JS and JSON |

Runtime integrations use Omarchy, Qt and Quickshell APIs; their implementation
and system fonts are not bundled. Python artwork tooling depends on Pillow,
Shapely and its transitive dependencies, installed separately by uv under
their respective licenses. Development tools are not shipped in runtime archives.

New third-party assets require documented provenance and compatible licensing.
Do not add unlicensed reference images or personal custom packs to a public release.

## Bundled third-party test material

`integration/protocols/duck-virtual-pointer.xml` contains the wlr virtual pointer
protocol from [wlr-protocols](https://gitlab.freedesktop.org/wlroots/wlr-protocols).
Its 2019 Josef Gajdusek copyright notice and MIT license text are retained inside
the XML. It is used only by the opt-in compositor input test and is not part of
the runtime archive. Generated pointer test binaries are temporary and are not
bundled.
