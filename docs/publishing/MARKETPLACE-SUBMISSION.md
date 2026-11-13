### Repository URL

https://github.com/ditrigo/desktop-pets

### Category

Desktop

### Tags

quickshell, hyprland, games

### Suggest a missing tag

_No response_

### Maintainer notes

Desktop Pets is a bar widget and own-service desktop companion for Omarchy
Quattro/Hyprland. Version 1.0.0 starts with a duck in classic, pixel and voxel
styles, fitted outfits, window walking, toys, saved looks and live EN/RU
localization. The permanent plugin ID is ditrigo.desktop-pets.

The public repository has one root manifest, README, MIT license, original art
sources and preview.png. The native omarchy plugin commands install and remove
the Git checkout. The running pet uses prebuilt SVG/PNG artwork, has no runtime
network access or telemetry, and uses no elevated privileges. Pet memory stays
under ~/.local/state/desktop-pets/ after normal removal.

The optional install.py/install.sh snapshot installer is an explicit user action;
native Git installation does not execute it. It writes only the plugin directory
and the plugin's own shell.json entries, backs up the previous installation and
configuration, and rolls back failed installation without reverting other
widgets' changes. Its presence is an installer capability for baseline review.

Omarchy, Quickshell and Qt Quick provide the runtime. Optional sound uses pw-play.
The pet-art studio uses uv/Python and Pillow/Shapely; it downloads declared Python
dependencies into the user's cache only when invoked. Node, rsvg-convert and
Blender are development tools. Full validation commands, access boundaries,
asset provenance and the retained third-party test protocol notice are documented.

### Submission checklist

- [ ] The repository is public and contains installation and removal instructions.
- [ ] I have documented the plugin license and any external dependencies.
- [ ] I confirm that I own or have permission to submit this plugin and its preview assets.
- [ ] The plugin does not overwrite user configuration without explicit consent.
- [ ] I understand that approval is for listing and is not a security review.
