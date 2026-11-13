# Desktop Pets 1.0.0

The first public release of desktop companions for Omarchy Quattro and
Hyprland. Version 1.0.0 starts with a duck and the shared `pet-art` studio for
compatible custom models and clothes.

- Three duck models: classic, pixel and Blender-rendered voxel.
- Window walking, petting, food placement and ball games.
- Twelve hats, ten garments, fourteen preset looks and personal saved looks.
- Live English and Russian localization following the Omarchy language setting.
- Quiet hours, work mode, reduced motion and power profiles.
- The `pet-art` studio for creating, fitting, previewing and exchanging custom
  models and clothes.

## Install

```sh
omarchy plugin add https://github.com/ditrigo/desktop-pets.git --enable
```

The plugin ID is `ditrigo.desktop-pets`. On first launch, a yellow classic duck
appears and its button is placed on the right side of the bar. Sound starts off.

Requires Omarchy Quattro with the shell plugin API and
`qs.Commons.Translations`. Tested on Omarchy 4.5 / Qt 6.12. Optional quacking
uses `pw-play` from `pipewire-audio`. Python, uv, Node and Blender are authoring
and development tools; the running pet uses bundled prebuilt artwork.

## Downloads

- `ditrigo.desktop-pets-1.0.0.tar.gz`: runtime plugin and documentation.
- `ditrigo.desktop-pets-1.0.0-source.tar.gz`: source, art studio, original artwork
  and tests.
- `SHA256SUMS`: checksums for both archives.
- `release.json`: artifact sizes, checksums and Omarchy validation status.

GitHub's automatically generated source downloads also contain the repository
files. Extract a prepared archive into its own directory; `./install.sh`
installs a snapshot with configuration preservation and rollback on failure.

The pet stores its memory locally and makes no runtime network requests.
Code and original assets are MIT licensed. See the
[README](https://github.com/ditrigo/desktop-pets#readme) for controls,
removal, privacy and custom artwork instructions.
