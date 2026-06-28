# -*- coding: utf-8 -*-
import maya.cmds as cmds


ALL_ATTRS = [
    "translateX", "translateY", "translateZ",
    "rotateX", "rotateY", "rotateZ"
]

GRP_A_KEYWORDS = ["COG", "Chest", "Pelvis"]
GRP_B_KEYWORDS = ["Hand", "Foot"]
GRP_C_KEYWORDS = ["Finger", "Shoulder", "Toe"]
GRP_D_KEYWORDS = ["upVector", "LegVector"]

GRP_A_INVERT_ATTRS = ["translateX", "rotateY", "rotateZ"]

GRP_B_INVERT_ATTRS = [
    "translateX", "translateY", "translateZ",
    "rotateY", "rotateZ"
]

GRP_C_INVERT_ATTRS = ["rotateY", "rotateZ"]
GRP_D_INVERT_ATTRS = ["translateX"]


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


def get_transform(node):
    if not cmds.objExists(node):
        return None

    if cmds.nodeType(node) == "transform":
        return node

    parent = cmds.listRelatives(node, parent=True, fullPath=True) or []
    if parent:
        return parent[0]

    return None


def is_target_rig(node):
    shapes = cmds.listRelatives(
        node,
        shapes=True,
        noIntermediate=True,
        fullPath=True
    ) or []

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

    for keyword in keywords:
        if keyword in original_name:
            return True

    return False


def is_attr_available(node, attr):
    plug = node + "." + attr

    if not cmds.objExists(plug):
        return False

    try:
        if cmds.getAttr(plug, lock=True):
            return False
    except:
        return False

    return True


def get_playback_range():
    start = int(cmds.playbackOptions(q=True, min=True))
    end = int(cmds.playbackOptions(q=True, max=True))
    return start, end


def find_node_by_short_name(short_name):
    result = cmds.ls(short_name, type="transform", long=True) or []

    if result:
        return result[0]

    all_transforms = cmds.ls(type="transform", long=True) or []

    for node in all_transforms:
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

    mirror_short_name = namespace + mirror_name
    mirror_obj = find_node_by_short_name(mirror_short_name)

    return mirror_obj


def copy_animation_data(obj, attrs, start, end):
    anim_data = {}

    for attr in attrs:
        if not cmds.objExists(obj + "." + attr):
            continue

        anim_data[attr] = []

        for frame in range(start, end + 1):
            cmds.currentTime(frame, edit=True)

            try:
                value = cmds.getAttr(obj + "." + attr)
                anim_data[attr].append((frame, value))
            except:
                pass

    return anim_data


def delete_keys(obj, attrs, start, end):
    for attr in attrs:
        if not is_attr_available(obj, attr):
            continue

        try:
            cmds.cutKey(
                obj,
                attribute=attr,
                time=(start, end),
                option="keys"
            )
        except:
            pass


def paste_animation_data(obj, anim_data, invert_attrs):
    for attr, keys in anim_data.items():
        if not is_attr_available(obj, attr):
            continue

        for frame, value in keys:
            cmds.currentTime(frame, edit=True)

            paste_value = value

            if attr in invert_attrs:
                paste_value = value * -1.0

            try:
                cmds.setAttr(obj + "." + attr, paste_value)

                if attr in ["rotateX", "rotateY", "rotateZ"]:
                    cmds.setKeyframe(
                        obj,
                        attribute=attr,
                        minimizeRotation=True
                    )
                else:
                    cmds.setKeyframe(
                        obj,
                        attribute=attr
                    )

            except:
                pass


def set_rotation_curves_quaternion(obj):
    rotate_attrs = ["rotateX", "rotateY", "rotateZ"]

    for attr in rotate_attrs:
        plug = obj + "." + attr

        anim_curves = cmds.listConnections(
            plug,
            source=True,
            destination=False,
            type="animCurve"
        ) or []

        for curve in anim_curves:
            try:
                cmds.rotationInterpolation(
                    curve,
                    conversion="quaternionSlerp"
                )
            except:
                pass


