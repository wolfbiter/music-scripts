#!/bin/bash

# exit when any command fails
set -e

cd "$(dirname "$0")"

# parse args
: ${1?' You forgot to supply a YOUTUBE_URL'}
: ${2?' You forgot to supply a PLAYLIST_NAME'}
YOUTUBE_URL=$1
PLAYLIST_NAME=$2
WORKING_DIR=${3:-'export'}

printf "STARTING SCRIPT: $(basename "$0") || CURRENT TIME: %s\n" "$(date)"
echo "YOUTUBE_URL: $YOUTUBE_URL"
echo "PLAYLIST_NAME: $PLAYLIST_NAME"

# reset working directory
if [ -d "$WORKING_DIR" ]; then rm -Rf $WORKING_DIR; fi
mkdir $WORKING_DIR

# download from youtube
cd $WORKING_DIR
youtube-dl -x -i --audio-format mp3 -f bestaudio "$YOUTUBE_URL"
cd "../"

# analyze tracks with keyfinder
for file in "$WORKING_DIR"/*
do
  echo "Analyzing track: $file"
  /Applications/KeyFinder.app/Contents/MacOS/KeyFinder -f "$file" -w
done

echo "DONE ANALYZING"

# add tracks to itunes
./create-itunes-playlist.scpt "$(find `pwd` -name $WORKING_DIR)" "$PLAYLIST_NAME"
