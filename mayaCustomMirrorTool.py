# -*- coding: utf-8 -*-
import maya.cmds as cmds
import json


ALL_ATTRS = [
    "translateX", "translateY", "translateZ",
    "rotateX", "rotateY", "rotateZ"
]

WINDOW_NAME = "AnimMirrorCustomUI"
RULE_ROWS = []
RULE_COLUMN = "ruleRowsColumn"

DEFAULT_RULES = [
    {"keywords": "COG, Chest, Pelvis", "attrs": "translateX, rotateY, rotateZ", "mode": u"通常反転"},
    {"keywords": "Hand, Foot", "attrs": "translateX, translateY, translateZ, rotateY, rotateZ", "mode": u"左右反転"},
    {"keywords": "Finger, Shoulder, Toe", "attrs": "rotateY, rotateZ", "mode": u"左右反転"},
    {"keywords": "upVector, LegVector", "attrs": "translateX", "mode": u"左右反転"},
]


def get_short_name(node):
    return node.split("|")[-1]


def remove_namespace(node):
    short_name = get_short_name(node)
    if ":" in short_name:
        return short_name.split(":")[-1]
    return short_name


def get_namespace(node):
    short_name = get_short_name(node)
    if ":" in short_name:
        return short_name.rsplit(":", 1)[0] + ":"
    return ""


def split_text(text):
    return [word.strip() for word in text.split(",") if word.strip()] if text else []


def get_transform(node):
    if not cmds.objExists(node):
        return None

    if cmds.nodeType(node) == "transform":
        return node

    parent = cmds.listRelatives(node, parent=True, fullPath=True) or []
    return parent[0] if parent else None


def is_target_rig(node):
    shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True, fullPath=True) or []
    for shape in shapes:
        if cmds.nodeType(shape) in ["nurbsCurve", "mesh", "nurbsSurface"]:
            return True
    return False


def get_selected_rigs():
    selected = cmds.ls(sl=True, long=True) or []

    if not selected:
        cmds.warning(u"オブジェクトを選択してください")
        return []

    rigs = []
    exists = set()

    for node in selected:
        transform = get_transform(node)
        if not transform:
            continue

        if not is_target_rig(transform):
            continue

        if transform in exists:
            continue

        exists.add(transform)
        rigs.append(transform)

    if not rigs:
        cmds.warning(u"NURBS Curve / Mesh / NURBS Surface のリグを選択してください")

    return rigs


def contains_keyword(node, keywords):
    original_name = remove_namespace(node)
    return any(keyword in original_name for keyword in keywords)


def is_attr_available(node, attr):
    plug = node + "." + attr

    if not cmds.objExists(plug):
        return False

    try:
        return not cmds.getAttr(plug, lock=True)
    except:
        return False


def get_playback_range():
    start = int(cmds.playbackOptions(q=True, min=True))
    end = int(cmds.playbackOptions(q=True, max=True))
    return start, end


def find_node_by_short_name(short_name):
    result = cmds.ls(short_name, type="transform", long=True) or []
    if result:
        return result[0]

    for node in cmds.ls(type="transform", long=True) or []:
        if get_short_name(node) == short_name:
            return node

    return None


def get_mirror_object(obj):
    namespace = get_namespace(obj)
    original_name = remove_namespace(obj)

    if "_L" in original_name:
        mirror_name = original_name.replace("_L", "_R", 1)
    elif "_R" in original_name:
        mirror_name = original_name.replace("_R", "_L", 1)
    else:
        return None

    return find_node_by_short_name(namespace + mirror_name)


def copy_animation_data(obj, attrs, start, end):
    anim_data = {}

    for attr in attrs:
        if not cmds.objExists(obj + "." + attr):
            continue

        anim_data[attr] = []

        for frame in range(start, end + 1):
            cmds.currentTime(frame, edit=True)
            try:
                anim_data[attr].append((frame, cmds.getAttr(obj + "." + attr)))
            except:
                pass

    return anim_data


