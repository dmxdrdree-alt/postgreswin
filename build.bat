@echo off
REM Build script for PostgreSQL Backup Manager on Windows
echo Building PostgreSQL Backup Manager...

REM Install dependencies
pip install -r requirements.txt

REM Build the executable
python build.py

echo Build process completed!
pause