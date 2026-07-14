import QtQuick

Item {
    id: root

    property string tileCode: "1w"
    property real tileWidth: 48
    property real tileHeight: 66

    width: tileWidth
    height: tileHeight

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.91
        width: parent.width * 0.82
        height: parent.height * 0.10
        radius: height / 2
        color: "#66000000"
    }

    Rectangle {
        anchors.fill: parent
        anchors.bottomMargin: parent.height * 0.045
        radius: Math.max(4, parent.width * 0.09)
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#fffef8" }
            GradientStop { position: 0.72; color: "#f3f0e4" }
            GradientStop { position: 1.0; color: "#c9d3cc" }
        }
        border.color: "#52666a"
        border.width: 1.5
    }

    Image {
        anchors.fill: parent
        anchors.margins: 3
        anchors.bottomMargin: 6
        source: "../../assets/tiles/" + root.tileCode + ".svg"
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
    }
}