def delete_keys(obj, attrs, start, end):
    for attr in attrs:
        if not is_attr_available(obj, attr):
            continue
        try:
            cmds.cutKey(obj, attribute=attr, time=(start, end), option="keys")
        except:
            pass


def paste_animation_data(obj, anim_data, invert_attrs):
    for attr, keys in anim_data.items():
        if not is_attr_available(obj, attr):
            continue

        for frame, value in keys:
            cmds.currentTime(frame, edit=True)
            paste_value = value * -1.0 if attr in invert_attrs else value

            try:
                cmds.setAttr(obj + "." + attr, paste_value)

                if attr in ["rotateX", "rotateY", "rotateZ"]:
                    cmds.setKeyframe(obj, attribute=attr, minimizeRotation=True)
                else:
                    cmds.setKeyframe(obj, attribute=attr)
            except:
                pass


def set_rotation_curves_quaternion(obj):
    for attr in ["rotateX", "rotateY", "rotateZ"]:
        plug = obj + "." + attr

        anim_curves = cmds.listConnections(
            plug,
            source=True,
            destination=False,
            type="animCurve"
        ) or []

        for curve in anim_curves:
            try:
                cmds.rotationInterpolation(curve, conversion="quaternionSlerp")
            except:
                pass


def create_temp_locator_from_anim(obj, anim_data):
    locator = cmds.spaceLocator(name=remove_namespace(obj) + "_Locator")[0]
    print("Create temp locator : {}".format(locator))

    paste_animation_data(locator, anim_data, invert_attrs=[])

    return locator


def mirror_single_rig(obj, start, end, invert_attrs):
    anim_data = copy_animation_data(obj, ALL_ATTRS, start, end)
    delete_keys(obj, ALL_ATTRS, start, end)
    paste_animation_data(obj, anim_data, invert_attrs)
    set_rotation_curves_quaternion(obj)


def mirror_pair_rig(obj, start, end, invert_attrs):
    mirror_obj = get_mirror_object(obj)

    if not mirror_obj:
        cmds.warning(u"{} の対になるオブジェクトが見つかりません".format(obj))
        return

    obj_name = remove_namespace(obj)

    if "_L" in obj_name:
        left_obj = obj
        right_obj = mirror_obj
    elif "_R" in obj_name:
        left_obj = mirror_obj
        right_obj = obj
    else:
        return

    left_data = copy_animation_data(left_obj, ALL_ATTRS, start, end)
    right_data = copy_animation_data(right_obj, ALL_ATTRS, start, end)

    temp_locator = create_temp_locator_from_anim(left_obj, left_data)
    locator_data = copy_animation_data(temp_locator, ALL_ATTRS, start, end)

    delete_keys(left_obj, ALL_ATTRS, start, end)
    delete_keys(right_obj, ALL_ATTRS, start, end)

    paste_animation_data(left_obj, right_data, invert_attrs)
    paste_animation_data(right_obj, locator_data, invert_attrs)

    set_rotation_curves_quaternion(left_obj)
    set_rotation_curves_quaternion(right_obj)

    if cmds.objExists(temp_locator):
        cmds.delete(temp_locator)


def get_ui_rules():
    rules = []

    for row in RULE_ROWS:
        if not cmds.rowLayout(row["layout"], exists=True):
            continue

        keyword_text = cmds.textField(row["keyword"], q=True, text=True)
        attr_text = cmds.textField(row["attrs"], q=True, text=True)
        mode_text = cmds.optionMenu(row["mode"], q=True, value=True)

        keywords = split_text(keyword_text)
        invert_attrs = split_text(attr_text)

        if keywords and invert_attrs:
            rules.append({
                "keywords": keywords,
                "invert_attrs": invert_attrs,
                "mode": mode_text
            })

    return rules


