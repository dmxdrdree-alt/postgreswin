"""
Скрипт для сборки standalone-исполнительного файла приложения
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def install_dependencies():
    """Устанавливает все необходимые зависимости"""
    print("Установка зависимостей...")
    
    try:
        # Устанавливаем зависимости из requirements.txt
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print(" ✓ Зависимости установлены")
    except subprocess.CalledProcessError as e:
        print(f" ✗ Ошибка установки зависимостей: {e}")
        return False
    
    # Устанавливаем PyInstaller, если не установлен
    try:
        import PyInstaller
        print(" ✓ PyInstaller уже установлен")
    except ImportError:
        print("PyInstaller не найден, устанавливаем...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print(" ✓ PyInstaller установлен")
    
    return True


def build_application():
    """Собирает standalone-исполнительный файл"""
    print("\nНачинаем сборку приложения...")
    
    # Определяем команду для PyInstaller
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",           # Создать один исполняемый файл
        "--windowed",          # Не показывать консольное окно
        "--name=PostgreSQL_Backup_Manager",  # Имя выходного файла
        "--distpath=dist",     # Папка для выходных файлов
        "--workpath=build",    # Временная папка для сборки
        "--specpath=.",        # Папка для .spec файла
        "--clean",             # Очистить временные файлы после сборки
        "main.py"              # Входной файл
    ]
    
    print(f"Выполняем команду: {' '.join(pyinstaller_cmd)}")
    
    try:
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)
        print(" ✓ Сборка завершена успешно")
        
        # Показываем вывод PyInstaller
        if result.stdout:
            print("STDOUT:", result.stdout[-500:])  # Последние 500 символов
        
        return True
    except subprocess.CalledProcessError as e:
        print(f" ✗ Ошибка сборки: {e}")
        print("STDERR:", e.stderr)
        return False


def create_setup_script():
    """Создает скрипт установки для Windows"""
    setup_content = '''@echo off
REM Скрипт установки PostgreSQL Backup Manager
echo Установка PostgreSQL Backup Manager
echo Пожалуйста, убедитесь, что у вас установлены PostgreSQL клиентские утилиты
echo (pg_dump, pg_restore, psql, pg_isready) перед запуском этого приложения.
echo.
echo Нажмите любую клавишу для продолжения...
pause >nul
start "" "PostgreSQL_Backup_Manager.exe"
'''
    
    with open("setup.bat", "w", encoding="utf-8") as f:
        f.write(setup_content)
    
    print(" ✓ Создан скрипт setup.bat")


def main():
    """Основная функция сборки"""
    print("=== Сборка PostgreSQL Backup Manager ===\n")
    
    # Устанавливаем зависимости
    if not install_dependencies():
        print("\nНе удалось установить зависимости. Завершение.")
        sys.exit(1)
    
    # Собираем приложение
    if not build_application():
        print("\nНе удалось собрать приложение. Завершение.")
        sys.exit(1)
    
    # Создаем установочный скрипт
    create_setup_script()
    
    print(f"\n=== Сборка завершена ===")
    print(f"Исполняемый файл находится в папке 'dist'")
    print(f"Путь к файлу: {os.path.abspath('dist/PostgreSQL_Backup_Manager.exe')}")
    
    # Проверяем, существует ли файл
    exe_path = Path("dist/PostgreSQL_Backup_Manager.exe")
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"Размер файла: {size_mb:.2f} MB")
        print("\nПриложение готово к использованию!")


if __name__ == "__main__":
    main()