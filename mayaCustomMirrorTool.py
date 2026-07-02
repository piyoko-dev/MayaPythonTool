# -*- coding: utf-8 -*-
import maya.cmds as cmds


MODE_SINGLE = "Single"
MODE_PAIR = "Pair"

WINDOW_NAME = "AnimMirrorV3_UI"
RULE_COLUMN = "animMirrorRuleColumn"
FINGER_CHECKBOX = "animMirrorFingerAliasCheckBox"
RULE_ROWS = []

ALL_ATTRS = [
    "translateX", "translateY", "translateZ",
    "rotateX", "rotateY", "rotateZ"
]

FINGER_ALIAS_KEYWORDS = [
    "Finger", "Index", "Middle", "Ring", "Pinky", "Little", "Thumb"
]

ATTR_ALIAS = {
    "tx": "translateX",
    "ty": "translateY",
    "tz": "translateZ",
    "rx": "rotateX",
    "ry": "rotateY",
    "rz": "rotateZ",
}

DEFAULT_RULES = [
    {"keywords": "COG, Chest, Pelvis", "attrs": "translateX, rotateY, rotateZ", "mode": MODE_SINGLE},
    {"keywords": "Hand", "attrs": "translateX, translateY, translateZ, rotateY, rotateZ", "mode": MODE_PAIR},
    {"keywords": "Foot", "attrs": "translateX, rotateY, rotateZ", "mode": MODE_PAIR},
    {"keywords": "Finger", "attrs": "rotateY, rotateZ", "mode": MODE_PAIR},
    {"keywords": "Arm_Upv, Leg_Upv", "attrs": "translateX", "mode": MODE_PAIR},
]


def log(msg):
    try:
        print(str(msg))
    except:
        print("Log failed.")


def short_name(node):
    return node.split("|")[-1]


def remove_namespace(node):
    name = short_name(node)
    if ":" in name:
        return name.split(":")[-1]
    return name


def get_namespace(node):
    name = short_name(node)
    if ":" in name:
        return name.rsplit(":", 1)[0] + ":"
    return ""


def split_text(text):
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def normalize_attr(attr):
    return ATTR_ALIAS.get(attr, attr)


def normalize_attrs(attrs):
    result = []
    for attr in attrs:
        attr = normalize_attr(attr)
        if attr not in result:
            result.append(attr)
    return result


def get_transform(node):
    if not cmds.objExists(node):
        return None

    if cmds.nodeType(node) == "transform":
        return node

    parent = cmds.listRelatives(node, parent=True, fullPath=True) or []
    if parent:
        return parent[0]

    return None


def get_selected_transforms():
    selected = cmds.ls(sl=True, long=True) or []

    if not selected:
        cmds.warning("Please select objects.")
        return []

    result = []
    exists = set()

    for node in selected:
        transform = get_transform(node)

        if not transform:
            continue

        if transform in exists:
            continue

        exists.add(transform)
        result.append(transform)

    return result


def is_finger_alias_enabled():
    if cmds.checkBox(FINGER_CHECKBOX, exists=True):
        return cmds.checkBox(FINGER_CHECKBOX, q=True, value=True)
    return False


def expand_keywords(keywords):
    if not is_finger_alias_enabled():
        return keywords

    result = []

    for keyword in keywords:
        if keyword == "Finger":
            for alias in FINGER_ALIAS_KEYWORDS:
                if alias not in result:
                    result.append(alias)
        else:
            if keyword not in result:
                result.append(keyword)

    return result


def contains_keyword(node, keywords):
    name = remove_namespace(node)
    keywords = expand_keywords(keywords)

    for keyword in keywords:
        if keyword in name:
            return True

    return False


def attr_exists(node, attr):
    return cmds.objExists(node + "." + attr)


def attr_is_locked(node, attr):
    plug = node + "." + attr

    if not cmds.objExists(plug):
        return True

    try:
        return cmds.getAttr(plug, lock=True)
    except:
        return True


def attr_is_available(node, attr):
    return attr_exists(node, attr) and not attr_is_locked(node, attr)


