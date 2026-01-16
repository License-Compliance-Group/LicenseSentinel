#!/bin/bash
# Custom merge driver that keeps the "theirs" version (incoming changes)
# Usage: git config merge.keep-theirs.driver "src/scripts/git-merge-keep-theirs.sh %O %A %B"

BASE="$1"
OURS="$2"
THEIRS="$3"

# For XML reports, simply take the theirs version
cp "$THEIRS" "$OURS"
exit 0
