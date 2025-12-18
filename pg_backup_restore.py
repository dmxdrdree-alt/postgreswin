#!/usr/bin/env python3
"""
PostgreSQL Backup and Restore Utility
GUI application for PostgreSQL database backup and restoration with scheduling capabilities
"""

import os
import sys
import subprocess
import threading
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime
import re
import shutil


class PostgreSQLBackupRestoreApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PostgreSQL Backup and Restore Utility")
        self.root.geometry("900x700")
        
        # Configuration
        self.config_file = "pg_config.json"
        self.load_config()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.connection_frame = ttk.Frame(self.notebook)
        self.backup_frame = ttk.Frame(self.notebook)
        self.restore_frame = ttk.Frame(self.notebook)
        self.schedule_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.connection_frame, text="Подключение")
        self.notebook.add(self.backup_frame, text="Резервное копирование")
        self.notebook.add(self.restore_frame, text="Восстановление")
        self.notebook.add(self.schedule_frame, text="Расписание")
        
        # Initialize frames
        self.create_connection_tab()
        self.create_backup_tab()
        self.create_restore_tab()
        self.create_schedule_tab()
    
    def load_config(self):
        """Load configuration from JSON file"""
        default_config = {
            "host": "localhost",
            "port": "5432",
            "database": "",
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
            messagebox.showerror("Ошибка", f"Не удалось сохранить конфигурацию: {str(e)}")
    
    def create_connection_tab(self):
        """Create connection tab UI"""
        # Connection settings frame
        conn_settings_frame = ttk.LabelFrame(self.connection_frame, text="Настройки подключения")
        conn_settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Host
        ttk.Label(conn_settings_frame, text="Хост:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.host_entry = ttk.Entry(conn_settings_frame, width=20)
        self.host_entry.grid(row=0, column=1, padx=5, pady=2)
        self.host_entry.insert(0, self.config["host"])
        
        # Port
        ttk.Label(conn_settings_frame, text="Порт:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.port_entry = ttk.Entry(conn_settings_frame, width=10)
        self.port_entry.grid(row=0, column=3, padx=5, pady=2)
        self.port_entry.insert(0, self.config["port"])
        
        # Database
        ttk.Label(conn_settings_frame, text="База данных:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.db_entry = ttk.Entry(conn_settings_frame, width=20)
        self.db_entry.grid(row=1, column=1, padx=5, pady=2)
        self.db_entry.insert(0, self.config["database"])
        
        # Username
        ttk.Label(conn_settings_frame, text="Пользователь:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.user_entry = ttk.Entry(conn_settings_frame, width=20)
        self.user_entry.grid(row=1, column=3, padx=5, pady=2)
        self.user_entry.insert(0, self.config["username"])
        
        # Password
        ttk.Label(conn_settings_frame, text="Пароль:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.pass_entry = ttk.Entry(conn_settings_frame, width=20, show="*")
        self.pass_entry.grid(row=2, column=1, padx=5, pady=2)
        self.pass_entry.insert(0, self.config["password"])
        
        # Executables paths
        exec_frame = ttk.LabelFrame(self.connection_frame, text="Пути к исполняемым файлам")
        exec_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # pg_dump path
        ttk.Label(exec_frame, text="pg_dump:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.pg_dump_entry = ttk.Entry(exec_frame, width=40)
        self.pg_dump_entry.grid(row=0, column=1, padx=5, pady=2)
        self.pg_dump_entry.insert(0, self.config["pg_dump_path"])
        ttk.Button(exec_frame, text="Обзор", command=self.browse_pg_dump).grid(row=0, column=2, padx=5, pady=2)
        
        # pg_restore path
        ttk.Label(exec_frame, text="pg_restore:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.pg_restore_entry = ttk.Entry(exec_frame, width=40)
        self.pg_restore_entry.grid(row=1, column=1, padx=5, pady=2)
        self.pg_restore_entry.insert(0, self.config["pg_restore_path"])
        ttk.Button(exec_frame, text="Обзор", command=self.browse_pg_restore).grid(row=1, column=2, padx=5, pady=2)
        
        # psql path
        ttk.Label(exec_frame, text="psql:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.psql_entry = ttk.Entry(exec_frame, width=40)
        self.psql_entry.grid(row=2, column=1, padx=5, pady=2)
        self.psql_entry.insert(0, self.config["psql_path"])
        ttk.Button(exec_frame, text="Обзор", command=self.browse_psql).grid(row=2, column=2, padx=5, pady=2)
        
        # Test connection button
        test_frame = ttk.Frame(self.connection_frame)
        test_frame.pack(fill=tk.X, padx=10, pady=10)
        self.test_conn_btn = ttk.Button(test_frame, text="Проверить подключение", command=self.test_connection)
        self.test_conn_btn.pack(side=tk.LEFT, padx=5)
        
        # Save config button
        self.save_config_btn = ttk.Button(test_frame, text="Сохранить настройки", command=self.save_connection_settings)
        self.save_config_btn.pack(side=tk.LEFT, padx=5)
    
    def create_backup_tab(self):
        """Create backup tab UI"""
        # Backup settings frame
        backup_settings_frame = ttk.LabelFrame(self.backup_frame, text="Настройки резервного копирования")
        backup_settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Format selection
        ttk.Label(backup_settings_frame, text="Формат:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.format_var = tk.StringVar(value="sql")
        ttk.Radiobutton(backup_settings_frame, text="Plain SQL (.sql)", variable=self.format_var, value="sql").grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Radiobutton(backup_settings_frame, text="Custom (.backup)", variable=self.format_var, value="custom").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        
        # Backup directory
        ttk.Label(backup_settings_frame, text="Каталог резервных копий:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.backup_dir_entry = ttk.Entry(backup_settings_frame, width=40)
        self.backup_dir_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=2)
        self.backup_dir_entry.insert(0, self.config["backup_directory"])
        ttk.Button(backup_settings_frame, text="Обзор", command=self.browse_backup_dir).grid(row=1, column=3, padx=5, pady=2)
        
        # Keep last N backups
        ttk.Label(backup_settings_frame, text="Хранить последних копий:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.keep_backups_spinbox = ttk.Spinbox(backup_settings_frame, from_=1, to=100, width=10)
        self.keep_backups_spinbox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        self.keep_backups_spinbox.set(self.config["keep_last_n_backups"])
        
        # Backup button
        backup_btn_frame = ttk.Frame(self.backup_frame)
        backup_btn_frame.pack(fill=tk.X, padx=10, pady=10)
        self.backup_btn = ttk.Button(backup_btn_frame, text="Создать резервную копию", command=self.start_backup)
        self.backup_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.backup_progress = ttk.Progressbar(backup_btn_frame, mode='determinate')
        self.backup_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Log area
        log_frame = ttk.LabelFrame(self.backup_frame, text="Лог выполнения")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.backup_log = scrolledtext.ScrolledText(log_frame, height=15)
        self.backup_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_restore_tab(self):
        """Create restore tab UI"""
        # File selection
        file_frame = ttk.LabelFrame(self.restore_frame, text="Файл резервной копии")
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(file_frame, text="Файл:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.restore_file_entry = ttk.Entry(file_frame, width=50)
        self.restore_file_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(file_frame, text="Обзор", command=self.browse_restore_file).grid(row=0, column=2, padx=5, pady=2)
        
        # Target database
        db_frame = ttk.LabelFrame(self.restore_frame, text="Целевая база данных")
        db_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(db_frame, text="База данных:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.target_db_entry = ttk.Entry(db_frame, width=30)
        self.target_db_entry.grid(row=0, column=1, padx=5, pady=2)
        
        # Warning label (initially hidden)
        self.warning_label = ttk.Label(db_frame, text="", foreground="red", font=("Arial", 10, "bold"))
        self.warning_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        self.warning_label.grid_remove()  # Hide initially
        
        # Confirmation input (initially hidden)
        self.confirm_frame = ttk.Frame(db_frame)
        self.confirm_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        self.confirm_frame.grid_remove()  # Hide initially
        
        ttk.Label(self.confirm_frame, text="Для подтверждения введите имя целевой базы:").grid(row=0, column=0, sticky=tk.W)
        self.confirm_entry = ttk.Entry(self.confirm_frame, width=30)
        self.confirm_entry.grid(row=0, column=1, padx=5)
        self.confirm_entry.bind('<KeyRelease>', self.check_confirmation)
        
        # Restore button
        restore_btn_frame = ttk.Frame(self.restore_frame)
        restore_btn_frame.pack(fill=tk.X, padx=10, pady=10)
        self.restore_btn = ttk.Button(restore_btn_frame, text="Восстановить", command=self.start_restore, state=tk.DISABLED)
        self.restore_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.restore_progress = ttk.Progressbar(restore_btn_frame, mode='determinate')
        self.restore_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Log area
        log_frame = ttk.LabelFrame(self.restore_frame, text="Лог выполнения")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.restore_log = scrolledtext.ScrolledText(log_frame, height=15)
        self.restore_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_schedule_tab(self):
        """Create schedule tab UI"""
        # Schedule settings frame
        schedule_settings_frame = ttk.LabelFrame(self.schedule_frame, text="Настройки задания")
        schedule_settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Task name
        ttk.Label(schedule_settings_frame, text="Имя задания:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.task_name_entry = ttk.Entry(schedule_settings_frame, width=30)
        self.task_name_entry.grid(row=0, column=1, padx=5, pady=2)
        self.task_name_entry.insert(0, "PostgreSQL_Backup")
        
        # Frequency
        ttk.Label(schedule_settings_frame, text="Периодичность:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.frequency_var = tk.StringVar(value="daily")
        ttk.Radiobutton(schedule_settings_frame, text="Ежедневно", variable=self.frequency_var, value="daily").grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Radiobutton(schedule_settings_frame, text="Еженедельно", variable=self.frequency_var, value="weekly").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        
        # Time
        ttk.Label(schedule_settings_frame, text="Время (ЧЧ:ММ):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.time_entry = ttk.Entry(schedule_settings_frame, width=10)
        self.time_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        self.time_entry.insert(0, "02:00")
        
        # Action buttons
        action_frame = ttk.Frame(self.schedule_frame)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.create_task_btn = ttk.Button(action_frame, text="Создать задание", command=self.create_scheduled_task)
        self.create_task_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_task_btn = ttk.Button(action_frame, text="Удалить задание", command=self.delete_scheduled_task)
        self.delete_task_btn.pack(side=tk.LEFT, padx=5)
        
        self.view_task_btn = ttk.Button(action_frame, text="Просмотреть состояние", command=self.view_scheduled_task)
        self.view_task_btn.pack(side=tk.LEFT, padx=5)
        
        # Task status log
        status_frame = ttk.LabelFrame(self.schedule_frame, text="Статус задания")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.task_status_log = scrolledtext.ScrolledText(status_frame, height=15)
        self.task_status_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def browse_pg_dump(self):
        """Browse for pg_dump executable"""
        filename = filedialog.askopenfilename(
            title="Выберите pg_dump.exe",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.pg_dump_entry.delete(0, tk.END)
            self.pg_dump_entry.insert(0, filename)
    
    def browse_pg_restore(self):
        """Browse for pg_restore executable"""
        filename = filedialog.askopenfilename(
            title="Выберите pg_restore.exe",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.pg_restore_entry.delete(0, tk.END)
            self.pg_restore_entry.insert(0, filename)
    
    def browse_psql(self):
        """Browse for psql executable"""
        filename = filedialog.askopenfilename(
            title="Выберите psql.exe",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.psql_entry.delete(0, tk.END)
            self.psql_entry.insert(0, filename)
    
    def browse_backup_dir(self):
        """Browse for backup directory"""
        dirname = filedialog.askdirectory(title="Выберите каталог для резервных копий")
        if dirname:
            self.backup_dir_entry.delete(0, tk.END)
            self.backup_dir_entry.insert(0, dirname)
    
    def browse_restore_file(self):
        """Browse for restore file"""
        filename = filedialog.askopenfilename(
            title="Выберите файл резервной копии",
            filetypes=[
                ("SQL files", "*.sql"),
                ("Backup files", "*.backup *.dump"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.restore_file_entry.delete(0, tk.END)
            self.restore_file_entry.insert(0, filename)
            
            # Check if target DB needs confirmation
            self.check_target_db_for_warning(filename)
    
    def save_connection_settings(self):
        """Save connection settings to config"""
        self.config["host"] = self.host_entry.get()
        self.config["port"] = self.port_entry.get()
        self.config["database"] = self.db_entry.get()
        self.config["username"] = self.user_entry.get()
        self.config["password"] = self.pass_entry.get()
        self.config["pg_dump_path"] = self.pg_dump_entry.get()
        self.config["pg_restore_path"] = self.pg_restore_entry.get()
        self.config["psql_path"] = self.psql_entry.get()
        self.config["backup_directory"] = self.backup_dir_entry.get()
        self.config["keep_last_n_backups"] = int(self.keep_backups_spinbox.get())
        
        self.save_config()
        messagebox.showinfo("Успешно", "Настройки подключения сохранены!")
    
    def test_connection(self):
        """Test PostgreSQL connection"""
        try:
            host = self.host_entry.get()
            port = self.port_entry.get()
            database = self.db_entry.get()
            username = self.user_entry.get()
            password = self.pass_entry.get()
            
            # Use environment variables to avoid password prompt
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Try pg_isready first
            cmd = [
                "pg_isready",
                "-h", host,
                "-p", port,
                "-U", username,
                "-d", database
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                messagebox.showinfo("Успешно", "Подключение к PostgreSQL установлено!")
            else:
                # If pg_isready fails, try SELECT 1
                psql_cmd = [
                    "psql",
                    "-h", host,
                    "-p", port,
                    "-U", username,
                    "-d", database,
                    "-c", "SELECT 1;"
                ]
                
                result = subprocess.run(psql_cmd, env=env, capture_output=True, text=True)
                if result.returncode == 0:
                    messagebox.showinfo("Успешно", "Подключение к PostgreSQL установлено!")
                else:
                    messagebox.showerror("Ошибка", f"Не удалось подключиться: {result.stderr}")
                    
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при проверке подключения: {str(e)}")
    
    def start_backup(self):
        """Start backup process in a separate thread"""
        self.backup_btn.config(state=tk.DISABLED)
        self.backup_log.delete(1.0, tk.END)
        
        # Start backup in a separate thread
        thread = threading.Thread(target=self.perform_backup)
        thread.daemon = True
        thread.start()
    
    def perform_backup(self):
        """Perform the actual backup operation"""
        try:
            # Get settings
            host = self.host_entry.get()
            port = self.port_entry.get()
            database = self.db_entry.get()
            username = self.user_entry.get()
            password = self.pass_entry.get()
            backup_format = self.format_var.get()
            backup_dir = self.backup_dir_entry.get()
            
            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if backup_format == "sql":
                filename = f"{database}_{timestamp}.sql"
            else:
                filename = f"{database}_{timestamp}.backup"
            
            backup_path = os.path.join(backup_dir, filename)
            
            # Set environment variables
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Build command
            if backup_format == "sql":
                cmd = [
                    "pg_dump",
                    "-h", host,
                    "-p", port,
                    "-U", username,
                    "-d", database,
                    "-f", backup_path
                ]
            else:
                cmd = [
                    "pg_dump",
                    "-h", host,
                    "-p", port,
                    "-U", username,
                    "-d", database,
                    "-Fc",
                    "-f", backup_path
                ]
            
            # Run backup command
            self.update_backup_log(f"Начинаю резервное копирование в {backup_path}...")
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.update_backup_log("Резервное копирование завершено успешно!")
                self.update_backup_log(f"Файл: {backup_path}")
                
                # Clean old backups
                self.cleanup_old_backups(backup_dir, database, backup_format)
            else:
                self.update_backup_log(f"Ошибка при резервном копировании: {result.stderr}")
                
        except Exception as e:
            self.update_backup_log(f"Ошибка: {str(e)}")
        finally:
            self.backup_btn.config(state=tk.NORMAL)
    
    def update_backup_log(self, message):
        """Update backup log with new message"""
        self.backup_log.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.backup_log.see(tk.END)
        self.root.update_idletasks()
    
    def cleanup_old_backups(self, backup_dir, database, backup_format):
        """Clean up old backup files, keeping only the last N"""
        try:
            keep_count = int(self.keep_backups_spinbox.get())
            
            # Determine file extension
            if backup_format == "sql":
                ext = ".sql"
            else:
                ext = ".backup"
            
            # Find all backup files for this database
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.startswith(database + "_") and filename.endswith(ext):
                    filepath = os.path.join(backup_dir, filename)
                    backup_files.append((filepath, os.path.getmtime(filepath)))
            
            # Sort by modification time (oldest first)
            backup_files.sort(key=lambda x: x[1])
            
            # Remove oldest files if we have more than allowed
            files_to_remove = len(backup_files) - keep_count
            if files_to_remove > 0:
                for i in range(files_to_remove):
                    filepath = backup_files[i][0]
                    os.remove(filepath)
                    self.update_backup_log(f"Удалена старая резервная копия: {os.path.basename(filepath)}")
                    
        except Exception as e:
            self.update_backup_log(f"Ошибка при очистке старых резервных копий: {str(e)}")
    
    def check_target_db_for_warning(self, backup_file):
        """Check if target DB matches source DB to show warning"""
        if not backup_file:
            return
            
        # Extract database name from backup file
        filename = os.path.basename(backup_file)
        # Pattern: database_timestamp.ext
        match = re.match(r'^([a-zA-Z0-9_]+)_\d{8}_\d{6}\.(sql|backup)$', filename)
        
        if match:
            source_db = match.group(1)
            target_db = self.target_db_entry.get().strip()
            
            if source_db and target_db and source_db.lower() == target_db.lower():
                self.show_restore_warning()
            else:
                self.hide_restore_warning()
        else:
            self.hide_restore_warning()
    
    def show_restore_warning(self):
        """Show warning about restoring over source database"""
        self.warning_label.config(text="⚠️ Вы пытаетесь восстановить данные поверх исходной базы! Это может привести к потере текущих данных.")
        self.warning_label.grid()
        
        self.confirm_frame.grid()
        self.confirm_entry.delete(0, tk.END)
        self.restore_btn.config(state=tk.DISABLED)
    
    def hide_restore_warning(self):
        """Hide restore warning"""
        self.warning_label.grid_remove()
        self.confirm_frame.grid_remove()
        self.restore_btn.config(state=tk.NORMAL)
    
    def check_confirmation(self, event=None):
        """Check if confirmation matches target database"""
        confirm_text = self.confirm_entry.get()
        target_db = self.target_db_entry.get().strip()
        
        if confirm_text == target_db:
            self.restore_btn.config(state=tk.NORMAL)
        else:
            self.restore_btn.config(state=tk.DISABLED)
    
    def start_restore(self):
        """Start restore process in a separate thread"""
        self.restore_btn.config(state=tk.DISABLED)
        self.restore_log.delete(1.0, tk.END)
        
        # Start restore in a separate thread
        thread = threading.Thread(target=self.perform_restore)
        thread.daemon = True
        thread.start()
    
    def perform_restore(self):
        """Perform the actual restore operation"""
        try:
            restore_file = self.restore_file_entry.get()
            target_db = self.target_db_entry.get()
            host = self.host_entry.get()
            port = self.port_entry.get()
            username = self.user_entry.get()
            password = self.pass_entry.get()
            
            if not restore_file or not target_db:
                self.update_restore_log("Ошибка: Не указан файл резервной копии или целевая база данных")
                return
            
            # Set environment variables
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Determine if it's a SQL file or custom format
            if restore_file.lower().endswith('.sql'):
                # Restore using psql
                cmd = [
                    "psql",
                    "-h", host,
                    "-p", port,
                    "-U", username,
                    "-d", target_db,
                    "-f", restore_file
                ]
            else:
                # Restore using pg_restore
                cmd = [
                    "pg_restore",
                    "-h", host,
                    "-p", port,
                    "-U", username,
                    "-d", target_db,
                    restore_file
                ]
            
            self.update_restore_log(f"Начинаю восстановление из {restore_file} в базу {target_db}...")
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.update_restore_log("Восстановление завершено успешно!")
            else:
                self.update_restore_log(f"Ошибка при восстановлении: {result.stderr}")
                
        except Exception as e:
            self.update_restore_log(f"Ошибка: {str(e)}")
        finally:
            self.restore_btn.config(state=tk.NORMAL)
    
    def update_restore_log(self, message):
        """Update restore log with new message"""
        self.restore_log.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.restore_log.see(tk.END)
        self.root.update_idletasks()
    
    def create_scheduled_task(self):
        """Create scheduled task for automatic backup"""
        try:
            task_name = self.task_name_entry.get()
            frequency = self.frequency_var.get()
            time_str = self.time_entry.get()
            
            # Validate time format
            if not re.match(r'^\d{2}:\d{2}$', time_str):
                messagebox.showerror("Ошибка", "Неверный формат времени. Используйте ЧЧ:ММ")
                return
            
            # Get current script path
            script_path = os.path.abspath(__file__)
            
            # Build command to run the backup
            cmd = [
                "schtasks",
                "/create",
                "/tn", task_name,
                "/tr", f'python "{script_path}" --backup-only',
                "/sc", "daily" if frequency == "daily" else "weekly",
                "/st", time_str,
                "/f"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.update_task_log(f"Задание '{task_name}' создано успешно")
            else:
                self.update_task_log(f"Ошибка при создании задания: {result.stderr}")
                
        except Exception as e:
            self.update_task_log(f"Ошибка: {str(e)}")
    
    def delete_scheduled_task(self):
        """Delete scheduled task"""
        try:
            task_name = self.task_name_entry.get()
            
            cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.update_task_log(f"Задание '{task_name}' удалено успешно")
            else:
                self.update_task_log(f"Ошибка при удалении задания: {result.stderr}")
                
        except Exception as e:
            self.update_task_log(f"Ошибка: {str(e)}")
    
    def view_scheduled_task(self):
        """View scheduled task status"""
        try:
            task_name = self.task_name_entry.get()
            
            cmd = ["schtasks", "/query", "/tn", task_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.update_task_log(f"Статус задания '{task_name}':\n{result.stdout}")
            else:
                self.update_task_log(f"Задание '{task_name}' не найдено или ошибка: {result.stderr}")
                
        except Exception as e:
            self.update_task_log(f"Ошибка: {str(e)}")
    
    def update_task_log(self, message):
        """Update task log with new message"""
        self.task_status_log.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.task_status_log.see(tk.END)


def main():
    # Handle command line arguments for automated backup
    if len(sys.argv) > 1 and sys.argv[1] == "--backup-only":
        # Perform automated backup only
        print("Running automated backup...")
        # In a real implementation, you would connect to PostgreSQL and perform backup
        # For now, just exit
        sys.exit(0)
    
    # Create main window
    root = tk.Tk()
    app = PostgreSQLBackupRestoreApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()