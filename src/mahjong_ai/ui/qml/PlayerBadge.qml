import QtQuick

Item {
    id: root

    property string playerName: "AI"
    property string scoreText: "2500"
    property string accent: "#f5b940"
    property bool dealer: false
    property bool active: false

    width: 112
    height: 128

    Rectangle {
        id: glow
        anchors.horizontalCenter: parent.horizontalCenter
        width: 86
        height: 86
        radius: 16
        color: "#33272b2d"
        border.color: root.active ? "#ffd75f" : "#687b76"
        border.width: root.active ? 4 : 2

        Rectangle {
            anchors.centerIn: parent
            width: 66
            height: 66
            radius: 33
            gradient: Gradient {
                GradientStop { position: 0.0; color: root.accent }
                GradientStop { position: 1.0; color: "#253a3a" }
            }

            Text {
                anchors.centerIn: parent
                text: root.playerName.substring(0, 1)
                color: "white"
                font.pixelSize: 28
                font.bold: true
                font.family: "Microsoft YaHei"
                renderType: Text.NativeRendering
            }
        }

        Rectangle {
            visible: root.dealer
            width: 31
            height: 31
            radius: 7
            x: -8
            y: -8
            color: "#d93525"
            border.color: "#ffd06a"
            border.width: 2

            Text {
                anchors.centerIn: parent
                text: "D"
                color: "#fff0bd"
                font.pixelSize: 18
                font.bold: true
                font.family: "Microsoft YaHei"
                renderType: Text.NativeRendering
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 89
        text: root.playerName
        color: "#f4ead7"
        font.pixelSize: 15
        font.bold: true
        font.family: "Microsoft YaHei"
        renderType: Text.NativeRendering
    }

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 109
        width: 82
        height: 23
        radius: 11
        color: "#b01b2020"

        Text {
            anchors.centerIn: parent
            text: "● " + root.scoreText
            color: "#ffd865"
            font.pixelSize: 14
            font.bold: true
            font.family: "Microsoft YaHei"
            renderType: Text.NativeRendering
        }
    }
}
