#!/bin/sh
# Build the entry and bundle the agent transcripts.
set -e
node cli/makefun.mjs bundle
python3 main.py
ls -l /output/entry.png