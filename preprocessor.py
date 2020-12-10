from mevis import *
import time
import os,os.path,sys
import thread
import shutil
from string import split
import random
import threading, subprocess
import math
import numpy as np
import time
import configparser
#import pydicom

# 设置目标路径文件
# 包括3d dcm的中间路径 temp
# 建立相关文件夹
def Generate3dFile():
  dst_root_path=os.path.join(ctx.field("DestinationDataDirectory").value,ctx.field("PatientID").value)
  # 建立空文件夹
  if(os.path.exists(dst_root_path)):
    shutil.rmtree(dst_root_path)
  os.makedirs(dst_root_path)

  #建立各种数据对应的文件夹
  ctx.field("Dcm3DDirectory").value=os.path.join(dst_root_path,"dcm3D")
  ctx.field("NiiDirectory").value=os.path.join(dst_root_path,"nii")
  ctx.field("RawDirectory").value=os.path.join(dst_root_path,"raw")
  ctx.field("ObjDirectory").value=os.path.join(dst_root_path,"obj")
  os.makedirs(ctx.field("Dcm3DDirectory").value) # temp文件夹，用于存储3d dcm文件,完成后删除 TODO
  os.makedirs(ctx.field("NiiDirectory").value)  # nii文件夹 存储nii文件
  os.makedirs(ctx.field("RawDirectory").value)  # raw文件夹 存储裸数据
  os.makedirs(ctx.field("ObjDirectory").value)  # obj文件夹 存储模型文件
  print("create folders done")
  
  #将2维dcm切片 转存为3维dcm和tiff数据
  ctx.field("DicomImport.source").value=ctx.field("PatientDataDirectory").value
  ctx.field("DicomImport.target").value=ctx.field("Dcm3DDirectory").value
  ctx.field("DicomImport.import").touch()
  # 不能放在这儿，因为dicomimport会另外开辟一个线程
  # 在resample之前，dicomimport未必能完成
  #ResampleDcmInFolder(ctx.field("Dcm3DDirectory").value)  # 将数据resample到各向同性 
  print("3d dcm file saved")
  pass

#对目录下的所有dcm文件，resample到各向同性
def ResampleDcmInFolder(root):
  root=root.replace("\\","/")
  file_dir=os.listdir(root)
  if(len(file_dir)==0):
    pass
  for i in range(len(file_dir)):
    print(str(i)+file_dir[i])
    if(file_dir[i][-3:] != "dcm"):  #跳过非dcm文件
      continue
    if(file_dir[i][-13:] == "resampled.dcm"):  #跳过resample过的文件
      continue
    # 生成并存储resample后的文件
    src_name=os.path.join(root,file_dir[i])
    print("resampling"+src_name)
    ctx.field("ImageLoad6.filename").value=src_name
    ctx.field("ImageLoad6.load").touch()
    dst_name=src_name[:-4]+"_resampled"+src_name[-4:]
    ctx.field("ImageSave2.filename").value=dst_name
    ctx.field("ImageSave2.save").touch()
  pass

# 寻找t2 adc序列数据 加载图像
def LoadImage():
  #路径、数据初始化
  InitializePath()
  InitializeLabel()

  ResampleDcmInFolder(ctx.field("Dcm3DDirectory").value)  # 将数据resample到各向同性

  file_type=""
  dst_root_path=os.path.join(ctx.field("DestinationDataDirectory").value,ctx.field("PatientID").value)
  root=ctx.field("Dcm3DDirectory").value
  file_dir=os.listdir(root)
  if(len(root)==0):
    pass
  for i in range(len(file_dir)):
    #if(file_dir[i][-3:] != "dcm"):
    #  continue
    if(file_dir[i][-13:]!="resampled.dcm"):  #仅采用resampled数据
      continue
    name=os.path.join(root,file_dir[i])
    ctx.field("ImageLoad2.filename").value=name
    ctx.field("ImageLoad2.load").touch()
    ctx.field("DicomTagViewer2.getValues").touch()
    file_type=ctx.field("DicomTagViewer2.tagValue3").value
    adc_found_flag=False
    if ("t2_tse_tra" in file_type): #找t2序列图像
      print("name  "+name)
      ctx.field("T2SeriesPath").value=name
    elif("ADC" in file_type): #找adc序列图像
      adc_found_flag=true
      print("name  "+name)
      ctx.field("ADCSeriesPath").value=name
    if(not adc_found_flag):
      ctx.field("ADCSeriesPath").value=ctx.field("T2SeriesPath").value
  #t2 adc序列路径修改后，FieldListener响应修改，调用相关函数完成图像读取和显示
  # 根据读取的dcm数据参数,设置其他模块对应的尺寸、体素大小信息
  ctx.field("ImageLoad3.rawX").value=ctx.field("Info2.sizeX").value
  ctx.field("ImageLoad3.rawY").value=ctx.field("Info2.sizeY").value
  ctx.field("ImageLoad3.rawZ").value=ctx.field("Info2.sizeZ").value
  ctx.field("ImagePropertyConvert1.voxelSizeX").value=ctx.field("Info2.voxelSizeX").value
  ctx.field("ImagePropertyConvert1.voxelSizeY").value=ctx.field("Info2.voxelSizeY").value
  ctx.field("ImagePropertyConvert1.voxelSizeZ").value=ctx.field("Info2.voxelSizeZ").value
  pass

