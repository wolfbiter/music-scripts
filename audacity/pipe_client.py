#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

TOFILE = None
FROMFILE = None
EOL = None

def load_track(filename, start=0, end=None, track=None):
  assert track != None
  assert end != None
  do( f'Import2: Filename="{filename}"' )

  # reset cursor to start of track
  trackString = f'Track={track}'
  do( f'Select: Start=0 End=0 {trackString}')

  # trim track to start / end
  startString = f'Start={start}' if start != None else ''
  endString = f'End={end}'
  do( f'Select: {startString} {endString} {trackString}')
  do( 'Trim' )
  
  do( 'FitInWindow' )


def align_tracks_end_to_end(track_count):
  do( f'SelectTracks: TrackCount={track_count}')
  do( 'Align_EndToEnd' )

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
