#!/usr/bin/env bash

# Script to remove additionalProperties key from JSON objects that have
# x-kubernetes-preserve-unknown-fields set to true.
#
# Usage: ./remove-additional-properties.sh <file1.json> [file2.json ...]
#
# Example:
#   ./remove-additional-properties.sh file.json
#   ./remove-additional-properties.sh *.json
#   ./remove-additional-properties.sh $(find . -name "*.json")

set -e

# Check if jq is installed
if ! command -v jq &>/dev/null; then
    echo "Error: jq is not installed. Please install jq to use this script." >&2
    exit 1
fi

# Check if at least one file argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <file1.json> [file2.json ...]" >&2
    echo "" >&2
    echo "This script removes the 'additionalProperties' key from JSON objects" >&2
    echo "that have 'x-kubernetes-preserve-unknown-fields' set to true." >&2
    exit 1
fi

# Process each file
for file in "$@"; do
    if [ ! -f "$file" ]; then
        echo "Warning: File not found: $file" >&2
        continue
    fi

    # Apply jq transformation and overwrite the file
    jq -a 'walk(if type == "object" and .["x-kubernetes-preserve-unknown-fields"] == true and has("additionalProperties") then del(.additionalProperties) else . end)' "$file" >"$file.tmp"

    # Replace original file with transformed version
    mv "$file.tmp" "$file"

    echo "Processed: $file"
done

echo "Done."
