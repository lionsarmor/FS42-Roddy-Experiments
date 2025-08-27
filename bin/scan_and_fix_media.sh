#!/bin/bash
# Scan bumps/commercials for broken MP4s and auto-fix them
# Auto-replaces broken files in-place ⚡

cd /mnt/media01/projects/FieldStation42 || { echo "❌ FS42 dir not found"; exit 1; }

SCAN_DIRS=("catalog" "commercials" "bumps")   # add more if needed
LOGFILE="scan_results.log"

: > "$LOGFILE"

echo "=== FS42 Media Scan $(date) ===" | tee -a "$LOGFILE"

# Function to test MP4 integrity
check_file() {
    local file="$1"
    echo "Scanning: $file"

    if ffmpeg -v error -i "$file" -f null - 2>>"$LOGFILE"; then
        echo "  ✅ OK"
    else
        echo "  ❌ Broken — re-encoding..."
        fix_file "$file"
    fi
}

# Function to re-encode and replace file
fix_file() {
    local infile="$1"
    local tmpfile="${infile}.fixed.mp4"

    ffmpeg -y -i "$infile" \
        -c:v libx264 -preset veryfast -crf 18 \
        -c:a aac -b:a 128k \
        "$tmpfile"

    if [ $? -eq 0 ]; then
        mv "$tmpfile" "$infile"
        echo "  🔧 Replaced $infile" | tee -a "$LOGFILE"
    else
        echo "  💥 Failed to fix $infile" | tee -a "$LOGFILE"
        rm -f "$tmpfile"
    fi
}

# Main scan loop
for dir in "${SCAN_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        find "$dir" -type f -iname "*.mp4" | while read -r f; do
            check_file "$f"
        done
    fi
done

echo "=== Scan complete. Results saved in $LOGFILE ==="