# 用于清空程序中现有的所有路径信息。包括某个特定病人的原始数据路径、程序自动寻找的t2及adc序列路径，以及输出的目标路径。
# 在程序中也会同时关闭这些图像。
def InitializePath():
  #测试用 待删除 TODO
  # os.makedirs("d:\\test1")

  ctx.field("RectumReverse").value=False

  ctx.field("T2SeriesPath").value=""
  ctx.field("ADCSeriesPath").value=""
  ctx.field("ImageLoad.close").touch()
  ctx.field("ImageLoad1.close").touch()
  ctx.field("ImageLoad2.close").touch()
  ctx.field("itkImageFileReader.close").touch()
  ctx.field("itkImageFileReader1.close").touch()
  ctx.field("itkImageFileReader2.close").touch()
  print("initialization of path done")

# delete all cso&label in the mlab file. set all display to false
def InitializeLabel():
  ctx.field("CSOManager.removeAllCSOsAndGroups").touch()
  ctx.field("CSOConvertTo3DMask.apply").touch()
  ctx.field("CSOConvertTo3DMask1.apply").touch()
  ctx.field("CSOConvertTo3DMask2.apply").touch()
  ctx.field("MarkingProstate").value=False
  ctx.field("MarkingLesion").value=False
  ctx.field("MarkingRectum").value=False
  ctx.field("DisplayProstate").value=False
  ctx.field("DisplayLesion").value=False
  ctx.field("DisplayRectum").value=False
  ctx.field("SoView2DOverlay.drawingOn").value=False
  ctx.field("SoView2DOverlay1.drawingOn").value=False
  ctx.field("SoView2DOverlay2.drawingOn").value=False
  print("initialization of label done")
  pass


# 输出txt文档,包含 t2序列文件名、adc序列文件名 t2序列的每一帧对应adc序列的帧数
def Test():
  # 取t2序列世界坐标第2列，对应其z'轴，即每个横断面的法向量,将其归一化，记为v_normal
  v_normal=[]
  v_normal.append(ctx.field("Info2.a02").value)
  v_normal.append(ctx.field("Info2.a12").value)
  v_normal.append(ctx.field("Info2.a22").value)
  k=math.sqrt(v_normal[0]*v_normal[0]+v_normal[1]*v_normal[1]+v_normal[2]*v_normal[2])
  v_normal[0]/=k
  v_normal[1]/=k
  v_normal[2]/=k
  print(v_normal)
  # 对t2序列上的每一帧，其与t2序列第0帧的距离为 帧数*voxelSizeZ
  d_t2=[]
  for i in range(ctx.field("Info2.sizeZ").value):
    d_t2.append(i*ctx.field("Info2.voxelSizeZ").value)
  # 对adc序列，先求其第0帧与t2序列第0帧之间的距离 记为d
  v_t0=[] #t2序列坐标(0,0,0)点对应的世界坐标
  v_a0=[] #adc序列坐标(0,0,0)点对应的世界坐标
  v_dif=[] #v_a0-v_t0
  v_t0.append(ctx.field("Info2.a03").value)
  v_t0.append(ctx.field("Info2.a13").value)
  v_t0.append(ctx.field("Info2.a23").value)
  v_a0.append(ctx.field("Info1.a03").value)
  v_a0.append(ctx.field("Info1.a13").value)
  v_a0.append(ctx.field("Info1.a23").value)
  v_dif.append(v_a0[0]-v_t0[0])
  v_dif.append(v_a0[1]-v_t0[1])
  v_dif.append(v_a0[2]-v_t0[2])
  distance_00=v_dif[0]*v_normal[0]+v_dif[1]*v_normal[1]+v_dif[2]*v_normal[2]
  # 类似的，adc序列的每帧与t2序列第0帧之间的距离为 帧数*voxelSizeZ+d
  d_adc=[]
  for i in range(ctx.field("Info1.sizeZ").value):
    d_adc.append(i*ctx.field("Info1.voxelSizeZ").value+distance_00)
  # 求t2序列每一帧对应的adc序列帧数
  dic=[]
  for i in range(len(d_t2)):
    min=9999
    min_index=-1
    for j in range(len(d_adc)):
      distance=abs(d_t2[i]-d_adc[j])
      if(distance<min):
        min=distance
        min_index=j
    dic.append(min_index)
  # 写入txt文件
  filename="E:\\study\\summer_break\\data\\test\\dictionary.txt"
  f=open(filename,'w')
  '''
  print("d_t2"+"\n")
  for i,distance in enumerate(d_t2):
    print(str(i)+':'+str(distance)+' ')
  print("d_adc"+"\n")
  for i,distance in enumerate(d_adc):
    print(str(i)+':'+str(distance)+' ')
  '''
  f.write(ctx.field("T2SeriesPath").value+"\n")
  f.write(ctx.field("ADCSeriesPath").value+"\n")
  for i in range(len(dic)):
    f.write(str(dic[i])+' ')
  f.close()
  pass

def SetT2Path():
  ctx.field("ImageLoad.filename").value=ctx.field("T2SeriesPath").value
  ctx.field("ImageLoad.load").touch()
  ctx.field("MatlabScriptWrapper.update").touch()  
  print("t2 series path set")
  pass

def SetADCPath():
  ctx.field("ImageLoad1.filename").value=ctx.field("ADCSeriesPath").value
  ctx.field("ImageLoad1.load").touch()
  print("ADC series path set")
  pass

