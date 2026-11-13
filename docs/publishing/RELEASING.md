# Publishing Desktop Pets 1.0.0

The repository is prepared for the [Omarchy publishing guide](https://plugins.omarchy.org/publish.html)
and [shell plugin contract](https://github.com/omacom/omarchy/blob/quattro/docs/omarchy-shell.md).
The installable unit is one public GitHub repository with `manifest.json` at
its root. The permanent ID is `ditrigo.desktop-pets`.

## First release metadata

- Repository: [ditrigo/desktop-pets](https://github.com/ditrigo/desktop-pets).
- Version/tag: `1.0.0` / `v1.0.0`.
- Category: **Desktop**.
- Tags: **Quickshell**, **Hyprland**, **Games**.
- Preview: root `preview.png`, rendered from bundled art without desktop capture.
- License: MIT; original artwork and Blender sources are included.

Work from a clean checkout of the public repository. Keep the version in
`manifest.json`, service diagnostics, release notes and tag consistent.

## Local release gates

```sh
./pet-art build
python integration/verify.py
python tools/release.py
cd dist && sha256sum -c SHA256SUMS
```

The default release builder validates both clean staging trees using the real
`omarchy plugin validate`. It emits:

- `ditrigo.desktop-pets-1.0.0.tar.gz`: runtime, translations and user docs.
- `ditrigo.desktop-pets-1.0.0-source.tar.gz`: complete public source and studio.
- `SHA256SUMS` and `release.json`.

Archives normalize timestamps, ownership and modes. Personal packs, virtual
environments, caches, diagnostics, reviews and Blender backup files are not
release content. Export/remove custom packs before a public build. Portable
CI may use `--skip-host-validation`; its report explicitly records that the
host validation was skipped and does not replace the full release gate.

## Prepare the first release

After pushing the release commit, wait for its Checks workflow to pass.
Review both archives and their checksums, then tag that commit and create a draft:

```sh
git tag v1.0.0
git push origin v1.0.0
gh release create v1.0.0 dist/ditrigo.desktop-pets-1.0.0.tar.gz dist/ditrigo.desktop-pets-1.0.0-source.tar.gz dist/SHA256SUMS dist/release.json --draft --verify-tag --title "Desktop Pets 1.0.0" --notes-file docs/publishing/RELEASE-NOTES.md
```

The release stays a draft until published from GitHub's release editor.
For corrections before publication, update the draft attachments and ensure the
tag points to the reviewed commit. Do not move a tag after a release is public.

## Marketplace submission

Use the official [submission form](https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=submit-plugin.yml)
after the release is ready. The form accepts one category and one to three
tags. [MARKETPLACE-SUBMISSION.md](MARKETPLACE-SUBMISSION.md) contains the prepared
fields and the maintainer confirmations from the official form.

**Maintainer notes:**

> Desktop Pets is a bar widget and own-service desktop companion for Omarchy
> Quattro/Hyprland. It ships prebuilt SVG/PNG art and supports live English and
> Russian localization. No runtime network access, telemetry or elevated
> privileges are used. The optional quack action uses pw-play; Python, uv, Node,
> rsvg-convert and Blender are development/studio tools only. Installation and
> removal are documented; existing settings and local pet memory are preserved.
> Source, preview and original assets are MIT licensed. Full local checks and
> Omarchy package validation have been completed for this version.

The form also asks the submitter to confirm ownership/permission, documented
dependencies and removal, configuration consent, and the listing's review
scope. Those confirmations belong to the submitting maintainer.
