# mr_preprocessor

# v2.0
前列腺、肿瘤、直肠手动标注。
直肠中轴线提取，最大截面姿态参数

## AnalyseProcess 姿态参数
记录分辨率信息，分别为MRI数据x,y,z方向上的像素数
记录体素大小信息，分别为MRI数据x,y,z方向上的体素大小(mm)
全部使用wld坐标系，以MRI数据(0,0,0)处为坐标原点，考虑体素大小信息
ScanCenter点:截取前列腺最大截面位置，B超探头在直肠中的坐标
RightDir向量:最大截面位置，2维B超图像的x轴正方向对应的三维空间向量
UpDir向量:最大截面位置，2维B超图像的y轴负方向对应的三维空间向量。
MoveDir向量:B超探头前进的方向，即从直肠入口 指向最大截面处B超探头坐标的向量
## SurgicalPlan 
仅图像的像素分辨率、体素大小

# v2.1
与prostate_puncture主程序v1.2联调通过。可以实现对应读取ini配置文件以及raw数据文件。修改了AnalyseProcess.ini和SurgicalPlan.ini两个文件里的一些路径信息和section名。

# v2.2
修复了rectum.obj存储文件名错误的问题
obj文件存储wld坐标信息(itk坐标*voxelSize)

# v2.3
用imagePropertyConvert模块来进行ijk到wld(始于0,0,0)的坐标转换，重写了部分py脚本。修正了截取平面的参数(528行)