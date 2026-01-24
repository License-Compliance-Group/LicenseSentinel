#!/bin/bash

# Check if coverage is at least 90%
# Returns 0 if coverage >= 90%, 1 otherwise
# Outputs coverage percentage to console

percentage=$(coverage report | tail -1 | awk '{print $4}' | sed 's/%//')
echo "${percentage}%"

if (( percentage >= 90 )); then
    exit 0
else
    exit 1
fi