def get_playback_range():
    start = int(cmds.playbackOptions(q=True, min=True))
    end = int(cmds.playbackOptions(q=True, max=True))
    return start, end


def find_node_by_short_name(name):
    found = cmds.ls(name, type="transform", long=True) or []
    if found:
        return found[0]

    for node in cmds.ls(type="transform", long=True) or []:
        if short_name(node) == name:
            return node

    return None


def get_lr_side(node):
    base = remove_namespace(node)

    if "_L" in base:
        return "L"
    if "_R" in base:
        return "R"
    if base.startswith("L_"):
        return "L"
    if base.startswith("R_"):
        return "R"

    return None


def get_mirror_object(node):
    ns = get_namespace(node)
    base = remove_namespace(node)

    if "_L" in base:
        mirror_base = base.replace("_L", "_R", 1)
    elif "_R" in base:
        mirror_base = base.replace("_R", "_L", 1)
    elif base.startswith("L_"):
        mirror_base = base.replace("L_", "R_", 1)
    elif base.startswith("R_"):
        mirror_base = base.replace("R_", "L_", 1)
    else:
        log("No L/R token : " + base)
        return None

    mirror_name = ns + mirror_base
    mirror_node = find_node_by_short_name(mirror_name)

    if mirror_node:
        log("Mirror found : " + short_name(node) + " -> " + short_name(mirror_node))
    else:
        log("Mirror not found : " + short_name(node) + " -> " + mirror_name)

    return mirror_node


def get_anim_curve(node, attr):
    plug = node + "." + attr

    if not cmds.objExists(plug):
        return None

    curves = cmds.listConnections(
        plug,
        source=True,
        destination=False,
        type="animCurve"
    ) or []

    if not curves:
        return None

    return curves[0]


def duplicate_anim_curve(node, attr):
    curve = get_anim_curve(node, attr)

    if not curve:
        return None

    try:
        dup = cmds.duplicate(
            curve,
            name=remove_namespace(node) + "_" + attr + "_mirrorTmp#"
        )[0]

        log("Duplicated animCurve : " + curve + " -> " + dup)
        return dup

    except Exception as e:
        log("Failed to duplicate animCurve : " + short_name(node) + "." + attr)
        log(e)

    return None


def duplicate_node_anim_curves(node, attrs):
    result = {}

    for attr in attrs:
        attr = normalize_attr(attr)

        if not attr_exists(node, attr):
            continue

        dup_curve = duplicate_anim_curve(node, attr)

        if dup_curve:
            result[attr] = dup_curve

    return result


def disconnect_anim_curve(node, attr):
    curve = get_anim_curve(node, attr)

    if not curve:
        return

    plug = node + "." + attr
    source_plug = curve + ".output"

    try:
        if cmds.isConnected(source_plug, plug):
            cmds.disconnectAttr(source_plug, plug)
            log("Disconnected : " + source_plug + " -> " + plug)
    except:
        pass


def delete_anim_curve(node, attr):
    curve = get_anim_curve(node, attr)

    if not curve:
        return

    disconnect_anim_curve(node, attr)

    try:
        if cmds.objExists(curve):
            cmds.delete(curve)
            log("Deleted old animCurve : " + curve)
    except:
        pass


def delete_anim_curves_on_attrs(node, attrs):
    for attr in attrs:
        attr = normalize_attr(attr)

        if not attr_is_available(node, attr):
            log("Skip delete locked/missing : " + short_name(node) + "." + attr)
            continue

        delete_anim_curve(node, attr)


def connect_anim_curve(curve, target, attr):
    if not curve:
        return False

    if not attr_is_available(target, attr):
        log("Skip connect locked/missing : " + short_name(target) + "." + attr)
        return False

    source_plug = curve + ".output"
    target_plug = target + "." + attr

    try:
        cmds.connectAttr(source_plug, target_plug, force=True)
        log("Connected : " + source_plug + " -> " + short_name(target) + "." + attr)
        return True
    except Exception as e:
        log("Failed to connect animCurve : " + curve + " -> " + short_name(target) + "." + attr)
        log(e)

    return False


