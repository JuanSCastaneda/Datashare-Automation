
set u=%1
set p=%2


plmxml_export -u=%u% -p=%p% -g=dba -query="VolumeDBA{Description:DataBase Administrator group.}" -xml_file=.\volume.xml

IF %ERRORLEVEL% NEQ 0 (
    echo An error occurred while exporting current volume config
    exit /B %ERRORLEVEL%
)