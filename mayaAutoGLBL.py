# -*- coding: utf-8 -*-
import maya.cmds as cmds


def is_nurbs_curve_transform(node):
    shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
    for s in shapes:
        if cmds.nodeType(s) == "nurbsCurve":
            return True
    return False


def get_selected_nurbs_curves():
    sel = cmds.ls(sl=True, long=True) or []
    curves = []

    for node in sel:
        if cmds.nodeType(node) == "nurbsCurve":
            parent = cmds.listRelatives(node, parent=True, fullPath=True)
            if parent:
                node = parent[0]

        if cmds.nodeType(node) == "transform" and is_nurbs_curve_transform(node):
            if node not in curves:
                curves.append(node)

    return curves


def get_selected_glb_locators():
    sel = cmds.ls(sl=True, long=True) or []
    locators = []

    for node in sel:
        if not cmds.objExists(node):
            continue

        if not node.split("|")[-1].endswith("_GLB"):
            continue

        shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
        for s in shapes:
            if cmds.nodeType(s) == "locator":
                locators.append(node)
                break

    return locators


def make_unique_name(name):
    if not cmds.objExists(name):
        return name

    i = 1
    while cmds.objExists("{}_{}".format(name, i)):
        i += 1
    return "{}_{}".format(name, i)


def is_attr_locked(node, attr):
    plug = "{}.{}".format(node, attr)
    if not cmds.objExists(plug):
        return True
    return cmds.getAttr(plug, lock=True)


def get_unlocked_axes(node, base_attr):
    axes = []
    for axis in ["x", "y", "z"]:
        attr = base_attr + axis.upper()
        if not is_attr_locked(node, attr):
            axes.append(axis)
    return axes


def delete_constraints_on_node(node):
    cons = cmds.listRelatives(node, children=True, type="constraint", fullPath=True) or []
    if cons:
        cmds.delete(cons)


def get_constrained_curves_from_locator(locator):
    result = []

    cons = cmds.listRelatives(locator, children=True, type="constraint", fullPath=True) or []
    cons += cmds.listConnections(locator, type="constraint") or []

    for con in cons:
        targets = cmds.listConnections(con + ".constraintParentInverseMatrix", source=True, destination=False) or []
        targets += cmds.listConnections(con, source=False, destination=True, type="transform") or []

        for t in targets:
            if cmds.objExists(t) and is_nurbs_curve_transform(t):
                if t not in result:
                    result.append(t)

    return result


def create_global_locators(curves):
    start = cmds.playbackOptions(q=True, min=True)
    end = cmds.playbackOptions(q=True, max=True)

    created_locs = []

    for curve in curves:
        short_name = curve.split("|")[-1]
        loc_name = make_unique_name(short_name + "_GLB")

        loc = cmds.spaceLocator(name=loc_name)[0]
        created_locs.append(loc)

        tmp_cons = []

        try:
            tmp_cons += cmds.pointConstraint(curve, loc, mo=False)
        except Exception as e:
            cmds.warning("PointConstraint skipped : {} -> {} / {}".format(curve, loc, e))

        try:
            tmp_cons += cmds.orientConstraint(curve, loc, mo=False)
        except Exception as e:
            cmds.warning("OrientConstraint skipped : {} -> {} / {}".format(curve, loc, e))

        cmds.bakeResults(
            loc,
            t=(start, end),
            simulation=True,
            sampleBy=1,
            disableImplicitControl=True,
            preserveOutsideKeys=True,
            sparseAnimCurveBake=False,
            removeBakedAttributeFromLayer=False,
            bakeOnOverrideLayer=False,
            minimizeRotation=True,
            controlPoints=False,
            shape=False
        )

        if tmp_cons:
            cmds.delete(tmp_cons)

        delete_constraints_on_node(loc)

        unlocked_t = get_unlocked_axes(curve, "translate")
        unlocked_r = get_unlocked_axes(curve, "rotate")

        if unlocked_t:
            skip_t = [a for a in ["x", "y", "z"] if a not in unlocked_t]
            try:
                cmds.pointConstraint(loc, curve, mo=False, skip=skip_t)
            except Exception as e:
                cmds.warning("Final PointConstraint skipped : {} -> {} / {}".format(loc, curve, e))
        else:
            cmds.warning("Translate locked. PointConstraint skipped : {}".format(curve))

        if unlocked_r:
            skip_r = [a for a in ["x", "y", "z"] if a not in unlocked_r]
            try:
                cmds.orientConstraint(loc, curve, mo=False, skip=skip_r)
            except Exception as e:
                cmds.warning("Final OrientConstraint skipped : {} -> {} / {}".format(loc, curve, e))
        else:
            cmds.warning("Rotate locked. OrientConstraint skipped : {}".format(curve))

    cmds.select(created_locs, r=True)
    print("Create GLB finished. Created locators: {}".format(len(created_locs)))


def bake_back_and_delete_glb(locators):
    start = cmds.playbackOptions(q=True, min=True)
    end = cmds.playbackOptions(q=True, max=True)

    baked_curves = []

    for loc in locators:
        curves = get_constrained_curves_from_locator(loc)

        if not curves:
            cmds.warning("Connected curve not found : {}".format(loc))
            continue

        for curve in curves:
            if curve not in baked_curves:
                baked_curves.append(curve)

    if not baked_curves:
        cmds.warning("No curves to bake.")
        return

    cmds.bakeResults(
        baked_curves,
        t=(start, end),
        simulation=True,
        sampleBy=1,
        disableImplicitControl=True,
        preserveOutsideKeys=True,
        sparseAnimCurveBake=False,
        removeBakedAttributeFromLayer=False,
        bakeOnOverrideLayer=False,
        minimizeRotation=True,
        controlPoints=False,
        shape=False
    )

    for curve in baked_curves:
        delete_constraints_on_node(curve)

    for loc in locators:
        if cmds.objExists(loc):
            cmds.delete(loc)

    cmds.select(baked_curves, r=True)
    print("Bake back finished. Baked curves: {}, Deleted locators: {}".format(
        len(baked_curves),
        len(locators)
    ))


def auto_global_tool():
    curves = get_selected_nurbs_curves()
    glb_locators = get_selected_glb_locators()

    if not curves and not glb_locators:
        cmds.warning("Please select NurbsCurve or GLB locator.")
        return

    cmds.undoInfo(openChunk=True)
    try:
        cmds.refresh(suspend=True)

        if glb_locators:
            bake_back_and_delete_glb(glb_locators)
        else:
            create_global_locators(curves)

    finally:
        cmds.refresh(suspend=False)
        cmds.undoInfo(closeChunk=True)


auto_global_tool()