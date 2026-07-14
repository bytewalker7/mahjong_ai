import QtQuick

Item {
    id: root

    property var tiles: []
    property real tileWidth: 45
    property real tileHeight: 62

    implicitWidth: tiles.length * (tileWidth + 2)
    implicitHeight: tileHeight
    width: implicitWidth
    height: implicitHeight
    visible: tiles.length > 0

    Row {
        anchors.fill: parent
        spacing: 2

        Repeater {
            model: root.tiles
            delegate: FaceTile {
                required property var modelData
                tileCode: modelData.code || "1w"
                faceDown: modelData.faceDown
                tileWidth: root.tileWidth
                tileHeight: root.tileHeight


                NumberAnimation on opacity {
                    from: 0.0
                    to: 1.0
                    duration: 180
                }
            }
        }
    }
}
