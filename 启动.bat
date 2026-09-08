@echo off
chcp 936 >nul
title 小狗桌宠

cd /d "%~dp0"

echo ========================================
echo   小狗桌宠 - 启动中
echo ========================================
echo.

REM ===== 检测 Python =====
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 环境！
    echo 请先双击运行 "安装环境.bat" 安装 Python 和依赖库。
    echo.
    pause
    exit /b 1
)

echo [检测] Python 路径：
where python
echo.
echo [检测] Python 版本：
python --version
echo.

REM ===== 检测 Pillow =====
python -c "import PIL; print('[检测] Pillow 版本：' + PIL.__version__)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 未检测到 Pillow 库，正在自动安装...
    python -m pip install --upgrade pip
    python -m pip install Pillow
    if %errorlevel% neq 0 (
        echo.
        echo [错误] Pillow 安装失败！
        echo 请检查网络连接，或手动执行：pip install Pillow
        echo.
        pause
        exit /b 1
    )
    echo [OK] Pillow 安装成功
    echo.
) else (
    python -c "import PIL; print('[OK] Pillow 版本：' + PIL.__version__)"
    echo.
)

REM ===== 检测 tkinter =====
python -c "import tkinter; print('[OK] tkinter 可用')" >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 当前 Python 未安装 tkinter 模块！
    echo tkinter 是 Python 标准库，通常随 Python 一起安装。
    echo 如果是自行编译的 Python，请重新安装官方版本并勾选 tcl/tk 组件。
    echo.
    pause
    exit /b 1
)

echo [检测] 配置文件：
if exist config.json (
    echo [OK] config.json 存在
) else (
    echo [提示] config.json 不存在，将使用默认配置
)
echo.

echo ========================================
echo   启动程序...
echo ========================================
echo.

REM ===== 运行主程序，捕获错误输出 =====
python main.py > error_log.txt 2>&1
set EXIT_CODE=%errorlevel%

if %EXIT_CODE% neq 0 (
    echo.
    echo ========================================
    echo   程序异常退出，错误码：%EXIT_CODE%
    echo ========================================
    echo.
    echo ----- 错误详情 -----
    type error_log.txt
    echo --------------------
    echo.
    echo 错误日志已保存到：error_log.txt
    echo 请将以上内容截图反馈。
    echo.
    pause
    exit /b %EXIT_CODE%
)

REM 正常退出时清理错误日志
if exist error_log.txt del error_log.txt
