# PostgreSQL Backup and Restore Utility - Complete Solution

## Overview
This project implements a comprehensive PostgreSQL backup and restore utility with a modern GUI using PyQt6. The application provides all the requested functionality for managing PostgreSQL databases with backup, restore, and scheduling capabilities.

## Features Implemented

### 1. Connection Management
- Fields for host, port, user, and password
- "Check Connection" button that executes pg_isready or SELECT 1
- Automatic or manual specification of paths to pg_dump.exe, pg_restore.exe, and psql.exe
- Auto-detection of PostgreSQL installation paths from Windows registry and common directories
- Cross-platform support (Windows registry detection on Windows, PATH detection on other systems)

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

## Files in the Solution

1. `pg_backup_restore_pyqt.py` - Main application file with complete PyQt6 implementation
2. `requirements_pyqt.txt` - Dependencies listing (PyQt6>=6.4.0)
3. `README_PYQT.md` - Comprehensive documentation
4. `run_pyqt_app.py` - Simple launcher script

## Security Notes
- Passwords are not saved to the configuration file
- Passwords are temporarily set as environment variables (PGPASSWORD) and immediately removed after operations
- The application handles all PostgreSQL operations securely

## Compilation to Executable

The application is ready for compilation to a standalone .exe file using PyInstaller:

```bash
pyinstaller --onefile --windowed --name "PostgreSQL_Backup_Restore" pg_backup_restore_pyqt.py
```

## Architecture Notes

The application uses a clean architecture with:
- Main window class (PostgreSQLBackupRestoreApp) managing the UI
- Worker threads (BackupWorker, RestoreWorker) for long-running operations
- Proper separation of concerns with dedicated methods for each feature
- Cross-platform compatibility with platform-specific code handling
- Comprehensive error handling and user feedback

## Dependencies

- PyQt6 (>=6.4.0)
- Python standard library modules (subprocess, json, datetime, etc.)

## Platform Compatibility

- Windows: Full functionality with registry detection and schtasks integration
- Linux/macOS: Core functionality with PATH-based executable detection (scheduling features may need adaptation)

## Key Implementation Details

1. **Password Security**: Uses PGPASSWORD environment variable temporarily during operations and clears it immediately
2. **Auto-detection**: Intelligent detection of PostgreSQL executables on Windows via registry and common paths
3. **Thread Safety**: Worker threads for backup/restore operations to keep UI responsive
4. **Error Handling**: Comprehensive error handling with user-friendly Russian messages
5. **Progress Tracking**: Real-time progress updates for long-running operations
6. **Auto-cleanup**: Automatic removal of old backup files based on retention policy

This implementation fully satisfies all requirements specified in the original request, providing a professional, secure, and user-friendly PostgreSQL backup and restore utility.