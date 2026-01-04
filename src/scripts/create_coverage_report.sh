#!/bin/bash

# This is intended to run as a GitHub action, hence Bash
# If you're on Windows, your default Git installation should come with Bash

# Parse command line arguments
omit=""
if [ "$1" = "--no-cover-tests" ]; then
    omit="--omit=test/*"
fi

cwd=$(pwd)
echo "Working in folder $cwd"

branch=$(git branch --show-current)
echo "Working on branch $branch"

echo "Executing tests..."
coverage run $omit -m pytest
echo "Generating coverage report..."
if [ ! -d "test/reports" ]; then
    echo "Target directory does not exist, is the project root correct?"
    exit 1
fi

coverage xml -o test/reports/coverage.xml

if [ ! -e "test/reports/coverage.xml" ]; then
    echo "Failed to create report file!"
    exit 2
fi

exit 0
