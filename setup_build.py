"""
Скрипт для сборки standalone-приложения с помощью PyInstaller
"""

import os
import sys
import subprocess
from pathlib import Path


def install_dependencies():
    """Устанавливает необходимые зависимости"""
    print("Установка зависимостей...")
    
    # Устанавливаем PyQt6 и другие зависимости
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    print("Зависимости установлены!")


def build_executable():
    """Собирает standalone-исполнительный файл с помощью PyInstaller"""
    print("Начинаем сборку приложения...")
    
    # Проверяем, установлен ли PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller не найден, устанавливаем...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Команда для PyInstaller
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",  # Создать один исполняемый файл
        "--windowed",  # Не показывать консольное окно (для GUI-приложений)
        "--name=PostgreSQL_Backup_Manager",  # Имя выходного файла
        "main.py"  # Входной файл
    ]
    
    print(f"Запуск PyInstaller с командой: {' '.join(pyinstaller_cmd)}")
    
    result = subprocess.run(pyinstaller_cmd, check=True)
    
    if result.returncode == 0:
        print("Сборка завершена успешно!")
        print("Исполняемый файл находится в папке 'dist'")
    else:
        print("Ошибка при сборке приложения")
        sys.exit(1)


def main():
    """Основная функция"""
    print("Сборка PostgreSQL Backup Manager в standalone-приложение")
    
    # Устанавливаем зависимости
    install_dependencies()
    
    # Собираем приложение
    build_executable()


if __name__ == "__main__":
    main()