@echo off
chcp 936 >nul
title 小狗桌宠 - 环境安装

echo ========================================
echo   小狗桌宠 - 环境检测与自动安装
echo ========================================
echo.

REM ===== 检测 Python =====
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [检测] 未找到 Python，需要安装 Python 3.7 或更高版本。
    echo.
    choice /c YN /n /m "是否自动下载安装 Python 3.12？(Y/N)："
    if errorlevel 2 (
        echo 已取消安装。
        pause
        exit /b 1
    )
    echo 正在下载 Python 安装包，请稍候...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%TEMP%\python_installer.exe' -UseBasicParsing"
    if %errorlevel% neq 0 (
        echo [错误] 下载失败，请检查网络后重试，或手动到 python.org 下载安装。
        pause
        exit /b 1
    )
    echo 正在安装 Python（当前用户，自动添加PATH）...
    start /wait "" "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
    if %errorlevel% neq 0 (
        echo [错误] Python 安装失败，请手动安装后重试。
        pause
        exit /b 1
    )
    del "%TEMP%\python_installer.exe" >nul 2>&1
    echo [OK] Python 安装完成！
    echo.
    echo [注意] PATH 刚更新，请关闭本窗口后重新运行本脚本。
    pause
    exit /b 0
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
    echo [OK] Python 已安装：%PYVER%
)

echo.

REM ===== 检测 tkinter =====
python -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 当前 Python 未安装 tkinter，桌宠将无法运行。
    echo 请重新安装官方 Python 并确保勾选 tcl/tk 组件。
    echo.
) else (
    echo [OK] tkinter 可用
)

echo.

REM ===== 检测/安装 Pillow =====
python -c "import PIL" >nul 2>&1
if %errorlevel% neq 0 (
    echo [检测] 未安装 Pillow 图形库，正在安装...
    python -m pip install --upgrade pip
    python -m pip install Pillow
    if %errorlevel% neq 0 (
        echo [错误] Pillow 安装失败，请检查网络后重试。
        pause
        exit /b 1
    )
    echo [OK] Pillow 安装成功！
) else (
    for /f "tokens=*" %%i in ('python -c "import PIL; print(PIL.__version__)" 2^>^&1') do set PILVER=%%i
    echo [OK] Pillow 已安装：%PILVER%
)

echo.
echo ========================================
echo   环境全部就绪！可以运行 "启动.bat" 了
echo ========================================
echo.
pause
