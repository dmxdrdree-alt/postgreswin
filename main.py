"""
PostgreSQL Backup Manager - Графический интерфейс для резервного копирования и восстановления баз данных PostgreSQL
"""

import os
import sys
import subprocess
import threading
import datetime
import shutil
from pathlib import Path
import re
from typing import List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QComboBox, QTextEdit, QProgressBar,
    QGroupBox, QCheckBox, QFileDialog, QMessageBox, QTabWidget, QFormLayout,
    QDialog, QInputDialog, QListWidget, QListWidgetItem, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QThread
from PyQt6.QtGui import QFont, QIcon, QPixmap


class WorkerSignals(QObject):
    """Сигналы для рабочего потока"""
    progress = pyqtSignal(int, str)  # процент, сообщение
    log = pyqtSignal(str)            # сообщение лога
    finished = pyqtSignal(bool)      # успешность выполнения
    error = pyqtSignal(str)          # ошибка


class ConnectionWorker(QThread):
    """Поток для проверки соединения с PostgreSQL"""
    def __init__(self, host, port, username, password):
        super().__init__()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()

    def run(self):
        try:
            # Устанавливаем переменную окружения для пароля
            env = os.environ.copy()
            env['PGPASSWORD'] = self.password
            
            # Пробуем выполнить команду pg_isready
            cmd = ['pg_isready', '-h', self.host, '-p', str(self.port), '-U', self.username]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env
            )
            
            # Удаляем переменную окружения сразу после использования
            del env['PGPASSWORD']
            
            if result.returncode == 0:
                self.signals.progress.emit(100, "Соединение успешно установлено")
                self.signals.finished.emit(True)
            else:
                self.signals.error.emit(f"Не удалось подключиться: {result.stderr}")
                self.signals.finished.emit(False)
                
        except Exception as e:
            self.signals.error.emit(f"Ошибка подключения: {str(e)}")
            self.signals.finished.emit(False)


class DatabaseListWorker(QThread):
    """Поток для получения списка баз данных"""
    def __init__(self, host, port, username, password, pg_path):
        super().__init__()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.pg_path = pg_path
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.log.emit("Получение списка баз данных...")
            
            # Устанавливаем переменную окружения для пароля
            env = os.environ.copy()
            env['PGPASSWORD'] = self.password
            
            # Команда для получения списка баз данных
            cmd = [
                os.path.join(self.pg_path, 'psql'),
                '-h', self.host,
                '-p', str(self.port),
                '-U', self.username,
                '-c', 'SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;',
                '-t'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env
            )
            
            # Удаляем переменную окружения сразу после использования
            del env['PGPASSWORD']
            
            if result.returncode == 0:
                # Извлекаем имена баз данных из вывода
                databases = []
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line and line != 'datname':
                        databases.append(line)
                
                self.signals.log.emit(f"Найдено баз данных: {len(databases)}")
                self.signals.finished.emit(True)
                
                # Отправляем список баз данных как строку
                for db in databases:
                    self.signals.progress.emit(0, f"DB:{db}")
            else:
                self.signals.error.emit(f"Ошибка получения списка баз: {result.stderr}")
                self.signals.finished.emit(False)
                
        except Exception as e:
            self.signals.error.emit(f"Ошибка получения списка баз: {str(e)}")
            self.signals.finished.emit(False)


