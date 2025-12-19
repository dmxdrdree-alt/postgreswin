# PostgreSQL Backup and Restore Utility (PyQt6 Version)

A comprehensive GUI application for PostgreSQL database backup and restoration with scheduling capabilities, built with PyQt6.

## Features

### 1. Connection Management
- Fields for host, port, user, and password
- "Check Connection" button that executes pg_isready or SELECT 1
- Automatic or manual specification of paths to pg_dump.exe, pg_restore.exe, and psql.exe
- Auto-detection of PostgreSQL installation paths from Windows registry and common directories

### 2. Multi-Database Backup
- Select one or multiple databases from an automatically populated list
- Alternative: manually enter database names via comma-separated input
- Support for two formats:
  - Plain SQL (.sql) - compatible with pgAdmin and psql
  - Custom (.backup) - for pg_restore
- Automatic naming: `dbname_YYYYMMDD_HHMMSS.sql` or `.backup`
- Common destination folder for all backups
- Auto-cleanup: retain only the last N backups per database (default: 10)
- Progress bar and logging with status per database

### 3. Restoration from Backup
- File selection dialog supporting .sql and .backup files
- Automatic source database name detection (from filename or file content)
- Target database specification field
- Protection against accidental overwrite:
  - Shows prominent warning (red background, warning icon) when target matches source
  - "⚠️ Вы пытаетесь восстановить данные поверх исходной базы! Это приведёт к потере текущих данных."
  - Requires confirmation by entering the target database name
- Supports restoration:
  - .sql → via psql
  - .backup → via pg_restore
- Progress tracking and detailed logging

### 4. Windows Task Scheduler
- Create scheduled tasks for automated backup of all selected databases
- Configuration options:
  - Frequency: Daily / Weekly (with day selection)
  - Start time (HH:MM)
- Buttons: "Create Task", "Delete Task", "View Tasks"
- Task parameters (connection and database list) are saved (but not password - prompts securely at runtime)

### 5. User Interface
- Tabbed interface with Connection, Backup, Restore, and Schedule panels
- All actions are visual with no console (except for logging)
- DPI scaling support and adaptive window sizing
- All errors are clear, in Russian, with recommendations

## Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL client tools (pg_dump, pg_restore, psql) installed on the system

### Setup
1. Clone or download the repository
2. Install dependencies:
   ```bash
   pip install -r requirements_pyqt.txt
   ```
3. Run the application:
   ```bash
   python pg_backup_restore_pyqt.py
   ```

## Usage

### Connection Tab
1. Enter your PostgreSQL server details (host, port, username, password)
2. The application will auto-detect PostgreSQL executable paths, or you can specify them manually
3. Click "Проверить подключение" to test the connection
4. Click "Сохранить настройки" to save your connection configuration

### Backup Tab
1. Select the backup format (Plain SQL or Custom)
2. Choose the backup destination directory
3. Click "Загрузить список баз данных" to populate the database list
4. Select one or more databases from the list
5. Alternatively, enter database names manually (comma-separated)
6. Click "Создать резервные копии" to start the backup process

### Restore Tab
1. Browse and select a backup file (.sql or .backup)
2. The source database name will be auto-detected
3. Enter the target database name
4. If source and target databases match, you'll see a warning and need to confirm
5. Click "Восстановить" to start the restoration process

### Schedule Tab
1. Configure the schedule parameters (frequency, day if weekly, time)
2. Click "Создать задание" to create a Windows scheduled task
3. Use "Просмотреть задания" to check the status of the scheduled task
4. Use "Удалить задание" to remove the scheduled task

## Security Notes
- Passwords are not saved to the configuration file
- Passwords are temporarily set as environment variables (PGPASSWORD) and immediately removed after operations
- The application handles all PostgreSQL operations securely

## Compilation to Executable

To compile the application to a standalone .exe file using PyInstaller:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Compile the application:
   ```bash
   pyinstaller --onefile --windowed --name "PostgreSQL_Backup_Restore" pg_backup_restore_pyqt.py
   ```

The resulting executable will be in the `dist` folder and will contain all dependencies needed to run on Windows systems.

## Troubleshooting

If you encounter issues with PostgreSQL executable paths:
1. Make sure PostgreSQL client tools are installed on your system
2. Use the "Обзор" buttons to manually specify paths to pg_dump.exe, pg_restore.exe, and psql.exe
3. Check that the paths are correct and the files exist

For connection issues:
1. Verify that PostgreSQL server is running and accessible
2. Check that the host, port, username, and password are correct
3. Ensure that the PostgreSQL client tools are compatible with your server version