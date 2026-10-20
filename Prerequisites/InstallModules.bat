echo off
pushd %~dp0


cd ..

IF NOT DEFINED TC_TMP_DIR (
	setx TC_TMP_DIR "E:\Temp" /m
)

IF NOT DEFINED MIG_HOME  (
	echo Setting MIG_HOME
	setx MIG_HOME "%cd%" && echo MIG_HOME Set Successfully || echo Failed to set MIG_HOME
)

echo.

cd .\Prerequisites

echo Installing OracleDB Module...
echo.

pip install oracledb --no-index --find-links=oracleDB && echo oracleDB Installed

echo.
echo.
echo Installing pyodbc Module...

echo.
pip install pyodbc --no-index --find-links=pyodbc && echo pyodbc Installed 
echo.
echo.
echo Installing Numpy Module...s

echo.
pip install numpy --no-index --find-links=numpy && echo numpy Installed 
echo.
echo.
echo Installing matplotlib Module...

echo.
pip install matplotlib --no-index --find-links=matplotlib && echo matplotlib Installed 
echo.

echo.
echo Installing PyQt6 Module...
pip install PyQt6 --no-index --find-links=PyQt && echo PyQt6 Installed 
echo.
echo.

echo.
echo Installing PyQt-Charts Module...
pip install PyQt6-Charts --no-index --find-links=PyQt && echo PyQt6-Charts Installed 
echo.
echo.

echo.
echo Installing pyqtgraph Module...
pip install pyqtgraph --no-index --find-links=PyQt && echo pyqtgraphs Installed 

echo.
echo Installing Requests Module...
pip install requests --no-index --find-links=requests && echo requests Installed 

echo.
echo Installing uvicorn Module...
pip install uvicorn --no-index --find-links=uvicorn && echo uvicorn Installed 

echo.
echo Installing FastAPI Module...
pip install FastAPI --no-index --find-links=FastAPI && echo FastAPI Installed 

echo.
echo Checking sqlite3 module version...
echo.

echo Version:
echo --------
python -c "import sqlite3; print(sqlite3.sqlite_version)" || echo SQLite3 is not installed. Verify Python installation.
echo.
echo.
echo Module installation complete
echo.
pause
exit