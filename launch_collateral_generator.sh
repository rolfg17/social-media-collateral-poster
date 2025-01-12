#!/bin/bash

# Debug logging
exec 1> >(tee -a "/tmp/collateral_generator_debug.log")
exec 2>&1
echo "$(date): Script started"

# Ensure we have a file argument
if [ -z "$1" ]; then
    echo "Error: No file path provided"
    exit 1
fi

# Clean up the file path (just remove quotes)
FILE_PATH=$(echo "$1" | sed 's/^"//g' | sed 's/"$//g' | sed "s/^'//g" | sed "s/'$//g")
echo "Original file path: '$1'"
echo "Cleaned file path: '$FILE_PATH'"

# Verify file exists
if [ ! -f "$FILE_PATH" ]; then
    echo "Error: File does not exist: $FILE_PATH"
    exit 1
fi

# Show file contents for debugging
echo "File preview (first 3 lines):"
head -n 3 "$FILE_PATH"

# Check if streamlit is already running
if pgrep -f "streamlit run app.py" > /dev/null; then
    echo "Streamlit is already running, killing existing process..."
    pkill -f "streamlit run app.py"
    sleep 2
fi

# Set up Python environment
echo "Setting up conda environment..."
export PATH="/opt/anaconda3/bin:$PATH"
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate base

# Run streamlit
echo "Running streamlit with file: $FILE_PATH"
streamlit run app.py -- --file="$FILE_PATH"
