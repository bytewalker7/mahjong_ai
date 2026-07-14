import QtQuick

Rectangle {
    id: root

    property string label: ""
    property color actionColor: "#247e9b"
    signal triggered()

    width: 76
    height: 76
    radius: 38
    color: actionColor
    border.color: "#ffe4a0"
    border.width: 4
    scale: mouse.pressed ? 0.92 : 1.0
    opacity: 0.96

    Behavior on scale { NumberAnimation { duration: 90 } }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 7
        radius: width / 2
        color: "transparent"
        border.color: "#66ffffff"
        border.width: 2
    }

    Text {
        anchors.centerIn: parent
        width: parent.width - 12
        text: root.label
        color: "white"
        font.family: "Microsoft YaHei"
        font.pixelSize: root.label.length > 2 ? 18 : 30
        font.bold: true
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.triggered()
    }
}
