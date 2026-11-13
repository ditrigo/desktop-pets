pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons as Commons
import qs.Ui
import "PetLooks.js" as Looks
import "PetCatalog.js" as Catalog
import "PetStatus.js" as Status

Column {
    id: root
    PetTranslations {
        id: strings
    }
    property var controller: null
    readonly property var backend: controller
    readonly property var cfg: backend ? backend.config : ({})
    property int tab: 0
    property string previewView: "threeQuarter"
    readonly property var stateNames: ({
            settle: strings.t("mode.settle"),
            idle: strings.t("mode.idle"),
            walk: strings.t("mode.walk"),
            fly: strings.t("mode.fly"),
            fall: strings.t("mode.fall"),
            wave: strings.t("mode.wave"),
            sleep: strings.t("mode.sleep"),
            preen: strings.t("mode.preen"),
            eat: strings.t("mode.eat"),
            love: strings.t("mode.love"),
            dance: strings.t("mode.dance"),
            quack: strings.t("mode.quack"),
            drag: strings.t("mode.drag"),
            notice: strings.t("mode.notice"),
            sniff: strings.t("mode.sniff"),
            turn: strings.t("mode.turn"),
            anticipate: strings.t("mode.anticipate"),
            land: strings.t("mode.land"),
            peek: strings.t("mode.peek"),
            look: strings.t("mode.look"),
            stretch: strings.t("mode.stretch"),
            shake: strings.t("mode.shake"),
            giggle: strings.t("mode.giggle"),
            surprise: strings.t("mode.surprise"),
            nudge: strings.t("mode.nudge")
        })
    function switchTab(next) {
        tab = Math.max(0, Math.min(2, next));
    }
    spacing: 14

    component PetAction: Button {
        required property string actionName
        enabled: root.backend.canAction(actionName)
        opacity: enabled ? 1 : .42
        onClicked: root.backend.action(actionName)
    }

    Rectangle {
        width: parent.width
        height: 105
        radius: 14
        color: Qt.rgba(1, .82, .38, .08)
        PetSprite {
            x: 5
            y: 0
            width: 112
            height: 105
            plumage: root.cfg.palette
            artStyle: root.cfg.artStyle
            hat: root.cfg.hat
            outfit: root.cfg.outfit
            mode: root.tab === 1 || root.backend.paused ? "idle" : root.backend.runtime.mode || "wave"
            view: root.tab === 1 ? root.previewView : root.backend.runtime.view || "threeQuarter"
            modeTime: root.backend.runtime.phase || 0
            clock: root.backend.runtime.animationClock || 0
            reducedMotion: root.cfg.reducedMotion
            animate: root.visible && !root.cfg.reducedMotion && !root.backend.paused
            MouseArea {
                anchors.fill: parent
                enabled: root.backend.canAction("head")
                cursorShape: Qt.PointingHandCursor
                onClicked: root.backend.action("head")
            }
        }
        Column {
            x: 128
            width: parent.width - x - 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 5
            PetLabel {
                width: parent.width
                text: root.cfg.name || strings.t("pet.default-name")
                font.pixelSize: 20
                font.bold: true
            }
            PetLabel {
                width: parent.width
                text: Status.label(root.backend.runState, strings) || (root.backend.runtime.mood ? strings.t("mood." + root.backend.runtime.mood, root.backend.runtime.mood) : strings.t("pet.neighbor"))
                opacity: .8
            }
            PetLabel {
                width: parent.width
                text: Status.hint(root.backend.runState, strings) || (root.backend.resting ? strings.tn("rest.remaining", root.backend.restMinutes).arg(Commons.I18n.formatNumber(root.backend.restMinutes)) : root.stateNames[root.backend.runtime.mode] || strings.t("pet.ready"))
                font.pixelSize: 11
                opacity: .55
            }
        }
    }
    PetLabel {
        width: parent.width
        visible: !!root.backend.quietNow
        text: strings.t("quiet.active").arg(root.cfg.quietMode === "work" ? strings.t("quiet.work") : strings.t("quiet.reduced"))
        font.pixelSize: 11
        opacity: .7
    }
    Row {
        width: parent.width
        spacing: 6
        Repeater {
            model: [strings.t("tab.play"), strings.t("tab.appearance"), strings.t("tab.behavior")]
            delegate: Button {
                required property string modelData
                required property int index
                width: (root.width - 12) / 3
                text: modelData
                selected: root.tab === index
                bordered: true
                focusable: true
                onClicked: root.switchTab(index)
            }
        }
    }
    Column {
        width: parent.width
        spacing: 14
        visible: root.tab === 0
        Flow {
            width: parent.width
            spacing: 7
            Repeater {
                model: [
                    {
                        label: strings.t("action.feed"),
                        action: "feed"
                    },
                    {
                        label: strings.t("action.ball"),
                        action: "ball"
                    },
                    {
                        label: strings.t("action.pet"),
                        action: "pet"
                    },
                    {
                        label: strings.t("action.come"),
                        action: "come"
                    },
                    {
                        label: strings.t("action.dance"),
                        action: "dance"
                    },
                    {
                        label: strings.t("action.home"),
                        action: "home"
                    }
                ]
                delegate: PetAction {
                    required property var modelData
                    actionName: modelData.action
                    width: (root.width - 14) / 3
                    text: strings.item(modelData)
                    fontSize: 12
                    verticalPadding: 12
                    bordered: true
                    focusable: true
                }
            }
        }
        PetLabel {
            width: parent.width
            text: strings.t("play.help")
            font.pixelSize: 11
            opacity: .6
        }
        Flow {
            width: parent.width
            spacing: 6
            PetAction {
                actionName: "hop"
                text: strings.t("action.hop")
                bordered: true
                focusable: true
                fontSize: 12
            }
            PetAction {
                actionName: "quack"
                text: strings.t("speech.quack")
                bordered: true
                focusable: true
                fontSize: 12
            }
            PetAction {
                actionName: root.backend.runtime.mode === "sleep" || root.backend.resting ? "wake" : "sleep"
                text: root.backend.runtime.mode === "sleep" || root.backend.resting ? strings.t("action.wake") : strings.t("action.sleep")
                bordered: true
                focusable: true
                fontSize: 12
            }
            PetAction {
                actionName: "pause"
                text: root.backend.paused ? strings.t("action.resume") : strings.t("action.pause")
                bordered: true
                focusable: true
                fontSize: 12
            }
        }
        PetSettingRow {
            label: strings.t("quiet.work")
            detail: strings.t("work.help")
            ToggleSwitch {
                checked: root.cfg.workMode
                onToggled: root.backend.setSetting("workMode", !root.cfg.workMode)
            }
        }
        Row {
            spacing: 6
            PetAction {
                actionName: root.backend.resting ? "wake" : "rest"
                text: root.backend.resting ? strings.t("action.cancel-rest") : strings.t("action.rest")
                bordered: true
                focusable: true
                fontSize: 12
            }
            PetAction {
                actionName: "clear"
                text: strings.t("action.clear")
                bordered: true
                focusable: true
                fontSize: 12
            }
        }
        PetLabel {
            width: parent.width
            font.pixelSize: 11
            opacity: .65
            text: strings.t("stats.summary").arg(Commons.I18n.formatNumber(root.backend.runtime.energy === undefined ? Math.round(root.backend.profile.energy) : root.backend.runtime.energy)).arg(Commons.I18n.formatNumber(root.backend.runtime.satiety === undefined ? Math.round(root.backend.profile.satiety) : root.backend.runtime.satiety)).arg(Commons.I18n.formatNumber(root.backend.runtime.trust === undefined ? Math.round(root.backend.profile.trust) : root.backend.runtime.trust))
        }
    }
    Column {
        width: parent.width
        spacing: 14
        visible: root.tab === 1
        PetSettingRow {
            label: strings.t("setting.name")
            detail: strings.t("name.help")
            TextField {
                width: 175
                text: root.cfg.name
                maximumLength: 32
                onEditingFinished: root.backend.setSetting("name", text)
            }
        }
        PetAppearancePicker {
            width: parent.width
            controller: root.backend
            previewView: root.previewView
            settingKey: "artStyle"
            heading: strings.t("setting.model")
            options: Catalog.data.models
        }
        PetLabel {
            text: strings.t("setting.view")
            font.bold: true
        }
        Row {
            spacing: 6
            Repeater {
                model: [
                    {
                        key: "side",
                        label: strings.t("view.side")
                    },
                    {
                        key: "threeQuarter",
                        label: strings.t("view.threeQuarter")
                    },
                    {
                        key: "front",
                        label: strings.t("view.front")
                    }
                ]
                delegate: Button {
                    required property var modelData
                    text: strings.item(modelData)
                    bordered: true
                    focusable: true
                    selected: root.previewView === modelData.key
                    onClicked: root.previewView = modelData.key
                }
            }
        }
        PetSettingRow {
            label: strings.t("setting.size")
            detail: strings.t("size.help")
            NumberField {
                value: root.cfg.size
                from: 48
                to: 144
                stepSize: 4
                fieldWidth: 105
                onModified: function (v) {
                    root.backend.setSetting("size", v);
                }
            }
        }
        PetLabel {
            text: strings.t("setting.palette")
            font.bold: true
        }
        Flow {
            width: parent.width
            spacing: 6
            Repeater {
                model: [
                    {
                        key: "yellow",
                        text: strings.t("palette.yellow")
                    },
                    {
                        key: "mallard",
                        text: strings.t("palette.mallard")
                    },
                    {
                        key: "white",
                        text: strings.t("palette.white")
                    }
                ]
                delegate: Button {
                    required property var modelData
                    text: modelData.text
                    bordered: true
                    focusable: true
                    selected: root.cfg.palette === modelData.key
                    onClicked: root.backend.setSetting("palette", modelData.key)
                }
            }
        }
        PetLabel {
            text: strings.t("collection.title")
            font.bold: true
        }
        TextField {
            id: lookName
            width: parent.width
            placeholderText: strings.t("collection.name")
            maximumLength: 32
        }
        Flow {
            width: parent.width
            spacing: 6
            Button {
                text: strings.t("collection.save-wardrobe")
                bordered: true
                focusable: true
                onClicked: root.backend.storeLook(lookName.text, "wardrobe")
            }
            Button {
                text: strings.t("collection.save-full")
                bordered: true
                focusable: true
                onClicked: root.backend.storeLook(lookName.text, "full")
            }
        }
        Repeater {
            model: root.backend.profile.looks || []
            delegate: Row {
                id: savedRow
                required property var modelData
                width: root.width
                spacing: 7
                PetSprite {
                    width: 70
                    height: 66
                    artStyle: savedRow.modelData.artStyle || root.cfg.artStyle
                    plumage: savedRow.modelData.palette || root.cfg.palette
                    hat: savedRow.modelData.hat
                    outfit: savedRow.modelData.outfit
                    view: root.previewView
                    animate: false
                }
                Column {
                    width: root.width - 77
                    spacing: 5
                    TextField {
                        width: parent.width
                        text: savedRow.modelData.name
                        maximumLength: 32
                        onEditingFinished: root.backend.renameLook(savedRow.modelData.id, text)
                    }
                    Flow {
                        width: parent.width
                        spacing: 5
                        Button {
                            text: savedRow.modelData.kind === "wardrobe" ? strings.t("collection.wear") : strings.t("collection.apply")
                            fontSize: 11
                            bordered: true
                            onClicked: root.backend.applySavedLook(savedRow.modelData.id)
                        }
                        Button {
                            text: strings.t("collection.remove")
                            fontSize: 11
                            bordered: true
                            onClicked: root.backend.removeLook(savedRow.modelData.id)
                        }
                    }
                }
            }
        }
        PetLabel {
            width: parent.width
            text: strings.t("collection.help")
            font.pixelSize: 11
            opacity: .6
        }
        PetLabel {
            text: strings.t("collection.presets")
            font.bold: true
        }
        Flow {
            width: parent.width
            spacing: 6
            Repeater {
                model: Looks.available(Looks.options, root.cfg.artStyle)
                delegate: Button {
                    required property var modelData
                    width: (root.width - 12) / 3
                    text: strings.item(modelData)
                    fontSize: 11
                    bordered: true
                    focusable: true
                    selected: Looks.matches(root.cfg, modelData)
                    onClicked: root.backend.applyLook(modelData.key)
                }
            }
        }
        PetLabel {
            width: parent.width
            text: strings.t("collection.mix")
            font.pixelSize: 11
            opacity: .6
        }
        PetAppearancePicker {
            width: parent.width
            controller: root.backend
            previewView: root.previewView
            settingKey: "hat"
            heading: strings.t("setting.hat")
            columns: 4
            options: Looks.available(Looks.hats, root.cfg.artStyle)
        }
        PetAppearancePicker {
            width: parent.width
            controller: root.backend
            previewView: root.previewView
            settingKey: "outfit"
            heading: strings.t("setting.outfit")
            options: Looks.available(Looks.outfits, root.cfg.artStyle)
        }
        PetLabel {
            width: parent.width
            text: strings.t("collection.compatibility")
            font.pixelSize: 11
            opacity: .6
        }
        PetSettingRow {
            label: strings.t("setting.enabled")
            ToggleSwitch {
                checked: root.cfg.enabled
                onToggled: root.backend.setSetting("enabled", !root.cfg.enabled)
            }
        }
        PetLabel {
            width: parent.width
            text: strings.t("interaction.help")
            font.pixelSize: 12
            opacity: .6
        }
    }
    Column {
        width: parent.width
        spacing: 14
        visible: root.tab === 2
        PetSettingRow {
            label: strings.t("setting.quiet")
            detail: strings.t("quiet.help")
            ToggleSwitch {
                checked: root.cfg.quietHours
                onToggled: root.backend.setSetting("quietHours", !root.cfg.quietHours)
            }
        }
        Row {
            spacing: 12
            enabled: root.cfg.quietHours
            Column {
                spacing: 4
                PetLabel {
                    text: strings.t("quiet.start")
                    font.pixelSize: 11
                    opacity: 0.65
                }
                TextField {
                    id: quietStart
                    objectName: "quietStart"
                    width: 100
                    text: root.cfg.quietStart
                    maximumLength: 5
                    placeholderText: "22:00"
                    validator: RegularExpressionValidator {
                        regularExpression: /^([01][0-9]|2[0-3]):[0-5][0-9]$/
                    }
                    foreground: acceptableInput ? Commons.Color.foreground : Commons.Color.urgent
                    onEditingFinished: if (acceptableInput)
                        root.backend.setSetting("quietStart", text)
                }
            }
            Column {
                spacing: 4
                PetLabel {
                    text: strings.t("quiet.end")
                    font.pixelSize: 11
                    opacity: 0.65
                }
                TextField {
                    id: quietEnd
                    objectName: "quietEnd"
                    width: 100
                    text: root.cfg.quietEnd
                    maximumLength: 5
                    placeholderText: "08:00"
                    validator: RegularExpressionValidator {
                        regularExpression: /^([01][0-9]|2[0-3]):[0-5][0-9]$/
                    }
                    foreground: acceptableInput ? Commons.Color.foreground : Commons.Color.urgent
                    onEditingFinished: if (acceptableInput)
                        root.backend.setSetting("quietEnd", text)
                }
            }
        }
        PetLabel {
            width: parent.width
            visible: root.cfg.quietHours
            text: !quietStart.acceptableInput || !quietEnd.acceptableInput ? strings.t("quiet.invalid") : root.cfg.quietStart === root.cfg.quietEnd ? strings.t("quiet.equal") : strings.t("quiet.time-help")
            color: !quietStart.acceptableInput || !quietEnd.acceptableInput ? Commons.Color.urgent : Commons.Color.foreground
            opacity: 0.7
            font.pixelSize: 11
        }
        Flow {
            width: parent.width
            spacing: 6
            Button {
                text: strings.t("quiet.work")
                selected: root.cfg.quietMode === "work"
                bordered: true
                onClicked: root.backend.setSetting("quietMode", "work")
            }
            Button {
                text: strings.t("quiet.reduced")
                selected: root.cfg.quietMode === "reduced"
                bordered: true
                onClicked: root.backend.setSetting("quietMode", "reduced")
            }
        }
        PetLabel {
            text: strings.t("setting.power")
            font.bold: true
        }
        Flow {
            width: parent.width
            spacing: 6
            Repeater {
                model: [
                    {
                        key: "normal",
                        label: strings.t("power.normal")
                    },
                    {
                        key: "economy",
                        label: strings.t("power.economy")
                    },
                    {
                        key: "auto",
                        label: strings.t("power.auto")
                    }
                ]
                delegate: Button {
                    required property var modelData
                    text: strings.item(modelData)
                    bordered: true
                    focusable: true
                    selected: root.cfg.powerProfile === modelData.key
                    onClicked: root.backend.setSetting("powerProfile", modelData.key)
                }
            }
        }
        PetLabel {
            width: parent.width
            font.pixelSize: 11
            opacity: .6
            text: strings.t("power.help")
        }
        PetLabel {
            text: strings.t("setting.personality")
            font.bold: true
        }
        Flow {
            width: parent.width
            spacing: 6
            Repeater {
                model: [
                    {
                        key: "calm",
                        text: strings.t("personality.calm")
                    },
                    {
                        key: "curious",
                        text: strings.t("personality.curious")
                    },
                    {
                        key: "playful",
                        text: strings.t("personality.playful")
                    }
                ]
                delegate: Button {
                    required property var modelData
                    text: modelData.text
                    bordered: true
                    focusable: true
                    selected: root.cfg.personality === modelData.key
                    onClicked: root.backend.setSetting("personality", modelData.key)
                }
            }
        }
        PetLabel {
            width: parent.width
            opacity: .6
            font.pixelSize: 11
            text: root.cfg.personality === "calm" ? strings.t("personality.calm-help") : root.cfg.personality === "playful" ? strings.t("personality.playful-help") : strings.t("personality.curious-help")
        }
        PetLabel {
            text: strings.t("setting.monitor")
            font.bold: true
        }
        Flow {
            width: parent.width
            spacing: 6
            Button {
                text: strings.t("monitor.follow")
                bordered: true
                focusable: true
                selected: root.cfg.monitorMode === "follow"
                onClicked: root.backend.setMonitor("")
            }
            Repeater {
                model: root.backend.monitors
                delegate: Button {
                    required property var modelData
                    text: modelData.name
                    bordered: true
                    focusable: true
                    selected: root.cfg.monitorMode === "fixed" && root.cfg.monitor === modelData.name
                    onClicked: root.backend.setMonitor(modelData.name)
                }
            }
        }
        PetLabel {
            width: parent.width
            text: strings.t("monitor.help")
            font.pixelSize: 11
            opacity: .6
        }
        PetLabel {
            width: parent.width
            font.pixelSize: 11
            opacity: .65
            text: {
                var f = root.backend.profile.favorites[root.backend.monitorName];
                return !f ? strings.t("favorite.none") : f.edge === "window" && f.app ? strings.t("favorite.window").arg(f.app) : strings.t("favorite.floor");
            }
        }
        PetSettingRow {
            label: strings.t("setting.speed")
            detail: strings.t("speed.help")
            NumberField {
                value: root.cfg.speed
                from: 25
                to: 180
                stepSize: 5
                fieldWidth: 105
                onModified: function (v) {
                    root.backend.setSetting("speed", v);
                }
            }
        }
        Row {
            spacing: 6
            PetAction {
                actionName: "remember"
                text: strings.t("action.remember")
                bordered: true
                focusable: true
                fontSize: 12
            }
            PetAction {
                actionName: "reset"
                text: strings.t("action.reset")
                bordered: true
                focusable: true
                fontSize: 12
            }
        }
        Repeater {
            model: [
                {
                    key: "walkOnWindows",
                    text: strings.t("setting.windows"),
                    detail: strings.t("windows.help")
                },
                {
                    key: "followCursor",
                    text: strings.t("setting.follow-cursor"),
                    detail: strings.t("follow-cursor.help")
                },
                {
                    key: "cursorReactions",
                    text: strings.t("setting.cursor"),
                    detail: strings.t("cursor.help")
                },
                {
                    key: "sound",
                    text: strings.t("setting.sound"),
                    detail: strings.t("sound.help")
                },
                {
                    key: "bubbles",
                    text: strings.t("setting.bubbles"),
                    detail: strings.t("bubbles.help")
                },
                {
                    key: "hideFullscreen",
                    text: strings.t("setting.fullscreen"),
                    detail: strings.t("fullscreen.help")
                },
                {
                    key: "reducedMotion",
                    text: strings.t("quiet.reduced"),
                    detail: strings.t("reduced.help")
                }
            ]
            delegate: PetSettingRow {
                id: toggleRow
                required property var modelData
                label: modelData.text
                detail: modelData.detail
                ToggleSwitch {
                    checked: root.cfg[toggleRow.modelData.key]
                    onToggled: root.backend.setSetting(toggleRow.modelData.key, !root.cfg[toggleRow.modelData.key])
                }
            }
        }
    }
}
