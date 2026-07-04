@echo off
setlocal enabledelayedexpansion

title 管件识别系统 v2.0

echo ============================================
echo   管件智能识别系统 - Pipe Annotator v2.0
echo ============================================
echo.

:: 检查 Python
py --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYCMD=py
    goto :check_ok
)
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYCMD=python
    goto :check_ok
)
echo [错误] 未检测到 Python！请先安装 Python 3.10+
echo 下载地址: https://www.python.org/downloads/
pause
exit /b 1

:check_ok
echo [1/3] 检测 Python 版本...
for /f "tokens=2" %%v in ('!PYCMD! --version 2^>^&1') do echo       已安装: Python %%v

set VENV_PYTHON=venv\Scripts\python.exe
set VENV_PIP=venv\Scripts\pip.exe

:: 检查 venv 是否可用（迁移来的 venv 路径可能不对）
set VENV_OK=0
if exist "venv\" (
    !VENV_PYTHON! --version >nul 2>&1
    if !errorlevel! equ 0 (
        !VENV_PIP! --version >nul 2>&1
        if !errorlevel! equ 0 set VENV_OK=1
    )
)
if !VENV_OK! equ 0 (
    if exist "venv\" (
        echo [2/3] 检测到旧 venv 不可用（路径已变），正在重建...
        rmdir /s /q venv
    ) else (
        echo [2/3] 创建虚拟环境...
    )
    !PYCMD! -m venv venv
    echo        venv 创建完成
) else (
    echo [2/3] 虚拟环境已就绪
)

:: 安装依赖
echo [3/3] 检查并安装依赖...
!VENV_PIP! install -r requirements.txt -q

echo.
echo ============================================
echo   启动应用程序...
echo ============================================
echo.

!VENV_PYTHON! main.py

if !errorlevel! neq 0 (
    echo.
    echo [错误] 程序异常退出，错误码: !errorlevel!
    pause
)

endlocal
