import QtQuick

Item {
    id: root

    property real tileWidth: 44
    property real tileHeight: 78

    width: tileWidth
    height: tileHeight

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.86
        width: parent.width * 0.78
        height: parent.height * 0.10
        radius: height / 2
        color: "#55000000"
        scale: 1.08
    }

    Image {
        anchors.fill: parent
        source: "../../assets/ui/tile_back_3d.png"
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        asynchronous: false
    }
}
