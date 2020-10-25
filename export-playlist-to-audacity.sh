#!/bin/bash

# exit when any command fails
set -e

printf "STARTING SCRIPT: $(basename "$0") || CURRENT TIME: %s\n" "$(date)"

# activate our virtualenv if we aren't in it
cd "$(dirname "$0")"
source ./venv/bin/activate

# parse optional arg
PLAYLIST_FILE_PATH=$1

# import the csv file to json
python ./export-playlist-to-audacity.py "$PLAYLIST_FILE_PATH"
