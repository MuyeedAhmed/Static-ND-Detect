#!/bin/bash

set -e

# Usage: ./RunPipeline.sh <project_path> <target_dir> [check_type]

PROJECT_PATH=$1
TARGET_DIR=$2
CHECK_TYPE=${3:-random}

if [ -z "$PROJECT_PATH" ] || [ -z "$TARGET_DIR" ]; then
    echo "Usage: $0 <project_path> <target_dir> [check_type]"
    echo "Example: $0 /path/to/project my_package random"
    exit 1
fi

PROJECT_PATH=$(python3 -c "import os, sys; print(os.path.abspath(sys.argv[1]))" "$PROJECT_PATH")
ROOT_DIR=$(pwd)

echo "--- [1/6] Copying Pysa Models & Generating Config ---"
python3 CopyPysaToLib.py "$PROJECT_PATH" "$TARGET_DIR" "$CHECK_TYPE"

if [[ "$CHECK_TYPE" == "random" ]]; then
    echo "--- [2/6] Modifying Source Code (Adding Taints) ---"
    python3 ModifySourceCode.py "$PROJECT_PATH"
fi

echo "--- [3/6] Running Pysa Analyze ---"
cd "$PROJECT_PATH"

pyre analyze --save-results-to ./pyre-output
cd "$ROOT_DIR"

echo "--- [4/6] Extracting Results to XLSX ---"
cd Utils
python3 ExtractJSON.py "$PROJECT_PATH"

echo "--- [5/6] Filtering Modules and Duplicates and add comments ---"
python3 Filter_SeparateModules.py
python3 ExtractComments.py "$PROJECT_PATH"

echo "--- [6/6] Generating TITO (Taint-In-Taint-Out) Mappings ---"
python3 GetTITO.py "$PROJECT_PATH"

echo "--- Cleaning Up JSONs ---"
python3 FilterPysaJSONs.py "$PROJECT_PATH/pyre-output"

cd "$ROOT_DIR"

echo ""
echo "Pipeline complete!"
echo "Main result: Results/$(basename "$PROJECT_PATH").xlsx"
echo "Filtered result: Results/Filtered/$(basename "$PROJECT_PATH").xlsx"
echo "TITO result: Results/Filtered/$(basename "$PROJECT_PATH")_TITO.xlsx"
