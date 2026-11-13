import QtQuick
import QtQuick.Controls as QQC
import Quickshell
import Quickshell.Wayland
import qs.Commons as Commons
import qs.Ui

// Quickshell creates this through its platform factory; qmltypes lists only the abstract interface.
PanelWindow { // qmllint disable uncreatable-type
    id: window
    DuckTranslations {
        id: strings
    }
    property var controller: null
    visible: !!controller && controller.opened
    screen: {
        let screens = Quickshell.screens;
        for (let i = 0; i < screens.length; i++)
            if (controller && screens[i].name === controller.monitorName)
                return screens[i];
        return screens.length ? screens[0] : null;
    }
    implicitWidth: Math.min(540, screen ? screen.width - 40 : 540)
    implicitHeight: Math.min(settings.tab === 2 ? 760 : settings.tab === 1 ? 610 : 620, screen ? screen.height - 80 : 760)
    color: "transparent"
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "ditrigo-duck-settings"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
    Rectangle {
        id: surface
        anchors.fill: parent
        color: Commons.Color.background
        border.color: Commons.Color.accent
        border.width: 1
        radius: 16
        FocusScope {
            anchors.fill: parent
            focus: true
            Keys.onEscapePressed: if (window.controller)
                window.controller.hide()
            Keys.onPressed: function (event) {
                if ((event.modifiers & Qt.ControlModifier) && event.key >= Qt.Key_1 && event.key <= Qt.Key_3) {
                    settings.switchTab(event.key - Qt.Key_1);
                    event.accepted = true;
                }
            }
            Item {
                id: header
                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top
                    margins: 20
                }
                height: 36
                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: strings.t("window.title")
                    textFormat: Text.PlainText
                    color: Commons.Color.foreground
                    font.pixelSize: 19
                    font.bold: true
                }
                Button {
                    anchors.right: parent.right
                    text: "✕"
                    focusable: true
                    tooltipText: strings.t("window.close")
                    onClicked: window.controller.hide()
                }
            }
            Rectangle {
                id: errorFooter
                anchors {
                    left: parent.left
                    right: parent.right
                    bottom: parent.bottom
                    margins: 20
                }
                height: errorText.implicitHeight + 16 + (retryButton.visible ? 36 : 0)
                visible: !!window.controller && (window.controller.lastError !== "" || window.controller.settingsState === "applying")
                color: Qt.rgba(.88, .60, .28, .10)
                radius: 8
                DuckLabel {
                    id: errorText
                    x: 8
                    y: 8
                    width: parent.width - 16
                    text: window.controller ? (window.controller.lastError || strings.t("settings.applying")) : ""
                    color: "#e2a567"
                    font.pixelSize: 12
                }
            }
            Button {
                id: retryButton
                parent: errorFooter
                x: 8
                y: errorText.y + errorText.height + 4
                text: strings.t("settings.retry")
                visible: !!window.controller && window.controller.settingsState === "failed"
                onClicked: window.controller.retrySettings()
            }
            Flickable {
                id: flick
                anchors {
                    top: header.bottom
                    left: parent.left
                    right: parent.right
                    bottom: errorFooter.visible ? errorFooter.top : parent.bottom
                    margins: 20
                }
                clip: true
                contentWidth: width
                contentHeight: settings.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                QQC.ScrollBar.vertical: QQC.ScrollBar {}
                DuckSettings {
                    id: settings
                    width: flick.width - 14
                    controller: window.controller
                    onTabChanged: flick.contentY = 0
                }
            }
        }
    }
}
