# Classic and pixel duck skins

Build from the repository root:

```sh
uv run --with pillow --with shapely --no-project python art/flat/build_skins.py
uv run --with pillow --no-project python integration/check_assets.py --generate
python integration/preview_flat.py
python integration/preview_flat.py --new-outfits
```

`build_skins.py` builds both styles. `classic.py` defines the rounded duckling;
`wardrobe.py` defines fitted clothing.
Classic artwork uses SVG curves, colored contours and restrained gradients. Pixel artwork is drawn
independently with integer polygons and a limited palette; it is not a filtered
or resized version of the vector art. Pixel PNG alpha is binary, with no soft
edges. Body canvas: 120×112 logical units / 60×56 source pixels.

Parts are in `src/assets/duck2d/vector/` and `src/assets/duck2d/pixel/` with matching
names. Each palette has side, quarter and front heads/bodies. Covered heads
omit the crest so feathers do not poke through hats. Resting bodies use their
own silhouettes. Face expressions are separate layers.

`DuckFlatSprite.qml` owns the joints and render order:

1. Cape behind body; far wing and feet.
2. Body and fitted uniform, with decorative details clipped to the torso.
3. Near wing and fitted sleeve, clipped to the feather silhouette.
4. Head, neckwear, eyes and headwear, all attached to the neck/head joint.

Head joint anchors are (78,64), (72,64), (60,64); sleeping lowers the joint to
74. Hats use offset (-30,-66) for the rounded classic head and (-30,-64)
for the pixel head, where the brim overlaps the upper steps of the crown.
Rendering and input contours share the same offset from the graphics contract.
Each style has its own generated alpha hulls, including all accessories.
Neckwear uses (-30,-48). Pixel uniforms use the torso's stepped outline in
both standing and sleeping poses. Uniforms move with the body, sleeves with wings,
scarves/collars with the head joint. Large hats limit the head's maximum nod
to keep the cap within the pet's normal display area.

Art and source are original for this MIT-licensed plugin. No additional
runtime renderer, editor or background process is needed.

The flat wardrobe has 12 hats and 10 garments, including
raincoat, detective, artist, gardener, tuxedo and pajamas. Every uniform has
its own torso, neck and sleeve parts; standing and resting silhouettes share
their outline with the corresponding duck body. Decorative details and
sleeves are clipped during the build. `vector_clip.py` uses Shapely to bake
intersections into plain SVG paths because Qt's SVG renderer does not apply
`clipPath`; the plugin has no Shapely dependency. Regenerating vector hulls
uses `rsvg-convert` at build time. Pixel masks stay binary.
