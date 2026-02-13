#!/bin/bash
# Backup script for Quest Pro data collection
# Usage: ./backup_quest_data.sh [backup_directory]

# Get date for backup folder name
DATE=$(date +%Y%m%d_%H%M%S)

# Set backup directory
if [ -z "$1" ]; then
    BACKUP_DIR="$HOME/VR_Study_Backups/Backup_$DATE"
else
    BACKUP_DIR="$1/Backup_$DATE"
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "=========================================="
echo "Quest Pro Data Backup Script"
echo "=========================================="
echo "Backup directory: $BACKUP_DIR"
echo ""

# Check if adb is available
if ! command -v adb &> /dev/null; then
    echo "Error: adb not found in PATH"
    echo "Please add Android SDK platform-tools to your PATH"
    echo "Or run this script from Unity Android SDK platform-tools directory"
    exit 1
fi

# Check if device is connected
echo "Checking for connected devices..."
DEVICES=$(adb devices | grep -v "List" | grep "device$" | wc -l)

if [ "$DEVICES" -eq 0 ]; then
    echo "Error: No Android device connected"
    echo "Please connect Quest Pro and enable USB debugging"
    exit 1
fi

echo "Found $DEVICES device(s) connected"
echo ""

# Quest Pro data path (adjust package name if needed)
PACKAGE_NAME="com.yourname.vrdatacollector"
DATA_PATH="/sdcard/Android/data/$PACKAGE_NAME/files/DataCollection"

echo "Checking for data files..."
# Check if data directory exists
adb shell ls "$DATA_PATH" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Warning: Data directory not found: $DATA_PATH"
    echo "Make sure the app has been run at least once"
    echo ""
    echo "Trying to list all data directories..."
    adb shell ls /sdcard/Android/data/ | head -20
    exit 1
fi

# Count files
FILE_COUNT=$(adb shell ls "$DATA_PATH" | grep -c "\.csv")
echo "Found $FILE_COUNT CSV files"
echo ""

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "No data files found. Nothing to backup."
    exit 0
fi

# Pull data files
echo "Copying data files..."
adb pull "$DATA_PATH" "$BACKUP_DIR/"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ Backup completed successfully!"
    echo "=========================================="
    echo "Backup location: $BACKUP_DIR"
    echo ""
    
    # List files
    echo "Backed up files:"
    ls -lh "$BACKUP_DIR" | grep "\.csv" | awk '{print "  " $9 " (" $5 ")"}'
    echo ""
    
    # Calculate total size
    TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
    echo "Total backup size: $TOTAL_SIZE"
else
    echo ""
    echo "Error: Backup failed"
    exit 1
fi