def scale_anim_curve(curve, start, end, scale_value):
    if not curve or not cmds.objExists(curve):
        return

    try:
        cmds.scaleKey(
            curve,
            time=(start, end),
            valueScale=scale_value,
            valuePivot=0.0
        )
        log("Scaled curve : " + curve)

    except Exception as e:
        log("scale animCurve failed : " + curve)
        log(e)


def set_rotation_interpolation(node):
    for attr in ["rotateX", "rotateY", "rotateZ"]:
        plug = node + "." + attr

        curves = cmds.listConnections(
            plug,
            source=True,
            destination=False,
            type="animCurve"
        ) or []

        for curve in curves:
            try:
                cmds.rotationInterpolation(curve, conversion="quaternionSlerp")
            except:
                pass


def mirror_single(node, invert_attrs, start, end):
    log("Single start : " + short_name(node))

    invert_attrs = normalize_attrs(invert_attrs)
    curves = duplicate_node_anim_curves(node, invert_attrs)

    if not curves:
        log("No animCurves : " + short_name(node))
        return False

    try:
        delete_anim_curves_on_attrs(node, curves.keys())

        for attr, curve in curves.items():
            scale_anim_curve(curve, start, end, -1.0)
            connect_anim_curve(curve, node, attr)

        set_rotation_interpolation(node)
        log("Single complete : " + short_name(node))
        return True

    except Exception as e:
        log("Single failed : " + short_name(node))
        log(e)

    return False


def mirror_pair(node, invert_attrs, start, end):
    side = get_lr_side(node)

    if side != "L":
        log("Skip non-left pair node : " + short_name(node))
        return False

    mirror_node = get_mirror_object(node)

    if not mirror_node:
        return False

    left_node = node
    right_node = mirror_node

    log("Pair start")
    log("Left  : " + short_name(left_node))
    log("Right : " + short_name(right_node))

    attrs = normalize_attrs(ALL_ATTRS)
    invert_attrs = normalize_attrs(invert_attrs)

    left_curves = duplicate_node_anim_curves(left_node, attrs)
    right_curves = duplicate_node_anim_curves(right_node, attrs)

    all_target_attrs = []

    for attr in attrs:
        if attr in left_curves or attr in right_curves:
            all_target_attrs.append(attr)

    if not all_target_attrs:
        log("No animCurves in pair.")
        return False

    log("Swap attrs : " + ", ".join(all_target_attrs))

    try:
        delete_anim_curves_on_attrs(left_node, all_target_attrs)
        delete_anim_curves_on_attrs(right_node, all_target_attrs)

        for attr in invert_attrs:
            if attr in right_curves:
                scale_anim_curve(right_curves[attr], start, end, -1.0)

            if attr in left_curves:
                scale_anim_curve(left_curves[attr], start, end, -1.0)

        for attr in all_target_attrs:
            if attr in right_curves:
                connect_anim_curve(right_curves[attr], left_node, attr)

        for attr in all_target_attrs:
            if attr in left_curves:
                connect_anim_curve(left_curves[attr], right_node, attr)

        set_rotation_interpolation(left_node)
        set_rotation_interpolation(right_node)

        log("Pair complete")
        return True

    except Exception as e:
        log("Pair failed.")
        log(e)

    return False


def get_ui_rules():
    rules = []

    for row in RULE_ROWS:
        if not cmds.rowLayout(row["layout"], exists=True):
            continue

        keywords_text = cmds.textField(row["keywords"], q=True, text=True)
        attrs_text = cmds.textField(row["attrs"], q=True, text=True)
        mode_text = cmds.optionMenu(row["mode"], q=True, value=True)

        keywords = split_text(keywords_text)
        invert_attrs = normalize_attrs(split_text(attrs_text))

        if not keywords or not invert_attrs:
            continue

        rules.append({
            "keywords": keywords,
            "invert_attrs": invert_attrs,
            "mode": mode_text
        })

    return rules


