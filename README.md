# PostgreSQL Backup and Restore Utility

A comprehensive GUI application for PostgreSQL database backup and restoration with scheduling capabilities.

## Features

### 1. Connection Management
- Fields for host, port, database name, user, and password
- "Check Connection" button (executes pg_isready or SELECT 1 via psql)
- **Automatic Path Detection**: The application automatically detects PostgreSQL executables from Windows registry or common installation paths (C:\Program Files\PostgreSQL\)
- Manual specification of paths to pg_dump.exe, pg_restore.exe, and psql.exe if automatic detection fails

### 2. Backup Capabilities
- **Format Selection**: Choose between Plain SQL (.sql) and Custom (.backup) formats
- **Backup Destination**: Specify backup directory
- **Automatic Naming**: Files named as `dbname_YYYYMMDD_HHMMSS.sql` or `.backup`
- **Auto Cleanup**: Maintain only the last N backups (configurable, default 10)
- **Progress Bar and Logs**: Visual feedback during backup operations

### 3. Restoration Features
- **File Selection**: Browse dialog for selecting backup files
- **Target Database**: Specify destination database for restoration
- **Security Warning**: Noticeable warning (red icon, highlighted text) when attempting to restore over the source database:
  - "Вы пытаетесь восстановить данные поверх исходной базы! Это может привести к потере текущих данных."
  - Requires explicit confirmation by entering the target database name in a text field
- **Format Support**: Restore both .sql (via psql) and .backup (via pg_restore) files
- **Progress and Logging**: Track restoration progress

### 4. Job Scheduler
- **Windows Task Scheduler Integration**: Create scheduled tasks for automatic backups
- **Configurable Parameters**: Frequency (daily/weekly) and start time
- **Management Options**: Create, delete, and view job status
- **Russian Language Interface**: All labels, messages, and warnings in Russian

### 5. User Interface
- **Tabbed Interface**: Connection, Backup, Restore, and Schedule panels
- **Clear Controls**: Intuitive elements with tooltips
- **Input Validation**: Error handling with clear Russian-language error messages
- **DPI Scaling**: Compatible with mobile scaling and high-DPI displays

## Requirements

- Python 3.6+
- PostgreSQL client tools (pg_dump, pg_restore, psql, pg_isready)
- Windows OS (for scheduler functionality)

## Usage

1. Run the application: `python pg_backup_restore.py`
2. Configure connection settings in the "Подключение" tab
3. Test the connection using the "Проверить подключение" button
4. Save the settings
5. Use the other tabs to perform backups, restores, or configure scheduling

## Command Line Options

- `--backup-only`: Run an automated backup (used by scheduled tasks)

## Security Notes

- Passwords are stored in plain text in the configuration file (pg_config.json)
- Consider using PostgreSQL service accounts with limited permissions
- The application includes security checks to prevent accidental overwrites during restoration

## License

This project is open-source and available under the MIT License.