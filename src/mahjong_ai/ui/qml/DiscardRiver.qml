import QtQuick

Item {
    id: root

    property var tiles: []
    property int columns: 6
    property real tileWidth: 34
    property real tileHeight: 46
    property real gap: 1

    readonly property int rowCount: Math.ceil(tiles.length / columns)
    implicitWidth: columns * (tileWidth + gap) - gap
    implicitHeight: rowCount * (tileHeight + gap) - gap
    width: implicitWidth
    height: implicitHeight

    Grid {
        anchors.fill: parent
        columns: root.columns
        columnSpacing: root.gap
        rowSpacing: root.gap

        Repeater {
            model: root.tiles

            delegate: Item {
                required property var modelData
                width: root.tileWidth
                height: root.tileHeight

                FaceTile {
                    anchors.fill: parent
                    tileCode: modelData.code
                    tileWidth: root.tileWidth
                    tileHeight: root.tileHeight
                    opacity: modelData.used ? 0.42 : 1.0

                    NumberAnimation on opacity {
                        from: 0.0
                        to: modelData.used ? 0.42 : 1.0
                        duration: 180
                    }
                }

                Rectangle {
                    visible: modelData.latest
                    anchors.fill: parent
                    anchors.bottomMargin: parent.height * 0.045
                    radius: Math.max(3, parent.width * 0.09)
                    color: "transparent"
                    border.color: "#ffd84d"
                    border.width: 3
                }

                Text {
                    visible: modelData.latest
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: -18
                    text: "▼"
                    color: "#ffd84d"
                    font.pixelSize: 17
                    font.bold: true
                }
            }
        }
    }
}
