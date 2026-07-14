import QtQuick
import QtQuick.Window

Window {
    id: window

    width: 1440
    height: 900
    minimumWidth: 1100
    minimumHeight: 700
    visible: true
    color: "#241710"
    title: "麻将桌 QML 2.5D 静态预览"

    // Warm wood floor around the table. The table deliberately does not fill
    // the window, so its hidden legs read as being below the camera frame.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#24130c" }
            GradientStop { position: 0.5; color: "#5b321c" }
            GradientStop { position: 1.0; color: "#21120c" }
        }
    }

    Repeater {
        model: Math.ceil(window.width / 92)
        Rectangle {
            required property int index
            x: index * 92
            width: 2
            height: window.height
            color: index % 2 ? "#382016" : "#7a4729"
            opacity: 0.35
        }
    }

    Repeater {
        model: Math.ceil(window.height / 180)
        Rectangle {
            required property int index
            y: index * 180
            width: window.width
            height: 1
            color: "#b47749"
            opacity: 0.18
        }
    }

    Rectangle {
        id: tableShadow
        width: window.width * 0.86
        height: window.height * 0.79
        anchors.centerIn: parent
        anchors.verticalCenterOffset: 30
        radius: 54
        color: "#99000000"
        scale: 1.015
    }

    Item {
        id: table
        width: window.width * 0.84
        height: window.height * 0.78
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -4

        transform: Rotation {
            origin.x: table.width / 2
            origin.y: table.height / 2
            axis.x: 1
            axis.y: 0
            axis.z: 0
            angle: 5.5
        }

        Rectangle {
            id: frontThickness
            anchors.fill: parent
            anchors.topMargin: 20
            radius: 48
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#8e532d" }
                GradientStop { position: 0.65; color: "#4a2818" }
                GradientStop { position: 1.0; color: "#24130d" }
            }
            border.color: "#b87a47"
            border.width: 3
        }

        Rectangle {
            id: frame
            anchors.fill: parent
            radius: 48
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#a96a3b" }
                GradientStop { position: 0.45; color: "#6b3a22" }
                GradientStop { position: 1.0; color: "#a66839" }
            }
            border.color: "#d09058"
            border.width: 3
        }

        Rectangle {
            id: cloth
            anchors.fill: parent
            anchors.margins: Math.max(24, table.width * 0.027)
            radius: 34
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#116f70" }
                GradientStop { position: 0.5; color: "#0b5d61" }
                GradientStop { position: 1.0; color: "#08464e" }
            }
            border.color: "#164c42"
            border.width: 4

            Repeater {
                model: 18
                Rectangle {
                    required property int index
                    x: index * cloth.width / 18
                    width: 1
                    height: cloth.height
                    color: "#65cbc0"
                    opacity: 0.055
                }
            }

            Repeater {
                model: 12
                Rectangle {
                    required property int index
                    y: index * cloth.height / 12
                    width: cloth.width
                    height: 1
                    color: "#65cbc0"
                    opacity: 0.045
                }
            }
        }

        OpponentHand {
            id: topHand
            concealedTileCount: 13
            tileWidth: Math.max(34, Math.min(46, table.width / 29))
            tileHeight: tileWidth * 1.76
            overlap: 4
            anchors.horizontalCenter: parent.horizontalCenter
            y: cloth.y + 25
        }

        OpponentHand {
            id: leftHand
            concealedTileCount: 13
            tileWidth: topHand.tileWidth
            tileHeight: topHand.tileHeight
            overlap: topHand.overlap
            x: cloth.x + 30 - width / 2
            y: table.height / 2 - height / 2
            rotation: 90
            transformOrigin: Item.Center
        }

        OpponentHand {
            id: rightHand
            concealedTileCount: 13
            tileWidth: topHand.tileWidth
            tileHeight: topHand.tileHeight
            overlap: topHand.overlap
            x: cloth.x + cloth.width - 30 - width / 2
            y: table.height / 2 - height / 2
            rotation: -90
            transformOrigin: Item.Center
        }

        Rectangle {
            id: centerDeck
            width: 150
            height: 116
            anchors.centerIn: cloth
            radius: 26
            color: "#183238"
            border.color: "#d9a34a"
            border.width: 4

            Text {
                anchors.centerIn: parent
                text: "58"
                color: "#78f6e5"
                font.pixelSize: 28
                font.bold: true
            }
        }

        Row {
            id: ownHand
            spacing: 2
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 24

            property var tiles: ["1w", "2w", "3w", "5w", "7w", "1s", "2s", "4s", "6s", "1p", "3p", "5p", "7p", "9p"]

            Repeater {
                model: ownHand.tiles
                delegate: FaceTile {
                    required property string modelData
                    tileCode: modelData
                    tileWidth: Math.max(42, Math.min(58, table.width / 23))
                    tileHeight: tileWidth * 1.34
                }
            }
        }
    }

}
