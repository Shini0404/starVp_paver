@echo off
REM Backup script for Quest Pro data collection (Windows)
REM Usage: backup_quest_data.bat [backup_directory]

setlocal enabledelayedexpansion

REM Get date for backup folder name
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set DATE=%datetime:~0,8%_%datetime:~8,6%

REM Set backup directory
if "%~1"=="" (
    set BACKUP_DIR=%USERPROFILE%\VR_Study_Backups\Backup_%DATE%
) else (
    set BACKUP_DIR=%~1\Backup_%DATE%
)

REM Create backup directory
mkdir "%BACKUP_DIR%" 2>nul

echo ==========================================
echo Quest Pro Data Backup Script
echo ==========================================
echo Backup directory: %BACKUP_DIR%
echo.

REM Check if adb is available
where adb >nul 2>&1
if errorlevel 1 (
    echo Error: adb not found in PATH
    echo Please add Android SDK platform-tools to your PATH
    echo Or run this script from Unity Android SDK platform-tools directory
    echo.
    echo Unity Android SDK location:
    echo C:\Program Files\Unity\Hub\Editor\2022.3.XX\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\
    pause
    exit /b 1
)

REM Check if device is connected
echo Checking for connected devices...
adb devices | findstr "device$" >nul
if errorlevel 1 (
    echo Error: No Android device connected
    echo Please connect Quest Pro and enable USB debugging
    pause
    exit /b 1
)

echo Found device(s) connected
echo.

REM Quest Pro data path (adjust package name if needed)
set PACKAGE_NAME=com.yourname.vrdatacollector
set DATA_PATH=/sdcard/Android/data/%PACKAGE_NAME%/files/DataCollection

echo Checking for data files...
REM Check if data directory exists
adb shell ls %DATA_PATH% >nul 2>&1
if errorlevel 1 (
    echo Warning: Data directory not found: %DATA_PATH%
    echo Make sure the app has been run at least once
    echo.
    echo Trying to list all data directories...
    adb shell ls /sdcard/Android/data/ | head -20
    pause
    exit /b 1
)

REM Pull data files
echo Copying data files...
adb pull %DATA_PATH% "%BACKUP_DIR%\"

if errorlevel 1 (
    echo.
    echo Error: Backup failed
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Backup completed successfully!
echo ==========================================
echo Backup location: %BACKUP_DIR%
echo.
echo Backed up files:
dir /b "%BACKUP_DIR%\*.csv" 2>nul
echo.

pause
