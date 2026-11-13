pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons as Commons

Column {
    id: picker
    PetTranslations {
        id: strings
    }
    required property var controller
    required property string settingKey
    required property string heading
    required property var options
    property int columns: 3
    property string previewView: "threeQuarter"
    readonly property var cfg: controller.config
    spacing: 8
    PetLabel {
        text: picker.heading
        font.bold: true
    }
    Flow {
        width: parent.width
        spacing: 6
        Repeater {
            model: picker.options
            delegate: FocusScope {
                id: card
                required property var modelData
                width: (picker.width - (picker.columns - 1) * 6) / picker.columns
                height: 110
                activeFocusOnTab: true
                readonly property bool selected: picker.cfg[picker.settingKey] === modelData.key
                function choose() {
                    picker.controller.setSetting(picker.settingKey, modelData.key);
                }
                Keys.onReturnPressed: choose()
                Keys.onSpacePressed: choose()
                Rectangle {
                    anchors.fill: parent
                    radius: 10
                    color: card.selected ? Qt.rgba(1, .8, .35, .13) : Qt.rgba(.5, .5, .5, .06)
                    border.width: card.selected || card.activeFocus ? 2 : 1
                    border.color: card.selected || card.activeFocus ? Commons.Color.accent : Qt.rgba(.5, .5, .5, .25)
                }
                PetSprite {
                    width: 78
                    height: 73
                    x: (parent.width - width) / 2
                    y: 5
                    mode: "idle"
                    view: picker.previewView
                    animate: false
                    plumage: picker.cfg.palette
                    artStyle: picker.settingKey === "artStyle" ? card.modelData.key : picker.cfg.artStyle
                    hat: picker.settingKey === "hat" ? card.modelData.key : picker.cfg.hat
                    outfit: picker.settingKey === "outfit" ? card.modelData.key : picker.cfg.outfit
                }
                PetLabel {
                    anchors {
                        left: parent.left
                        right: parent.right
                        bottom: parent.bottom
                        margins: 5
                    }
                    text: strings.item(card.modelData)
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        card.forceActiveFocus();
                        card.choose();
                    }
                }
                Accessible.role: Accessible.RadioButton
                Accessible.name: strings.item(modelData)
                Accessible.checked: selected
                Accessible.onPressAction: choose()
            }
        }
    }
}
