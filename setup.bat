@echo off
setlocal enabledelayedexpansion

title 管件识别系统 - 环境配置

echo ============================================
echo   管件智能识别系统 v2.0 - 环境配置工具
echo ============================================
echo.

:: ── 1. 检查 Python ──
echo [1/4] 检查 Python...

py --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=2" %%v in ('py --version 2^>^&1') do echo        已安装: Python %%v
    set PYCMD=py
    goto :check_ok
)

python --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo        已安装: Python %%v
    set PYCMD=python
    goto :check_ok
)

echo [错误] 未检测到 Python！
echo.
echo 请先安装 Python 3.10+：https://www.python.org/downloads/
echo 安装时务必勾选 "Add Python to PATH"
echo.
pause
exit /b 1

:check_ok
echo.

:: ── 2. 升级 pip ──
echo [2/4] 升级 pip...
!PYCMD! -m pip install --upgrade pip -q
echo        pip 已就绪
echo.

:: ── 3. 重建虚拟环境 ──
echo [3/4] 重建虚拟环境...

:: 直接删旧建新（venv 跨盘拷贝不可用，pip.exe 路径硬编码）
if exist "venv\" (
    echo        删除旧 venv...
    rmdir /s /q venv
)
!PYCMD! -m venv venv
echo        venv 创建完成

set VENV_PIP=venv\Scripts\pip.exe
echo.

:: ── 4. 安装依赖 ──
echo [4/4] 安装依赖包...
echo.
echo    ^(CPU 版 PyTorch，安装较快，约 3-8 分钟^)
echo.

!VENV_PIP! install torch torchvision --index-url https://download.pytorch.org/whl/cpu
if !errorlevel! neq 0 (
    echo [警告] PyTorch 官方源失败，尝试国内镜像...
    !VENV_PIP! install torch torchvision --index-url https://download.pytorch.org/whl/cpu -i https://pypi.tuna.tsinghua.edu.cn/simple
)

!VENV_PIP! install opencv-python opencv-contrib-python numpy Pillow pyyaml openpyxl transformers -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ============================================
echo   环境配置完成！
echo ============================================
echo.
echo 启动方式：
echo   - 双击 run.bat（一键启动）
echo   - 或在命令行执行：venv\Scripts\activate ^&^& python main.py
echo.

pause
endlocal
