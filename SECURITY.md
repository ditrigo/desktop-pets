# Security and privacy

Omarchy plugins execute with the user's privileges inside the shared shell
process. Desktop Duck does not use sudo, privileged helpers, network requests,
remote images, telemetry or automatic downloads at runtime.

The runtime reads local Hyprland window/display/cursor state, local Omarchy
settings, battery status and local pet memory. Window titles and contents are
not transmitted anywhere. Memory and saved looks remain under
`~/.local/state/omarchy-desktop-duck/`; normal plugin removal retains them.

The optional sound action starts `pw-play` with a bundled local audio file.
The art studio may download declared Python development dependencies through
uv and may run Blender or Quickshell when explicitly requested. Those tools
are separate from the running pet.

Custom packs contain metadata and local SVG/PNG/atlas files. The studio rejects
path traversal, symlinks, oversized inputs, external SVG resources and scripts,
invalid pixel alpha and incompatible rigs. Import validation is not a sandbox:
review source repositories and Blender masters before using them.

Use English or Russian catalogs only for plugin-owned text; custom names and
labels remain data. Text is plain in plugin-owned UI, and markup is escaped
before passing user-controlled values to shell-owned tooltips.

For a vulnerability, use
[private vulnerability reporting](https://github.com/ditrigo/omarchy-desktop-duck/security/advisories/new).
Do not include credentials, personal shell configuration or private logs in
public reports. Feature requests and ordinary visual bugs can use normal issues.