# 由cso轮廓生成3D mask
def GenerateProstate():
  # 为所有未分配标签的cso轮廓 分配标签"prostate"
  cso_list=[]
  num_cso=ctx.field("CSOManager.numCSOs").value
  cso_tree=ctx.field("CSOManager.csoDisplayTree").value
  cso_tree=cso_tree.split("|")
  for i in range(num_cso):
    cso_list.append(cso_tree[i+1].split(" ")[0]) # 获取现有的每个cso轮廓的名称，存储为数组
  for i in range(num_cso):
    ctx.field("CSOManager.csoSelectedItems").value=cso_list[i]
    if(len(ctx.field("CSOManager.csoSingleLabel").value)==0):
      ctx.field("CSOManager.csoSingleLabel").value="prostate"
  # 生成3D mask
  ctx.field("CSOFilter.apply").touch()
  ctx.field("CSOConvertTo3DMask.apply").touch()
  #显示 cso
  print("label of prostate generated")
  ctx.field("MarkingProstate").value=True
  pass

# 由cso轮廓生成3D mask
def GenerateLesion():
  # 为所有未分配标签的cso轮廓 分配标签"lesion"
  cso_list=[]
  num_cso=ctx.field("CSOManager.numCSOs").value
  cso_tree=ctx.field("CSOManager.csoDisplayTree").value
  cso_tree=cso_tree.split("|")
  for i in range(num_cso):
    cso_list.append(cso_tree[i+1].split(" ")[0]) # 获取现有的每个cso轮廓的名称，存储为数组
  for i in range(num_cso):
    ctx.field("CSOManager.csoSelectedItems").value=cso_list[i]
    if(len(ctx.field("CSOManager.csoSingleLabel").value)==0):
      ctx.field("CSOManager.csoSingleLabel").value="lesion"
  # 生成3D mask
  ctx.field("CSOFilter1.apply").touch()
  ctx.field("CSOConvertTo3DMask1.apply").touch()
  #显示 cso
  print("label of lesion generated")
  ctx.field("MarkingLesion").value=True
  pass

# 由cso轮廓生成3D mask
def GenerateRectum():
  # 为所有未分配标签的cso轮廓 分配标签"rectum"
  cso_list=[]
  num_cso=ctx.field("CSOManager.numCSOs").value
  cso_tree=ctx.field("CSOManager.csoDisplayTree").value
  cso_tree=cso_tree.split("|")
  for i in range(num_cso):
    cso_list.append(cso_tree[i+1].split(" ")[0]) # 获取现有的每个cso轮廓的名称，存储为数组
  for i in range(num_cso):
    ctx.field("CSOManager.csoSelectedItems").value=cso_list[i]
    if(len(ctx.field("CSOManager.csoSingleLabel").value)==0):
      ctx.field("CSOManager.csoSingleLabel").value="rectum"
  # 生成3D mask
  ctx.field("CSOFilter2.apply").touch()
  ctx.field("CSOConvertTo3DMask2.apply").touch()
  #显示 cso
  print("label of rectum generated")
  ctx.field("MarkingRectum").value=True
  pass

# � 除所有的prostate及未命名cso
def DeleteProstate():
  cso_list=[]
  num_cso=ctx.field("CSOManager.numCSOs").value
  cso_tree=ctx.field("CSOManager.csoDisplayTree").value
  cso_tree=cso_tree.split("|")
  for i in range(num_cso):
    cso_list.append(cso_tree[i+1].split(" ")[0])
  for i in range(num_cso):
    ctx.field("CSOManager.csoSelectedItems").value=cso_list[i]
    if(len(ctx.field("CSOManager.csoSingleLabel").value)==0 or ctx.field("CSOManager.csoSingleLabel").value=="prostate"):
      ctx.field("CSOManager.csoRemoveSelected").touch()
  ctx.field("CSOConvertTo3DMask.apply").touch()
  print("cso and label of prostate deleted")
  pass

# � 除所有的lesion及未命名cso
def DeleteLesion():
  cso_list=[]
  num_cso=ctx.field("CSOManager.numCSOs").value
  cso_tree=ctx.field("CSOManager.csoDisplayTree").value
  cso_tree=cso_tree.split("|")
  for i in range(num_cso):
    cso_list.append(cso_tree[i+1].split(" ")[0])
  for i in range(num_cso):
    ctx.field("CSOManager.csoSelectedItems").value=cso_list[i]
    if(len(ctx.field("CSOManager.csoSingleLabel").value)==0 or ctx.field("CSOManager.csoSingleLabel").value=="lesion"):
      ctx.field("CSOManager.csoRemoveSelected").touch()
  ctx.field("CSOConvertTo3DMask1.apply").touch()
  print("cso and label of lesion deleted")
  pass

# � 除所有的rectum及未命名cso
def DeleteRectum():
  cso_list=[]
  num_cso=ctx.field("CSOManager.numCSOs").value
  cso_tree=ctx.field("CSOManager.csoDisplayTree").value
  cso_tree=cso_tree.split("|")
  for i in range(num_cso):
    cso_list.append(cso_tree[i+1].split(" ")[0])
  for i in range(num_cso):
    ctx.field("CSOManager.csoSelectedItems").value=cso_list[i]
    if(len(ctx.field("CSOManager.csoSingleLabel").value)==0 or ctx.field("CSOManager.csoSingleLabel").value=="rectum"):
      ctx.field("CSOManager.csoRemoveSelected").touch()
  ctx.field("CSOConvertTo3DMask2.apply").touch()
  print("cso and label of rectum deleted")
  pass

