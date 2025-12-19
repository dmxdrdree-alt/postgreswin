#!/usr/bin/env python3
"""
PostgreSQL Backup and Restore Utility with PyQt6
GUI application for PostgreSQL database backup and restoration with scheduling capabilities
"""

import os
import sys
import subprocess
import threading
import json
import tempfile
from datetime import datetime
import re
import shutil

# Import winreg only on Windows
if sys.platform.startswith('win'):
    import winreg

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QTabWidget, QGroupBox,
    QCheckBox, QListWidget, QFileDialog, QMessageBox, QProgressBar,
    QComboBox, QTimeEdit, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon


class PostgreSQLBackupRestoreApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PostgreSQL Backup and Restore Utility")
        self.setGeometry(100, 100, 1000, 700)
        
        # Configuration
        self.config_file = "pg_config.json"
        self.load_config()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.connection_tab = QWidget()
        self.backup_tab = QWidget()
        self.restore_tab = QWidget()
        self.schedule_tab = QWidget()
        
        self.tab_widget.addTab(self.connection_tab, "Подключение")
        self.tab_widget.addTab(self.backup_tab, "Резервное копирование")
        self.tab_widget.addTab(self.restore_tab, "Восстановление")
        self.tab_widget.addTab(self.schedule_tab, "Расписание")
        
        # Initialize tabs
        self.create_connection_tab()
        self.create_backup_tab()
        self.create_restore_tab()
        self.create_schedule_tab()
        
        # Auto-detect PostgreSQL paths if not configured
        self.auto_detect_postgresql_paths()

    def auto_detect_postgresql_paths(self):
        """Auto-detect PostgreSQL installation paths from Windows registry"""
        # Only try to detect PostgreSQL paths on Windows
        if sys.platform.startswith('win'):
            try:
                # Try to get PostgreSQL installation path from registry
                reg_paths = [
                    r"SOFTWARE\PostgreSQL\Installations",
                    r"SOFTWARE\Wow6432Node\PostgreSQL\Installations"
                ]
                
                for reg_path in reg_paths:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                            i = 0
                            while True:
                                try:
                                    subkey_name = winreg.EnumKey(key, i)
                                    with winreg.OpenKey(key, subkey_name) as subkey:
                                        try:
                                            pgsql_dir = winreg.QueryValueEx(subkey, "Base Directory")[0]
                                            bin_dir = os.path.join(pgsql_dir, "bin")
                                            
                                            # Check if executables exist in this directory
                                            pg_dump_path = os.path.join(bin_dir, "pg_dump.exe")
                                            pg_restore_path = os.path.join(bin_dir, "pg_restore.exe")
                                            psql_path = os.path.join(bin_dir, "psql.exe")
                                            
                                            # Update config if executables exist and not already set
                                            if not self.config.get("pg_dump_path") and os.path.exists(pg_dump_path):
                                                self.config["pg_dump_path"] = pg_dump_path
                                            if not self.config.get("pg_restore_path") and os.path.exists(pg_restore_path):
                                                self.config["pg_restore_path"] = pg_restore_path
                                            if not self.config.get("psql_path") and os.path.exists(psql_path):
                                                self.config["psql_path"] = psql_path
                                            
                                            # Update GUI entries if they're empty
                                            if hasattr(self, 'pg_dump_line_edit') and not self.pg_dump_line_edit.text() and os.path.exists(pg_dump_path):
                                                self.pg_dump_line_edit.setText(pg_dump_path)
                                            if hasattr(self, 'pg_restore_line_edit') and not self.pg_restore_line_edit.text() and os.path.exists(pg_restore_path):
                                                self.pg_restore_line_edit.setText(pg_restore_path)
                                            if hasattr(self, 'psql_line_edit') and not self.psql_line_edit.text() and os.path.exists(psql_path):
                                                self.psql_line_edit.setText(psql_path)
                                                
                                        except FileNotFoundError:
                                            pass
                                    i += 1
                                except OSError:
                                    break
                    except FileNotFoundError:
                        continue
                        
                # Also try common installation paths
                common_paths = [
                    r"C:\Program Files\PostgreSQL",
                    r"C:\Program Files (x86)\PostgreSQL"
                ]
                
                for base_path in common_paths:
                    if os.path.exists(base_path):
                        # Find the latest version folder
                        versions = []
                        for item in os.listdir(base_path):
                            item_path = os.path.join(base_path, item)
                            if os.path.isdir(item_path) and item.replace('.', '').isdigit():
                                versions.append((item, item_path))
                        
                        # Sort by version number (descending)
                        versions.sort(key=lambda x: [int(i) for i in x[0].split('.')], reverse=True)
                        
                        for version, version_path in versions:
                            bin_dir = os.path.join(version_path, "bin")
                            pg_dump_path = os.path.join(bin_dir, "pg_dump.exe")
                            pg_restore_path = os.path.join(bin_dir, "pg_restore.exe")
                            psql_path = os.path.join(bin_dir, "psql.exe")
                            
                            if not self.config.get("pg_dump_path") and os.path.exists(pg_dump_path):
                                self.config["pg_dump_path"] = pg_dump_path
                            if not self.config.get("pg_restore_path") and os.path.exists(pg_restore_path):
                                self.config["pg_restore_path"] = pg_restore_path
                            if not self.config.get("psql_path") and os.path.exists(psql_path):
                                self.config["psql_path"] = psql_path
                                
                            # Update GUI entries if they're empty
                            if hasattr(self, 'pg_dump_line_edit') and not self.pg_dump_line_edit.text() and os.path.exists(pg_dump_path):
                                self.pg_dump_line_edit.setText(pg_dump_path)
                            if hasattr(self, 'pg_restore_line_edit') and not self.pg_restore_line_edit.text() and os.path.exists(pg_restore_path):
                                self.pg_restore_line_edit.setText(pg_restore_path)
                            if hasattr(self, 'psql_line_edit') and not self.psql_line_edit.text() and os.path.exists(psql_path):
                                self.psql_line_edit.setText(psql_path)
                            
                            # Break after finding the first valid installation
                            if any([os.path.exists(path) for path in [pg_dump_path, pg_restore_path, psql_path]]):
                                break
            except Exception:
                # If registry access fails, silently continue
                pass
        else:
            # On non-Windows systems, try to find executables in PATH
            try:
                # Check if executables are available in PATH
                for cmd in ['pg_dump', 'pg_restore', 'psql']:
                    try:
                        result = subprocess.run(['which', cmd], capture_output=True, text=True)
                        if result.returncode == 0:
                            path = result.stdout.strip()
                            if cmd == 'pg_dump':
                                self.config["pg_dump_path"] = path
                                if hasattr(self, 'pg_dump_line_edit') and not self.pg_dump_line_edit.text():
                                    self.pg_dump_line_edit.setText(path)
                            elif cmd == 'pg_restore':
                                self.config["pg_restore_path"] = path
                                if hasattr(self, 'pg_restore_line_edit') and not self.pg_restore_line_edit.text():
                                    self.pg_restore_line_edit.setText(path)
                            elif cmd == 'psql':
                                self.config["psql_path"] = path
                                if hasattr(self, 'psql_line_edit') and not self.psql_line_edit.text():
                                    self.psql_line_edit.setText(path)
                    except Exception:
                        continue
            except Exception:
                pass

    def validate_executables(self):
        """Validate that all required PostgreSQL executables exist"""
        errors = []
        
        # Check pg_dump
        pg_dump_path = self.config.get("pg_dump_path", "")
        if not pg_dump_path or not os.path.exists(pg_dump_path):
            errors.append("pg_dump не найден. Укажите правильный путь в настройках подключения.")
        else:
            self.pg_dump_path_to_use = pg_dump_path
        
        # Check pg_restore
        pg_restore_path = self.config.get("pg_restore_path", "")
        if not pg_restore_path or not os.path.exists(pg_restore_path):
            errors.append("pg_restore не найден. Укажите правильный путь в настройках подключения.")
        else:
            self.pg_restore_path_to_use = pg_restore_path
            
        # Check psql
        psql_path = self.config.get("psql_path", "")
        if not psql_path or not os.path.exists(psql_path):
            errors.append("psql не найден. Укажите правильный путь в настройках подключения.")
        else:
            self.psql_path_to_use = psql_path
        
        # If we don't have configured paths, try to use system PATH
        if not hasattr(self, 'pg_dump_path_to_use'):
            self.pg_dump_path_to_use = "pg_dump"
        if not hasattr(self, 'pg_restore_path_to_use'):
            self.pg_restore_path_to_use = "pg_restore"
        if not hasattr(self, 'psql_path_to_use'):
            self.psql_path_to_use = "psql"
        
        return errors

    def load_config(self):
        """Load configuration from JSON file"""
        default_config = {
            "host": "localhost",
            "port": "5432",
            "username": "postgres",
            "password": "",
            "pg_dump_path": "",
            "pg_restore_path": "",
            "psql_path": "",
            "backup_directory": "./backups",
            "keep_last_n_backups": 10
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                self.config = config
            except Exception:
                self.config = default_config
        else:
            self.config = default_config

    def save_config(self):
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить конфигурацию: {str(e)}")

    def create_connection_tab(self):
        """Create connection tab UI"""
        layout = QVBoxLayout(self.connection_tab)
        
        # Connection settings group
        conn_group = QGroupBox("Настройки подключения")
        conn_layout = QGridLayout(conn_group)
        
        # Host
        conn_layout.addWidget(QLabel("Хост:"), 0, 0)
        self.host_line_edit = QLineEdit()
        self.host_line_edit.setText(self.config["host"])
        conn_layout.addWidget(self.host_line_edit, 0, 1)
        
        # Port
        conn_layout.addWidget(QLabel("Порт:"), 0, 2)
        self.port_line_edit = QLineEdit()
        self.port_line_edit.setText(self.config["port"])
        conn_layout.addWidget(self.port_line_edit, 0, 3)
        
        # Username
        conn_layout.addWidget(QLabel("Пользователь:"), 1, 0)
        self.user_line_edit = QLineEdit()
        self.user_line_edit.setText(self.config["username"])
        conn_layout.addWidget(self.user_line_edit, 1, 1)
        
        # Password
        conn_layout.addWidget(QLabel("Пароль:"), 1, 2)
        self.pass_line_edit = QLineEdit()
        self.pass_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        conn_layout.addWidget(self.pass_line_edit, 1, 3)
        
        layout.addWidget(conn_group)
        
        # Executables paths group
        exec_group = QGroupBox("Пути к исполняемым файлам")
        exec_layout = QGridLayout(exec_group)
        
        # pg_dump path
        exec_layout.addWidget(QLabel("pg_dump:"), 0, 0)
        self.pg_dump_line_edit = QLineEdit()
        self.pg_dump_line_edit.setText(self.config["pg_dump_path"])
        exec_layout.addWidget(self.pg_dump_line_edit, 0, 1)
        browse_pg_dump_btn = QPushButton("Обзор")
        browse_pg_dump_btn.clicked.connect(self.browse_pg_dump)
        exec_layout.addWidget(browse_pg_dump_btn, 0, 2)
        
        # pg_restore path
        exec_layout.addWidget(QLabel("pg_restore:"), 1, 0)
        self.pg_restore_line_edit = QLineEdit()
        self.pg_restore_line_edit.setText(self.config["pg_restore_path"])
        exec_layout.addWidget(self.pg_restore_line_edit, 1, 1)
        browse_pg_restore_btn = QPushButton("Обзор")
        browse_pg_restore_btn.clicked.connect(self.browse_pg_restore)
        exec_layout.addWidget(browse_pg_restore_btn, 1, 2)
        
        # psql path
        exec_layout.addWidget(QLabel("psql:"), 2, 0)
        self.psql_line_edit = QLineEdit()
        self.psql_line_edit.setText(self.config["psql_path"])
        exec_layout.addWidget(self.psql_line_edit, 2, 1)
        browse_psql_btn = QPushButton("Обзор")
        browse_psql_btn.clicked.connect(self.browse_psql)
        exec_layout.addWidget(browse_psql_btn, 2, 2)
        
        layout.addWidget(exec_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        test_conn_btn = QPushButton("Проверить подключение")
        test_conn_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(test_conn_btn)
        
        save_config_btn = QPushButton("Сохранить настройки")
        save_config_btn.clicked.connect(self.save_connection_settings)
        button_layout.addWidget(save_config_btn)
        
        layout.addLayout(button_layout)

    def create_backup_tab(self):
        """Create backup tab UI"""
        layout = QVBoxLayout(self.backup_tab)
        
        # Backup settings group
        backup_group = QGroupBox("Настройки резервного копирования")
        backup_layout = QGridLayout(backup_group)
        
        # Format selection
        format_label = QLabel("Формат:")
        backup_layout.addWidget(format_label, 0, 0)
        
        format_layout = QHBoxLayout()
        self.sql_format_radio = QRadioButton("Plain SQL (.sql)")
        self.sql_format_radio.setChecked(True)
        format_layout.addWidget(self.sql_format_radio)
        
        self.custom_format_radio = QRadioButton("Custom (.backup)")
        format_layout.addWidget(self.custom_format_radio)
        
        backup_layout.addLayout(format_layout, 0, 1)
        
        # Backup directory
        backup_layout.addWidget(QLabel("Каталог резервных копий:"), 1, 0)
        self.backup_dir_line_edit = QLineEdit()
        self.backup_dir_line_edit.setText(self.config["backup_directory"])
        backup_layout.addWidget(self.backup_dir_line_edit, 1, 1)
        browse_backup_btn = QPushButton("Обзор")
        browse_backup_btn.clicked.connect(self.browse_backup_dir)
        backup_layout.addWidget(browse_backup_btn, 1, 2)
        
        layout.addWidget(backup_group)
        
        # Databases selection group
        db_group = QGroupBox("Выбор баз данных")
        db_layout = QVBoxLayout(db_group)
        
        # Load databases button
        load_dbs_btn = QPushButton("Загрузить список баз данных")
        load_dbs_btn.clicked.connect(self.load_databases)
        db_layout.addWidget(load_dbs_btn)
        
        # Database list
        self.db_list_widget = QListWidget()
        self.db_list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        db_layout.addWidget(self.db_list_widget)
        
        # Manual database input
        db_layout.addWidget(QLabel("Или введите имена баз через запятую:"))
        self.manual_db_line_edit = QLineEdit()
        db_layout.addWidget(self.manual_db_line_edit)
        
        layout.addWidget(db_group)
        
        # Backup button
        self.backup_btn = QPushButton("Создать резервные копии")
        self.backup_btn.clicked.connect(self.start_backup_process)
        layout.addWidget(self.backup_btn)
        
        # Progress bar
        self.backup_progress_bar = QProgressBar()
        self.backup_progress_bar.setVisible(False)
        layout.addWidget(self.backup_progress_bar)
        
        # Log area
        log_label = QLabel("Лог выполнения:")
        layout.addWidget(log_label)
        self.backup_log_text_edit = QTextEdit()
        self.backup_log_text_edit.setMaximumHeight(150)
        layout.addWidget(self.backup_log_text_edit)

    def create_restore_tab(self):
        """Create restore tab UI"""
        layout = QVBoxLayout(self.restore_tab)
        
        # File selection group
        file_group = QGroupBox("Выбор файла резервной копии")
        file_layout = QHBoxLayout(file_group)
        
        file_layout.addWidget(QLabel("Файл:"))
        self.restore_file_line_edit = QLineEdit()
        file_layout.addWidget(self.restore_file_line_edit)
        browse_restore_btn = QPushButton("Обзор")
        browse_restore_btn.clicked.connect(self.browse_restore_file)
        file_layout.addWidget(browse_restore_btn)
        
        layout.addWidget(file_group)
        
        # Source and target database group
        db_group = QGroupBox("Базы данных")
        db_layout = QGridLayout(db_group)
        
        # Source DB (auto-detected)
        db_layout.addWidget(QLabel("Исходная база:"), 0, 0)
        self.source_db_line_edit = QLineEdit()
        self.source_db_line_edit.setReadOnly(True)
        db_layout.addWidget(self.source_db_line_edit, 0, 1)
        
        # Target DB
        db_layout.addWidget(QLabel("Целевая база:"), 1, 0)
        self.target_db_line_edit = QLineEdit()
        db_layout.addWidget(self.target_db_line_edit, 1, 1)
        
        layout.addWidget(db_group)
        
        # Warning label
        self.warning_label = QLabel()
        self.warning_label.setStyleSheet("background-color: #ffcccc; padding: 5px; border: 1px solid red;")
        self.warning_label.setVisible(False)
        layout.addWidget(self.warning_label)
        
        # Confirmation input
        self.confirmation_group = QGroupBox("Подтверждение")
        self.confirmation_group.setVisible(False)
        confirmation_layout = QHBoxLayout(self.confirmation_group)
        
        confirmation_layout.addWidget(QLabel("Для подтверждения введите имя целевой базы:"))
        self.confirmation_line_edit = QLineEdit()
        confirmation_layout.addWidget(self.confirmation_line_edit)
        
        layout.addWidget(self.confirmation_group)
        
        # Restore button
        self.restore_btn = QPushButton("Восстановить")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self.start_restore_process)
        layout.addWidget(self.restore_btn)
        
        # Progress bar
        self.restore_progress_bar = QProgressBar()
        self.restore_progress_bar.setVisible(False)
        layout.addWidget(self.restore_progress_bar)
        
        # Log area
        log_label = QLabel("Лог выполнения:")
        layout.addWidget(log_label)
        self.restore_log_text_edit = QTextEdit()
        self.restore_log_text_edit.setMaximumHeight(150)
        layout.addWidget(self.restore_log_text_edit)

    def create_schedule_tab(self):
        """Create schedule tab UI"""
        layout = QVBoxLayout(self.schedule_tab)
        
        # Schedule settings group
        schedule_group = QGroupBox("Настройки задания")
        schedule_layout = QGridLayout(schedule_group)
        
        # Frequency
        schedule_layout.addWidget(QLabel("Периодичность:"), 0, 0)
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["Ежедневно", "Еженедельно"])
        schedule_layout.addWidget(self.frequency_combo, 0, 1)
        
        # Day selection (for weekly)
        self.day_label = QLabel("День недели:")
        self.day_label.setVisible(False)
        schedule_layout.addWidget(self.day_label, 1, 0)
        self.day_combo = QComboBox()
        self.day_combo.addItems(["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"])
        self.day_combo.setVisible(False)
        schedule_layout.addWidget(self.day_combo, 1, 1)
        
        # Time
        schedule_layout.addWidget(QLabel("Время запуска:"), 2, 0)
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(datetime.now().time())
        schedule_layout.addWidget(self.time_edit, 2, 1)
        
        # Refresh day combo visibility when frequency changes
        self.frequency_combo.currentTextChanged.connect(self.update_day_visibility)
        
        layout.addWidget(schedule_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        create_task_btn = QPushButton("Создать задание")
        create_task_btn.clicked.connect(self.create_scheduled_task)
        button_layout.addWidget(create_task_btn)
        
        delete_task_btn = QPushButton("Удалить задание")
        delete_task_btn.clicked.connect(self.delete_scheduled_task)
        button_layout.addWidget(delete_task_btn)
        
        view_tasks_btn = QPushButton("Просмотреть задания")
        view_tasks_btn.clicked.connect(self.view_scheduled_tasks)
        button_layout.addWidget(view_tasks_btn)
        
        layout.addLayout(button_layout)
        
        # Scheduled tasks log
        log_label = QLabel("Лог выполнения:")
        layout.addWidget(log_label)
        self.schedule_log_text_edit = QTextEdit()
        self.schedule_log_text_edit.setMaximumHeight(200)
        layout.addWidget(self.schedule_log_text_edit)

    def update_day_visibility(self):
        """Update visibility of day selection based on frequency"""
        is_weekly = self.frequency_combo.currentText() == "Еженедельно"
        self.day_label.setVisible(is_weekly)
        self.day_combo.setVisible(is_weekly)

    def browse_pg_dump(self):
        """Browse for pg_dump executable"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите pg_dump.exe", "", "Executable Files (*.exe)"
        )
        if file_path:
            self.pg_dump_line_edit.setText(file_path)
            self.config["pg_dump_path"] = file_path

    def browse_pg_restore(self):
        """Browse for pg_restore executable"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите pg_restore.exe", "", "Executable Files (*.exe)"
        )
        if file_path:
            self.pg_restore_line_edit.setText(file_path)
            self.config["pg_restore_path"] = file_path

    def browse_psql(self):
        """Browse for psql executable"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите psql.exe", "", "Executable Files (*.exe)"
        )
        if file_path:
            self.psql_line_edit.setText(file_path)
            self.config["psql_path"] = file_path

    def browse_backup_dir(self):
        """Browse for backup directory"""
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите каталог для резервных копий")
        if dir_path:
            self.backup_dir_line_edit.setText(dir_path)
            self.config["backup_directory"] = dir_path

    def browse_restore_file(self):
        """Browse for restore file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл резервной копии", "", 
            "Backup Files (*.sql *.backup);;SQL Files (*.sql);;Custom Backup (*.backup);;All Files (*)"
        )
        if file_path:
            self.restore_file_line_edit.setText(file_path)
            # Extract source database name from filename
            filename = os.path.basename(file_path)
            # Expected format: dbname_YYYYMMDD_HHMMSS.sql or .backup
            match = re.match(r'^([a-zA-Z0-9_]+)_\d{8}_\d{6}\.(sql|backup)$', filename)
            if match:
                source_db = match.group(1)
                self.source_db_line_edit.setText(source_db)
            else:
                # Try to extract from file content if possible
                self.extract_source_db_from_file(file_path)
            
            # Enable restore button
            self.check_restore_confirmation()

    def extract_source_db_from_file(self, file_path):
        """Extract source database name from backup file if possible"""
        # For .sql files, we might be able to detect the database from comments
        if file_path.lower().endswith('.sql'):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_lines = f.read(2048)  # Read first 2KB
                    # Look for PostgreSQL comment indicating the source database
                    match = re.search(r'-- Database: ([^\s]+)', first_lines)
                    if match:
                        self.source_db_line_edit.setText(match.group(1))
                        return
            except Exception:
                pass
        # For .backup files, we can't easily extract the database name without pg_restore

    def save_connection_settings(self):
        """Save connection settings to config"""
        self.config["host"] = self.host_line_edit.text()
        self.config["port"] = self.port_line_edit.text()
        self.config["username"] = self.user_line_edit.text()
        # Note: We don't save the password for security reasons
        self.config["pg_dump_path"] = self.pg_dump_line_edit.text()
        self.config["pg_restore_path"] = self.pg_restore_line_edit.text()
        self.config["psql_path"] = self.psql_line_edit.text()
        self.config["backup_directory"] = self.backup_dir_line_edit.text()
        
        self.save_config()
        QMessageBox.information(self, "Сохранено", "Настройки подключения сохранены.")

    def test_connection(self):
        """Test PostgreSQL connection"""
        # Validate executables first
        errors = self.validate_executables()
        if errors:
            QMessageBox.critical(self, "Ошибка", "\n".join(errors))
            return
        
        # Get connection parameters
        host = self.host_line_edit.text()
        port = self.port_line_edit.text()
        username = self.user_line_edit.text()
        password = self.pass_line_edit.text()
        
        # Set password as environment variable temporarily
        os.environ['PGPASSWORD'] = password
        
        try:
            # Test connection using psql
            cmd = [
                self.psql_path_to_use,
                "-h", host,
                "-p", port,
                "-U", username,
                "-c", "SELECT 1;",
                "-t",  # Tuple only output
                "-A"   # Unaligned output
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Remove password from environment immediately
            if 'PGPASSWORD' in os.environ:
                del os.environ['PGPASSWORD']
            
            if result.returncode == 0 and '1' in result.stdout:
                QMessageBox.information(self, "Успешно", "Подключение к PostgreSQL установлено!")
            else:
                error_msg = result.stderr.strip() if result.stderr else "Неизвестная ошибка"
                QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к PostgreSQL:\n{error_msg}")
                
        except subprocess.TimeoutExpired:
            # Remove password from environment
            if 'PGPASSWORD' in os.environ:
                del os.environ['PGPASSWORD']
            QMessageBox.critical(self, "Ошибка", "Таймаут подключения к PostgreSQL.")
        except Exception as e:
            # Remove password from environment
            if 'PGPASSWORD' in os.environ:
                del os.environ['PGPASSWORD']
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения: {str(e)}")

    def load_databases(self):
        """Load list of databases from PostgreSQL server"""
        # Validate executables first
        errors = self.validate_executables()
        if errors:
            QMessageBox.critical(self, "Ошибка", "\n".join(errors))
            return
        
        # Get connection parameters
        host = self.host_line_edit.text()
        port = self.port_line_edit.text()
        username = self.user_line_edit.text()
        password = self.pass_line_edit.text()
        
        # Set password as environment variable temporarily
        os.environ['PGPASSWORD'] = password
        
        try:
            # List databases using psql
            cmd = [
                self.psql_path_to_use,
                "-h", host,
                "-p", port,
                "-U", username,
                "-c", "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;",
                "-t",  # Tuple only output
                "-A"   # Unaligned output
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            # Remove password from environment immediately
            if 'PGPASSWORD' in os.environ:
                del os.environ['PGPASSWORD']
            
            if result.returncode == 0:
                databases = [db.strip() for db in result.stdout.split('\n') if db.strip() and db.strip() != 'datname']
                self.db_list_widget.clear()
                self.db_list_widget.addItems(databases)
            else:
                error_msg = result.stderr.strip() if result.stderr else "Неизвестная ошибка"
                QMessageBox.critical(self, "Ошибка", f"Не удалось получить список баз данных:\n{error_msg}")
                
        except Exception as e:
            # Remove password from environment
            if 'PGPASSWORD' in os.environ:
                del os.environ['PGPASSWORD']
            QMessageBox.critical(self, "Ошибка", f"Ошибка получения списка баз данных: {str(e)}")

    def start_backup_process(self):
        """Start the backup process in a separate thread"""
        # Validate executables first
        errors = self.validate_executables()
        if errors:
            QMessageBox.critical(self, "Ошибка", "\n".join(errors))
            return
        
        # Get selected databases
        selected_items = [self.db_list_widget.item(i).text() for i in range(self.db_list_widget.count()) 
                         if self.db_list_widget.item(i).isSelected()]
        
        # Add manually entered databases
        manual_dbs = self.manual_db_line_edit.text().strip()
        if manual_dbs:
            manual_list = [db.strip() for db in manual_dbs.split(',') if db.strip()]
            selected_items.extend(manual_list)
        
        if not selected_items:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы одну базу данных для резервного копирования.")
            return
        
        # Get other parameters
        backup_dir = self.backup_dir_line_edit.text()
        if not backup_dir:
            QMessageBox.warning(self, "Внимание", "Укажите каталог для резервных копий.")
            return
        
        if not os.path.exists(backup_dir):
            try:
                os.makedirs(backup_dir)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать каталог резервных копий: {str(e)}")
                return
        
        format_type = "sql" if self.sql_format_radio.isChecked() else "custom"
        
        # Prepare parameters for the worker thread
        params = {
            'databases': selected_items,
            'backup_dir': backup_dir,
            'format_type': format_type,
            'host': self.host_line_edit.text(),
            'port': self.port_line_edit.text(),
            'username': self.user_line_edit.text(),
            'password': self.pass_line_edit.text()
        }
        
        # Start backup thread
        self.backup_worker = BackupWorker(params)
        self.backup_worker.progress.connect(self.update_backup_progress)
        self.backup_worker.log.connect(self.update_backup_log)
        self.backup_worker.finished.connect(self.backup_finished)
        
        # Show progress bar and disable button
        self.backup_progress_bar.setValue(0)
        self.backup_progress_bar.setVisible(True)
        self.backup_btn.setEnabled(False)
        
        self.backup_worker.start()

    def update_backup_progress(self, value):
        """Update backup progress bar"""
        self.backup_progress_bar.setValue(value)

    def update_backup_log(self, message):
        """Update backup log"""
        self.backup_log_text_edit.append(message)

    def backup_finished(self, success, message):
        """Handle backup completion"""
        self.backup_progress_bar.setVisible(False)
        self.backup_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Успешно", message)
        else:
            QMessageBox.critical(self, "Ошибка", message)

    def check_restore_confirmation(self):
        """Check if restore button should be enabled based on confirmation"""
        source_db = self.source_db_line_edit.text().strip()
        target_db = self.target_db_line_edit.text().strip()
        confirmation_text = self.confirmation_line_edit.text().strip()
        
        # If source and target are the same, check confirmation
        if source_db and target_db and source_db == target_db:
            self.warning_label.setText("⚠️ Вы пытаетесь восстановить данные поверх исходной базы! Это приведёт к потере текущих данных.")
            self.warning_label.setVisible(True)
            self.confirmation_group.setVisible(True)
            self.restore_btn.setEnabled(target_db == confirmation_text)
        else:
            self.warning_label.setVisible(False)
            self.confirmation_group.setVisible(False)
            self.restore_btn.setEnabled(bool(target_db))

    def start_restore_process(self):
        """Start the restore process in a separate thread"""
        # Validate executables first
        errors = self.validate_executables()
        if errors:
            QMessageBox.critical(self, "Ошибка", "\n".join(errors))
            return
        
        # Get parameters
        restore_file = self.restore_file_line_edit.text().strip()
        target_db = self.target_db_line_edit.text().strip()
        
        if not restore_file or not target_db:
            QMessageBox.warning(self, "Внимание", "Укажите файл резервной копии и целевую базу данных.")
            return
        
        if not os.path.exists(restore_file):
            QMessageBox.critical(self, "Ошибка", "Файл резервной копии не найден.")
            return
        
        # Check if source and target are the same and confirm
        source_db = self.source_db_line_edit.text().strip()
        if source_db and source_db == target_db:
            confirmation_text = self.confirmation_line_edit.text().strip()
            if target_db != confirmation_text:
                QMessageBox.warning(self, "Внимание", "Введите имя целевой базы для подтверждения.")
                return
        
        # Prepare parameters for the worker thread
        params = {
            'restore_file': restore_file,
            'target_db': target_db,
            'host': self.host_line_edit.text(),
            'port': self.port_line_edit.text(),
            'username': self.user_line_edit.text(),
            'password': self.pass_line_edit.text()
        }
        
        # Start restore thread
        self.restore_worker = RestoreWorker(params)
        self.restore_worker.progress.connect(self.update_restore_progress)
        self.restore_worker.log.connect(self.update_restore_log)
        self.restore_worker.finished.connect(self.restore_finished)
        
        # Show progress bar and disable button
        self.restore_progress_bar.setValue(0)
        self.restore_progress_bar.setVisible(True)
        self.restore_btn.setEnabled(False)
        
        self.restore_worker.start()

    def update_restore_progress(self, value):
        """Update restore progress bar"""
        self.restore_progress_bar.setValue(value)

    def update_restore_log(self, message):
        """Update restore log"""
        self.restore_log_text_edit.append(message)

    def restore_finished(self, success, message):
        """Handle restore completion"""
        self.restore_progress_bar.setVisible(False)
        self.restore_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Успешно", message)
        else:
            QMessageBox.critical(self, "Ошибка", message)

    def create_scheduled_task(self):
        """Create scheduled task using schtasks"""
        try:
            # Get parameters
            frequency = self.frequency_combo.currentText()
            time_value = self.time_edit.time().toString("HH:mm")
            
            # Build the command to run the backup
            # For now, just run the Python script itself
            script_path = os.path.abspath(__file__)
            cmd = [
                "schtasks",
                "/CREATE",
                "/SC", "DAILY" if frequency == "Ежедневно" else "WEEKLY",
                "/TN", "PostgreSQL_Backup_Automation",
                "/TR", f'"{sys.executable}" "{script_path}" --scheduled',
                "/ST", time_value,
                "/F"  # Force overwrite if exists
            ]
            
            # Add day if weekly
            if frequency == "Еженедельно":
                day_map = {
                    "Понедельник": "MON",
                    "Вторник": "TUE", 
                    "Среда": "WED",
                    "Четверг": "THU",
                    "Пятница": "FRI",
                    "Суббота": "SAT",
                    "Воскресенье": "SUN"
                }
                selected_day = self.day_combo.currentText()
                cmd.extend(["/D", day_map[selected_day]])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.schedule_log_text_edit.append("Задание успешно создано.")
            else:
                self.schedule_log_text_edit.append(f"Ошибка создания задания: {result.stderr}")
                
        except Exception as e:
            self.schedule_log_text_edit.append(f"Ошибка создания задания: {str(e)}")

    def delete_scheduled_task(self):
        """Delete scheduled task using schtasks"""
        try:
            cmd = ["schtasks", "/DELETE", "/TN", "PostgreSQL_Backup_Automation", "/F"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.schedule_log_text_edit.append("Задание успешно удалено.")
            else:
                self.schedule_log_text_edit.append(f"Ошибка удаления задания: {result.stderr}")
                
        except Exception as e:
            self.schedule_log_text_edit.append(f"Ошибка удаления задания: {str(e)}")

    def view_scheduled_tasks(self):
        """View scheduled tasks using schtasks"""
        try:
            cmd = ["schtasks", "/QUERY", "/TN", "PostgreSQL_Backup_Automation"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.schedule_log_text_edit.append("Информация о задании:")
                self.schedule_log_text_edit.append(result.stdout)
            else:
                # Check if task exists
                if "не существует" in result.stderr or "does not exist" in result.stderr:
                    self.schedule_log_text_edit.append("Задание не найдено.")
                else:
                    self.schedule_log_text_edit.append(f"Ошибка получения информации: {result.stderr}")
                
        except Exception as e:
            self.schedule_log_text_edit.append(f"Ошибка получения информации: {str(e)}")


class BackupWorker(QThread):
    """Worker thread for backup operations"""
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        """Run the backup process"""
        try:
            total_dbs = len(self.params['databases'])
            success_count = 0
            
            for i, db_name in enumerate(self.params['databases']):
                # Update progress
                progress_percent = int((i / total_dbs) * 100)
                self.progress.emit(progress_percent)
                self.log.emit(f"Обработка базы данных: {db_name}")
                
                # Set password as environment variable temporarily
                os.environ['PGPASSWORD'] = self.params['password']
                
                try:
                    # Generate filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    if self.params['format_type'] == 'sql':
                        filename = f"{db_name}_{timestamp}.sql"
                        format_flag = "--format=p"
                    else:
                        filename = f"{db_name}_{timestamp}.backup"
                        format_flag = "--format=c"
                    
                    backup_path = os.path.join(self.params['backup_dir'], filename)
                    
                    # Build pg_dump command
                    cmd = [
                        self.params['pg_dump_path_to_use'],
                        "-h", self.params['host'],
                        "-p", self.params['port'],
                        "-U", self.params['username'],
                        format_flag,
                        "-f", backup_path,
                        db_name
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    # Remove password from environment immediately
                    if 'PGPASSWORD' in os.environ:
                        del os.environ['PGPASSWORD']
                    
                    if result.returncode == 0:
                        self.log.emit(f"✓ Резервная копия базы '{db_name}' создана: {filename}")
                        success_count += 1
                        
                        # Clean up old backups
                        self.cleanup_old_backups(db_name, self.params['backup_dir'])
                    else:
                        self.log.emit(f"✗ Ошибка создания резервной копии базы '{db_name}': {result.stderr}")
                        
                except Exception as e:
                    # Remove password from environment
                    if 'PGPASSWORD' in os.environ:
                        del os.environ['PGPASSWORD']
                    self.log.emit(f"✗ Ошибка обработки базы '{db_name}': {str(e)}")
            
            # Final progress update
            self.progress.emit(100)
            
            # Report final result
            if success_count == total_dbs:
                self.finished.emit(True, f"Все {total_dbs} баз данных успешно сохранены.")
            elif success_count > 0:
                self.finished.emit(True, f"Частично успешно: {success_count} из {total_dbs} баз данных сохранены.")
            else:
                self.finished.emit(False, "Не удалось создать резервные копии ни одной базы данных.")
                
        except Exception as e:
            self.finished.emit(False, f"Критическая ошибка во время резервного копирования: {str(e)}")

    def cleanup_old_backups(self, db_name, backup_dir):
        """Clean up old backup files, keeping only the last N"""
        try:
            keep_count = self.params.get('keep_last_n_backups', 10)
            
            # Find all backup files for this database
            pattern = f"{db_name}_*.sql"
            sql_files = [f for f in os.listdir(backup_dir) if f.startswith(f"{db_name}_") and f.endswith(".sql")]
            
            pattern = f"{db_name}_*.backup"
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith(f"{db_name}_") and f.endswith(".backup")]
            
            all_files = sql_files + backup_files
            
            # Sort by modification time (oldest first)
            all_files_with_time = []
            for f in all_files:
                file_path = os.path.join(backup_dir, f)
                mod_time = os.path.getmtime(file_path)
                all_files_with_time.append((mod_time, file_path))
            
            all_files_with_time.sort()
            
            # Remove oldest files beyond the keep count
            files_to_remove = all_files_with_time[:-keep_count] if len(all_files_with_time) > keep_count else []
            
            for _, file_path in files_to_remove:
                os.remove(file_path)
                self.log.emit(f"Удалена старая резервная копия: {os.path.basename(file_path)}")
                
        except Exception as e:
            self.log.emit(f"Ошибка очистки старых резервных копий: {str(e)}")


class RestoreWorker(QThread):
    """Worker thread for restore operations"""
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        """Run the restore process"""
        try:
            restore_file = self.params['restore_file']
            target_db = self.params['target_db']
            
            # Determine if it's a SQL or custom backup file
            is_sql = restore_file.lower().endswith('.sql')
            
            # Set password as environment variable temporarily
            os.environ['PGPASSWORD'] = self.params['password']
            
            # First, make sure the target database exists
            # For simplicity, we'll assume it exists or create it if needed
            # In a real application, you might want to check first
            self.progress.emit(10)
            self.log.emit(f"Подготовка к восстановлению в базу: {target_db}")
            
            if is_sql:
                # Restore using psql
                cmd = [
                    self.params['psql_path_to_use'],
                    "-h", self.params['host'],
                    "-p", self.params['port'],
                    "-U", self.params['username'],
                    "-d", target_db,
                    "-f", restore_file
                ]
            else:
                # Restore using pg_restore
                cmd = [
                    self.params['pg_restore_path_to_use'],
                    "-h", self.params['host'],
                    "-p", self.params['port'],
                    "-U", self.params['username'],
                    "-d", target_db,
                    restore_file
                ]
            
            # Execute the restore command
            self.progress.emit(30)
            self.log.emit(f"Выполнение команды {'psql' if is_sql else 'pg_restore'}...")
            
            # Use subprocess.Popen to get real-time output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )
            
            # Read output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.log.emit(output.strip())
            
            # Wait for process to finish and get return code
            return_code = process.poll()
            stderr = process.stderr.read()
            
            # Remove password from environment immediately
            if 'PGPASSWORD' in os.environ:
                del os.environ['PGPASSWORD']
            
            self.progress.emit(100)
            
            if return_code == 0:
                self.finished.emit(True, f"Восстановление базы данных '{target_db}' успешно завершено.")
            else:
                self.log.emit(f"Ошибка восстановления: {stderr}")
                self.finished.emit(False, f"Ошибка восстановления базы данных: {stderr}")
                
        except Exception as e:
            # Remove password from environment
            if 'PGPASSWORD' in os.environ:
                del os.environ['PGPASSWORD']
            self.finished.emit(False, f"Критическая ошибка во время восстановления: {str(e)}")


def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("PostgreSQL Backup and Restore Utility")
    app.setOrganizationName("PostgreSQL Tools")
    
    window = PostgreSQLBackupRestoreApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()