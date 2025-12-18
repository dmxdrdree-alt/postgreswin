"""
Setup script for PostgreSQL Backup Manager
This script is used for packaging the application with PyInstaller
"""
from setuptools import setup

# This setup.py is primarily for creating a package with PyInstaller
setup(
    name="PostgreSQL Backup Manager",
    version="1.0.0",
    description="PostgreSQL Backup Manager with GUI for Windows",
    author="PostgreSQL Backup Manager",
    author_email="",
    url="",
    packages=[],
    install_requires=[
        "PyQt6>=6.4.0",
        "pyinstaller>=5.13.0"
    ],
    entry_points={
        'console_scripts': [
            'postgres-backup-manager=main:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Environment :: Win32 (MS Windows)",
        "Intended Audience :: System Administrators",
        "Topic :: Database :: Database Engines/Servers",
    ],
    python_requires='>=3.8',
)