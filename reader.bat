@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo        TXT 文件朗读工具
echo ========================================
echo.

set /p folder_path=请输入txt文件所在的文件夹路径: 

if not exist "%folder_path%" (
    echo 错误: 文件夹不存在！
    pause
    exit /b
)

:: 获取所有txt文件并排序
set count=0
for /f "delims=" %%f in ('dir /b /a-d "%folder_path%\*.txt" 2^>nul ^| sort') do (
    set /a count+=1
    set "file_!count!=%%f"
)

if %count% equ 0 (
    echo 该文件夹下没有txt文件！
    pause
    exit /b
)

echo.
echo 找到 %count% 个txt文件:
echo ----------------------------------------

for /L %%i in (1,1,%count%) do (
    echo %%i. !file_%%i!
)

echo ----------------------------------------
echo.

set /p choice=请选择要朗读的文件编号 (输入 all 朗读全部): 

if /i "%choice%" equ "all" (
    :: 朗读所有文件
    for /L %%i in (1,1,%count%) do (
        echo.
        echo ========================================
        echo 正在朗读: !file_%%i!
        echo ========================================
        call :read_file "%folder_path%\!file_%%i!"
        if %%i lss %count% (
            echo.
            set /p cont=按回车继续下一篇，输入 q 退出: 
            if /i "!cont!" equ "q" exit /b
        )
    )
) else (
    :: 朗读指定文件
    set /a idx=%choice%
    if !idx! geq 1 if !idx! leq %count% (
        echo.
        echo 正在朗读: !file_!idx!!
        call :read_file "%folder_path%\!file_!idx!!"
    ) else (
        echo 无效的选择！
    )
)

echo.
echo 朗读完成！
pause
exit /b

:read_file
:: 使用PowerShell进行朗读
powershell -Command ^
    "$content = Get-Content -Path '%~1' -Encoding UTF8 -Raw; " ^
    "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; " ^
    "$speak.Rate = 0; " ^
    "$speak.Speak($content);"
exit /b
