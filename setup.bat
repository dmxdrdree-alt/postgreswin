@echo off
REM Скрипт установки PostgreSQL Backup Manager
echo Установка PostgreSQL Backup Manager
echo Пожалуйста, убедитесь, что у вас установлены PostgreSQL клиентские утилиты
echo (pg_dump, pg_restore, psql, pg_isready) перед запуском этого приложения.
echo.
echo Нажмите любую клавишу для продолжения...
pause >nul
start "" "PostgreSQL_Backup_Manager.exe"
