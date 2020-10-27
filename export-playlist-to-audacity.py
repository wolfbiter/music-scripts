import argparse
import subprocess

from os import listdir
from os.path import isfile, join, basename
from pathlib import Path
from datetime import datetime

import untangle

import audacity.pipe_client as audacity

ap = argparse.ArgumentParser()
ap.add_argument('playlist_path', metavar='playlist_path', type=str, help="path to playlist folder to convert, .m3u file in a flat folder with audio files")
flags = ap.parse_args()

PLAYLIST_PATH = '/Users/kane/Desktop/panako-input' or flags.playlist_path
DOCKER_AUDIO_PATH = '/home/audioinput'
DOCKER_WORKING_DIRECTORY = '/Users/kane/projects/docker-panako'
DOCKER_COMMAND = f'docker run -i --volume {PLAYLIST_PATH}:{DOCKER_AUDIO_PATH} --rm panako bash'

TRANSITION_START_INDEX = 1 - 1 # subtract 1 for 0 index
TRANSITION_END_INDEX = None # None for last element in array

def add_transitions_to_audacity(transitions):
  for i, transition in enumerate(transitions):
    x_offset = transition['x_offset']
    y_offset = transition['y_offset']

    print(f'\nTransition {i + 1 + TRANSITION_START_INDEX}/{len(transitions) + TRANSITION_START_INDEX}')
    print(f'x: {basename(transition["x"]["absolute_path"])}')
    print(f'y: {basename(transition["y"]["absolute_path"])}')
    print(f'x_offset: {x_offset}')
    print(f'y_offset: {y_offset}')

    # compute y_start and y_end
    y_start = y_offset or 0
    if i != len(transitions) - 1:
      next_transition = transitions[i + 1]
      y_end = next_transition['x_offset']
    y_end = 1000 if y_end == None else y_end
    if y_start >= y_end:
      print('WARNING y_start >= y_end')
      print(f'y_start: {y_start}')
      print(f'y_end: {y_end}')

    # prompt user if they want to add this transition
    tracks_info = audacity.get_tracks_info()
    next_track = len(tracks_info)
    audacity.zoom_to_transition(next_track - 1)
    should_add_transition = None
    while should_add_transition == None:
      user_input = input('Would you like to add this transition? (y/n): ').lower().strip()
      if user_input == 'y':
        should_add_transition = True
      elif user_input == 'n':
        should_add_transition = False
    tracks_info = audacity.get_tracks_info()
    next_track = len(tracks_info)
    audacity.zoom_to_transition(next_track - 1)

    # proceed to next iteration if we are not adding tracks
    if not should_add_transition:
      print('NOT ADDING TRANSITION')
      continue
    else:
      print('ADDING TRANSITION')

    # only load x for first transition
    if i == 0 and TRANSITION_START_INDEX == 0:
      audacity.load_track(
        transition['x'],
        end=x_offset,
        track=next_track
      )
      next_track += 1

    # load y. if overlap issue, load two copies of y
    if y_end <= y_start:
      audacity.load_track(
        transition['y'],
        start=y_start,
        end=1000,
        track=next_track
      )
      next_track += 1
      audacity.load_track(
        transition['y'],
        end=y_end,
        track=next_track
      )
      next_track += 1
    else:
      audacity.load_track(
        transition['y'],
        start=y_start,
        end=y_end,
        track=next_track
      )
      next_track += 1

    # line up new tracks
    new_tracks_info = audacity.get_tracks_info()
    tracks_created = len(new_tracks_info) - len(tracks_info)
    audacity.align_tracks_end_to_end(
      track=max(next_track - tracks_created - 1, 0),
      track_count=tracks_created + 1
    )

    # if last transition, focus
    if i == len(transitions) - 1:
      audacity.zoom_to_transition(next_track - 1)


  audacity.close_pipes()


def main():
  print(f'PYTHON EXPORT PLAYLIST_PATH: {PLAYLIST_PATH}')

  # find .nml
  try:
    nml_file = [f for f in listdir(PLAYLIST_PATH) if Path(f).suffix == '.nml'][0]
    print(f'Found nml file: {nml_file}')
  except:
    raise Exception('{DOCKER_AUDIO_PATH} should contain a .nml file')

  # parse audio files from .nml
  nml_path = join(PLAYLIST_PATH, nml_file)
  nml_dict = untangle.parse(nml_path)
  entries = nml_dict.NML.COLLECTION.ENTRY
  audio_objects = [{
    'absolute_path': join(PLAYLIST_PATH, e.LOCATION['FILE']),
    'auto_gain': e.LOUDNESS['PERCEIVED_DB'],
    'is_recorded_mix': _is_recorded_mix(e)
  } for e in entries]

  # collect audio_objects into transition pairs
  transitions = []
  for i in range(len(audio_objects) - 1):
    x = audio_objects[i]
    y = audio_objects[i + 1]
    transitions.append({ 'x': x, 'y': y })

  # sync transition pairs in panako
  transitions = transitions[TRANSITION_START_INDEX:TRANSITION_END_INDEX]
  for i, transition in enumerate(transitions):
    print(f'\n{i + 1 + TRANSITION_START_INDEX}/{len(transitions) + TRANSITION_START_INDEX}')
    x_offset, y_offset = sync_pair(
      transition['x']['absolute_path'],
      transition['y']['absolute_path']
    )
    transition['x_offset'] = x_offset
    transition['y_offset'] = y_offset

  # add synced transitions to audacity project
  add_transitions_to_audacity(transitions)

def sync_pair(x, y, SYNC_MIN_ALIGNED_MATCHES=2):
  print('Syncing pair: ')
  print(basename(x))
  print(basename(y))

  # start docker panako
  process = subprocess.Popen([DOCKER_COMMAND], 
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    universal_newlines=True,
    bufsize=0,
    shell=True,
    cwd=DOCKER_WORKING_DIRECTORY)

  # run sync command
  xPath = join(DOCKER_AUDIO_PATH, basename(x))
  yPath = join(DOCKER_AUDIO_PATH, basename(y))
  stdout, stderr = process.communicate(
    input=f'panako sync SYNC_MIN_ALIGNED_MATCHES={SYNC_MIN_ALIGNED_MATCHES} "{xPath}" "{yPath}"')
  if stderr:
    raise Exception(stderr)

  if stdout.find('No alignment found') != -1:
    print('NO ALIGNMENT FOUND')
    return None, None

  print(stdout)

  # parse x_offset
  start_string = f'{basename(x)} ['
  start_index = stdout.find(start_string) + len(start_string)
  end_string = 's - '
  end_index = stdout.find(end_string, start_index)
  x_offset = stdout[start_index:end_index]
  print(f'x_offset: {x_offset}')

  # parse y_offset
  start_string = f'{basename(y)} ['
  start_index = stdout.find(start_string) + len(start_string)
  end_string = 's - '
  end_index = stdout.find(end_string, start_index)
  y_offset = stdout[start_index:end_index]
  print(f'y_offset: {y_offset}')

  # parse offset
  start_string = 'with an offset of '
  start_index = stdout.find(start_string) + len(start_string)
  end_string = 's ('
  end_index = stdout.find(end_string, start_index)
  offset = stdout[start_index:end_index]
  print(f'offset: {offset}')

  return float(x_offset), float(y_offset)


def _is_recorded_mix(entry):
  # if title is in this date format, it's probably a traktor recording
  try:
    datetime.strptime(entry['TITLE'], '%Y-%m-%d_%Hh%Mm%S')
    return True
  except Exception as e:
    return False


if __name__ == '__main__':
  main()
