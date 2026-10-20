echo off
title Clear Temp Directory

set suffixes=%1
set interval=%2

IF NOT DEFINED MIG_HOME (
    echo Please define MIG_HOME
    pause
    exit
)

IF DEFINED TC_TMP_DIR (
    
    cd /d %TC_TMP_DIR%
    set tempDir=%TC_TMP_DIR%

    py %MIG_HOME%\Bin\HelperMethods\TempClearer.py %suffixes% %interval% %tempDir%
    cmd /k



) ELSE (
    echo Please Define TC_TMP_DIR
    pause
    exit
)