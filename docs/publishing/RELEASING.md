# Publishing Desktop Pets 1.0.0

Repository: https://github.com/ditrigo/desktop-pets  
Permanent plugin ID: `ditrigo.desktop-pets`  
Version/tag: `1.0.0` / `v1.0.0`

Use the marketplace repository's current
[CLI/AI submission guide](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md),
[security baseline policy](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SECURITY.md#automated-security-baseline)
and [verification guide](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/VERIFICATION.md).
The [publishing overview](https://plugins.omarchy.org/publish.html) and
[Quattro plugin contract](https://github.com/omacom/omarchy/blob/quattro/docs/omarchy-shell.md)
describe the repository and runtime structure.

## Required repository layout

- One public GitHub repository with `manifest.json` at its root.
- Root README with installation/removal and a root license file.
- Documented runtime/development dependencies and configuration access.
- Unique namespaced ID outside `omarchy.*`. Keep it unchanged after listing;
  retired IDs cannot be reused.
- Optional root preview. `preview.png` is generated from bundled art; the
  marketplace optimizes it automatically. Its input limits are 50 MB / 40 MP.

The submission category is **Desktop** and the three tags are **quickshell**,
**hyprland**, **games**. The manifest's `barWidget.category` is a separate shell
widget grouping, not the marketplace category.

## Local release gates

```sh
./pet-art build
python integration/verify.py
python tools/release.py
cd dist && sha256sum -c SHA256SUMS
```

The builder validates both clean staging trees using `omarchy plugin validate`:

- `ditrigo.desktop-pets-1.0.0.tar.gz`: runtime and user documentation.
- `ditrigo.desktop-pets-1.0.0-source.tar.gz`: source, studio, original art and tests.
- `SHA256SUMS` and `release.json`: hashes and host-validation status.

Archives exclude personal packs, virtual environments, caches, local diagnostics
and backup files, and normalize timestamps, ownership and modes. Portable CI uses
`--skip-host-validation`; that report does not replace workstation verification.

## Review the release candidate

Wait for the Checks workflow on the final `main` commit. Check the current tag
and draft before editing them:

```sh
git rev-parse HEAD
git rev-parse 'v1.0.0^{}'
gh release view v1.0.0 --repo ditrigo/desktop-pets
```

The tag, draft notes and all uploaded files must describe the reviewed commit.
While the release is a draft, replace attachments after rebuilding corrections.
Do not move a tag after its release is public. Publishing the GitHub release is
a useful distribution step; the marketplace's submission requirements are based
on the public repository and exact commit, not on the presence of a GitHub release.

## Submit to the marketplace

Issue title: **`[Plugin]: Desktop Pets`**.

[MARKETPLACE-SUBMISSION.md](MARKETPLACE-SUBMISSION.md) is a ready-to-review issue
body with the six required headings in the official order. Keep their spelling,
order and all five checklist statements unchanged. The owner must review and
confirm all five statements; the checked state is deliberately not prefilled.
An agent must show the title/body and receive explicit owner approval before
creating the issue, as required by the official CLI/AI guide.

Use the [issue form](https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=submit-plugin.yml)
or copy the prepared body, confirm its checklist, and submit it with GitHub CLI:

```sh
cp docs/publishing/MARKETPLACE-SUBMISSION.md /tmp/desktop-pets-submission.md
${EDITOR:-vi} /tmp/desktop-pets-submission.md
gh issue create --repo omacom/omarchy-plugin-marketplace --title "[Plugin]: Desktop Pets" --body-file /tmp/desktop-pets-submission.md
```

Do not send the unconfirmed template or open a duplicate issue for corrections.

## Validation and approval

The bot validates repository structure and scans the exact validated commit
without executing the plugin. The current baseline identifies `install.py` and
`install.sh` as an `installer` capability, so expect `review-required`. This is
not a finding by itself; its documented scope needs marketplace-maintainer
review. Do not remove or disguise legitimate capabilities to change that result.

An authorized marketplace maintainer reviews the current reports and applies
`approved-and-verified` last. The workflow performs a fresh matching scan before
publication. Our CI and local preflight are not marketplace verification.

Keep the submitted HEAD stable during review. If code changes, update the same
issue and let validation run again; old evidence does not cover a newer commit.
After listing, use the official verification/update form for future releases.
