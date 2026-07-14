import QtQuick
import QtQuick.Window

Window {
    id: window

    width: 1600
    height: 900
    minimumWidth: 1120
    minimumHeight: 630
    visible: true
    color: "#170c08"
    title: "麻将桌 QML 静态视觉稿"

    readonly property real fitScale: Math.min(width / 1600, height / 900)

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#1d0d07" }
            GradientStop { position: 0.18; color: "#4b2816" }
            GradientStop { position: 0.50; color: "#22110b" }
            GradientStop { position: 0.82; color: "#4b2816" }
            GradientStop { position: 1.0; color: "#190b07" }
        }
    }

    Repeater {
        model: 22
        Rectangle {
            required property int index
            x: index * window.width / 22
            width: 2
            height: window.height
            color: index % 2 ? "#744026" : "#120906"
            opacity: 0.30
        }
    }

    Item {
        id: scene
        width: 1600
        height: 900
        anchors.centerIn: parent
        scale: window.fitScale

        Rectangle {
            id: tableShadow
            x: 132
            y: 19
            width: 1336
            height: 906
            radius: 72
            color: "#a8000000"
        }

        Item {
            id: table
            x: 132
            y: -28
            width: 1336
            height: 920

            transform: Rotation {
                origin.x: table.width / 2
                origin.y: table.height / 2
                axis.x: 1
                axis.y: 0
                axis.z: 0
                angle: 3.8
            }

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 24
                radius: 68
                color: "#3d1e12"
                border.color: "#7b4328"
                border.width: 8
            }

            Rectangle {
                anchors.fill: parent
                radius: 68
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#9d5732" }
                    GradientStop { position: 0.16; color: "#5b2f1c" }
                    GradientStop { position: 0.50; color: "#7a4024" }
                    GradientStop { position: 0.84; color: "#5b2f1c" }
                    GradientStop { position: 1.0; color: "#9d5732" }
                }
                border.color: "#c27b49"
                border.width: 4
            }

            Rectangle {
                id: cloth
                anchors.fill: parent
                anchors.margins: 43
                radius: 44
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#14777c" }
                    GradientStop { position: 0.48; color: "#0d666b" }
                    GradientStop { position: 1.0; color: "#07515b" }
                }
                border.color: "#163f3d"
                border.width: 5

                Repeater {
                    model: 20
                    Rectangle {
                        required property int index
                        x: index * cloth.width / 20
                        width: 1
                        height: cloth.height
                        color: "#89d9cd"
                        opacity: 0.035
                    }
                }

                Repeater {
                    model: 14
                    Rectangle {
                        required property int index
                        y: index * cloth.height / 14
                        width: cloth.width
                        height: 1
                        color: "#89d9cd"
                        opacity: 0.028
                    }
                }
            }

            OpponentHand {
                concealedTileCount: 13
                tileWidth: 42
                tileHeight: 74
                overlap: 5
                x: (table.width - width) / 2
                y: 47
            }

            OpponentHand {
                concealedTileCount: 13
                tileWidth: 42
                tileHeight: 74
                overlap: 5
                x: 57 - width / 2
                y: table.height / 2 - height / 2
                rotation: 90
                transformOrigin: Item.Center
            }

            OpponentHand {
                concealedTileCount: 13
                tileWidth: 42
                tileHeight: 74
                overlap: 5
                x: table.width - 57 - width / 2
                y: table.height / 2 - height / 2
                rotation: -90
                transformOrigin: Item.Center
            }

            // Public discards arranged around the centre like the reference.
            DiscardRiver {
                tiles: ["2s", "4p", "7w", "6p", "8p", "5s", "3s", "1s", "5w", "2p", "9w", "1p"]
                columns: 6
                tileWidth: 35
                tileHeight: 47
                x: table.width / 2 - width / 2
                y: 210
                rotation: 180
                transformOrigin: Item.Center
            }

            DiscardRiver {
                tiles: ["2w", "5w", "7w", "3p", "1p", "9w", "8w", "6s", "5p", "2s", "1s"]
                columns: 6
                tileWidth: 35
                tileHeight: 47
                x: 340 - width / 2
                y: table.height / 2 - height / 2
                rotation: 90
                transformOrigin: Item.Center
            }

            DiscardRiver {
                tiles: ["1p", "9w", "7w", "4p", "3s", "1s", "2w", "5s", "8p", "6p", "1w"]
                columns: 6
                tileWidth: 35
                tileHeight: 47
                x: table.width - 340 - width / 2
                y: table.height / 2 - height / 2
                rotation: -90
                transformOrigin: Item.Center
            }

            DiscardRiver {
                tiles: ["6w", "5w", "1s", "1p", "5p", "7w", "1w", "7w", "5p", "8p", "1w", "2p", "6p", "9w"]
                columns: 8
                tileWidth: 37
                tileHeight: 50
                x: table.width / 2 - width / 2
                y: 586
            }

            TurnDial {
                x: table.width / 2 - width / 2
                y: table.height / 2 - height / 2 - 12
                wallRemaining: 31
                activeSide: 3
            }

            Text {
                x: table.width / 2 - width / 2
                y: 563
                text: "BASE 300"
                color: "#183e42"
                font.pixelSize: 22
                font.bold: true
                font.family: "Microsoft YaHei"
                renderType: Text.NativeRendering
            }

            Row {
                id: ownHand
                x: 128
                y: 748
                spacing: 2
                property var tiles: ["4s", "5s", "6s", "7s", "8s", "4p", "5p", "7p", "2p"]

                Repeater {
                    model: ownHand.tiles
                    delegate: FaceTile {
                        required property string modelData
                        tileCode: modelData
                        tileWidth: 67
                        tileHeight: 92
                    }
                }
            }

            // Two public melds at the human player's right, separated from hand.
            Row {
                x: 1035
                y: 757
                spacing: 2
                Repeater {
                    model: ["9p", "9p", "9p", "6s", "6s", "6s"]
                    delegate: FaceTile {
                        required property string modelData
                        tileCode: modelData
                        tileWidth: 48
                        tileHeight: 66
                    }
                }
            }
        }

        PlayerBadge {
            x: 61
            y: 245
            playerName: "Left AI"
            scoreText: "1141"
            accent: "#db9951"
        }

        PlayerBadge {
            x: 1168
            y: 18
            playerName: "Top AI"
            scoreText: "2728"
            accent: "#6ea85d"
        }

        PlayerBadge {
            x: 1441
            y: 247
            playerName: "Right AI"
            scoreText: "1102"
            accent: "#5789bd"
            dealer: true
        }

        PlayerBadge {
            x: 61
            y: 620
            playerName: "You"
            scoreText: "28000"
            accent: "#d65b42"
            active: true
        }

        Rectangle {
            x: 32
            y: 26
            width: 58
            height: 58
            radius: 29
            color: "#c01c1b18"
            border.color: "#756655"
            border.width: 3

            Text {
                anchors.centerIn: parent
                text: "☰"
                color: "#fff0ca"
                font.pixelSize: 30
                font.bold: true
                font.family: "Microsoft YaHei"
                renderType: Text.NativeRendering
            }
        }

        Rectangle {
            x: 101
            y: 29
            width: 42
            height: 52
            radius: 8
            color: "#18872b"
            border.color: "#8de56d"
            border.width: 2

            Text {
                anchors.centerIn: parent
                text: "5"
                color: "#efff87"
                font.pixelSize: 29
                font.bold: true
                font.family: "Microsoft YaHei"
                renderType: Text.NativeRendering
            }
        }

        Rectangle {
            x: 1521
            y: 491
            width: 54
            height: 54
            radius: 27
            color: "#a5212322"
            border.color: "#746a5e"
            border.width: 2

            Text {
                anchors.centerIn: parent
                text: "•••"
                color: "#fff3d5"
                font.pixelSize: 22
                font.family: "Microsoft YaHei"
                renderType: Text.NativeRendering
            }
        }
    }
}