class BackupWorker(QThread):
    """Поток для создания резервных копий"""
    def __init__(self, host, port, username, password, databases, backup_dir, format_type, max_backups, pg_path):
        super().__init__()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.databases = databases
        self.backup_dir = backup_dir
        self.format_type = format_type  # 'sql' или 'custom'
        self.max_backups = max_backups
        self.pg_path = pg_path
        self.signals = WorkerSignals()

    def run(self):
        try:
            success_count = 0
            total_dbs = len(self.databases)
            
            for i, db_name in enumerate(self.databases):
                try:
                    self.signals.log.emit(f"Начинаем резервное копирование базы: {db_name}")
                    
                    # Устанавливаем переменную окружения для пароля
                    env = os.environ.copy()
                    env['PGPASSWORD'] = self.password
                    
                    # Формируем имя файла резервной копии
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    if self.format_type == 'sql':
                        filename = f"{db_name}_{timestamp}.sql"
                        format_flag = '--format=plain'
                    else:
                        filename = f"{db_name}_{timestamp}.backup"
                        format_flag = '--format=custom'
                    
                    backup_path = os.path.join(self.backup_dir, filename)
                    
                    # Формируем команду pg_dump
                    cmd = [
                        os.path.join(self.pg_path, 'pg_dump'),
                        '-h', self.host,
                        '-p', str(self.port),
                        '-U', self.username,
                        format_flag,
                        '-f', backup_path,
                        db_name
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        env=env
                    )
                    
                    # Удаляем переменную окружения сразу после использования
                    del env['PGPASSWORD']
                    
                    if result.returncode == 0:
                        self.signals.log.emit(f"✓ Резервная копия базы '{db_name}' создана: {filename}")
                        success_count += 1
                        
                        # Очистка старых резервных копий
                        self.cleanup_old_backups(db_name)
                    else:
                        self.signals.log.emit(f"✗ Ошибка при создании резервной копии базы '{db_name}': {result.stderr}")
                        
                except Exception as e:
                    self.signals.log.emit(f"✗ Ошибка при резервном копировании базы '{db_name}': {str(e)}")
                
                # Обновляем прогресс
                progress_percent = int(((i + 1) / total_dbs) * 100)
                self.signals.progress.emit(progress_percent, f"Обработана база {i + 1} из {total_dbs}: {db_name}")
            
            self.signals.finished.emit(success_count == total_dbs)
            
        except Exception as e:
            self.signals.error.emit(f"Ошибка при резервном копировании: {str(e)}")
            self.signals.finished.emit(False)

    def cleanup_old_backups(self, db_name):
        """Удаляет старые резервные копии, оставляя только последние max_backups"""
        try:
            backup_files = []
            for file in os.listdir(self.backup_dir):
                if file.startswith(f"{db_name}_") and (file.endswith('.sql') or file.endswith('.backup')):
                    filepath = os.path.join(self.backup_dir, file)
                    backup_files.append((filepath, os.path.getctime(filepath)))
            
            # Сортируем по времени создания (новые первыми)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Удаляем старые файлы, если их больше max_backups
            for filepath, _ in backup_files[self.max_backups:]:
                os.remove(filepath)
                self.signals.log.emit(f"Удалена старая резервная копия: {os.path.basename(filepath)}")
                
        except Exception as e:
            self.signals.log.emit(f"Ошибка при очистке старых резервных копий для '{db_name}': {str(e)}")


class RestoreWorker(QThread):
    """Поток для восстановления из резервной копии"""
    def __init__(self, backup_file, target_db, host, port, username, password, pg_path):
        super().__init__()
        self.backup_file = backup_file
        self.target_db = target_db
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.pg_path = pg_path
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.log.emit(f"Начинаем восстановление из файла: {os.path.basename(self.backup_file)}")
            self.signals.log.emit(f"Целевая база: {self.target_db}")
            
            # Устанавливаем переменную окружения для пароля
            env = os.environ.copy()
            env['PGPASSWORD'] = self.password
            
            # Определяем тип файла по расширению
            if self.backup_file.lower().endswith('.sql'):
                # Для SQL используем psql
                cmd = [
                    os.path.join(self.pg_path, 'psql'),
                    '-h', self.host,
                    '-p', str(self.port),
                    '-U', self.username,
                    '-d', self.target_db,
                    '-f', self.backup_file
                ]
            else:
                # Для .backup используем pg_restore
                cmd = [
                    os.path.join(self.pg_path, 'pg_restore'),
                    '-h', self.host,
                    '-p', str(self.port),
                    '-U', self.username,
                    '-d', self.target_db,
                    self.backup_file
                ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env
            )
            
            # Удаляем переменную окружения сразу после использования
            del env['PGPASSWORD']
            
            if result.returncode == 0:
                self.signals.log.emit("✓ Восстановление завершено успешно")
                self.signals.progress.emit(100, "Восстановление завершено")
                self.signals.finished.emit(True)
            else:
                self.signals.error.emit(f"Ошибка при восстановлении: {result.stderr}")
                self.signals.finished.emit(False)
                
        except Exception as e:
            self.signals.error.emit(f"Ошибка при восстановлении: {str(e)}")
            self.signals.finished.emit(False)