def create_temp_locator_from_anim(obj, anim_data):
    base_name = remove_namespace(obj)
    locator_name = base_name + "_Locator"

    locator = cmds.spaceLocator(name=locator_name)[0]

    print("Create temp locator : {}".format(locator))

    paste_animation_data(
        locator,
        anim_data,
        invert_attrs=[]
    )

    return locator


def mirror_single_rig(obj, start, end, invert_attrs):
    anim_data = copy_animation_data(
        obj,
        ALL_ATTRS,
        start,
        end
    )

    delete_keys(
        obj,
        ALL_ATTRS,
        start,
        end
    )

    paste_animation_data(
        obj,
        anim_data,
        invert_attrs
    )

    set_rotation_curves_quaternion(obj)


def mirror_pair_rig(obj, start, end, invert_attrs):
    mirror_obj = get_mirror_object(obj)

    if not mirror_obj:
        cmds.warning(
            u"{} の対になるオブジェクトが見つかりません".format(obj)
        )
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

    left_data = copy_animation_data(
        left_obj,
        ALL_ATTRS,
        start,
        end
    )

    right_data = copy_animation_data(
        right_obj,
        ALL_ATTRS,
        start,
        end
    )

    temp_locator = create_temp_locator_from_anim(
        left_obj,
        left_data
    )

    locator_data = copy_animation_data(
        temp_locator,
        ALL_ATTRS,
        start,
        end
    )

    delete_keys(
        left_obj,
        ALL_ATTRS,
        start,
        end
    )

    delete_keys(
        right_obj,
        ALL_ATTRS,
        start,
        end
    )

    paste_animation_data(
        left_obj,
        right_data,
        invert_attrs
    )

    paste_animation_data(
        right_obj,
        locator_data,
        invert_attrs
    )

    set_rotation_curves_quaternion(left_obj)
    set_rotation_curves_quaternion(right_obj)

    if cmds.objExists(temp_locator):
        cmds.delete(temp_locator)


def anim_mirror_main():
    rigs = get_selected_rigs()

    if not rigs:
        return

    start, end = get_playback_range()
    current_time = cmds.currentTime(q=True)

    grpA_rig_list = []
    grpB_rig_list = []
    grpC_rig_list = []
    grpD_rig_list = []

    for rig in rigs:
        if contains_keyword(rig, GRP_A_KEYWORDS):
            grpA_rig_list.append(rig)

        if contains_keyword(rig, GRP_B_KEYWORDS):
            grpB_rig_list.append(rig)

        if contains_keyword(rig, GRP_C_KEYWORDS):
            grpC_rig_list.append(rig)

        if contains_keyword(rig, GRP_D_KEYWORDS):
            grpD_rig_list.append(rig)

    print("GrpA_Rig_List : {}".format(grpA_rig_list))
    print("GrpB_Rig_List : {}".format(grpB_rig_list))
    print("GrpC_Rig_List : {}".format(grpC_rig_list))
    print("GrpD_Rig_List : {}".format(grpD_rig_list))

    processed_pairs = set()

    cmds.undoInfo(openChunk=True)

    try:
        cmds.refresh(suspend=True)

        for obj in grpA_rig_list:
            mirror_single_rig(
                obj,
                start,
                end,
                GRP_A_INVERT_ATTRS
            )

        pair_groups = [
            (grpB_rig_list, GRP_B_INVERT_ATTRS),
            (grpC_rig_list, GRP_C_INVERT_ATTRS),
            (grpD_rig_list, GRP_D_INVERT_ATTRS),
        ]

        for rig_list, invert_attrs in pair_groups:
            for obj in rig_list:
                mirror_obj = get_mirror_object(obj)

                if not mirror_obj:
                    cmds.warning(
                        u"{} の対になるオブジェクトが見つかりません".format(obj)
                    )
                    continue

                pair_key = tuple(
                    sorted([
                        get_short_name(obj),
                        get_short_name(mirror_obj)
                    ])
                )

                if pair_key in processed_pairs:
                    continue

                processed_pairs.add(pair_key)

                mirror_pair_rig(
                    obj,
                    start,
                    end,
                    invert_attrs
                )

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


anim_mirror_main()