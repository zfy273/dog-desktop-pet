@echo off
chcp 936 >nul
title 小狗桌宠

cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 环境！
    echo 请先双击运行 "安装环境.bat" 安装 Python 和依赖库。
    echo.
    pause
    exit /b 1
)

python -c "import PIL" >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 未检测到 Pillow 库，正在自动安装...
    python -m pip install Pillow
    if %errorlevel% neq 0 (
        echo [错误] Pillow 安装失败，请手动运行 "安装环境.bat"
        pause
        exit /b 1
    )
)

python main.py

if %errorlevel% neq 0 (
    echo.
    echo 程序异常退出，错误码：%errorlevel%
    pause
)
