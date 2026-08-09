# -*- coding: utf-8 -*-
import maya.cmds as cmds
import os, random, re

# ==================================================
# Utility
# ==================================================
def _sanitize_filename(name, default="CineCameraActor_export"):
    name = (name or "").strip()
    if not name:
        name = default
    name = re.sub(r'[\\/:*?"<>|]', '_', name).strip(" .")
    return name or default


def _section_header(title):
    frm = cmds.formLayout(nd=100)
    lbl = cmds.text(label=title, align='left', font='smallBoldLabelFont', height=14)
    sep = cmds.separator(style='in', height=6)
    cmds.formLayout(frm, e=True,
        attachForm=[(lbl, 'left', 0), (lbl, 'top', 2),
                    (sep, 'right', 0), (sep, 'top', 6)],
        attachControl=[(sep, 'left', 4, lbl)])
    cmds.setParent('..')


def _browse_export_folder(text_field):
    folder = cmds.fileDialog2(dialogStyle=2, fileMode=3, okCaption=u"選択")
    if folder:
        cmds.textField(text_field, e=True, text=folder[0])


def _force_delete_leftovers(patterns):
    found = []
    for p in patterns:
        for n in (cmds.ls(p, long=True) or []):
            if n not in found:
                found.append(n)
    for n in found:
        try:
            cmds.lockNode(n, lock=False)
            cmds.delete(n)
        except:
            pass


# ==================================================
# Tool① CamRig Import / Delete
# ==================================================
def import_cam_rig(*_):
    if cmds.namespace(ex="CamRig"):
        cmds.inViewMessage(amg=u"既に <hl>CamRig</hl> が存在します", pos='midCenter', fade=True)
        return
    try:
        cmds.file(r'F:/SgOriginalResource/Animation/Event/Camera/CameraRig.ma', r=True, ns="CamRig")
        cmds.inViewMessage(amg=u"<hl>CamRig</hl> をインポートしました", pos='midCenter', fade=True)
    except Exception as e:
        cmds.warning(u"CameraRig.ma の読み込みに失敗: {}".format(e))


def delete_camrig_reference(*_):
    removed = False
    for rfn in (cmds.ls(type='reference') or []):
        try:
            ns = cmds.referenceQuery(rfn, namespace=True)
            if ns and ns.replace(':', '') == "CamRig":
                cmds.file(removeReference=True, referenceNode=rfn)
                removed = True
        except:
            pass
    if cmds.namespace(ex="CamRig"):
        try:
            nodes = cmds.ls("CamRig:*") or []
            if nodes: cmds.delete(nodes)
            cmds.namespace(rm="CamRig", mnr=True)
            removed = True
        except: pass
    _force_delete_leftovers(["RNforsterParent", "*RNforsterParent*"])
    msg = "<hl>CamRig</hl> を削除しました。" if removed else "CamRig が見つかりません。"
    cmds.inViewMessage(amg=msg, pos='midCenter', fade=True)


