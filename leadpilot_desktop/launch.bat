@echo off
cd /d "%~dp0"
py -3 leadpilot_desktop.py
if errorlevel 1 (
 echo Python 3 could not start the desktop tool.
 pause
)
