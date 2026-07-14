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

            delegate: FaceTile {
                required property string modelData
                tileCode: modelData
                tileWidth: root.tileWidth
                tileHeight: root.tileHeight
            }
        }
    }
}
