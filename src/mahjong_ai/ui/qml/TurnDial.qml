import QtQuick

Item {
    id: root

    property int wallRemaining: 31
    property int activeSide: 3

    width: 210
    height: 178

    Rectangle {
        anchors.centerIn: parent
        width: 198
        height: 154
        radius: 77
        color: "#31161920"
        border.color: "#8f714b"
        border.width: 4
    }

    Repeater {
        model: 4

        Rectangle {
            required property int index
            width: 48
            height: 36
            radius: 18
            color: index === root.activeSide ? "#a2352b" : "#303438"
            border.color: index === root.activeSide ? "#ffd36a" : "#596268"
            border.width: 2
            x: index === 1 ? 12 : index === 2 ? root.width - width - 12 : (root.width - width) / 2
            y: index === 0 ? 8 : index === 3 ? root.height - height - 8 : (root.height - height) / 2

            Text {
                anchors.centerIn: parent
                text: ["N", "W", "E", "S"][parent.index]
                color: "#f2e8d2"
                font.pixelSize: 19
                font.bold: true
                font.family: "Microsoft YaHei"
                renderType: Text.NativeRendering
            }
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 72
        height: 58
        radius: 13
        color: "#102a2e"
        border.color: "#22282c"
        border.width: 4

        Text {
            anchors.centerIn: parent
            text: root.wallRemaining
            color: "#58f3ef"
            font.pixelSize: 31
            font.bold: true
            font.family: "Microsoft YaHei"
            renderType: Text.NativeRendering
        }
    }
}