def get_ui_rules_for_save():
    save_data = []

    for row in RULE_ROWS:
        if not cmds.rowLayout(row["layout"], exists=True):
            continue

        save_data.append({
            "keywords": cmds.textField(row["keyword"], q=True, text=True),
            "attrs": cmds.textField(row["attrs"], q=True, text=True),
            "mode": cmds.optionMenu(row["mode"], q=True, value=True)
        })

    return save_data


def clear_rule_rows():
    global RULE_ROWS

    for row in list(RULE_ROWS):
        if cmds.rowLayout(row["layout"], exists=True):
            cmds.deleteUI(row["layout"])

    RULE_ROWS = []


def load_rules_to_ui(rules):
    clear_rule_rows()

    for rule in rules:
        add_rule_row(
            keyword_text=rule.get("keywords", ""),
            attr_text=rule.get("attrs", ""),
            mode_text=rule.get("mode", u"左右反転")
        )


def save_settings(*args):
    file_path = cmds.fileDialog2(
        fileMode=0,
        caption=u"設定を保存",
        fileFilter="JSON Files (*.json)"
    )

    if not file_path:
        return

    data = {
        "animMirrorSettings": get_ui_rules_for_save()
    }

    try:
        with open(file_path[0], "w") as f:
            json.dump(data, f, indent=4)

        cmds.confirmDialog(title=u"保存完了", message=u"設定を保存しました。", button=["OK"])

    except Exception as e:
        cmds.warning(u"設定の保存に失敗しました: {}".format(e))


def import_settings(*args):
    file_path = cmds.fileDialog2(
        fileMode=1,
        caption=u"設定を読み込み",
        fileFilter="JSON Files (*.json)"
    )

    if not file_path:
        return

    try:
        with open(file_path[0], "r") as f:
            data = json.load(f)

        rules = data.get("animMirrorSettings", [])

        if not rules:
            cmds.warning(u"読み込める設定がありません")
            return

        load_rules_to_ui(rules)

        cmds.confirmDialog(title=u"読み込み完了", message=u"設定を読み込みました。", button=["OK"])

    except Exception as e:
        cmds.warning(u"設定の読み込みに失敗しました: {}".format(e))


def execute_anim_mirror_from_ui(*args):
    rigs = get_selected_rigs()

    if not rigs:
        return

    rules = get_ui_rules()

    if not rules:
        cmds.warning(u"Keyword と INVERT_ATTRS を入力してください")
        return

    start, end = get_playback_range()
    current_time = cmds.currentTime(q=True)
    processed_pairs = set()

    cmds.undoInfo(openChunk=True)

    try:
        cmds.refresh(suspend=True)

        for rule in rules:
            for obj in rigs:
                if not contains_keyword(obj, rule["keywords"]):
                    continue

                if rule["mode"] == u"通常反転":
                    mirror_single_rig(obj, start, end, rule["invert_attrs"])

                elif rule["mode"] == u"左右反転":
                    mirror_obj = get_mirror_object(obj)

                    if not mirror_obj:
                        cmds.warning(u"{} の対になるオブジェクトが見つかりません".format(obj))
                        continue

                    pair_key = tuple(sorted([get_short_name(obj), get_short_name(mirror_obj)]))

                    if pair_key in processed_pairs:
                        continue

                    processed_pairs.add(pair_key)
                    mirror_pair_rig(obj, start, end, rule["invert_attrs"])

        cmds.currentTime(current_time, edit=True)

        cmds.confirmDialog(
            title=u"完了",
            message=u"アニメーションを反転しました。",
            button=["OK"]
        )

    except Exception as e:
        cmds.warning(u"反転処理中にエラーが発生しました: {}".format(e))
        cmds.currentTime(current_time, edit=True)

    finally:
        cmds.refresh(suspend=False)
        cmds.undoInfo(closeChunk=True)