# ==================================================
# Tool② Animation Copy / Delete
# ==================================================
def cam_anim_copy(*_):
    if cmds.objExists("Camera_Base_mot"):
        cmds.delete("Camera_Base_mot")
        return
    start = cmds.playbackOptions(q=True, min=True)
    end   = cmds.playbackOptions(q=True, max=True)

    try:
        cmds.spaceLocator(n='Camera_Base_mot')
        cmds.spaceLocator(n='Camera_Aim_mot')
        cmds.parent('Camera_Aim_mot', 'Camera_Base_mot')
        cmds.setAttr("Camera_Aim_mot.translateZ", -250)
    except:
        cmds.warning(u"ロケータ作成時に問題が発生しましたが処理を継続します。")

    try:
        cmds.pointConstraint('CineCameraActor', 'Camera_Base_mot')
        cmds.orientConstraint('CineCameraActor', 'Camera_Base_mot')
    except:
        cmds.warning(u"CineCameraActor へのコンストレイントに失敗しました。")

    try:
        src_shape = cmds.listRelatives("CineCameraActor", shapes=True, fullPath=True)[0]
        kts = cmds.keyframe(src_shape+'.focalLength', q=True, timeChange=True)
        kvs = cmds.keyframe(src_shape+'.focalLength', q=True, valueChange=True)
        if kts and kvs:
            for t, v in zip(kts, kvs):
                cmds.setKeyframe("CamRig:Focus_Ctrl", attribute='rotateZ', t=t, value=v)
    except Exception as e:
        cmds.warning(u"focalLengthコピー時にエラー: {}".format(e))

    try:
        cmds.bakeResults('Camera_Base_mot', t=(start, end), sm=True, disableImplicitControl=True)
        for n in (cmds.listConnections("Camera_Base_mot", type='constraint') or []):
            try: cmds.delete(n)
            except: pass
    except Exception as e:
        cmds.warning(u"Camera_Base_mot ベイク中にエラー: {}".format(e))

    try:
        cmds.pointConstraint('Camera_Base_mot', 'CamRig:BodyMain_Ctrl')
        cmds.orientConstraint('Camera_Base_mot', 'CamRig:BodyMain_Ctrl', offset=(0, 0, 0))
        cmds.bakeResults('CamRig:BodyMain_Ctrl', t=(start, end), sm=True, disableImplicitControl=True)
        for n in (cmds.listConnections("CamRig:BodyMain_Ctrl", type='constraint') or []):
            try: cmds.delete(n)
            except: pass
    except Exception as e:
        cmds.warning(u"CamRig転送中にエラー: {}".format(e))

    try:
        cmds.pointConstraint('CamRig:Dummy_camera', 'CineCameraActor')
        cmds.orientConstraint('CamRig:Dummy_camera', 'CineCameraActor', offset=(0, 0, 0))
        cmds.connectAttr('CamRig:Focus_Ctrl.rotateZ', 'CineCameraActorShape.focalLength', f=True)
    except Exception as e:
        cmds.warning(u"CineCameraActor リンク時にエラー: {}".format(e))

    try:
        if cmds.objExists("Camera_Base_mot"):
            cmds.delete("Camera_Base_mot")
    except:
        pass

    cmds.inViewMessage(amg=u"アニメーションコピー完了（スキップ発生時も継続）", pos='midCenter', fade=True)


def cam_anim_delete(*_):
    ctrls = [
        "CamRig:Rotate_Ctrl",
        "CamRig:BodyMain_Ctrl",
        "CamRig:BodyMail_Ctrl",
        "CamRig:Aim_Ctrl",
        "CamRig:BodySub_Ctrl",
    ]
    existed = False
    for ctrl in ctrls:
        if not cmds.objExists(ctrl): continue
        existed = True
        try: cmds.cutKey(ctrl, clear=True)
        except: pass
        for s in (cmds.listRelatives(ctrl, s=True, fullPath=True) or []):
            try: cmds.cutKey(s, clear=True)
            except: pass
        try:
            anim_nodes = cmds.listConnections(ctrl, type='animCurve', s=True, d=False) or []
            if anim_nodes: cmds.delete(anim_nodes)
        except: pass
    if existed:
        cmds.inViewMessage(amg=u"<hl>CamRig</hl> のキーを削除しました。", pos='midCenter', fade=True)
    else:
        cmds.warning(u"CamRigのコントローラが見つかりません。CamRigを読み込んでください。")


# ==================================================
# Export memory (出力先とファイル名を記憶)
# ==================================================
_last_export_settings = {
    "folder": "C:/temp",
    "filename": "CineCameraActor_export.fbx"
}