# 设定目前标注的是哪种轮廓
def SetMarkingProstate():
  marking=ctx.field("MarkingProstate").value
  #确保只能同时标注一种轮廓
  if(marking):
    ctx.field("MarkingLesion").value=False
    ctx.field("MarkingRectum").value=False
  else:
    return

  # 仅显示标注物体的cso轮廓线
  cso_list=[]
  num_cso=ctx.field("CSOManager.numCSOs").value
  cso_tree=ctx.field("CSOManager.csoDisplayTree").value
  cso_tree=cso_tree.split("|")
  for i in range(num_cso):
    cso_list.append(cso_tree[i+1].split(" ")[0]) # 获取现有的每个cso轮廓的名称，存储为数组
  for i in range(num_cso):
    ctx.field("CSOManager.csoSelectedItems").value=cso_list[i]
    #只显示prostate的轮廓线
    if(ctx.field("CSOManager.csoSingleLabel").value=="prostate"):
      ctx.field("CSOManager.csoSingleShowState").value=marking
    else:
      ctx.field("CSOManager.csoSingleShowState").value=(not marking)
  pass

# 设定目前标注的是哪种轮廓
def SetMarkingLesion():
  marking=ctx.field("MarkingLesion").value
  #确保只能同时标注一种轮廓
  if(marking):
    ctx.field("MarkingProstate").value=False
    ctx.field("MarkingRectum").value=False
  else:
    return

  # 仅显示标注物体的cso轮廓线
  cso_list=[]
  num_cso=ctx.field("CSOManager.numCSOs").value
  cso_tree=ctx.field("CSOManager.csoDisplayTree").value
  cso_tree=cso_tree.split("|")
  for i in range(num_cso): #标注开始时 numCSOs可能错误地被置为非0值
    cso_list.append(cso_tree[i+1].split(" ")[0]) # 获取现有的每个cso轮廓的名称，存储为数组
  for i in range(num_cso):
    ctx.field("CSOManager.csoSelectedItems").value=cso_list[i]
    #只显示lesion的轮廓线
    if(ctx.field("CSOManager.csoSingleLabel").value=="lesion"):
      ctx.field("CSOManager.csoSingleShowState").value=marking
    else:
      ctx.field("CSOManager.csoSingleShowState").value=(not marking)
  pass

# 设定目前标注的是哪种轮廓
def SetMarkingRectum():
  marking=ctx.field("MarkingRectum").value
  #确保只能同时标注一种轮廓
  if(marking):
    ctx.field("MarkingProstate").value=False
    ctx.field("MarkingLesion").value=False
  else:
    return

  # 仅显示标注物体的cso轮廓线
  cso_list=[]
  num_cso=ctx.field("CSOManager.numCSOs").value
  cso_tree=ctx.field("CSOManager.csoDisplayTree").value
  cso_tree=cso_tree.split("|")
  for i in range(num_cso): #标注开始时 numCSOs可能错误地被置为非0值
    cso_list.append(cso_tree[i+1].split(" ")[0]) # 获取现有的每个cso轮廓的名称，存储为数组
  for i in range(num_cso):
    ctx.field("CSOManager.csoSelectedItems").value=cso_list[i]
    #只显示lesion的轮廓线
    if(ctx.field("CSOManager.csoSingleLabel").value=="rectum"):
      ctx.field("CSOManager.csoSingleShowState").value=marking
    else:
      ctx.field("CSOManager.csoSingleShowState").value=(not marking)
  pass

def SetDisplayProstate():
  if(ctx.field("DisplayProstate").value):
    ctx.field("SoView2DOverlay.drawingOn").value=True
  else:
    ctx.field("SoView2DOverlay.drawingOn").value=False
  print("display of prostate set to "+str(ctx.field("SoView2DOverlay.drawingOn").value))
  pass

def SetDisplayLesion():
  if(ctx.field("DisplayLesion").value):
    ctx.field("SoView2DOverlay1.drawingOn").value=True
  else:
    ctx.field("SoView2DOverlay1.drawingOn").value=False
  print("display of lesion set to "+str(ctx.field("SoView2DOverlay1.drawingOn").value))
  pass

def SetDisplayRectum():
  if(ctx.field("DisplayRectum").value):
    ctx.field("SoView2DOverlay2.drawingOn").value=True
  else:
    ctx.field("SoView2DOverlay2.drawingOn").value=False
  print("display of rectum set to "+str(ctx.field("SoView2DOverlay2.drawingOn").value))
  pass

#更新obj文件 统计点、面的数量
def transformObj(strFileName):
    nVCount=0
    nFCount=0
    #s=""
    file=open(strFileName,"r+",1)
    lines=file.readlines()
    #统计点、面的数量
    for line in lines:
        if line.startswith('v'):
            nVCount+=1
        elif line.startswith('f'):
            nFCount+=1
    #写入点、面的数量
    lines.insert(0,str(nVCount)+'\n')
    lines.insert(nVCount+1,str(nFCount)+'\n')
    #写回硬盘
    file.seek(0,0)
    #s='\n'.join(lines)
    file.writelines(lines)
    #file.write(s)
    file.close()
    pass

