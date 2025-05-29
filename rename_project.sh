#!/bin/bash

# Project renaming script: RaspberryPi-CM4-main -> Rider-Robot-Controller
set -e

OLD_NAME="RaspberryPi-CM4-main"
NEW_NAME="Rider-Robot-Controller"
OLD_PATH="/home/pi/$OLD_NAME"
NEW_PATH="/home/pi/$NEW_NAME"

echo "========================================="
echo "Renaming project: $OLD_NAME -> $NEW_NAME"
echo "========================================="

# Step 1: Update all hardcoded paths in Python files
echo "Step 1: Updating hardcoded paths in files..."

# Find all files with the old path and update them
find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" \) -exec grep -l "$OLD_PATH" {} \; | while read file; do
    echo "  Updating: $file"
    sed -i "s|$OLD_PATH|$NEW_PATH|g" "$file"
done

# Step 2: Update the startup script
echo "Step 2: Updating startup script..."
if [ -f "/home/pi/start1.sh" ]; then
    echo "  Updating /home/pi/start1.sh"
    sudo sed -i "s|$OLD_PATH|$NEW_PATH|g" /home/pi/start1.sh
else
    echo "  /home/pi/start1.sh not found, skipping..."
fi

# Step 3: Create the new directory and move files
echo "Step 3: Moving project to new location..."
cd /home/pi
if [ -d "$NEW_NAME" ]; then
    echo "  Warning: Directory $NEW_NAME already exists!"
    read -p "  Do you want to remove it and continue? (y/N): " confirm
    if [[ $confirm == [yY] ]]; then
        rm -rf "$NEW_NAME"
    else
        echo "  Aborting rename operation"
        exit 1
    fi
fi

# Copy the directory to new location
echo "  Copying $OLD_NAME to $NEW_NAME..."
cp -r "$OLD_NAME" "$NEW_NAME"

# Verify the copy was successful
if [ -d "$NEW_NAME" ]; then
    echo "  Successfully created $NEW_NAME"
    echo "  Original directory $OLD_NAME preserved (you can delete it manually if everything works)"
else
    echo "  ERROR: Failed to create new directory"
    exit 1
fi

echo ""
echo "========================================="
echo "Project renamed successfully!"
echo "========================================="
echo "New project location: $NEW_PATH"
echo "Original directory preserved at: $OLD_PATH"
echo ""
echo "Next steps:"
echo "1. Test the robot controller: cd $NEW_PATH && python3 main.py"
echo "2. If everything works, you can remove the old directory: rm -rf $OLD_PATH"
echo "3. The startup script has been updated to use the new path"
echo "=========================================" 