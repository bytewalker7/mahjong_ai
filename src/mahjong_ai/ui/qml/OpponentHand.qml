import QtQuick

Item {
    id: root

    property int concealedTileCount: 13
    property real tileWidth: 44
    property real tileHeight: 78
    property real overlap: 4

    readonly property real step: tileWidth - overlap
    implicitWidth: concealedTileCount > 0 ? concealedTileCount * step + overlap : 0
    implicitHeight: tileHeight
    width: implicitWidth
    height: implicitHeight

    Row {
        id: row
        anchors.fill: parent
        spacing: -root.overlap

        Repeater {
            model: root.concealedTileCount

            delegate: TileBack3D {
                required property int index
                tileWidth: root.tileWidth
                tileHeight: root.tileHeight
                z: index
            }
        }
    }
}