# 存储prostate的相关参以及原图
def SaveProstate():
  #存储nii
  original_name=ctx.field("PatientID").value+"_original.nii"
  prostate_name=ctx.field("PatientID").value+"_prostate.nii"
  ctx.field("itkImageFileWriter.fileName").value=os.path.join(ctx.field("NiiDirectory").value,original_name)
  ctx.field("itkImageFileWriter1.fileName").value=os.path.join(ctx.field("NiiDirectory").value,prostate_name)
  ctx.field("itkImageFileWriter.save").touch()
  ctx.field("itkImageFileWriter1.save").touch()
  print("nii of prostate mask saved")
  #存储raw
  dst_root_path=os.path.join(ctx.field("DestinationDataDirectory").value,ctx.field("PatientID").value)
  dst_root_path=os.path.join(dst_root_path,"raw")
  original_name=ctx.field("PatientID").value+"_original.raw"
  prostate_name=ctx.field("PatientID").value+"_prostate.raw"
  ctx.field("ImageSave1.filename").value=os.path.join(ctx.field("RawDirectory").value,original_name)
  ctx.field("ImageSave1.save").touch()
  Nii2Raw(ctx.field("itkImageFileWriter1.fileName").value,os.path.join(ctx.field("RawDirectory").value,prostate_name))
  print("raw of prostate mask saved")
  #存储obj网格数据
  print("测试路径")
  print(os.path.join(ctx.field("RawDirectory").value,prostate_name))
  ctx.field("ImageLoad3.filename").value=os.path.join(ctx.field("RawDirectory").value,prostate_name)
  prostate_name=ctx.field("PatientID").value+"_prostate.obj"
  ctx.field("WEMSave3.filename").value=os.path.join(ctx.field("ObjDirectory").value,prostate_name)
  ctx.field("WEMSave3.save").touch()
  transformObj(os.path.join(ctx.field("ObjDirectory").value,prostate_name))
  print("obj of prostate mask saved")
  pass

# 存储lesion的相关参数
def SaveLesion():
  #存储nii
  lesion_name=ctx.field("PatientID").value+"_lesion.nii"
  ctx.field("itkImageFileWriter2.fileName").value=os.path.join(ctx.field("NiiDirectory").value,lesion_name)
  ctx.field("itkImageFileWriter2.save").touch()
  print("nii of lesion mask saved")
  #存储raw
  lesion_name=ctx.field("PatientID").value+"_lesion.raw"
  Nii2Raw(ctx.field("itkImageFileWriter2.fileName").value,os.path.join(ctx.field("RawDirectory").value,lesion_name))
  print("raw of lesion mask saved")
  #存储obj网格数据
  ctx.field("ImageLoad3.filename").value=os.path.join(ctx.field("RawDirectory").value,lesion_name)
  lesion_name=ctx.field("PatientID").value+"_lesion.obj"
  ctx.field("WEMSave3.filename").value=os.path.join(ctx.field("ObjDirectory").value,lesion_name)
  ctx.field("WEMSave3.save").touch()
  transformObj(os.path.join(ctx.field("ObjDirectory").value,lesion_name))
  print("obj of lesion mask saved")
  pass

# 存储rectum的相关参数
def SaveRectum():
  #存储nii
  rectum_name=ctx.field("PatientID").value+"_rectum.nii"
  ctx.field("itkImageFileWriter6.fileName").value=os.path.join(ctx.field("NiiDirectory").value,rectum_name)
  ctx.field("itkImageFileWriter6.save").touch()
  print("nii of rectum mask saved")
  #存储raw
  rectum_name=ctx.field("PatientID").value+"_rectum.raw"
  Nii2Raw(ctx.field("itkImageFileWriter6.fileName").value,os.path.join(ctx.field("RawDirectory").value,rectum_name))
  print("raw of rectum mask saved")
  #存储obj网格数据
  ctx.field("ImageLoad3.filename").value=os.path.join(ctx.field("RawDirectory").value,rectum_name)
  rectum_name=ctx.field("PatientID").value+"_rectum.obj"
  ctx.field("WEMSave3.filename").value=os.path.join(ctx.field("ObjDirectory").value,rectum_name)
  ctx.field("WEMSave3.save").touch()
  transformObj(os.path.join(ctx.field("ObjDirectory").value,rectum_name))
  print("obj of rectum mask saved")
  #计算最大截面位置
  CalBasePlane()
  pass

# 计算并存储直肠中轴线最大截面位置
def CalBasePlane():
  points,vectors,max_index=FindLargestSection() #提取直肠中轴线,找到最大截面位置
  attitude=CalAttitude(points,vectors,max_index) #计算MRI模拟采样base平面的一组姿态参数
  WriteConfig(attitude) #根据一组病人数据和MRI模拟采样base平面姿态，写两个ini配置文件
  return

