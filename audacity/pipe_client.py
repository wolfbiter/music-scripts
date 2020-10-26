#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

TOFILE = None
FROMFILE = None
EOL = None

def load_track(filename, start=0, end=None, track=None):
  do( f'Import2: Filename="{filename}"' )

  # optionally trim track to start / end
  if start != None and end != None and track != None:
    do( f'Select: Start={start} End={end} Track={track}')
    do( 'Trim' )
    do( 'FitInWindow' )


def align_tracks_end_to_end(track=0, track_count=0):
  do( f'SelectTracks: Track={track} TrackCount={track_count}')
  do( 'Align_EndToEnd' )


def zoom_to_transition(track):
  do( 'ZoomNormal' )
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


def send_command(command):
  """Send a single command."""
  global TOFILE
  global EOL
  TOFILE.write(command + EOL)
  TOFILE.flush()

def get_response():
  """Return the command response."""
  global FROMFILE
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
  # print("Send: >>> \n"+command)
  send_command(command)
  response = get_response()
  # print("Rcvd: <<< \n" + response)
  return response

def do(command):
  do_command(command)

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
