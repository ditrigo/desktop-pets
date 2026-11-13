import QtQuick

Item {
    id: row
    property string label: ""
    property string detail: ""
    default property alias controls: control.data
    implicitHeight: Math.max(labels.implicitHeight, control.implicitHeight) + 8
    width: parent.width
    Column {
        id: labels
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: Math.max(80, parent.width - control.width - 20)
        spacing: 4
        DuckLabel {
            width: parent.width
            text: row.label
        }
        DuckLabel {
            width: parent.width
            text: row.detail
            visible: text !== ""
            opacity: 0.55
            font.pixelSize: 11
        }
    }
    Row {
        id: control
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6
    }
}
