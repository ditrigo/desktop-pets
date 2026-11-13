# Translations

English is the fallback language. Russian is also shipped. Both catalogs live
under `src/i18n/` and use identical stable keys. Omarchy's
`qs.Commons.Translations` reads the system language and updates bindings live.
There is no independent plugin language setting.

Use `PetTranslations { id: strings }` and call `strings.t("key")` directly
from a binding. Use complete sentences with `%1` placeholders, not fragments.
Counts use `strings.tn("key", count)` and `Commons.I18n.formatNumber(count)`.
Russian plural entries include `one`, `few`, `many` and `other`.

Built-in catalogue entries carry English metadata and `labelKey`; the UI calls
`strings.item(entry)`. Custom entries do not inherit a built-in translation key
and retain their author-supplied label. Saved pet names and personal looks are data.

Errors and speech retain a key rather than a rendered sentence, so a current
error or bubble can change language without restarting its operation. Stable
IPC codes and pure-model state identifiers remain language-neutral.

```sh
python integration/check_i18n.py
```

This checks key/placeholder parity and switches a private fixture from English
to Russian and then to an unsupported locale. It verifies live UI, wardrobe
labels, plural forms, existing errors, English fallback and unchanged settings.
The test never edits the user's language file.
