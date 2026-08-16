# -*- coding: utf-8 -*-

import maya.cmds as cmds
import random


# ==================================================
# Add Noise Animation
# ==================================================
def add_noise_animation(*args):

    # 選択ノードを取得
    sel = cmds.ls(sl=True)

    if not sel:
        cmds.warning("Please select a node.")
        return

    # 元ツールと同じく、最初に選択されたノードを対象にする
    node = sel[0]

    # --------------------------------------------------
    # Min / Max
    # --------------------------------------------------
    try:
        min_val = float(
            cmds.textField(
                "noiseMinField",
                q=True,
                text=True
            )
        )

        max_val = float(
            cmds.textField(
                "noiseMaxField",
                q=True,
                text=True
            )
        )

    except Exception:
        cmds.warning("Min / Max value is invalid.")
        return

    # Min > Max の場合は入れ替える
    if min_val > max_val:
        min_val, max_val = max_val, min_val

    # --------------------------------------------------
    # Start / End
    # --------------------------------------------------
    start = cmds.intField(
        "noiseStartField",
        q=True,
        value=True
    )

    end = cmds.intField(
        "noiseEndField",
        q=True,
        value=True
    )

    if start > end:
        cmds.warning("Start frame must be less than End frame.")
        return

    # --------------------------------------------------
    # Attribute
    # --------------------------------------------------
    all_attrs = [
        "translateX",
        "translateY",
        "translateZ",
        "rotateX",
        "rotateY",
        "rotateZ"
    ]

    attrs = []

    for attr in all_attrs:

        checkbox_name = "noiseCheck_{0}".format(attr)

        if cmds.checkBox(
            checkbox_name,
            q=True,
            value=True
        ):
            attrs.append(attr)

    if not attrs:
        cmds.warning("Please select at least one attribute.")
        return

    # --------------------------------------------------
    # Add Noise
    # --------------------------------------------------
    for attr in attrs:

        # Attributeが存在するか確認
        if not cmds.attributeQuery(
            attr,
            node=node,
            exists=True
        ):
            continue

        # Start ～ Endまで1フレームずつキーを作成
        for frame in range(start, end + 1):

            noise_value = random.uniform(
                min_val,
                max_val
            )

            cmds.setKeyframe(
                node,
                attribute=attr,
                time=frame,
                value=noise_value
            )

    # --------------------------------------------------
    # Finish Message
    # --------------------------------------------------
    cmds.inViewMessage(
        amg="<hl>Noise</hl> animation added.",
        pos="midCenter",
        fade=True
    )


# ==================================================
# UI
# ==================================================
def noise_animation_ui():

    window_name = "NoiseAnimationTool"

    # 既にUIが存在していたら削除
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    # Window
    cmds.window(
        window_name,
        title="Noise Animation Tool",
        widthHeight=(430, 230),
        sizeable=False
    )

    # Main Layout
    cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=8,
        columnOffset=("both", 20)
    )

    cmds.separator(
        height=5,
        style="none"
    )

    # ==================================================
    # Min / Max
    # ==================================================
    cmds.text(
        label="Noise Range",
        align="left",
        font="boldLabelFont"
    )

    cmds.rowLayout(
        numberOfColumns=4,
        columnWidth4=(45, 80, 45, 80),
        height=25
    )

    cmds.text(
        label="Min:",
        align="left"
    )

    cmds.textField(
        "noiseMinField",
        text="1",
        width=70
    )

    cmds.text(
        label="Max:",
        align="left"
    )

    cmds.textField(
        "noiseMaxField",
        text="5",
        width=70
    )

    cmds.setParent("..")

    # ==================================================
    # Start / End
    # ==================================================
    cmds.text(
        label="Frame Range",
        align="left",
        font="boldLabelFont"
    )

    cmds.rowLayout(
        numberOfColumns=4,
        columnWidth4=(45, 80, 45, 80),
        height=25
    )

    cmds.text(
        label="Start:",
        align="left"
    )

    cmds.intField(
        "noiseStartField",
        value=int(cmds.currentTime(q=True)),
        width=70
    )

    cmds.text(
        label="End:",
        align="left"
    )

    cmds.intField(
        "noiseEndField",
        value=int(
            cmds.playbackOptions(
                q=True,
                max=True
            )
        ),
        width=70
    )

    cmds.setParent("..")

    # ==================================================
    # Attributes
    # ==================================================
    cmds.text(
        label="Attributes",
        align="left",
        font="boldLabelFont"
    )

    cmds.rowLayout(
        numberOfColumns=6,
        columnWidth6=(
            60,
            60,
            60,
            60,
            60,
            60
        ),
        height=25
    )

    attrs = [
        ("translateX", "Trs X"),
        ("translateY", "Trs Y"),
        ("translateZ", "Trs Z"),
        ("rotateX", "Rot X"),
        ("rotateY", "Rot Y"),
        ("rotateZ", "Rot Z")
    ]

    for attr, label in attrs:

        cmds.checkBox(
            "noiseCheck_{0}".format(attr),
            label=label,
            value=False
        )

    cmds.setParent("..")

    cmds.separator(
        height=1,
        style="none"
    )

    # ==================================================
    # Add Noise Button
    # ==================================================
    cmds.button(
        label="Add Noise",
        height=35,
        command=add_noise_animation
    )

    cmds.separator(
        height=5,
        style="none"
    )

    cmds.showWindow(window_name)


# ==================================================
# Run
# ==================================================
noise_animation_ui()