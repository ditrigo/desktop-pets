import QtQuick
import Quickshell
import qs.Ui as Ui
import qs.Commons as Commons
import "PetStatus.js" as Status
import "PetText.js" as SafeText

Ui.BarWidget {
    id: root
    PetTranslations {
        id: strings
    }
    moduleName: "ditrigo.desktop-pets"
    // Ui.BarWidget exposes only QtObject. The host injects its bar API at runtime,
    // matching the dynamic bar interface used by Ui.WidgetButton.
    readonly property var hostBar: bar
    readonly property var service: hostBar && hostBar.shell ? hostBar.shell.serviceFor(moduleName) : null
    readonly property color foreground: hostBar ? hostBar.barForeground : Commons.Color.foreground
    readonly property bool opened: service ? service.opened : false
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    function invoke(method, arg) {
        if (service) {
            if (arg === undefined)
                service[method]();
            else
                service[method](arg);
        } else {
            const cmd = ["omarchy-shell", "desktop-pets", method];
            if (arg !== undefined)
                cmd.push(arg);
            Quickshell.execDetached(cmd);
        }
    }
    function open() {
        invoke("show");
    }
    function close() {
        invoke("hide");
    }
    Ui.BarIconButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "󰇥"
        active: root.opened
        foreground: root.service && root.service.lastError ? Commons.Color.urgent : root.service && root.service.runState !== "active" ? Qt.darker(root.foreground, 1.5) : root.foreground
        tooltipText: {
            var pet = root.service;
            var state = pet ? Status.label(pet.runState, strings) || (pet.resting ? strings.tn("rest.remaining", pet.restMinutes).arg(Commons.I18n.formatNumber(pet.restMinutes)) : strings.t(pet.config.workMode ? "bar.quiet" : "bar.ready")) : strings.t("bar.loading");
            return SafeText.escapeMarkup(strings.t("bar.tooltip").arg(pet ? pet.config.name : strings.t("bar.name")).arg(state).arg(strings.t(pet && pet.paused ? "action.resume" : "action.pause")));
        }
        onPressed: function (code) {
            if (code === Qt.MiddleButton)
                root.invoke("action", "treat");
            else if (code === Qt.RightButton)
                root.invoke("action", "pause");
            else if (code === Qt.LeftButton)
                root.invoke("toggle");
        }
    }
}