class ScheduleManager:
    """Класс для управления задачами планировщика Windows"""
    
    @staticmethod
    def create_backup_task(task_name, program_path, backup_params, schedule_type, time_value):
        """Создает задачу в планировщике Windows"""
        try:
            # Создаем скрипт для запуска резервного копирования
            script_content = f'''@echo off
REM Автоматически созданная задача резервного копирования PostgreSQL
echo Запуск резервного копирования...
set /p PGPASSWORD="Введите пароль для PostgreSQL: "
"{program_path}" --backup-scheduled {backup_params}
set PGPASSWORD=
echo Задача резервного копирования завершена.
pause
'''
            
            script_path = os.path.join(os.path.expanduser("~"), f"pg_backup_{task_name.replace(' ', '_')}.bat")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Создаем задачу в планировщике
            if schedule_type == "daily":
                schtasks_cmd = [
                    'schtasks',
                    '/create',
                    '/tn', f'PostgreSQLBackup_{task_name}',
                    '/tr', f'"{script_path}"',
                    '/sc', 'daily',
                    '/st', time_value,
                    '/f'
                ]
            elif schedule_type == "weekly":
                day_map = {
                    "Понедельник": "MON",
                    "Вторник": "TUE", 
                    "Среда": "WED",
                    "Четверг": "THU",
                    "Пятница": "FRI",
                    "Суббота": "SAT",
                    "Воскресенье": "SUN"
                }
                day = day_map.get(time_value.split('_')[1], "MON")
                time_val = time_value.split('_')[0]
                
                schtasks_cmd = [
                    'schtasks',
                    '/create',
                    '/tn', f'PostgreSQLBackup_{task_name}',
                    '/tr', f'"{script_path}"',
                    '/sc', 'weekly',
                    '/d', day,
                    '/st', time_val,
                    '/f'
                ]
            
            result = subprocess.run(schtasks_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, f"Задача '{task_name}' создана успешно"
            else:
                return False, f"Ошибка создания задачи: {result.stderr}"
                
        except Exception as e:
            return False, f"Ошибка создания задачи: {str(e)}"
    
    @staticmethod
    def delete_backup_task(task_name):
        """Удаляет задачу из планировщика Windows"""
        try:
            schtasks_cmd = [
                'schtasks',
                '/delete',
                '/tn', f'PostgreSQLBackup_{task_name}',
                '/f'
            ]
            
            result = subprocess.run(schtasks_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, f"Задача '{task_name}' удалена успешно"
            else:
                return False, f"Ошибка удаления задачи: {result.stderr}"
                
        except Exception as e:
            return False, f"Ошибка удаления задачи: {str(e)}"
    
    @staticmethod
    def list_tasks():
        """Получает список задач резервного копирования"""
        try:
            schtasks_cmd = ['schtasks', '/query']
            
            result = subprocess.run(schtasks_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                tasks = []
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'PostgreSQLBackup_' in line:
                        parts = line.split()
                        if parts:
                            task_name = parts[0]
                            tasks.append(task_name)
                return tasks
            else:
                return []
                
        except Exception:
            return []


class ConnectionTab(QWidget):
    """Вкладка подключения к PostgreSQL"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Группа подключения
        conn_group = QGroupBox("Параметры подключения")
        conn_layout = QFormLayout()
        
        self.host_input = QLineEdit("localhost")
        self.port_input = QLineEdit("5432")
        self.user_input = QLineEdit("postgres")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        conn_layout.addRow("Хост:", self.host_input)
        conn_layout.addRow("Порт:", self.port_input)
        conn_layout.addRow("Пользователь:", self.user_input)
        conn_layout.addRow("Пароль:", self.password_input)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Группа путей к PostgreSQL
        path_group = QGroupBox("Пути к инструментам PostgreSQL")
        path_layout = QVBoxLayout()
        
        self.pg_path_input = QLineEdit()
        self.browse_pg_btn = QPushButton("Обзор...")
        self.auto_find_btn = QPushButton("Автопоиск")
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.pg_path_input)
        h_layout.addWidget(self.browse_pg_btn)
        h_layout.addWidget(self.auto_find_btn)
        
        path_layout.addLayout(h_layout)
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        self.test_conn_btn = QPushButton("Проверить подключение")
        self.save_conn_btn = QPushButton("Сохранить настройки")
        
        btn_layout.addWidget(self.test_conn_btn)
        btn_layout.addWidget(self.save_conn_btn)
        layout.addLayout(btn_layout)
        
        # Лог
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(150)
        self.log_area.setReadOnly(True)
        layout.addWidget(QLabel("Лог:"))
        layout.addWidget(self.log_area)
        
        self.setLayout(layout)
        
        # Подключение сигналов
        self.browse_pg_btn.clicked.connect(self.browse_pg_path)
        self.auto_find_btn.clicked.connect(self.auto_find_pg_path)
        self.test_conn_btn.clicked.connect(self.test_connection)
        
        # Ищем PostgreSQL автоматически при запуске
        self.auto_find_pg_path()
    
    def browse_pg_path(self):
        """Открывает диалог выбора пути к PostgreSQL"""
        path = QFileDialog.getExistingDirectory(self, "Выберите папку с PostgreSQL bin")
        if path:
            self.pg_path_input.setText(path)
    
    def auto_find_pg_path(self):
        """Автоматически находит путь к PostgreSQL"""
        possible_paths = []
        base_path = r"C:\Program Files\PostgreSQL"
        
        if os.path.exists(base_path):
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if os.path.isdir(item_path):
                    bin_path = os.path.join(item_path, "bin")
                    if os.path.exists(bin_path):
                        # Проверяем наличие необходимых утилит
                        required_tools = ['pg_dump.exe', 'pg_restore.exe', 'psql.exe', 'pg_isready.exe']
                        if all(os.path.exists(os.path.join(bin_path, tool)) for tool in required_tools):
                            possible_paths.append(bin_path)
        
        if possible_paths:
            # Выбираем самую новую версию
            latest = max(possible_paths, key=lambda x: os.path.basename(os.path.dirname(x)))
            self.pg_path_input.setText(latest)
            self.log_area.append(f"Найден PostgreSQL: {latest}")
        else:
            self.log_area.append("Не найдены инструменты PostgreSQL. Укажите путь вручную.")
    
    def test_connection(self):
        """Тестирует подключение к PostgreSQL"""
        host = self.host_input.text().strip()
        port = self.port_input.text().strip()
        username = self.user_input.text().strip()
        password = self.password_input.text().strip()
        pg_path = self.pg_path_input.text().strip()
        
        if not all([host, port, username, password, pg_path]):
            QMessageBox.warning(self, "Ошибка", "Заполните все поля подключения!")
            return
        
        try:
            port_int = int(port)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом!")
            return
        
        # Проверяем существование файлов
        required_tools = ['pg_dump.exe', 'pg_restore.exe', 'psql.exe', 'pg_isready.exe']
        missing_tools = []
        for tool in required_tools:
            tool_path = os.path.join(pg_path, tool)
            if not os.path.exists(tool_path):
                missing_tools.append(tool)
        
        if missing_tools:
            QMessageBox.warning(self, "Ошибка", f"Отсутствуют следующие инструменты PostgreSQL: {', '.join(missing_tools)}")
            return
        
        # Запускаем тест подключения в отдельном потоке
        self.conn_worker = ConnectionWorker(host, port_int, username, password)
        self.conn_worker.signals.log.connect(self.log_area.append)
        self.conn_worker.signals.error.connect(self.handle_connection_error)
        self.conn_worker.signals.finished.connect(self.handle_connection_result)
        
        self.test_conn_btn.setEnabled(False)
        self.log_area.clear()
        self.log_area.append("Проверка подключения...")
        
        self.conn_worker.start()
    
    def handle_connection_error(self, error_msg):
        """Обрабатывает ошибку подключения"""
        self.log_area.append(f"ОШИБКА: {error_msg}")
    
    def handle_connection_result(self, success):
        """Обрабатывает результат проверки подключения"""
        self.test_conn_btn.setEnabled(True)
        if success:
            self.log_area.append("✓ Подключение успешно установлено!")
        else:
            self.log_area.append("✗ Не удалось подключиться к серверу.")


class BackupTab(QWidget):
    """Вкладка резервного копирования"""
    
    def __init__(self, conn_tab):
        super().__init__()
        self.conn_tab = conn_tab
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Группа выбора баз данных
        db_group = QGroupBox("Выбор баз данных")
        db_layout = QVBoxLayout()
        
        # Кнопка обновления списка
        refresh_layout = QHBoxLayout()
        self.refresh_db_btn = QPushButton("Обновить список баз данных")
        self.load_selected_btn = QPushButton("Загрузить ранее выбранные")
        
        refresh_layout.addWidget(self.refresh_db_btn)
        refresh_layout.addWidget(self.load_selected_btn)
        db_layout.addLayout(refresh_layout)
        
        # Список баз данных
        self.db_list_widget = QListWidget()
        self.db_list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        db_layout.addWidget(self.db_list_widget)
        
        # Поле для ручного ввода баз
        manual_input_layout = QHBoxLayout()
        manual_input_layout.addWidget(QLabel("Ручной ввод (через запятую):"))
        self.manual_db_input = QLineEdit()
        manual_input_layout.addWidget(self.manual_db_input)
        db_layout.addLayout(manual_input_layout)
        
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)
        
        # Группа параметров резервного копирования
        backup_group = QGroupBox("Параметры резервного копирования")
        backup_layout = QFormLayout()
        
        self.backup_format_combo = QComboBox()
        self.backup_format_combo.addItems(["SQL (plain)", "Custom (.backup)"])
        
        self.backup_dir_input = QLineEdit()
        self.backup_dir_btn = QPushButton("Обзор...")
        
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.backup_dir_input)
        dir_layout.addWidget(self.backup_dir_btn)
        
        self.max_backups_spin = QSpinBox()
        self.max_backups_spin.setMinimum(1)
        self.max_backups_spin.setMaximum(100)
        self.max_backups_spin.setValue(10)
        
        backup_layout.addRow("Формат резервной копии:", self.backup_format_combo)
        backup_layout.addRow("Директория резервных копий:", dir_layout)
        backup_layout.addRow("Макс. кол-во копий на базу:", self.max_backups_spin)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        # Кнопка начала резервного копирования
        self.start_backup_btn = QPushButton("Начать резервное копирование")
        layout.addWidget(self.start_backup_btn)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Лог
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(150)
        self.log_area.setReadOnly(True)
        layout.addWidget(QLabel("Лог:"))
        layout.addWidget(self.log_area)
        
        self.setLayout(layout)
        
        # Подключение сигналов
        self.refresh_db_btn.clicked.connect(self.refresh_db_list)
        self.backup_dir_btn.clicked.connect(self.browse_backup_dir)
        self.start_backup_btn.clicked.connect(self.start_backup)
    
    def refresh_db_list(self):
        """Обновляет список баз данных"""
        host = self.conn_tab.host_input.text().strip()
        port = self.conn_tab.port_input.text().strip()
        username = self.conn_tab.user_input.text().strip()
        password = self.conn_tab.password_input.text().strip()
        pg_path = self.conn_tab.pg_path_input.text().strip()
        
        if not all([host, port, username, password, pg_path]):
            QMessageBox.warning(self, "Ошибка", "Сначала заполните параметры подключения!")
            return
        
        try:
            port_int = int(port)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом!")
            return
        
        # Запускаем получение списка баз в отдельном потоке
        self.db_worker = DatabaseListWorker(host, port_int, username, password, pg_path)
        self.db_worker.signals.log.connect(self.log_area.append)
        self.db_worker.signals.progress.connect(self.handle_db_progress)
        self.db_worker.signals.error.connect(self.handle_db_error)
        self.db_worker.signals.finished.connect(self.handle_db_finished)
        
        self.refresh_db_btn.setEnabled(False)
        self.log_area.clear()
        self.log_area.append("Получение списка баз данных...")
        
        self.db_worker.start()
    
    def handle_db_progress(self, percent, msg):
        """Обрабатывает прогресс получения списка баз"""
        if msg.startswith("DB:"):
            db_name = msg[3:]  # Убираем префикс "DB:"
            item = QListWidgetItem(db_name)
            self.db_list_widget.addItem(item)
    
    def handle_db_error(self, error_msg):
        """Обрабатывает ошибку получения списка баз"""
        self.log_area.append(f"ОШИБКА: {error_msg}")
    
    def handle_db_finished(self, success):
        """Обрабатывает завершение получения списка баз"""
        self.refresh_db_btn.setEnabled(True)
        if success:
            self.log_area.append("✓ Список баз данных обновлен!")
        else:
            self.log_area.append("✗ Не удалось получить список баз данных.")
    
    def browse_backup_dir(self):
        """Открывает диалог выбора директории резервных копий"""
        path = QFileDialog.getExistingDirectory(self, "Выберите директорию для резервных копий")
        if path:
            self.backup_dir_input.setText(path)
    
    def start_backup(self):
        """Начинает процесс резервного копирования"""
        # Получаем выбранные базы
        selected_items = self.db_list_widget.selectedItems()
        selected_dbs = [item.text() for item in selected_items]
        
        # Добавляем ручной ввод
        manual_dbs = self.manual_db_input.text().strip()
        if manual_dbs:
            manual_list = [db.strip() for db in manual_dbs.split(',') if db.strip()]
            selected_dbs.extend(manual_list)
        
        if not selected_dbs:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы одну базу данных!")
            return
        
        # Получаем параметры подключения
        host = self.conn_tab.host_input.text().strip()
        port = self.conn_tab.port_input.text().strip()
        username = self.conn_tab.user_input.text().strip()
        password = self.conn_tab.password_input.text().strip()
        pg_path = self.conn_tab.pg_path_input.text().strip()
        backup_dir = self.backup_dir_input.text().strip()
        max_backups = self.max_backups_spin.value()
        
        if not all([host, port, username, password, pg_path, backup_dir]):
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля!")
            return
        
        try:
            port_int = int(port)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом!")
            return
        
        if not os.path.exists(backup_dir):
            QMessageBox.warning(self, "Ошибка", "Указанная директория резервных копий не существует!")
            return
        
        # Определяем формат резервной копии
        format_type = 'sql' if self.backup_format_combo.currentIndex() == 0 else 'custom'
        
        # Запускаем резервное копирование в отдельном потоке
        self.backup_worker = BackupWorker(
            host, port_int, username, password, 
            selected_dbs, backup_dir, format_type, 
            max_backups, pg_path
        )
        self.backup_worker.signals.progress.connect(self.update_progress)
        self.backup_worker.signals.log.connect(self.log_area.append)
        self.backup_worker.signals.error.connect(self.handle_backup_error)
        self.backup_worker.signals.finished.connect(self.handle_backup_finished)
        
        # Настройка UI
        self.start_backup_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_area.clear()
        self.log_area.append(f"Начинаем резервное копирование {len(selected_dbs)} баз данных...")
        self.log_area.append(f"Формат: {format_type}, Директория: {backup_dir}")
        
        self.backup_worker.start()
    
    def update_progress(self, percent, msg):
        """Обновляет прогресс-бар"""
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"{msg} ({percent}%)")
    
    def handle_backup_error(self, error_msg):
        """Обрабатывает ошибку резервного копирования"""
        self.log_area.append(f"ОШИБКА: {error_msg}")
    
    def handle_backup_finished(self, success):
        """Обрабатывает завершение резервного копирования"""
        self.start_backup_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.log_area.append("✓ Резервное копирование завершено успешно!")
            QMessageBox.information(self, "Успех", "Резервное копирование завершено успешно!")
        else:
            self.log_area.append("✗ Один или несколько этапов резервного копирования завершились с ошибками.")
            QMessageBox.warning(self, "Ошибка", "Процесс резервного копирования завершился с ошибками. См. лог для деталей.")


class RestoreTab(QWidget):
    """Вкладка восстановления из резервной копии"""
    
    def __init__(self, conn_tab):
        super().__init__()
        self.conn_tab = conn_tab
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Группа выбора файла резервной копии
        file_group = QGroupBox("Файл резервной копии")
        file_layout = QFormLayout()
        
        self.backup_file_input = QLineEdit()
        self.backup_file_btn = QPushButton("Обзор...")
        
        file_h_layout = QHBoxLayout()
        file_h_layout.addWidget(self.backup_file_input)
        file_h_layout.addWidget(self.backup_file_btn)
        
        file_layout.addRow("Файл резервной копии:", file_h_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Группа параметров восстановления
        restore_group = QGroupBox("Параметры восстановления")
        restore_layout = QFormLayout()
        
        self.source_db_input = QLineEdit()
        self.target_db_input = QLineEdit()
        
        restore_layout.addRow("Исходная база (из файла):", self.source_db_input)
        restore_layout.addRow("Целевая база для восстановления:", self.target_db_input)
        
        restore_group.setLayout(restore_layout)
        layout.addWidget(restore_group)
        
        # Предупреждение о перезаписи
        self.warning_frame = QFrame()
        self.warning_frame.setFrameShape(QFrame.Shape.Box)
        self.warning_frame.setStyleSheet("QFrame { border: 2px solid red; background-color: #ffe6e6; }")
        warning_layout = QHBoxLayout()
        warning_layout.addWidget(QLabel("⚠️ "))
        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        warning_layout.addWidget(self.warning_label)
        self.warning_frame.setLayout(warning_layout)
        self.warning_frame.setVisible(False)
        layout.addWidget(self.warning_frame)
        
        # Подтверждение перезаписи
        self.confirm_frame = QFrame()
        self.confirm_frame.setFrameShape(QFrame.Shape.NoFrame)
        confirm_layout = QFormLayout()
        self.confirm_input = QLineEdit()
        confirm_layout.addRow("Для подтверждения введите имя целевой базы:", self.confirm_input)
        self.confirm_frame.setLayout(confirm_layout)
        self.confirm_frame.setVisible(False)
        layout.addWidget(self.confirm_frame)
        
        # Кнопка начала восстановления
        self.start_restore_btn = QPushButton("Начать восстановление")
        layout.addWidget(self.start_restore_btn)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Лог
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(150)
        self.log_area.setReadOnly(True)
        layout.addWidget(QLabel("Лог:"))
        layout.addWidget(self.log_area)
        
        self.setLayout(layout)
        
        # Подключение сигналов
        self.backup_file_btn.clicked.connect(self.browse_backup_file)
        self.target_db_input.textChanged.connect(self.check_overwrite_warning)
        self.confirm_input.textChanged.connect(self.check_confirm_input)
        self.start_restore_btn.clicked.connect(self.start_restore)
    
    def browse_backup_file(self):
        """Открывает диалог выбора файла резервной копии"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Выберите файл резервной копии",
            "",
            "Файлы резервных копий (*.sql *.backup);;SQL файлы (*.sql);;Backup файлы (*.backup);;Все файлы (*)"
        )
        if file_path:
            self.backup_file_input.setText(file_path)
            
            # Пытаемся извлечь имя исходной базы из имени файла
            filename = os.path.basename(file_path)
            if '_' in filename and ('.sql' in filename or '.backup' in filename):
                db_name = filename.split('_')[0]
                self.source_db_input.setText(db_name)
    
    def check_overwrite_warning(self):
        """Проверяет, нужно ли показывать предупреждение о перезаписи"""
        source_db = self.source_db_input.text().strip()
        target_db = self.target_db_input.text().strip()
        
        if source_db and target_db and source_db.lower() == target_db.lower():
            self.warning_frame.setVisible(True)
            self.confirm_frame.setVisible(True)
            self.warning_label.setText(
                "Вы пытаетесь восстановить данные поверх исходной базы! "
                "Это приведёт к потере текущих данных."
            )
            self.start_restore_btn.setEnabled(False)
        else:
            self.warning_frame.setVisible(False)
            self.confirm_frame.setVisible(False)
            self.start_restore_btn.setEnabled(True)
    
    def check_confirm_input(self):
        """Проверяет, совпадает ли введенное имя с целевой базой"""
        target_db = self.target_db_input.text().strip()
        confirm_text = self.confirm_input.text().strip()
        
        if target_db and confirm_text and target_db.lower() == confirm_text.lower():
            self.start_restore_btn.setEnabled(True)
        else:
            # Не отключаем кнопку, если это не режим перезаписи
            source_db = self.source_db_input.text().strip()
            if not (source_db and target_db and source_db.lower() == target_db.lower()):
                self.start_restore_btn.setEnabled(True)
            else:
                self.start_restore_btn.setEnabled(False)
    
    def start_restore(self):
        """Начинает процесс восстановления"""
        backup_file = self.backup_file_input.text().strip()
        target_db = self.target_db_input.text().strip()
        
        if not backup_file or not target_db:
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля!")
            return
        
        if not os.path.exists(backup_file):
            QMessageBox.warning(self, "Ошибка", "Указанный файл резервной копии не существует!")
            return
        
        # Проверяем, что файл имеет правильное расширение
        if not (backup_file.lower().endswith('.sql') or backup_file.lower().endswith('.backup')):
            QMessageBox.warning(self, "Ошибка", "Неподдерживаемый формат файла резервной копии!")
            return
        
        # Получаем параметры подключения
        host = self.conn_tab.host_input.text().strip()
        port = self.conn_tab.port_input.text().strip()
        username = self.conn_tab.user_input.text().strip()
        password = self.conn_tab.password_input.text().strip()
        pg_path = self.conn_tab.pg_path_input.text().strip()
        
        if not all([host, port, username, password, pg_path]):
            QMessageBox.warning(self, "Ошибка", "Заполните параметры подключения!")
            return
        
        try:
            port_int = int(port)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом!")
            return
        
        # Запускаем восстановление в отдельном потоке
        self.restore_worker = RestoreWorker(backup_file, target_db, host, port_int, username, password, pg_path)
        self.restore_worker.signals.progress.connect(self.update_progress)
        self.restore_worker.signals.log.connect(self.log_area.append)
        self.restore_worker.signals.error.connect(self.handle_restore_error)
        self.restore_worker.signals.finished.connect(self.handle_restore_finished)
        
        # Настройка UI
        self.start_restore_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_area.clear()
        self.log_area.append(f"Начинаем восстановление из файла: {os.path.basename(backup_file)}")
        self.log_area.append(f"Целевая база: {target_db}")
        
        self.restore_worker.start()
    
    def update_progress(self, percent, msg):
        """Обновляет прогресс-бар"""
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"{msg} ({percent}%)")
    
    def handle_restore_error(self, error_msg):
        """Обрабатывает ошибку восстановления"""
        self.log_area.append(f"ОШИБКА: {error_msg}")
    
    def handle_restore_finished(self, success):
        """Обрабатывает завершение восстановления"""
        self.start_restore_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.log_area.append("✓ Восстановление завершено успешно!")
            QMessageBox.information(self, "Успех", "Восстановление завершено успешно!")
        else:
            self.log_area.append("✗ Ошибка при восстановлении. См. лог для деталей.")
            QMessageBox.warning(self, "Ошибка", "Ошибка при восстановлении. См. лог для деталей.")


class ScheduleTab(QWidget):
    """Вкладка планировщика заданий"""
    
    def __init__(self, conn_tab, backup_tab):
        super().__init__()
        self.conn_tab = conn_tab
        self.backup_tab = backup_tab
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Группа параметров задания
        task_group = QGroupBox("Параметры задания резервного копирования")
        task_layout = QFormLayout()
        
        self.task_name_input = QLineEdit("Мое резервное копирование")
        
        self.schedule_type_combo = QComboBox()
        self.schedule_type_combo.addItems(["Ежедневно", "Еженедельно"])
        
        self.time_input = QLineEdit("02:00")
        self.day_combo = QComboBox()
        self.day_combo.addItems([
            "Понедельник", "Вторник", "Среда", "Четверг", 
            "Пятница", "Суббота", "Воскресенье"
        ])
        self.day_combo.setVisible(False)  # Скрываем до выбора недельного расписания
        
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.time_input)
        time_layout.addWidget(QLabel("День:"))
        time_layout.addWidget(self.day_combo)
        
        task_layout.addRow("Имя задания:", self.task_name_input)
        task_layout.addRow("Периодичность:", self.schedule_type_combo)
        task_layout.addRow("Время запуска:", time_layout)
        
        task_group.setLayout(task_layout)
        layout.addWidget(task_group)
        
        # Кнопки управления заданиями
        btn_layout = QHBoxLayout()
        self.create_task_btn = QPushButton("Создать задание")
        self.delete_task_btn = QPushButton("Удалить задание")
        self.view_tasks_btn = QPushButton("Просмотреть задания")
        
        btn_layout.addWidget(self.create_task_btn)
        btn_layout.addWidget(self.delete_task_btn)
        btn_layout.addWidget(self.view_tasks_btn)
        layout.addLayout(btn_layout)
        
        # Обновляем видимость дня при изменении типа расписания
        self.schedule_type_combo.currentTextChanged.connect(self.on_schedule_type_changed)
        
        # Лог
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(150)
        self.log_area.setReadOnly(True)
        layout.addWidget(QLabel("Лог:"))
        layout.addWidget(self.log_area)
        
        self.setLayout(layout)
        
        # Подключение сигналов
        self.create_task_btn.clicked.connect(self.create_backup_task)
        self.delete_task_btn.clicked.connect(self.delete_backup_task)
        self.view_tasks_btn.clicked.connect(self.view_tasks)
    
    def on_schedule_type_changed(self, text):
        """Обновляет видимость элементов при изменении типа расписания"""
        is_weekly = text == "Еженедельно"
        self.day_combo.setVisible(is_weekly)
    
    def create_backup_task(self):
        """Создает задание резервного копирования"""
        task_name = self.task_name_input.text().strip()
        schedule_type = self.schedule_type_combo.currentText()
        time_value = self.time_input.text().strip()
        
        if not task_name or not time_value:
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля!")
            return
        
        # Проверяем формат времени
        try:
            datetime.datetime.strptime(time_value, '%H:%M')
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Неверный формат времени! Используйте ЧЧ:ММ (например, 02:00)")
            return
        
        # Формируем параметры для передачи в задачу
        # Здесь мы будем сохранять параметры в виде строки, которую можно будет разобрать при запуске
        selected_items = self.backup_tab.db_list_widget.selectedItems()
        selected_dbs = [item.text() for item in selected_items]
        
        manual_dbs = self.backup_tab.manual_db_input.text().strip()
        if manual_dbs:
            manual_list = [db.strip() for db in manual_dbs.split(',') if db.strip()]
            selected_dbs.extend(manual_list)
        
        if not selected_dbs:
            QMessageBox.warning(self, "Ошибка", "Для планирования резервного копирования выберите хотя бы одну базу данных!")
            return
        
        # Формируем строку параметров (в реальном приложении нужно использовать безопасное хранение)
        params = f"--host={self.conn_tab.host_input.text()} --port={self.conn_tab.port_input.text()} " \
                 f"--username={self.conn_tab.user_input.text()} " \
                 f"--format={'sql' if self.backup_tab.backup_format_combo.currentIndex() == 0 else 'custom'} " \
                 f"--max-backups={self.backup_tab.max_backups_spin.value()} " \
                 f"--backup-dir=\"{self.backup_tab.backup_dir_input.text()}\" " \
                 f"--databases={','.join(selected_dbs)}"
        
        # Определяем тип расписания
        real_schedule_type = "daily" if schedule_type == "Ежедневно" else "weekly"
        if real_schedule_type == "weekly":
            day = self.day_combo.currentText()
            time_value = f"{time_value}_{day}"  # Объединяем время и день
        
        # Получаем путь к текущему исполняемому файлу
        program_path = sys.executable if getattr(sys, 'frozen', False) else __file__
        
        success, message = ScheduleManager.create_backup_task(
            task_name, program_path, params, real_schedule_type, time_value
        )
        
        self.log_area.append(message)
        
        if success:
            QMessageBox.information(self, "Успех", message)
        else:
            QMessageBox.warning(self, "Ошибка", message)
    
    def delete_backup_task(self):
        """Удаляет задание резервного копирования"""
        task_name = self.task_name_input.text().strip()
        
        if not task_name:
            QMessageBox.warning(self, "Ошибка", "Введите имя задания для удаления!")
            return
        
        success, message = ScheduleManager.delete_backup_task(task_name)
        
        self.log_area.append(message)
        
        if success:
            QMessageBox.information(self, "Успех", message)
        else:
            QMessageBox.warning(self, "Ошибка", message)
    
    def view_tasks(self):
        """Показывает список задач резервного копирования"""
        tasks = ScheduleManager.list_tasks()
        
        if tasks:
            task_list = "\n".join(tasks)
            QMessageBox.information(self, "Список задач", f"Найденные задачи резервного копирования:\n\n{task_list}")
        else:
            QMessageBox.information(self, "Список задач", "Задачи резервного копирования не найдены.")


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PostgreSQL Backup Manager")
        self.setGeometry(100, 100, 800, 600)
        
        # Устанавливаем шрифт
        font = QFont("Arial", 10)
        self.setFont(font)
        
        # Создаем вкладки
        self.conn_tab = ConnectionTab()
        self.backup_tab = BackupTab(self.conn_tab)
        self.restore_tab = RestoreTab(self.conn_tab)
        self.schedule_tab = ScheduleTab(self.conn_tab, self.backup_tab)
        
        # Создаем вкладки
        tab_widget = QTabWidget()
        tab_widget.addTab(self.conn_tab, "Подключение")
        tab_widget.addTab(self.backup_tab, "Резервное копирование")
        tab_widget.addTab(self.restore_tab, "Восстановление")
        tab_widget.addTab(self.schedule_tab, "Расписание")
        
        self.setCentralWidget(tab_widget)
        
        # Добавляем статусную строку
        self.statusBar().showMessage("Готово")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()