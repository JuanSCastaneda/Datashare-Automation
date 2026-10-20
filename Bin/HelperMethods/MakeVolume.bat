
set u=%1
set p=%2
set vol=%3
set path=%4
set node=%5
set fscid=%6

echo Creating Volume
make_user -u=%u% -p=%p% -g=dba -volume=%vol% -path=%path% -node=%node% -fscid=%fscid% 

IF %ERRORLEVEL% NEQ 0 (
    echo An error occurred while creating the volume
    exit /B %ERRORLEVEL%
)

echo Assigning to DBA
make_user -u=%u% -p=%p% -g=dba -group=dba -defaultvolume=%vol% -update

IF %ERRORLEVEL% NEQ 0 (
    echo An error occurred while assigning %vol% to dba
    exit /B %ERRORLEVEL%
)
