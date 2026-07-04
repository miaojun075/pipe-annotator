# -*- coding: utf-8 -*-
"""
管件智能识别系统 - 主入口文件

直接运行即可启动桌面应用程序：
    python main.py

首次运行会自动检查依赖并提示安装。
"""

import sys
import os

# 确保当前目录在 path 中，方便模块导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from src.gui import main

if __name__ == '__main__':
    main()