def FindLargestSection():
  """
  提取直肠中轴线,找到最大截面位置
  Args:
    none
  Returns:
    points:   直肠中轴线各点  始于(0,0,0)的wld坐标
    vectors:  起点到第i点的方向向量 始于(0,0,0)的wld坐标
    max_index:前列腺最大截面处 对应的点下标
  """
  #提取直肠中轴线
  rectum_name=ctx.field("PatientID").value+"_rectum.raw"
  ctx.field("ImageLoad4.filename").value=os.path.join(ctx.field("RawDirectory").value,rectum_name)
  ctx.field("ImageLoad4.rawX").value=ctx.field("Info2.sizeX").value
  ctx.field("ImageLoad4.rawY").value=ctx.field("Info2.sizeY").value
  ctx.field("ImageLoad4.rawZ").value=ctx.field("Info2.sizeZ").value
  ctx.field("ImagePropertyConvert2.voxelSizeX").value=ctx.field("Info2.voxelSizeX").value
  ctx.field("ImagePropertyConvert2.voxelSizeY").value=ctx.field("Info2.voxelSizeY").value
  ctx.field("ImagePropertyConvert2.voxelSizeZ").value=ctx.field("Info2.voxelSizeZ").value
  ctx.field("ImageLoad4.load").touch()
  ctx.field("MarkerListInspector.update").touch()
  num_points=ctx.field("MarkerListInspector.numMarkers").value
  points=np.zeros((num_points,3))
  for i in range(num_points):
    ctx.field("MarkerListInspector.currentMarker").value=i
    points[i]=ctx.field("MarkerListInspector.markerPosition").value
  #翻转 使得低下标点对应直肠外侧(肛门一侧)
  if(ctx.field("RectumReverse").value):
    points=points[::-1]
    print("Rectum points reversed")
  #沿直肠中轴线遍历截面 找到截取前列腺最大截面
  prostate_name=ctx.field("PatientID").value+"_prostate.raw"
  ctx.field("ImageLoad5.filename").value=os.path.join(ctx.field("RawDirectory").value,prostate_name)
  ctx.field("ImageLoad5.rawX").value=ctx.field("Info2.sizeX").value
  ctx.field("ImageLoad5.rawY").value=ctx.field("Info2.sizeY").value
  ctx.field("ImageLoad5.rawZ").value=ctx.field("Info2.sizeZ").value
  ctx.field("ImagePropertyConvert3.voxelSizeX").value=ctx.field("Info2.voxelSizeX").value
  ctx.field("ImagePropertyConvert3.voxelSizeY").value=ctx.field("Info2.voxelSizeY").value
  ctx.field("ImagePropertyConvert3.voxelSizeZ").value=ctx.field("Info2.voxelSizeZ").value
  ctx.field("ImageLoad5.load").touch()
  vectors=points.copy() #vector[i,:]用于记录起点到第i点的方向向量
  max_area=-1
  max_index=-1
  for i in range(4,points.shape[0]):  #从第4个点开始计算直肠截面积，避免前2个点误差过大
    vectors[i,:]=points[i,:]-points[0,:]
    print("vector "+str(i)+"\t") #测试用 待删除 TODO
    print(vectors[i]) #测试用 待删除 TODO
    #自动计算参考平面，通过field connection更新平面参数至MPR
    ctx.field("ComposePlane1.point").value=points[i].tolist() #设置平面上的点
    ctx.field("ComposePlane1.normal").value=vectors[i].tolist() #设置平面法向量
    #MRP截取平面
    #比较 计算前景区域大小
    ctx.field("ImageStatistics.update").touch()
    print("area of section "+str(i)+'\t'+str(ctx.field("ImageStatistics.innerVoxels").value)+"\n")#测试用 待删除 TODO
    if(ctx.field("ImageStatistics.innerVoxels").value>max_area):
      max_index=i
      max_area=ctx.field("ImageStatistics.innerVoxels").value
  print("max_index:\t"+str(max_index))
  return points,vectors,max_index

def CalAttitude(points,vectors,max_index):
  """
  计算MRI模拟采样base平面的一组姿态参数
  Args:
    points:   直肠中轴线各点
    vectors:  起点到第i点的方向向量
    max_index:前列腺最大截面处 对应的点下标
  Returns:
    attitude: MRI模拟采样超声探头姿态 ScanCenter点,RightDir向量,UpDir向量,MoveDir向量
              wld坐标(非真实wld坐标，而是(0,0,0)对应itk(0,0,0)的伪wld坐标)
  """

  # 定位到最大截面
  ctx.field("ComposePlane1.point").value=points[max_index].tolist() #设置平面上的点
  ctx.field("ComposePlane1.normal").value=vectors[max_index].tolist() #设置平面法向量
  # 获取三个关键点坐标
  prostate_center=np.zeros(3) #前列腺中心点 用于计算UpDir
  start_pt=np.zeros(3) #直肠中轴线起点
  base_rectum_pt=np.zeros(3) #最大截面位置对应的直肠中轴点
  prostate_center[0]=(ctx.field("ImageStatistics.bBoxInX1").value+ctx.field("ImageStatistics.bBoxInX2").value)/2
  prostate_center[1]=(ctx.field("ImageStatistics.bBoxInY1").value+ctx.field("ImageStatistics.bBoxInY2").value)/2
  prostate_center[2]=0
  ctx.field("WorldVoxelConvert.voxelPos").value=prostate_center.tolist()
  prostate_center=np.array(ctx.field("WorldVoxelConvert.worldPos").value)
  start_pt=points[0]
  base_rectum_pt=points[max_index]
  print("prostate_center:\t"+str(prostate_center))
  print("start_pt:\t"+str(start_pt))
  print("base_rectum_pt"+str(base_rectum_pt))
  # 计算一组姿态参数
  attitude=np.zeros((4,3))  #一组姿态参数 ScanCenter,RightDir,UpDir,MoveDir
  attitude[0]=base_rectum_pt
  attitude[3]=base_rectum_pt-start_pt
  attitude[1]=np.cross(attitude[3],prostate_center-base_rectum_pt)
  attitude[2]=np.cross(attitude[1],attitude[3])
  print("attitude (0,0,0 wld)")
  print(attitude)


  '''
  #计算base平面的姿态参数(WLD)
  #关于base平面的三个关键点，计算坐标
  #  获取三个点的真实wld坐标
  prostate_center=np.zeros(3) #前列腺中心点 用于计算UpDir
  start_pt=np.zeros(3) #直肠中轴线起点
  base_rectum_pt=np.zeros(3) #最大截面位置对应的直肠中轴点
  prostate_center[0]=(ctx.field("ImageStatistics.bBoxInX1").value+ctx.field("ImageStatistics.bBoxInX2").value)/2
  prostate_center[1]=(ctx.field("ImageStatistics.bBoxInY1").value+ctx.field("ImageStatistics.bBoxInY2").value)/2
  prostate_center[2]=0
  ctx.field("WorldVoxelConvert.voxelPos").value=prostate_center.tolist()
  prostate_center=np.array(ctx.field("WorldVoxelConvert.worldPos").value)
  start_pt=points[0]
  base_rectum_pt=points[max_index]
  print("prostate center\t"+str(prostate_center))
  print("start point\t"+str(start_pt))
  print("base rectum pt\t"+str(base_rectum_pt))
  #将三个点转到itk坐标
  ctx.field("WorldVoxelConvert1.worldPos").value=prostate_center.tolist()
  prostate_center=np.array(ctx.field("WorldVoxelConvert1.voxelPos").value)
  ctx.field("WorldVoxelConvert1.worldPos").value=start_pt.tolist()
  start_pt=np.array(ctx.field("WorldVoxelConvert1.voxelPos").value)
  ctx.field("WorldVoxelConvert1.worldPos").value=base_rectum_pt.tolist()
  base_rectum_pt=np.array(ctx.field("WorldVoxelConvert1.voxelPos").value)
  #将三个点转到始于(0,0,0)的wld坐标
  voxel_size=np.zeros((3))
  voxel_size[0]=ctx.field("Info4.voxelSizeX").value
  voxel_size[1]=ctx.field("Info4.voxelSizeY").value
  voxel_size[2]=ctx.field("Info4.voxelSizeZ").value
  prostate_center=prostate_center*voxel_size
  start_pt=start_pt*voxel_size
  base_rectum_pt=base_rectum_pt*voxel_size
  #计算一组姿态参数
  attitude=np.zeros((4,3))  #一组姿态参数 ScanCenter,RightDir,UpDir,MoveDir
  attitude[0]=base_rectum_pt
  attitude[3]=base_rectum_pt-start_pt
  attitude[1]=np.cross(attitude[3],prostate_center-base_rectum_pt)
  attitude[2]=np.cross(attitude[1],attitude[3])
  print("attitude (0,0,0 wld)")
  print(attitude)
  '''

  return attitude

