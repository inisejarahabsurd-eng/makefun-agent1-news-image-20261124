#!/bin/sh
# Bundle the agent transcripts once sessions are final, from inside the kit:
#   node cli/makefun.mjs bundle
# Then submit repo_url, commit_sha and the bundle.
set -e
python3 main.py
ls -l /output/entry.png