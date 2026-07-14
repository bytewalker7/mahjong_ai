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
    title: "Mahjong AI"

    property int speedIndex: 1
    property var speedValues: [250, 550, 900]
    property var speedLabels: ["FAST", "NORMAL", "SLOW"]
    property string errorMessage: ""
    property bool rulesVisible: false
    readonly property real fitScale: Math.min(width / 1600, height / 900)

    Connections {
        target: gameBridge
        function onErrorOccurred(message) {
            window.errorMessage = message
            errorTimer.restart()
        }
    }

    Timer {
        id: errorTimer
        interval: 2600
        onTriggered: window.errorMessage = ""
    }

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

        MouseArea {
            anchors.fill: parent
            onClicked: gameBridge.clearSelection()
        }

        Rectangle {
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
            }

            OpponentHand {
                concealedTileCount: gameBridge.oppositeConcealedCount
                tileWidth: 42
                tileHeight: 74
                overlap: 5
                x: (table.width - width) / 2
                y: 47
            }

            // Left and right are deliberately reversed by 180 degrees from
            // the earlier draft, as requested. The entire hand is rotated.
            OpponentHand {
                concealedTileCount: gameBridge.leftConcealedCount
                tileWidth: 42
                tileHeight: 74
                overlap: 5
                x: 57 - width / 2
                y: table.height / 2 - height / 2
                rotation: -90
                transformOrigin: Item.Center
            }

            OpponentHand {
                concealedTileCount: gameBridge.rightConcealedCount
                tileWidth: 42
                tileHeight: 74
                overlap: 5
                x: table.width - 57 - width / 2
                y: table.height / 2 - height / 2
                rotation: 90
                transformOrigin: Item.Center
            }

            DiscardRiver {
                tiles: gameBridge.oppositeDiscards
                columns: 6
                tileWidth: 35
                tileHeight: 47
                x: table.width / 2 - width / 2
                y: 210
                rotation: 180
                transformOrigin: Item.Center
            }

            DiscardRiver {
                tiles: gameBridge.leftDiscards
                columns: 6
                tileWidth: 35
                tileHeight: 47
                x: 340 - width / 2
                y: table.height / 2 - height / 2
                rotation: 90
                transformOrigin: Item.Center
            }

            DiscardRiver {
                tiles: gameBridge.rightDiscards
                columns: 6
                tileWidth: 35
                tileHeight: 47
                x: table.width - 340 - width / 2
                y: table.height / 2 - height / 2
                rotation: -90
                transformOrigin: Item.Center
            }

            DiscardRiver {
                tiles: gameBridge.selfDiscards
                columns: 8
                tileWidth: 37
                tileHeight: 50
                x: table.width / 2 - width / 2
                y: 586
            }

            MeldStrip {
                tiles: gameBridge.oppositeMelds
                tileWidth: 38
                tileHeight: 52
                x: 270
                y: 128
                rotation: 180
                transformOrigin: Item.Center
            }

            MeldStrip {
                tiles: gameBridge.leftMelds
                tileWidth: 38
                tileHeight: 52
                x: 165 - width / 2
                y: 650
                rotation: 90
                transformOrigin: Item.Center
            }

            MeldStrip {
                tiles: gameBridge.rightMelds
                tileWidth: 38
                tileHeight: 52
                x: table.width - 165 - width / 2
                y: 190
                rotation: -90
                transformOrigin: Item.Center
            }

            TurnDial {
                x: table.width / 2 - width / 2
                y: table.height / 2 - height / 2 - 12
                wallRemaining: gameBridge.wallRemaining
                activeSide: gameBridge.dialSide
            }

            Row {
                id: ownHand
                readonly property real leftBoundary: 190
                readonly property real rightBoundary: selfMeldStrip.visible
                    ? selfMeldStrip.x - 20
                    : table.width - 105
                x: Math.max(leftBoundary,
                            leftBoundary + (rightBoundary - leftBoundary - width) / 2)
                y: 748
                spacing: 2

                Repeater {
                    model: gameBridge.handTiles
                    delegate: Item {
                        required property var modelData
                        width: 69 + (modelData.drawn ? 18 : 0)
                        height: 112

                        FaceTile {
                            x: modelData.drawn ? 18 : 0
                            y: modelData.selected ? -17 : 0
                            tileCode: modelData.code
                            tileWidth: 67
                            tileHeight: 92
                            selected: modelData.selected
                            interactive: modelData.legal
                            opacity: modelData.legal ? 1.0 : 0.82
                            onClicked: gameBridge.clickTileAt(modelData.instance)

                            Behavior on y { NumberAnimation { duration: 130; easing.type: Easing.OutCubic } }
                        }
                    }
                }
            }

            MeldStrip {
                id: selfMeldStrip
                tiles: gameBridge.selfMelds
                tileWidth: 48
                tileHeight: 66
                x: table.width - width - 105
                y: 757
            }
        }

        PlayerBadge {
            x: 61
            y: 245
            playerName: "Left AI"
            scoreText: String(gameBridge.leftScore)
            accent: "#db9951"
            dealer: gameBridge.dealer === 1
            active: gameBridge.currentPlayer === 1
        }

        PlayerBadge {
            x: 1168
            y: 18
            playerName: "Top AI"
            scoreText: String(gameBridge.oppositeScore)
            accent: "#6ea85d"
            dealer: gameBridge.dealer === 2
            active: gameBridge.currentPlayer === 2
        }

        PlayerBadge {
            x: 1441
            y: 247
            playerName: "Right AI"
            scoreText: String(gameBridge.rightScore)
            accent: "#5789bd"
            dealer: gameBridge.dealer === 3
            active: gameBridge.currentPlayer === 3
        }

        PlayerBadge {
            x: 61
            y: 660
            playerName: "You"
            scoreText: String(gameBridge.selfScore)
            accent: "#d65b42"
            dealer: gameBridge.dealer === 0
            active: gameBridge.currentPlayer === 0
        }

        Rectangle {
            x: 28
            y: 27
            width: 132
            height: 50
            radius: 12
            color: "#c01c1b18"
            border.color: "#756655"
            border.width: 2

            Text {
                anchors.centerIn: parent
                text: "新的一局"
                color: "#fff0ca"
                font.family: "Microsoft YaHei"
                font.pixelSize: 18
                font.bold: true
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: gameBridge.newGame()
            }
        }

        Rectangle {
            x: 171
            y: 28
            width: 110
            height: 52
            radius: 10
            color: "#b018442e"
            border.color: "#6ecb87"
            border.width: 2

            Text {
                anchors.centerIn: parent
                text: window.speedLabels[window.speedIndex]
                color: "#efffca"
                font.pixelSize: 16
                font.bold: true
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    window.speedIndex = (window.speedIndex + 1) % window.speedValues.length
                    gameBridge.setAiDelay(window.speedValues[window.speedIndex])
                }
            }
        }

        Rectangle {
            x: 292
            y: 28
            width: 118
            height: 52
            radius: 10
            color: gameBridge.musicEnabled ? "#b018442e" : "#b03f3230"
            border.color: gameBridge.musicEnabled ? "#6ecb87" : "#9d8881"
            border.width: 2

            Text {
                anchors.centerIn: parent
                text: gameBridge.musicEnabled ? "音乐：开" : "音乐：关"
                color: gameBridge.musicEnabled ? "#efffca" : "#dbcac4"
                font.family: "Microsoft YaHei"
                font.pixelSize: 16
                font.bold: true
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: gameBridge.toggleMusic()
            }
        }

        Rectangle {
            x: 421
            y: 28
            width: 118
            height: 52
            radius: 10
            color: "#b02b3f49"
            border.color: "#80b9c9"
            border.width: 2

            Text {
                anchors.centerIn: parent
                text: "游戏规则"
                color: "#f3f0df"
                font.family: "Microsoft YaHei"
                font.pixelSize: 16
                font.bold: true
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: window.rulesVisible = true
            }
        }

        Row {
            x: 1195
            y: 665
            spacing: 12

            Repeater {
                model: gameBridge.actionOptions
                delegate: RoundGameAction {
                    required property var modelData
                    label: modelData.label
                    actionColor: modelData.color
                    onTriggered: gameBridge.performAction(modelData.key)
                }
            }
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            y: 678
            width: Math.max(320, statusLabel.implicitWidth + 42)
            height: 40
            radius: 20
            color: "#c0162b2d"
            border.color: gameBridge.currentPlayer === 0 ? "#65f2d5" : "#537276"
            border.width: 2

            Text {
                id: statusLabel
                anchors.centerIn: parent
                text: gameBridge.statusText
                color: "#f3f0df"
                font.family: "Microsoft YaHei"
                font.pixelSize: 16
                font.bold: true
            }
        }

        Rectangle {
            visible: window.errorMessage.length > 0
            anchors.horizontalCenter: parent.horizontalCenter
            y: 112
            width: Math.max(360, errorLabel.implicitWidth + 44)
            height: 46
            radius: 12
            color: "#e0a52a25"
            border.color: "#ffd18a"
            border.width: 2

            Text {
                id: errorLabel
                anchors.centerIn: parent
                text: window.errorMessage
                color: "white"
                font.family: "Microsoft YaHei"
                font.pixelSize: 16
            }
        }

        Rectangle {
            visible: gameBridge.finished
            anchors.centerIn: parent
            width: 440
            height: 230
            radius: 28
            color: "#ef142a30"
            border.color: "#e7b755"
            border.width: 5

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 45
                text: gameBridge.statusText
                color: "#fff1bd"
                font.family: "Microsoft YaHei"
                font.pixelSize: 30
                font.bold: true
            }

            Rectangle {
                x: 72
                y: 135
                width: 136
                height: 56
                radius: 16
                color: "#2b9071"
                Text { anchors.centerIn: parent; text: "NEW"; color: "white"; font.pixelSize: 20; font.bold: true }
                MouseArea { anchors.fill: parent; onClicked: gameBridge.newGame(); cursorShape: Qt.PointingHandCursor }
            }

            Rectangle {
                x: 232
                y: 135
                width: 136
                height: 56
                radius: 16
                color: "#704844"
                Text { anchors.centerIn: parent; text: "EXIT"; color: "white"; font.pixelSize: 20; font.bold: true }
                MouseArea { anchors.fill: parent; onClicked: gameBridge.quit(); cursorShape: Qt.PointingHandCursor }
            }
        }

        Item {
            anchors.fill: parent
            z: 100
            visible: window.rulesVisible

            Rectangle {
                anchors.fill: parent
                color: "#99000000"
            }

            MouseArea {
                anchors.fill: parent
                onClicked: window.rulesVisible = false
            }

            Rectangle {
                anchors.centerIn: parent
                width: 790
                height: 600
                radius: 24
                color: "#f01a3034"
                border.color: "#d9ad5b"
                border.width: 4

                MouseArea {
                    anchors.fill: parent
                    onClicked: function(mouse) { mouse.accepted = true }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 25
                    text: "游戏规则"
                    color: "#ffe8a3"
                    font.family: "Microsoft YaHei"
                    font.pixelSize: 28
                    font.bold: true
                }

                Rectangle {
                    x: 735
                    y: 18
                    width: 38
                    height: 38
                    radius: 19
                    color: "#75433d"
                    border.color: "#d69a7c"

                    Text {
                        anchors.centerIn: parent
                        text: "×"
                        color: "white"
                        font.pixelSize: 25
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: window.rulesVisible = false
                    }
                }

                Text {
                    x: 45
                    y: 84
                    width: 700
                    text: "基本规则"
                    color: "#71ead2"
                    font.family: "Microsoft YaHei"
                    font.pixelSize: 22
                    font.bold: true
                }

                Text {
                    x: 45
                    y: 124
                    width: 700
                    text: "• 四人麻将，只使用万、条、筒，共 108 张牌。\n" +
                          "• 不使用字牌、花牌，不允许吃牌。\n" +
                          "• 庄家 14 张先出牌，其他玩家 13 张。\n" +
                          "• 胡牌结构：4 组面子 + 1 对将，只计算普通平胡。\n" +
                          "• 支持碰、明杠、暗杠和补杠；杠后立即补牌。\n" +
                          "• 响应优先级：胡 > 明杠 > 碰；同级时近家优先。\n" +
                          "• 牌墙摸完且无人胡牌则流局。\n" +
                          "• 每局随机庄家，积分跨局累计。"
                    color: "#f0eee3"
                    font.family: "Microsoft YaHei"
                    font.pixelSize: 17
                    lineHeight: 1.28
                }

                Text {
                    x: 45
                    y: 365
                    width: 700
                    text: "计分规则"
                    color: "#71ead2"
                    font.family: "Microsoft YaHei"
                    font.pixelSize: 22
                    font.bold: true
                }

                Text {
                    x: 45
                    y: 405
                    width: 700
                    text: "• 普通点炮：胡牌者 +1，点炮者 -1；庄家翻倍。\n" +
                          "• 普通自摸：其他三家各 -2，胡牌者共 +6；庄家翻倍。\n" +
                          "• 暗杠 +2，明杠 +1，补杠 +1。\n" +
                          "• 当前炮子数固定为 0，不计算炮子分。"
                    color: "#f0eee3"
                    font.family: "Microsoft YaHei"
                    font.pixelSize: 17
                    lineHeight: 1.35
                }
            }
        }
    }
}
