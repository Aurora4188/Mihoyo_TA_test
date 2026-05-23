Mihoyo TA 测试工具

========================
工具功能：

- IK/FK 自动创建（三段骨骼）
- IK / FK 对齐（IK Align FK / FK Align IK）
- Stretch 系统（IK / FK）
- Reset 控制器
- IK/FK 切换控制
- 控制器显示管理（Auto Vis / IK Vis / FK Vis）
- 多模块（多套骨骼链）支持

========================
使用方法：

1. 解压 zip 文件到任意位置

2. 打开 Maya

3. 打开 Script Editor，运行以下代码：

import sys
sys.path.append(r"你的工具路径")

import scripts.ui
scripts.ui.showUI()

（例如：sys.path.append(r"D:/mihoyo_tool_test")）

========================
使用流程：

1. 选择三段骨骼（例如：大腿 / 小腿 / 脚）
2. 在 Name 中输入名称（例如：leg_l）
3. 点击 Build IKFK
4. 在 Current Module 下拉框中选择当前模块
5. 使用其他功能（Stretch / Align / Reset / Visibility）

========================
注意事项：

- 每次创建一套 IKFK 系统都需要输入唯一名称
- 工具支持场景中多套骨骼链操作
- 若未创建 IKFK，部分功能会提示错误

========================
说明：

工具内部已自动处理路径加载（跨平台支持 Mac / Windows），无需修改源码路径。