def delete_rule_row(row_layout):
    for row in list(RULE_ROWS):
        if row["layout"] == row_layout:
            RULE_ROWS.remove(row)
            break

    if cmds.rowLayout(row_layout, exists=True):
        cmds.deleteUI(row_layout)


def add_rule_row(keyword_text="", attr_text="", mode_text=u"左右反転", *args):
    row_layout = cmds.rowLayout(
        numberOfColumns=4,
        adjustableColumn=2,
        columnWidth4=(220, 340, 110, 60),
        columnAlign4=("left", "left", "left", "center"),
        parent=RULE_COLUMN
    )

    keyword_field = cmds.textField(text=keyword_text, annotation=u"例：Hand, Foot")
    attrs_field = cmds.textField(text=attr_text, annotation=u"例：translateX, translateY, rotateZ")

    mode_menu = cmds.optionMenu()
    cmds.menuItem(label=u"通常反転")
    cmds.menuItem(label=u"左右反転")
    cmds.optionMenu(mode_menu, e=True, value=mode_text)

    delete_button = cmds.button(
        label=u"削除",
        command=lambda *x: delete_rule_row(row_layout)
    )

    RULE_ROWS.append({
        "layout": row_layout,
        "keyword": keyword_field,
        "attrs": attrs_field,
        "mode": mode_menu,
        "delete": delete_button
    })


def create_anim_mirror_ui():
    global RULE_ROWS
    RULE_ROWS = []

    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    window = cmds.window(
        WINDOW_NAME,
        title=u"Anim Mirror Custom Tool",
        sizeable=True,
        widthHeight=(820, 450)
    )

    main_layout = cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=8,
        columnOffset=("both", 12)
    )

    cmds.text(
        label=u"Keyword と INVERT_ATTRS を設定して、選択リグのアニメーションを反転します。",
        align="left"
    )

    cmds.separator(height=8, style="in")

    cmds.rowLayout(
        numberOfColumns=4,
        columnWidth4=(220, 340, 110, 60),
        columnAlign4=("left", "left", "left", "center")
    )
    cmds.text(label=u"Keyword")
    cmds.text(label=u"INVERT_ATTRS")
    cmds.text(label=u"処理タイプ")
    cmds.text(label="")
    cmds.setParent("..")

    cmds.columnLayout(RULE_COLUMN, adjustableColumn=True, rowSpacing=4)

    for rule in DEFAULT_RULES:
        add_rule_row(
            keyword_text=rule["keywords"],
            attr_text=rule["attrs"],
            mode_text=rule["mode"]
        )

    cmds.setParent(main_layout)

    cmds.rowLayout(
        numberOfColumns=1,
        columnWidth1=100,
        columnAlign1="left"
    )

    cmds.button(
        label=u"追加",
        width=90,
        command=add_rule_row
    )

    cmds.setParent(main_layout)

    cmds.separator(height=8, style="in")

    cmds.rowLayout(
        numberOfColumns=3,
        columnWidth3=(50, 50, 180),
        columnAlign3=("left", "left", "left")
    )

    cmds.iconTextButton(
        style="iconOnly",
        image1="save.png",
        width=36,
        height=32,
        annotation=u"設定保存",
        command=save_settings
    )

    cmds.iconTextButton(
        style="iconOnly",
        image1="openScript.png",
        width=36,
        height=32,
        annotation=u"設定読込",
        command=import_settings
    )

    cmds.button(
        label=u"反転実行",
        width=160,
        height=34,
        backgroundColor=(0.55, 0.85, 0.55),
        command=execute_anim_mirror_from_ui
    )

    cmds.setParent(main_layout)

    cmds.separator(height=8, style="none")

    cmds.text(
        label=u"入力例：Keyword = Hand, Foot / INVERT_ATTRS = translateX, translateY, translateZ, rotateY, rotateZ",
        align="left"
    )

    cmds.showWindow(window)


create_anim_mirror_ui()