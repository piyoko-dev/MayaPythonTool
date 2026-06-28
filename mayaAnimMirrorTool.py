# -*- coding: utf-8 -*-
import maya.cmds as cmds

MIRROR_SIGN_ATTRS = set(['translateX', 'rotateY', 'rotateZ'])
NAME_PAIRS = [('_L', '_R'), ('_R', '_L'), ('L_', 'R_'), ('R_', 'L_')]
TRANSFORM_ATTRS = [
    'translateX', 'translateY', 'translateZ',
    'rotateX', 'rotateY', 'rotateZ',
    'scaleX', 'scaleY', 'scaleZ'
]
WINDOW_NAME = 'mayaAnimMirrorToolWin'


def to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def short_name(node):
    return node.split('|')[-1]


def no_namespace(name):
    return name.split(':')[-1]


def mirror_name(name):
    for a, b in NAME_PAIRS:
        if a in name:
            return name.replace(a, b, 1)
    return None


def get_selected_nodes(include_hierarchy=True):
    selected = cmds.ls(selection=True, long=True, type='transform') or []
    result = []

    for node in selected:
        if node not in result:
            result.append(node)

        if include_hierarchy:
            children = cmds.listRelatives(
                node,
                allDescendents=True,
                fullPath=True,
                type='transform'
            ) or []
            for child in children:
                if child not in result:
                    result.append(child)

    return result


def make_lookup(nodes):
    lookup = {}
    for node in nodes:
        s = short_name(node)
        lookup[s] = node
        ns = no_namespace(s)
        if ns not in lookup:
            lookup[ns] = node
    return lookup


def find_mirror_node(node, lookup):
    s = short_name(node)
    m = mirror_name(s)
    if m and m in lookup:
        return lookup[m]

    ns = no_namespace(s)
    m = mirror_name(ns)
    if m and m in lookup:
        return lookup[m]

    return None


def attr_exists(attr):
    return cmds.objExists(attr)


def is_settable(attr):
    try:
        return (not cmds.getAttr(attr, lock=True)) and bool(cmds.getAttr(attr, settable=True))
    except Exception:
        return False


def get_key_times(attr, start_frame, end_frame):
    return to_list(cmds.keyframe(attr, query=True, time=(start_frame, end_frame), timeChange=True))


def get_value(attr, frame):
    data = to_list(cmds.keyframe(attr, query=True, time=(frame, frame), valueChange=True))
    if data:
        return data[0]
    try:
        return cmds.getAttr(attr, time=frame)
    except Exception:
        return None


def set_value(attr, frame, value):
    if value is None or not is_settable(attr):
        return
    try:
        cmds.setKeyframe(attr, time=frame, value=value)
    except Exception:
        pass


def mirror_value(attr_name, value):
    if value is None:
        return None
    if attr_name in MIRROR_SIGN_ATTRS:
        return value * -1.0
    return value


def get_target_attrs(node_a, node_b):
    attrs = []
    keyable = cmds.listAttr(node_a, keyable=True) or []

    for attr_name in TRANSFORM_ATTRS + keyable:
        if attr_name in attrs:
            continue
        if attr_exists(node_a + '.' + attr_name) and attr_exists(node_b + '.' + attr_name):
            attrs.append(attr_name)

    return attrs


def mirror_pair(node_a, node_b, start_frame, end_frame):
    for attr_name in get_target_attrs(node_a, node_b):
        attr_a = node_a + '.' + attr_name
        attr_b = node_b + '.' + attr_name
        times = sorted(list(set(get_key_times(attr_a, start_frame, end_frame) + get_key_times(attr_b, start_frame, end_frame))))

        if not times:
            continue

        saved = []
        for frame in times:
            saved.append((frame, get_value(attr_a, frame), get_value(attr_b, frame)))

        for frame, value_a, value_b in saved:
            set_value(attr_a, frame, mirror_value(attr_name, value_b))
            set_value(attr_b, frame, mirror_value(attr_name, value_a))


def mirror_center(node, start_frame, end_frame):
    for attr_name in MIRROR_SIGN_ATTRS:
        attr = node + '.' + attr_name
        if not attr_exists(attr):
            continue
        for frame in get_key_times(attr, start_frame, end_frame):
            value = get_value(attr, frame)
            if value is not None:
                set_value(attr, frame, value * -1.0)


def mirror_selected_animation(include_hierarchy=True):
    nodes = get_selected_nodes(include_hierarchy)
    if not nodes:
        cmds.warning('Please select controller root or controllers.')
        return

    start_frame = cmds.playbackOptions(query=True, min=True)
    end_frame = cmds.playbackOptions(query=True, max=True)
    lookup = make_lookup(nodes)
    done = set()
    pair_count = 0
    center_count = 0

    cmds.undoInfo(openChunk=True)
    try:
        for node in nodes:
            if node in done:
                continue
            mirror_node = find_mirror_node(node, lookup)
            if mirror_node and mirror_node != node:
                mirror_pair(node, mirror_node, start_frame, end_frame)
                done.add(node)
                done.add(mirror_node)
                pair_count += 1
            else:
                mirror_center(node, start_frame, end_frame)
                done.add(node)
                center_count += 1
        print('Mirror Animation Done. pairs={0}, center={1}'.format(pair_count, center_count))
    except Exception:
        cmds.warning('Mirror animation error. See Script Editor.')
        import traceback
        traceback.print_exc()
    finally:
        cmds.undoInfo(closeChunk=True)


def show_mirror_animation_tool():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)
    cmds.window(WINDOW_NAME, title='Maya Anim Mirror Tool', sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnOffset=('both', 20))
    cmds.text(label='Select controller root or controllers.\nMirror keys in current time range.', align='left')
    cb = cmds.checkBox(label='Include hierarchy', value=True)
    cmds.button(
        label='Mirror Animation',
        height=40,
        command=lambda *_: mirror_selected_animation(cmds.checkBox(cb, query=True, value=True))
    )
    cmds.showWindow(WINDOW_NAME)


show_mirror_animation_tool()
