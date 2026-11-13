import QtQml
import qs.Commons as Commons

// Plugin-owned catalogs follow Omarchy's language and update live.
Commons.Translations {
    directory: Qt.resolvedUrl("i18n")

    function item(entry) {
        return entry.labelKey ? t(entry.labelKey, entry.label) : entry.label;
    }

    function format(key, values) {
        let message = t(key);
        for (let value of values || [])
            message = message.arg(value);
        return message;
    }
}