def WriteConfig(attitude):
  """
  根据一组病人数据和MRI模拟采样base平面姿态，写两个ini配置文件
  Args:
    attitude: MRI模拟采样超声探头姿态 ScanCenter点,RightDir向量,UpDir向量,MoveDir向量
              wld坐标(非真实wld坐标，而是(0,0,0)对应itk(0,0,0)的伪wld坐标)
  Returns:
    none
  """
  print("start writing config")
  dst_root_path=os.path.join(ctx.field("DestinationDataDirectory").value,ctx.field("PatientID").value)
  #SurgicalPlan
  surgical_plan_path=os.path.join(dst_root_path,"SurgicalPlan.ini")
  s_config=configparser.ConfigParser()

  s_config.add_section("PATH")
  s_config.set("PATH","mri_filename",os.path.join("raw",ctx.field("PatientID").value+"_original.raw"))
  s_config.set("PATH","prostate_mask_filename",os.path.join("raw",ctx.field("PatientID").value+"_prostate.raw"))
  s_config.set("PATH","lesion_mask_filename",os.path.join("raw",ctx.field("PatientID").value+"_lesion.raw"))
  s_config.set("PATH","rectum_mask_filename",os.path.join("raw",ctx.field("PatientID").value+"_rectum.raw"))
  s_config.set("PATH","prostate_surface_filename",os.path.join("obj",ctx.field("PatientID").value+"_prostate.obj"))
  s_config.set("PATH","lesion_surface_fileName",os.path.join("obj",ctx.field("PatientID").value+"_lesion.obj"))
  s_config.set("PATH","rectum_surface_fileName",os.path.join("obj",ctx.field("PatientID").value+"_rectum.obj"))

  s_config.add_section("ImageSize")
  s_config.set("ImageSize","CX",ctx.field("Info2.sizeX").value)
  s_config.set("ImageSize","CY",ctx.field("Info2.sizeY").value)
  s_config.set("ImageSize","CZ",ctx.field("Info2.sizeZ").value)

  s_config.add_section("VoxelSize")
  s_config.set("VoxelSize","ResX",ctx.field("Info2.voxelSizeX").value)
  s_config.set("VoxelSize","ResY",ctx.field("Info2.voxelSizeY").value)
  s_config.set("VoxelSize","ResZ",ctx.field("Info2.voxelSizeZ").value)
  s_config.write(open(surgical_plan_path,"w"))
  #AnalyseProcess
  analyse_procees_path=os.path.join(dst_root_path,"AnalyseProcess.ini")
  a_config=configparser.ConfigParser()

  a_config.add_section("ImageSize")
  a_config.set("ImageSize","x",ctx.field("Info2.sizeX").value)
  a_config.set("ImageSize","y",ctx.field("Info2.sizeY").value)
  a_config.set("ImageSize","z",ctx.field("Info2.sizeZ").value)

  a_config.add_section("VoxelSize")
  a_config.set("VoxelSize","x",ctx.field("Info2.voxelSizeX").value)
  a_config.set("VoxelSize","y",ctx.field("Info2.voxelSizeY").value)
  a_config.set("VoxelSize","z",ctx.field("Info2.voxelSizeZ").value)

  a_config.add_section("ScanCenter")
  a_config.set("ScanCenter","x",attitude[0][0])
  a_config.set("ScanCenter","y",attitude[0][1])
  a_config.set("ScanCenter","z",attitude[0][2])
  a_config.add_section("RightDir")
  a_config.set("RightDir","x",attitude[1][0])
  a_config.set("RightDir","y",attitude[1][1])
  a_config.set("RightDir","z",attitude[1][2])
  a_config.add_section("UpDir")
  a_config.set("UpDir","x",attitude[2][0])
  a_config.set("UpDir","y",attitude[2][1])
  a_config.set("UpDir","z",attitude[2][2])
  a_config.add_section("MoveDir")
  a_config.set("MoveDir","x",attitude[3][0])
  a_config.set("MoveDir","y",attitude[3][1])
  a_config.set("MoveDir","z",attitude[3][2])
  a_config.write(open(analyse_procees_path,"w"))
  return

