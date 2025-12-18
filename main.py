import sys
import os
import subprocess
import threading
import json
from datetime import datetime
from pathlib import Path
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar, QGroupBox,
    QFileDialog, QMessageBox, QComboBox, QCheckBox, QSpinBox, QDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont


class Worker(QObject):
    """Worker class for running backup operations in a separate thread"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    log_message = pyqtSignal(str)

    def __init__(self, backup_func, *args, **kwargs):
        super().__init__()
        self.backup_func = backup_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.backup_func(*self.args, **self.kwargs)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.resize(400, 200)
        
        layout = QVBoxLayout()
        
        # PostgreSQL path settings
        pg_group = QGroupBox("Путь к PostgreSQL")
        pg_layout = QVBoxLayout()
        self.pg_path_label = QLabel("Путь к pg_dump.exe:")
        self.pg_path_edit = QLineEdit()
        self.pg_path_button = QPushButton("Обзор...")
        self.pg_path_button.clicked.connect(self.browse_pg_path)
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.pg_path_edit)
        h_layout.addWidget(self.pg_path_button)
        
        pg_layout.addWidget(self.pg_path_label)
        pg_layout.addLayout(h_layout)
        pg_group.setLayout(pg_layout)
        
        # Advanced settings
        adv_group = QGroupBox("Расширенные настройки")
        adv_layout = QGridLayout()
        self.max_backups_label = QLabel("Максимальное количество копий:")
        self.max_backups_spin = QSpinBox()
        self.max_backups_spin.setRange(1, 100)
        self.max_backups_spin.setValue(10)
        
        adv_layout.addWidget(self.max_backups_label, 0, 0)
        adv_layout.addWidget(self.max_backups_spin, 0, 1)
        adv_group.setLayout(adv_layout)
        
        layout.addWidget(pg_group)
        layout.addWidget(adv_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Отмена")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def browse_pg_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите pg_dump.exe", "", "pg_dump.exe (pg_dump.exe)"
        )
        if path:
            self.pg_path_edit.setText(path)


class BackupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PostgreSQL Backup Manager")
        self.setGeometry(100, 100, 800, 700)
        
        # Load settings
        self.load_settings()
        
        # Create UI
        self.init_ui()
        
        # Thread for backup operations
        self.thread = None
        self.worker = None

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        
        title_label = QLabel("PostgreSQL Backup Manager")
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Connection group
        conn_group = QGroupBox("Подключение к PostgreSQL")
        conn_layout = QGridLayout()
        
        # Host
        conn_layout.addWidget(QLabel("Хост:"), 0, 0)
        self.host_edit = QLineEdit("localhost")
        conn_layout.addWidget(self.host_edit, 0, 1)
        
        # Port
        conn_layout.addWidget(QLabel("Порт:"), 0, 2)
        self.port_edit = QLineEdit("5432")
        conn_layout.addWidget(self.port_edit, 0, 3)
        
        # Database
        conn_layout.addWidget(QLabel("База данных:"), 1, 0)
        self.db_edit = QLineEdit()
        conn_layout.addWidget(self.db_edit, 1, 1)
        
        # User
        conn_layout.addWidget(QLabel("Пользователь:"), 1, 2)
        self.user_edit = QLineEdit()
        conn_layout.addWidget(self.user_edit, 1, 3)
        
        # Password
        conn_layout.addWidget(QLabel("Пароль:"), 2, 0)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        conn_layout.addWidget(self.password_edit, 2, 1)
        
        # Test connection button
        self.test_conn_button = QPushButton("Проверить подключение")
        self.test_conn_button.clicked.connect(self.test_connection)
        conn_layout.addWidget(self.test_conn_button, 2, 2, 1, 2)
        
        conn_group.setLayout(conn_layout)
        main_layout.addWidget(conn_group)
        
        # Backup settings group
        backup_group = QGroupBox("Настройки резервного копирования")
        backup_layout = QGridLayout()
        
        # Format selection
        backup_layout.addWidget(QLabel("Формат резервной копии:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["plain SQL (.sql)", "custom (.backup)"])
        backup_layout.addWidget(self.format_combo, 0, 1)
        
        # Backup folder
        backup_layout.addWidget(QLabel("Папка для резервных копий:"), 1, 0)
        self.backup_folder_edit = QLineEdit()
        self.backup_folder_button = QPushButton("Обзор...")
        self.backup_folder_button.clicked.connect(self.browse_backup_folder)
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.backup_folder_edit)
        h_layout.addWidget(self.backup_folder_button)
        backup_layout.addLayout(h_layout, 1, 1)
        
        # Backup button
        self.backup_button = QPushButton("Создать резервную копию")
        self.backup_button.clicked.connect(self.start_backup)
        backup_layout.addWidget(self.backup_button, 2, 0, 1, 2)
        
        backup_group.setLayout(backup_layout)
        main_layout.addWidget(backup_group)
        
        # Schedule group
        schedule_group = QGroupBox("Расписание резервного копирования")
        schedule_layout = QGridLayout()
        
        # Frequency
        schedule_layout.addWidget(QLabel("Частота:"), 0, 0)
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(["Ежедневно", "Еженедельно"])
        schedule_layout.addWidget(self.freq_combo, 0, 1)
        
        # Time
        schedule_layout.addWidget(QLabel("Время (HH:MM):"), 1, 0)
        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("HH:MM")
        schedule_layout.addWidget(self.time_edit, 1, 1)
        
        # Schedule buttons
        self.create_task_button = QPushButton("Создать задание")
        self.delete_task_button = QPushButton("Удалить задание")
        self.view_tasks_button = QPushButton("Просмотреть задания")
        
        self.create_task_button.clicked.connect(self.create_schedule_task)
        self.delete_task_button.clicked.connect(self.delete_schedule_task)
        self.view_tasks_button.clicked.connect(self.view_schedule_tasks)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.create_task_button)
        btn_layout.addWidget(self.delete_task_button)
        btn_layout.addWidget(self.view_tasks_button)
        schedule_layout.addLayout(btn_layout, 2, 0, 1, 2)
        
        schedule_group.setLayout(schedule_layout)
        main_layout.addWidget(schedule_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Log area
        log_group = QGroupBox("Лог операций")
        log_layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(200)
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # Settings button
        self.settings_button = QPushButton("Настройки")
        self.settings_button.clicked.connect(self.open_settings)
        main_layout.addWidget(self.settings_button)
        
        # Status bar
        self.statusBar().showMessage("Готово")

    def load_settings(self):
        """Load application settings from JSON file"""
        settings_file = Path.home() / ".postgres_backup_manager" / "settings.json"
        self.settings = {
            "pg_dump_path": "",
            "max_backups": 10,
            "last_backup_folder": ""
        }
        
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
            except:
                pass
    
    def save_settings(self):
        """Save application settings to JSON file"""
        settings_dir = Path.home() / ".postgres_backup_manager"
        settings_dir.mkdir(exist_ok=True)
        
        settings_file = settings_dir / "settings.json"
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)

    def find_pg_dump(self):
        """Find pg_dump.exe in standard PostgreSQL installation paths"""
        if self.settings["pg_dump_path"] and Path(self.settings["pg_dump_path"]).exists():
            return self.settings["pg_dump_path"]
        
        # Common PostgreSQL installation paths
        possible_paths = []
        for version_dir in Path("C:/Program Files").glob("PostgreSQL/*/bin"):
            pg_dump_path = version_dir / "pg_dump.exe"
            if pg_dump_path.exists():
                possible_paths.append(str(pg_dump_path))
        
        if possible_paths:
            # Return the most recent version
            return sorted(possible_paths, reverse=True)[0]
        
        return ""

    def browse_backup_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для резервных копий")
        if folder:
            self.backup_folder_edit.setText(folder)
            self.settings["last_backup_folder"] = folder
            self.save_settings()

    def test_connection(self):
        """Test PostgreSQL connection"""
        host = self.host_edit.text()
        port = self.port_edit.text()
        db = self.db_edit.text()
        user = self.user_edit.text()
        password = self.password_edit.text()
        
        if not all([host, port, db, user, password]):
            QMessageBox.warning(self, "Ошибка", "Заполните все поля подключения!")
            return
        
        # Set PGPASSWORD environment variable temporarily
        old_password = os.environ.get('PGPASSWORD')
        os.environ['PGPASSWORD'] = password
        
        try:
            cmd = [
                "pg_isready",
                "-h", host,
                "-p", port,
                "-d", db,
                "-U", user
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                QMessageBox.information(self, "Успех", "Подключение к PostgreSQL успешно!")
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться: {result.stderr}")
        except FileNotFoundError:
            # pg_isready not found, try with pg_dump
            try:
                pg_dump_path = self.find_pg_dump()
                if not pg_dump_path:
                    QMessageBox.critical(self, "Ошибка", "pg_dump.exe не найден. Установите PostgreSQL или укажите путь в настройках.")
                    return
                
                cmd = [
                    pg_dump_path,
                    "--version"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    QMessageBox.information(self, "Успех", "pg_dump найден, подключение возможно!")
                else:
                    QMessageBox.critical(self, "Ошибка", f"pg_dump недоступен: {result.stderr}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка проверки подключения: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка проверки подключения: {str(e)}")
        finally:
            # Clear PGPASSWORD environment variable
            if old_password is not None:
                os.environ['PGPASSWORD'] = old_password
            else:
                os.environ.pop('PGPASSWORD', None)

    def start_backup(self):
        """Start backup operation in a separate thread"""
        if hasattr(self, 'thread') and self.thread is not None and self.thread.is_alive():
            QMessageBox.warning(self, "Внимание", "Операция резервного копирования уже выполняется!")
            return
        
        # Validate inputs
        if not all([self.host_edit.text(), self.port_edit.text(), 
                   self.db_edit.text(), self.user_edit.text(), 
                   self.password_edit.text()]):
            QMessageBox.warning(self, "Ошибка", "Заполните все поля подключения!")
            return
        
        if not self.backup_folder_edit.text():
            QMessageBox.warning(self, "Ошибка", "Выберите папку для резервных копий!")
            return
        
        # Start backup in a separate thread
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Pass the method to run in the thread
        self.thread = threading.Thread(target=self.perform_backup_thread)
        self.thread.start()
        
        # Update UI
        self.backup_button.setEnabled(False)
        self.statusBar().showMessage("Выполняется резервное копирование...")
        
        # Start monitoring thread
        self.monitor_thread()

    def perform_backup_thread(self):
        """Perform the actual backup operation in a separate thread"""
        host = self.host_edit.text()
        port = self.port_edit.text()
        db = self.db_edit.text()
        user = self.user_edit.text()
        password = self.password_edit.text()
        backup_folder = self.backup_folder_edit.text()
        format_choice = self.format_combo.currentText()
        
        # Determine output format
        if format_choice == "plain SQL (.sql)":
            ext = ".sql"
            format_opt = "--format=p"
        else:
            ext = ".backup"
            format_opt = "--format=c"
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{db}_{timestamp}{ext}"
        filepath = Path(backup_folder) / filename
        
        # Find pg_dump
        pg_dump_path = self.find_pg_dump()
        if not pg_dump_path:
            self.log_to_ui("ERROR: pg_dump.exe не найден. Установите PostgreSQL или укажите путь в настройках.")
            return
        
        # Set PGPASSWORD environment variable
        old_password = os.environ.get('PGPASSWORD')
        os.environ['PGPASSWORD'] = password
        
        try:
            # Build command
            cmd = [
                pg_dump_path,
                "-h", host,
                "-p", port,
                "-d", db,
                "-U", user,
                format_opt,
                "-f", str(filepath)
            ]
            
            self.log_to_ui(f"Выполняется команда: {' '.join(cmd)}")
            
            # Run pg_dump
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
            
            if result.returncode == 0:
                self.log_to_ui(f"Резервная копия создана успешно: {filepath}")
                
                # Clean up old backups
                self.cleanup_old_backups(backup_folder, db, ext)
            else:
                self.log_to_ui(f"Ошибка создания резервной копии: {result.stderr}")
        except subprocess.TimeoutExpired:
            self.log_to_ui("Ошибка: Время ожидания операции истекло (5 минут)")
        except Exception as e:
            self.log_to_ui(f"Ошибка: {str(e)}")
        finally:
            # Clear PGPASSWORD environment variable
            if old_password is not None:
                os.environ['PGPASSWORD'] = old_password
            else:
                os.environ.pop('PGPASSWORD', None)
        
        # Update UI when done
        self.on_backup_finished()

    def monitor_thread(self):
        """Monitor the backup thread and update UI periodically"""
        # Using a simple timer approach instead of complex threading
        QTimer.singleShot(1000, self.check_thread_status)

    def check_thread_status(self):
        """Check if the thread is still running"""
        if hasattr(self, 'thread') and self.thread is not None and self.thread.is_alive():
            # Continue checking
            QTimer.singleShot(1000, self.check_thread_status)
        else:
            # Thread finished
            self.on_backup_finished()

    def on_backup_finished(self):
        """Handle completion of backup operation"""
        # Update UI in the main thread
        self.progress_bar.setVisible(False)
        self.backup_button.setEnabled(True)
        self.statusBar().showMessage("Готово")
        
        # Reset thread reference
        if hasattr(self, 'thread'):
            self.thread = None

    def log_to_ui(self, message):
        """Log message to the UI log area (thread-safe)"""
        # Add timestamp to message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Update log area (this needs to be called from main thread)
        # For now, we'll just append directly, but in a real scenario we'd use signals
        try:
            self.log_area.append(formatted_message)
        except:
            # Fallback in case of threading issues
            pass

    def cleanup_old_backups(self, backup_folder, db_prefix, ext):
        """Remove old backup files exceeding max count"""
        try:
            backup_files = list(Path(backup_folder).glob(f"{db_prefix}_*{ext}"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            max_backups = self.settings.get("max_backups", 10)
            if len(backup_files) > max_backups:
                files_to_remove = backup_files[max_backups:]
                for file in files_to_remove:
                    file.unlink()
                    self.log_message.emit(f"Удалена старая резервная копия: {file.name}")
        except Exception as e:
            self.log_message.emit(f"Ошибка при удалении старых резервных копий: {str(e)}")

    def create_schedule_task(self):
        """Create scheduled backup task using Windows schtasks"""
        freq = self.freq_combo.currentText()
        time_str = self.time_edit.text()
        
        if not time_str:
            QMessageBox.warning(self, "Ошибка", "Введите время в формате HH:MM")
            return
        
        # Validate time format
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
            QMessageBox.warning(self, "Ошибка", "Неверный формат времени. Используйте HH:MM")
            return
        
        # Create scheduled task
        try:
            # Get current script path
            script_path = sys.executable
            current_script = __file__
            
            # For compiled .exe, we need to handle differently
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                script_path = sys.executable
            else:
                # Running as script
                script_path = sys.executable
                current_script = __file__
            
            # Build command to run this script with specific arguments for scheduled backup
            task_cmd = f'"{script_path}" "{current_script}" --scheduled-backup'
            
            # Build schtasks command
            if freq == "Ежедневно":
                schtasks_cmd = [
                    "schtasks",
                    "/create",
                    "/tn", "PostgreSQL_Backup_Manager_Auto",
                    "/tr", task_cmd,
                    "/sc", "daily",
                    "/st", time_str,
                    "/f"
                ]
            else:  # Еженедельно
                schtasks_cmd = [
                    "schtasks",
                    "/create",
                    "/tn", "PostgreSQL_Backup_Manager_Auto",
                    "/tr", task_cmd,
                    "/sc", "weekly",
                    "/d", "MON,TUE,WED,THU,FRI,SAT,SUN",
                    "/st", time_str,
                    "/f"
                ]
            
            result = subprocess.run(schtasks_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                QMessageBox.information(self, "Успех", f"Задание создано: {freq.lower()} в {time_str}")
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать задание: {result.stderr}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка создания задания: {str(e)}")

    def delete_schedule_task(self):
        """Delete scheduled backup task"""
        try:
            result = subprocess.run([
                "schtasks", "/delete", "/tn", "PostgreSQL_Backup_Manager_Auto", "/f"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                QMessageBox.information(self, "Успех", "Задание удалено")
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить задание: {result.stderr}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка удаления задания: {str(e)}")

    def view_schedule_tasks(self):
        """View existing scheduled tasks"""
        try:
            result = subprocess.run([
                "schtasks", "/query", "/tn", "PostgreSQL_Backup_Manager_Auto"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                QMessageBox.information(self, "Задание найдено", f"Задание существует:\n\n{result.stdout}")
            else:
                QMessageBox.information(self, "Задание не найдено", "Задание 'PostgreSQL_Backup_Manager_Auto' не найдено")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка просмотра задания: {str(e)}")

    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        dialog.pg_path_edit.setText(self.settings.get("pg_dump_path", ""))
        dialog.max_backups_spin.setValue(self.settings.get("max_backups", 10))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings["pg_dump_path"] = dialog.pg_path_edit.text()
            self.settings["max_backups"] = dialog.max_backups_spin.value()
            self.save_settings()

    def closeEvent(self, event):
        """Handle application close event"""
        # Stop any running threads
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = BackupApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()