def execute_from_ui(*args):
    nodes = get_selected_transforms()

    if not nodes:
        return

    rules = get_ui_rules()

    if not rules:
        cmds.warning("Please input rules.")
        return

    start, end = get_playback_range()

    log("AnimMirror V3 start")
    log("Frame range : " + str(start) + " - " + str(end))
    log("Selected count : " + str(len(nodes)))

    processed_count = 0

    cmds.undoInfo(openChunk=True)

    try:
        cmds.refresh(suspend=True)

        for rule in rules:
            keywords = rule["keywords"]
            invert_attrs = rule["invert_attrs"]
            mode = rule["mode"]

            log("----- Rule -----")
            log("Keywords : " + ", ".join(keywords))
            log("Invert attrs : " + ", ".join(invert_attrs))
            log("Mode : " + mode)

            for node in nodes:
                if not contains_keyword(node, keywords):
                    continue

                log("Matched : " + short_name(node))

                if mode == MODE_SINGLE:
                    if mirror_single(node, invert_attrs, start, end):
                        processed_count += 1

                elif mode == MODE_PAIR:
                    if mirror_pair(node, invert_attrs, start, end):
                        processed_count += 1

        if processed_count == 0:
            cmds.warning("No target rigs were processed.")
        else:
            cmds.confirmDialog(
                title="Complete",
                message="Animation mirror completed. Count: " + str(processed_count),
                button=["OK"]
            )

    except Exception as e:
        cmds.warning("Mirror failed. Check Script Editor.")
        log(e)

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


def add_rule_row(keyword_text="", attr_text="", mode_text=MODE_PAIR, *args):
    row_layout = cmds.rowLayout(
        numberOfColumns=4,
        columnWidth4=(220, 360, 90, 60),
        adjustableColumn=2,
        columnAlign4=("left", "left", "left", "center"),
        parent=RULE_COLUMN
    )

    keyword_field = cmds.textField(
        text=keyword_text,
        annotation="Example: Hand, Foot"
    )

    attr_field = cmds.textField(
        text=attr_text,
        annotation="Example: translateX, translateY, rotateZ"
    )

    mode_menu = cmds.optionMenu()
    cmds.menuItem(label=MODE_SINGLE)
    cmds.menuItem(label=MODE_PAIR)
    cmds.optionMenu(mode_menu, e=True, value=mode_text)

    delete_button = cmds.button(
        label="Delete",
        command=lambda *x: delete_rule_row(row_layout)
    )

    RULE_ROWS.append({
        "layout": row_layout,
        "keywords": keyword_field,
        "attrs": attr_field,
        "mode": mode_menu,
        "delete": delete_button
    })


def create_ui():
    global RULE_ROWS
    RULE_ROWS = []

    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    window = cmds.window(
        WINDOW_NAME,
        title="Anim Mirror V3",
        sizeable=True,
        widthHeight=(820, 420)
    )

    main = cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=8,
        columnOffset=("both", 12)
    )

    cmds.text(
        label="Set keyword and invert attributes. Pair mode runs left side only.",
        align="left"
    )

    cmds.separator(height=8, style="in")

    cmds.rowLayout(
        numberOfColumns=4,
        columnWidth4=(220, 360, 90, 60),
        columnAlign4=("left", "left", "left", "center")
    )

    cmds.text(label="Keyword")
    cmds.text(label="INVERT_ATTRS")
    cmds.text(label="Mode")
    cmds.text(label="")

    cmds.setParent("..")

    cmds.columnLayout(
        RULE_COLUMN,
        adjustableColumn=True,
        rowSpacing=4
    )

    for rule in DEFAULT_RULES:
        add_rule_row(
            keyword_text=rule["keywords"],
            attr_text=rule["attrs"],
            mode_text=rule["mode"]
        )

    cmds.setParent(main)

    cmds.button(
        label="Add",
        width=90,
        command=add_rule_row
    )

    cmds.checkBox(
        FINGER_CHECKBOX,
        label="Treat Index / Thumb etc. as Finger",
        value=True
    )

    cmds.separator(height=8, style="in")

    cmds.button(
        label="Mirror Execute",
        width=160,
        height=34,
        backgroundColor=(0.55, 0.85, 0.55),
        command=execute_from_ui
    )

    cmds.text(
        label="Tip: Pair mode only executes nodes with _L or L_ names. R side is skipped.",
        align="left"
    )

    cmds.showWindow(window)


create_ui()