def camera_export(*_):
    """Camera Export UI — 前回使用したフォルダ/ファイル名を再表示"""
    global _last_export_settings

    start = int(cmds.playbackOptions(q=True, min=True))
    end   = int(cmds.playbackOptions(q=True, max=True))
    win = "ExportConfirmUI"
    if cmds.window(win, exists=True): cmds.deleteUI(win)

    # 前回設定を取得
    last_folder = _last_export_settings.get("folder", "C:/temp")
    last_filename = _last_export_settings.get("filename", "CineCameraActor_export.fbx")

    WIN_W, WIN_H = 460, 260
    cmds.window(win, title=u"Camera Export", sizeable=False, widthHeight=(WIN_W, WIN_H))
    form = cmds.formLayout(nd=100)
    header = cmds.formLayout(nd=100)
    icon = cmds.iconTextStaticLabel(style='iconOnly', image="out_camera.png", width=24, height=24)
    title = cmds.text(label="Export", align='left', font='boldLabelFont', height=24)
    cmds.formLayout(header, e=True,
        attachForm=[(icon, 'left', 6), (icon, 'top', 6), (title, 'top', 6)],
        attachControl=[(title, 'left', 6, icon)])
    cmds.setParent('..')

    body = cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    _section_header("Frame Range")
    cmds.rowLayout(numberOfColumns=4, columnWidth4=(70,80,70,80), height=22)
    cmds.text(label="開始：", align='left')
    start_field = cmds.intField(value=start, width=60)
    cmds.text(label="終了：", align='left')
    end_field = cmds.intField(value=end, width=60)
    cmds.setParent('..')

    _section_header("Output")
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(70,250,30))
    cmds.text(label="出力先：", align='left')
    folder_field = cmds.textField("exportFolderPath", text=last_folder, width=250)
    cmds.iconTextButton(style='iconOnly', image1='fileOpen.png',
                        c=lambda *_:_browse_export_folder(folder_field))
    cmds.setParent('..')

    cmds.rowLayout(numberOfColumns=2, columnWidth2=(70,250))
    cmds.text(label="ファイル名：", align='left')
    filename_field = cmds.textField("exportFileName", text=last_filename, width=250)
    cmds.setParent('..')

    cmds.separator(h=10, style='none')
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(200,220), columnAlign2=('center','center'))
    cmds.button(label="実行", w=150, h=28, bgc=(0.3,0.3,0.3),
                c=lambda *_:_do_camera_export(folder_field, filename_field, start_field, end_field))
    cmds.button(label="キャンセル", w=150, h=28, bgc=(0.25,0.25,0.25), c=lambda *_:cmds.deleteUI(win))
    cmds.setParent('..')

    cmds.formLayout(form, e=True,
        attachForm=[(header,'top',6),(header,'left',6),
                    (body,'left',10),(body,'right',10),(body,'bottom',10)],
        attachControl=[(body,'top',10,header)])
    cmds.showWindow(win)


# ==================================================
# Tool③ Export（disconnect安全処理付き）
# ==================================================
def _do_camera_export(folder_field, filename_field, start_field, end_field):
    folder = cmds.textField(folder_field, q=True, text=True).strip()
    filename = _sanitize_filename(cmds.textField(filename_field, q=True, text=True))
    if not filename.lower().endswith(".fbx"): filename += ".fbx"
    export_path = os.path.join(folder, filename).replace("\\", "/")
    start = cmds.intField(start_field, q=True, value=True)
    end = cmds.intField(end_field, q=True, value=True)

    if not os.path.isdir(folder):
        cmds.warning("フォルダが存在しません。"); return
    if not cmds.objExists("CineCameraActor"):
        cmds.warning("CineCameraActor が見つかりません。"); return

    if os.path.exists(export_path):
        ans = cmds.confirmDialog(title="上書き確認",
            message="既に同名のファイルがあります。\n上書きしますか？",
            button=["上書きする","キャンセル"], defaultButton="上書きする", cancelButton="キャンセル")
        if ans != "上書きする": return

    src = "CineCameraActor"
    exp = "CineCameraActor_export"
    if cmds.objExists(exp): cmds.delete(exp)
    exp = cmds.duplicate(src, name=exp)[0]
    src_shape = cmds.listRelatives(src, s=True, f=True)[0]
    exp_shape = cmds.listRelatives(exp, s=True, f=True)[0]
    cons = cmds.parentConstraint(src, exp, mo=False)[0]

    # focalLength接続 → ベイク → 安全切断
    cmds.connectAttr(src_shape+".focalLength", exp_shape+".focalLength", f=True)
    bake_attrs = [
        exp+".translateX", exp+".translateY", exp+".translateZ",
        exp+".rotateX", exp+".rotateY", exp+".rotateZ",
        exp_shape+".focalLength"
    ]
    cmds.bakeResults(bake_attrs, t=(start, end), sm=True, disableImplicitControl=True)
    cmds.delete(cons)

    # 🔧 安全なdisconnect処理
    try:
        connections = cmds.listConnections(exp_shape + ".focalLength", s=True, d=False, p=True) or []
        for c in connections:
            if c == src_shape + ".focalLength":
                cmds.disconnectAttr(c, exp_shape + ".focalLength")
    except:
        pass

    cmds.select(exp)
    cmds.file(export_path, force=True, options="v=0;", type="FBX export", exportSelected=True)
    cmds.inViewMessage(amg=f"<hl>エクスポート完了</hl>: {export_path}", pos='midCenter', fade=True)
    cmds.delete(exp)
    cmds.deleteUI("ExportConfirmUI", window=True)


