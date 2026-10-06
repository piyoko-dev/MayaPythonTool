# -*- coding: utf-8 -*-
import maya.cmds as cmds

#=======================================
#          処理前に取得しておく情報
#=======================================
#ファイルパスの設定
myfile_Path = r"C:\Users\sonku\Pictures\CamGrid\Grid_00.png".replace("\\","/")

#Attributeリスト
attr_List = [
    "translateX",
    "translateY",
    "translateZ",
    "rotateX",
    "rotateY",
    "rotateZ"
]

#グリッドを適用させたいカメラ
source_obj = "test_camera"

#カメラのアトリビュート
cam_values = {}

for attr in attr_List:
    get_cam_attr = cmds.getAttr(source_obj + "." + attr)
    cam_values[attr] = get_cam_attr
print(cam_values)



#=======================================
#       処理①　イメージプレーンの作成
#=======================================
def create_MyImagePlane():
    #すでに作成されているかどうかの確認
    if cmds.objExists("ImgPlaneTESTShape*"):
        cmds.warning("既にImgPlaneTESTは作成されているため処理をスキップしました。")
        return #存在する場合は何もせず終了
    
    #存在しない場合は新規作成
    make_imgPlane = cmds.imagePlane(camera=source_obj, maintainRatio=True, name="ImgPlaneTEST", fileName=myfile_Path)
    imgPlane_trans = make_imgPlane[0]
    
    #各種アトリビュートの設定
    cmds.setAttr("ImgPlaneTESTShape2.fit",1)
    cmds.setAttr("ImgPlaneTESTShape2.type",0)
    cmds.setAttr("ImgPlaneTESTShape2.depth",5)
    cmds.setAttr("ImgPlaneTESTShape2.useFrameExtension",1) #イメージシーケンスの使用をオン
    cmds.disconnectAttr("time1.outTime","ImgPlaneTESTShape2.frameExtension")
    cmds.setAttr("ImgPlaneTESTShape2.frameExtension",0) #連番画像の0番目を表示
    
    cmds.inViewMessage(amg=u"<hl>test_Cameraにグリッド画像を適用しました。</hl>", pos='midCenter', fade=True)


#create_MyImagePlane()


#=======================================
#       処理②　Ctrlノード作成
#=======================================
def setting_CtrlNode():
    if cmds.objExists("CamGrid_Ctrl"):
        cmds.warning("既に作成されています。")
        return
        
    cmds.group(em=True, name="CamGrid_Ctrl") #空ノード作成
    cmds.setAttr("CamGrid_Ctrl.tx", keyable=False, lock=True) #不要な移動値アトリビュート非表示
    cmds.setAttr("CamGrid_Ctrl.ty", keyable=False, lock=True)
    cmds.setAttr("CamGrid_Ctrl.tz", keyable=False, lock=True)
    cmds.setAttr("CamGrid_Ctrl.rx", keyable=False, lock=True) #不要な回転値アトリビュート非表示
    cmds.setAttr("CamGrid_Ctrl.ry", keyable=False, lock=True)
    cmds.setAttr("CamGrid_Ctrl.rz", keyable=False, lock=True)
    cmds.setAttr("CamGrid_Ctrl.sx", keyable=False, lock=True) #不要なスケール値アトリビュート非表示
    cmds.setAttr("CamGrid_Ctrl.sy", keyable=False, lock=True)
    cmds.setAttr("CamGrid_Ctrl.sz", keyable=False, lock=True)
    
    cmds.select("CamGrid_Ctrl")
    cmds.addAttr(longName="Transparency", attributeType='double', min=0, max=1, defaultValue=1, hidden=False)
    cmds.setAttr("CamGrid_Ctrl.Transparency", keyable=True)
    cmds.addAttr(longName="Type", attributeType='enum', enumName="Center:PhiGrid:RuleOfThird:Diagonal:GR_RBot:GR_LBot:GR_RTop:GR_LTop", hidden=False)
    cmds.setAttr("CamGrid_Ctrl.Type", keyable=False, channelBox=True)
    cmds.connectAttr("CamGrid_Ctrl.Transparency", "ImgPlaneTESTShape2.alphaGain")
    cmds.connectAttr("CamGrid_Ctrl.Type", "ImgPlaneTESTShape2.frameExtension")
        


#=======================================
#       処理③　Delete処理
#=======================================
def delete_camGrid():
    if cmds.objExists("ImgPlaneTESTShape2"):
        cmds.delete("CamGrid_Ctrl")
        cmds.delete("ImgPlaneTEST1")




#=======================================
#                UI
#=======================================
WINDOW_NAME="CameraGridSetting"

def create_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)
    
    main_window = cmds.window(
        WINDOW_NAME,
        title = "Camera Grid Tool",
        #sazeable=True,
        widthHeight=(300,100)
    )
    
    main_Layout = cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=20,
        columnOffset=("both",10)
    )
    
    cmds.text("▼ menu ", align="left", font="boldLabelFont")
    cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1,20),(2,140),(3,200)], rowSpacing=[(1,10)])
    
    cmds.text(label="  ", align="left") #余白用
    cmds.button(label="ImagePlane作成", command="create_MyImagePlane()")
    cmds.text(label=" 指定のカメラにCamGrid用のImagePlaneを適用", align="left")
    
    cmds.text(label="  ", align="left") #余白用
    cmds.button(label="ノード作成", command="setting_CtrlNode()")
    cmds.text(label=" Ctrl用の空ノードを作成", align="left")
    
    cmds.text(label="  ", align="left") #余白用
    cmds.button(label="削除", command="delete_camGrid()")
    cmds.text(label=" ", align="left")
    cmds.setParent("..")
    
    cmds.showWindow(main_window)
    

create_ui()
#=======================================
#                END
#=======================================
