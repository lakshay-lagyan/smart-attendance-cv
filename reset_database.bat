@echo off
echo Resetting database...
if exist attendance.db del attendance.db
if exist instance\attendance.db del instance\attendance.db
echo Database files removed.
echo Please restart your app - it will create a fresh database with the correct schema.
pause
