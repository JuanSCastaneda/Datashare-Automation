ECHO off
pushd %~dp0
rem setlocal EnableDelayedExpansion


:loop
if "%~1"=="" goto done
FOR /f "tokens=1,2 delims==" %%A IN ("%~1") DO (
	IF "%%A"=="-mode" SET MODE=%%B
	IF "%%A"=="-idsm" SET IDSM=%%B
	IF "%%A"=="-order" SET ORDER=%%B
)
shift
goto loop

:done 
rem Check
IF NOT DEFINED MIG_HOME (
	echo Please set MIG_HOME Environment Variable
	pause
	exit
)


set TC_TMP_DIR=E:\Temp


IF "%MODE%" == "DEBUG" (
	echo Entering Debug
	set IMAN_KEEP_SYSTEM_LOG=true
	set UGII_KEEP_SYSTEM_LOG=ON
	set TC_KEEP_SYSTEM_LOG=true
	set TC_TRACEBACK=ON
	set UGII_CHECKING_LEVEL=1
	set GS_LOGGING_ENABLED=TRUE
	set TC_SQL_DEBUG=BJPT
	set TC_Application_Logging=ON
	set TC_POM_SQL_ALL_ROWS=Y

)
set TC_PREFERENCES_OVERLAY_FILE=".\Configuration\%IDSM%.xml"

rem Please change to site%batch
title Datashare5 - %ORDER% - %IDSM%
call ".\TC.bat"

rem Main
py "%MIG_HOME%\Bin\Main.py" %*
cmd /k