#将int16 nii的mask，转存为uint8 raw的mask 
def Nii2Raw(src_name,dst_name):
  '''
  args:
    src_name: 源文件名(nii,int16)
    dst_name: 目� �文件名(raw,uint8)
  returns:
    none
  '''
  temp_name=os.path.join(os.path.split(src_name)[0],"temp.nii")
  #int16 nii转存为uint8 nii
  ctx.field("itkImageFileReader.fileName").value=src_name
  ctx.field("itkImageFileReader.open").touch()
  ctx.field("itkImageFileWriter4.fileName").value=temp_name
  ctx.field("itkImageFileWriter4.save").touch()
  #uint8 nii转存为uint8 raw
  ctx.field("itkImageFileReader1.fileName").value=temp_name
  ctx.field("itkImageFileReader1.open").touch()
  ctx.field("ImageSave.filename").value=dst_name
  ctx.field("ImageSave.save").touch()
  #释放资源
  ctx.field("itkImageFileReader.close").touch()
  ctx.field("itkImageFileReader1.close").touch()
  os.remove(temp_name)

# 输出txt文档,包含 t2序列文件名、adc序列文件名 t2序列的每一帧对应adc序列的帧数
def SaveT2ADCDirectory():
  if(len(ctx.field("DestinationProstatePath").value)!=0):
    filename=ctx.field("DestinationProstatePath").value
  elif(len(ctx.field("DestinationLesionPath").value)!=0):
    filename=ctx.field("DestinationLesionPath").value
  else:
    pass
  # 取t2序列世界坐肠第2列，对应其z'轴，即每个横断面的法向量,将其归一化，记为v_normal
  v_normal=[]
  v_normal.append(ctx.field("Info2.a02").value)
  v_normal.append(ctx.field("Info2.a12").value)
  v_normal.append(ctx.field("Info2.a22").value)
  k=math.sqrt(v_normal[0]*v_normal[0]+v_normal[1]*v_normal[1]+v_normal[2]*v_normal[2])
  v_normal[0]/=k
  v_normal[1]/=k
  v_normal[2]/=k
  print(v_normal)
  # 对t2序列上的每一帧，其与t2序列第0帧的距离为 帧数*voxelSizeZ
  d_t2=[]
  for i in range(ctx.field("Info2.sizeZ").value):
    d_t2.append(i*ctx.field("Info2.voxelSizeZ").value)
  # 对adc序列，先求其第0帧与t2序列第0帧之间的距离 记为d
  v_t0=[] #t2序列坐肠(0,0,0)点对应的世界坐肠
  v_a0=[] #adc序列坐肠(0,0,0)点对应的世界坐肠
  v_dif=[] #v_a0-v_t0
  v_t0.append(ctx.field("Info2.a03").value)
  v_t0.append(ctx.field("Info2.a13").value)
  v_t0.append(ctx.field("Info2.a23").value)
  v_a0.append(ctx.field("Info1.a03").value)
  v_a0.append(ctx.field("Info1.a13").value)
  v_a0.append(ctx.field("Info1.a23").value)
  v_dif.append(v_a0[0]-v_t0[0])
  v_dif.append(v_a0[1]-v_t0[1])
  v_dif.append(v_a0[2]-v_t0[2])
  distance_00=v_dif[0]*v_normal[0]+v_dif[1]*v_normal[1]+v_dif[2]*v_normal[2]
  # 类似的，adc序列的每帧与t2序列第0帧之间的距离为 帧数*voxelSizeZ+d
  d_adc=[]
  for i in range(ctx.field("Info1.sizeZ").value):
    d_adc.append(i*ctx.field("Info1.voxelSizeZ").value+distance_00)
  # 求t2序列每一帧对应的adc序列帧数
  dic=[]
  for i in range(len(d_t2)):
    min=9999
    min_index=-1
    for j in range(len(d_adc)):
      distance=abs(d_t2[i]-d_adc[j])
      if(distance<min):
        min=distance
        min_index=j
    dic.append(min_index)
  # 写入txt文件
  filename=os.path.join(filename,ctx.field("DicomTagViewer.tagValue1").value+"_"+"dictionary.txt")
  print("!!! filename")
  print(filename)
  f=open(filename,'w')
  f.write(ctx.field("T2SeriesPath").value+"\n")
  f.write(ctx.field("ADCSeriesPath").value+"\n")
  for i in range(len(dic)):
    f.write(str(dic[i])+' ')
  f.close()
  pass


def SetProstateAlpha():
  alpha=ctx.field("ProstateFaceAlpha").value
  ctx.field("SoWEMRenderer.faceAlphaValue").value=alpha
  pass

def SetLesionAlpha():
  alpha=ctx.field("LesionFaceAlpha").value
  ctx.field("SoWEMRenderer1.faceAlphaValue").value=alpha
  pass

def SetRectumAlpha():
  alpha=ctx.field("RectumFaceAlpha").value
  ctx.field("SoWEMRenderer2.faceAlphaValue").value=alpha
  pass
