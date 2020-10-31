#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json

TOFILE = None
FROMFILE = None
EOL = None

def load_track(audio_object, track=None):
  filename = audio_object['absolute_path']
  do( f'SelectTracks: Track={track} TrackCount=1')
  do( f'Import2: Filename="{filename}"' )

  # set auto gain for original files (dont adjust post-mix files)
  if not audio_object['is_recorded_mix']:
    do( f'SelectTracks: Track={track}')
    do( f'SetTrackAudio: Gain={audio_object["auto_gain"]}' )


def trim_track(start=0, end=999999, track=None):
  if end == None:
    end = 999999
  if start != None and end != None and track != None:
    do( f'Select: Start={start} End={end} Track={track}')
    do( 'Trim' )


def move_clip(at=0, start=0, track=None):
  if track != None:
    do( f'SetClip: At={at} Track={track} Start={start}' )


def align_tracks_end_to_end(track=0, track_count=0):
  do( f'SelectTracks: Track={track} TrackCount={track_count}')
  do( 'Align_EndToEnd' )


def delete_track(track):
  if track != None:
    do( f'SelectTracks: Track={track} TrackCount=1')
    do( f'RemoveTracks:' )


def mute_track(track):
  if track != None:
    do( f'SelectTracks: Track={track} TrackCount=1')
    do( f'MuteTracks:' )


def zoom_to_transition(track = 0):
  track = max(track, 0)
  do( f'Select: Track={track}' )

  # jump to 30s before start of track
  do( 'CursTrackStart' )
  do( 'SelectNone' )
  do( 'CursorLongJumpLeft' )
  do( 'CursorLongJumpLeft' )

  # then select to end of track, and zoom
  do( f'Select: Track={track}' )
  do( 'SelCursorToTrackEnd' )
  do( 'ZoomSel' )


def get_tracks_info():
  tracks_info_string = do( 'GetInfo: Type=Tracks' ) or ''
  end_index = tracks_info_string.find('BatchCommand finished:')
  return json.loads(tracks_info_string[0:end_index])


def send_command(command):
  """Send a single command."""
  TOFILE.write(command + EOL)
  TOFILE.flush()

def get_response():
  """Return the command response."""
  result = ''
  line = ''
  while True:
    result += line
    line = FROMFILE.readline()
    if line == '\n' and len(result) > 0:
      break
  return result

def do_command(command):
  """Send one command, and return the response."""
  assert_pipes()
  # print("Send: >>> \n" + command)
  send_command(command)
  response = get_response()
  # print("Rcvd: <<< \n" + response)
  return response

def do(command):
  return do_command(command)

def assert_pipes():
  if not (TOFILE and FROMFILE):
    get_pipes()

def get_pipes():
  global TOFILE
  global FROMFILE
  global EOL
  if sys.platform == 'win32':
      TONAME = '\\\\.\\pipe\\ToSrvPipe'
      FROMNAME = '\\\\.\\pipe\\FromSrvPipe'
      EOL = '\r\n\0'
  else:
      TONAME = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
      FROMNAME = '/tmp/audacity_script_pipe.from.' + str(os.getuid())
      EOL = '\n'

  TOFILE = open(TONAME, 'w')
  FROMFILE = open(FROMNAME, 'rt')


def close_pipes():
  global TOFILE
  global FROMFILE

  if TOFILE:
    TOFILE.close()
    TOFILE = None

  if FROMFILE:
    FROMFILE.close()
    FROMFILE = None