def camera_export(*_):
    start = int(cmds.playbackOptions(q=True, min=True))
    end   = int(cmds.playbackOptions(q=True, max=True))
    win = "ExportConfirmUI"
    if cmds.window(win, exists=True): cmds.deleteUI(win)
    WIN_W, WIN_H = 460, 260
    cmds.window(win, title=u"Camera Export", sizeable=False, widthHeight=(WIN_W, WIN_H))
    form = cmds.formLayout(nd=100)
    header = cmds.formLayout(nd=100)
    icon = cmds.iconTextStaticLabel(style='iconOnly', image="out_camera.png", width=24, height=24)
    title = cmds.text(label="Export", align='left', font='boldLabelFont', height=24)
    cmds.formLayout(header, e=True,
        attachForm=[(icon, 'left', 6), (icon, 'top', 6), (title, 'top', 6)],
        attachControl=[(title, 'left', 6, icon)])
    cmds.setParent('..')

    body = cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    _section_header("Frame Range")
    cmds.rowLayout(numberOfColumns=4, columnWidth4=(70,80,70,80), height=22)
    cmds.text(label="開始：", align='left')
    start_field = cmds.intField(value=start, width=60)
    cmds.text(label="終了：", align='left')
    end_field = cmds.intField(value=end, width=60)
    cmds.setParent('..')
    _section_header("Output")
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(70,250,30))
    cmds.text(label="出力先：", align='left')
    folder_field = cmds.textField("exportFolderPath", text="C:/temp", width=250)
    cmds.iconTextButton(style='iconOnly', image1='fileOpen.png', c=lambda *_:_browse_export_folder(folder_field))
    cmds.setParent('..')
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(70,250))
    cmds.text(label="ファイル名：", align='left')
    filename_field = cmds.textField("exportFileName", text="CineCameraActor_export.fbx", width=250)
    cmds.setParent('..')

    cmds.separator(h=10, style='none')
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(200,220), columnAlign2=('center','center'))
    cmds.button(label="実行", w=150, h=28, bgc=(0.3,0.3,0.3),
                c=lambda *_:_do_camera_export(folder_field, filename_field, start_field, end_field))
    cmds.button(label="キャンセル", w=150, h=28, bgc=(0.25,0.25,0.25), c=lambda *_:cmds.deleteUI(win))
    cmds.setParent('..')

    cmds.formLayout(form, e=True,
        attachForm=[(header,'top',6),(header,'left',6),
                    (body,'left',10),(body,'right',10),(body,'bottom',10)],
        attachControl=[(body,'top',10,header)])
    cmds.showWindow(win)


# ==================================================
# Tool④ Noise Add（Start/End対応）
# ==================================================
def add_noise_animation(*_):
    sel = cmds.ls(sl=True)
    if not sel:
        cmds.warning("ノードを選択してください。")
        return
    node = sel[0]
    try:
        min_val = float(cmds.textField("noiseMinField", q=True, text=True))
        max_val = float(cmds.textField("noiseMaxField", q=True, text=True))
    except:
        cmds.warning("数値の入力が正しくありません。")
        return
    start = cmds.intField("noiseStartField", q=True, value=True)
    end   = cmds.intField("noiseEndField", q=True, value=True)
    attrs = [a for a in ["translateX","translateY","translateZ","rotateX","rotateY","rotateZ"]
              if cmds.checkBox(f"noiseCheck_{a}", q=True, v=True)]
    if not attrs:
        cmds.warning("アトリビュートを選択してください。")
        return
    for attr in attrs:
        if not cmds.attributeQuery(attr, node=node, exists=True): continue
        for f in range(start, end+1):
            cmds.setKeyframe(node, attribute=attr, t=f, value=random.uniform(min_val,max_val))
    cmds.inViewMessage(amg="<hl>Noise</hl> アニメーション追加", pos='midCenter', fade=True)


