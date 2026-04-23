@echo off
chcp 65001 >nul
cd /d "%~dp0"
title MiniMax Agent 启动器

:menu
cls
echo ========================================
echo   MiniMax Agent 网页版启动器
echo ========================================
echo.
echo  [1] 启动服务
echo  [2] 重启服务
echo  [3] 退出
echo.
echo  提示：服务运行时可按 Ctrl+C 停止
echo        然后选择 [2] 重启或 [3] 退出
echo.
echo ========================================
set /p choice="请选择操作 (1/2/3): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto restart
if "%choice%"=="3" goto exit
if "%choice%"=="r" goto restart
if "%choice%"=="R" goto restart
if "%choice%"=="q" goto exit
if "%choice%"=="Q" goto exit
echo.
echo 无效选择，请重新输入...
timeout /t 2 >nul
goto menu

:start
echo.
echo 正在启动 MiniMax Agent 网页版...
echo 启动后请访问 http://127.0.0.1:5000
echo.
echo ┌────────────────────────────────────────┐
echo │  提示：如需停止服务，请按 Ctrl+C       │
echo │       然后在提示时：                   │
echo │       按 Y 完全退出程序                │
echo │       按 N 返回此菜单可选择重启        │
echo └────────────────────────────────────────┘
echo.
python app.py
echo.

:: 检查是否是被 Ctrl+C 中断（errorlevel 通常为非零值）
if errorlevel 1 (
    echo.
    echo ┌────────────────────────────────────────┐
    echo │  服务已停止                            │
    echo └────────────────────────────────────────┘
    echo.
    echo 按任意键返回主菜单...
    pause >nul
)
goto menu

:restart
echo.
echo 正在重启 MiniMax Agent 网页版...
echo.
timeout /t 1 >nul
goto start

:exit
echo.
echo 感谢使用，再见！
timeout /t 1 >nul
exit
