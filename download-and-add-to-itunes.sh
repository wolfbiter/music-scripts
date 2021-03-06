#!/bin/bash

# exit when any command fails
set -e

cd "$(dirname "$0")"
TIME_STAMP="$(date +%s%3N)"

# parse args
: ${1?' You forgot to supply a YOUTUBE_URL'}
: ${2?' You forgot to supply a PLAYLIST_NAME'}
YOUTUBE_URL=$1
PLAYLIST_NAME=$2
WORKING_DIR=${3:-"export/$TIME_STAMP"}

printf "STARTING SCRIPT: $(basename "$0") || CURRENT TIME: %s\n" "$(date)"
echo "YOUTUBE_URL: $YOUTUBE_URL"
echo "PLAYLIST_NAME: $PLAYLIST_NAME"

# create working directory
mkdir -p $WORKING_DIR

# download from youtube
cd $WORKING_DIR
if youtube-dl -x -i --audio-format mp3 -f bestaudio "$YOUTUBE_URL"
then
  printf "\nSUCCESSFULLY DOWNLOADED ALL TRACKS\n\n"
else
  printf "\nERROR DOWNLOADING SOME TRACK(S)\n\n"
fi
cd "../../"

# analyze tracks with keyfinder
for file in "$WORKING_DIR"/*
do
  if /Applications/KeyFinder.app/Contents/MacOS/KeyFinder -f "$file" -w
  then
    echo "  -  Analyzed track: $file"
  else
    printf "\n\nERROR ANALYZING TRACK: $(file)\n\n"
  fi
done

echo "DONE ANALYZING"

# add tracks to itunes
echo "$(find `pwd` -name $TIME_STAMP)"
./create-itunes-playlist.scpt "$(find `pwd` -name $TIME_STAMP)" "$PLAYLIST_NAME"

echo "ADDED ITUNES PLAYLIST $PLAYLIST_NAME"

# clear working directory
if [ -d "$WORKING_DIR" ]; then rm -rf $WORKING_DIR; fi

echo "CLEARED WORKING DIRECTORY: $WORKING_DIR"