# ==================================================
# Main UI
# ==================================================
def _section_button_row(label, cmd, delete_cmd=None):
    main_width, delete_width, space_width = 300, 60, 20
    cmds.columnLayout(adjustableColumn=True, columnOffset=("left", 15))
    if delete_cmd:
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(main_width, space_width, delete_width), height=32)
        cmds.button(label=label, w=main_width, h=28, bgc=(0.3,0.3,0.3), c=cmd)
        cmds.text(label="", w=space_width)
        cmds.button(label="Delete", w=delete_width, h=26, c=delete_cmd, bgc=(0.45,0.2,0.2))
        cmds.setParent('..')
    else:
        cmds.rowLayout(numberOfColumns=1, columnWidth1=main_width, height=32)
        cmds.button(label=label, w=main_width, h=28, bgc=(0.3,0.3,0.3), c=cmd)
        cmds.setParent('..')
    cmds.setParent('..')


def camera_tool_ui():
    win = "CameraRigTool"
    if cmds.window(win, exists=True):
        cmds.deleteUI(win)
    cmds.window(win, title="CameraRigTool", widthHeight=(430, 460), sizeable=False)
    form = cmds.formLayout(nd=100)
    col = cmds.columnLayout(adjustableColumn=True, rowSpacing=8)

    # Header
    h = cmds.formLayout(nd=100)
    icon = cmds.iconTextStaticLabel(style='iconOnly', image="out_camera.png", width=24, height=24)
    title = cmds.text(label="CAMERA RIG TOOL", align='left', font='boldLabelFont', height=24)
    cmds.formLayout(h, e=True, attachForm=[(icon, 'left', 4), (icon, 'top', 4), (title, 'top', 4)],
                    attachControl=[(title, 'left', 6, icon)])
    cmds.setParent('..')

    # Sections
    _section_header("CamRig Import")
    _section_button_row("Rig Import", import_cam_rig, delete_camrig_reference)
    _section_header("Animation")
    _section_button_row("CamRigにアニメーション移植実行", cam_anim_copy, cam_anim_delete)
    _section_header("Export")
    _section_button_row("Export Setting", camera_export)
    _section_header("Noise")

    # Noise Min/Max
    cmds.rowLayout(numberOfColumns=4, columnWidth4=(45,60,45,60), height=22, columnAttach=[(1,'left',20),(3,'left',20)])
    cmds.text(label="Min："); cmds.textField("noiseMinField", text="1", width=50)
    cmds.text(label="Max："); cmds.textField("noiseMaxField", text="5", width=50)
    cmds.setParent('..')

   # Noise Start/End
    cmds.rowLayout(numberOfColumns=4, columnWidth4=(45, 60, 45, 60), height=22, columnAttach=[(1, 'left', 20), (3, 'left', 20)])
    cmds.text(label="Start：")
    cmds.intField("noiseStartField", value=int(cmds.currentTime(q=True)), width=50)
    cmds.text(label="End：")
    cmds.intField("noiseEndField", value=int(cmds.playbackOptions(q=True, max=True)), width=50)
    cmds.setParent('..')

    # Noise Attributes
    cmds.columnLayout(adjustableColumn=True, columnOffset=("left", 35))
    cmds.rowLayout(numberOfColumns=6, columnWidth6=(60, 60, 60, 60, 60, 60), height=24)
    for attr in ["translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ"]:
        cmds.checkBox(f"noiseCheck_{attr}", label=attr.replace("translate", "Trs ").replace("rotate", "Rot "), v=False)
    cmds.setParent('..')
    cmds.setParent('..')

    # Add Noise button
    _section_button_row("Add Noise", add_noise_animation)

    # フォームに配置
    cmds.setParent('..')
    cmds.formLayout(form, e=True,
        attachForm=[(col, 'left', 10), (col, 'right', 10), (col, 'top', 10), (col, 'bottom', 10)]
    )

    cmds.showWindow(win)


# ==================================================
# 実行
# ==================================================
camera_tool_ui()
