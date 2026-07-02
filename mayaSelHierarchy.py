import maya.cmds as cmds

# 1. 選択ノード以下のすべてのトランスフォームノードを取得
all_transforms = cmds.ls(selection=True, dag=True, type="transform")

# 2. 直下に「目的のシェイプ（CurveやMesh）」を持っているものだけに絞り込む
filtered_nodes = [node for node in all_transforms if cmds.listRelatives(node, shapes=True, type=["nurbsCurve", "mesh", "nurbsSurface"])]

# 3. 実際に選択を実行する
cmds.select(filtered_nodes, replace=True)

# 4. 現在選択されているものを改めて取得して変数に入れる
sel_hierarchy = cmds.ls(selection=True)
print(sel_hierarchy)