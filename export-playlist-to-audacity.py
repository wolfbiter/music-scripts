import argparse
import subprocess

from os import listdir
from os.path import isfile, join, basename
from pathlib import Path

import audacity.pipe_client as audacity

ap = argparse.ArgumentParser()
ap.add_argument('playlist_path', metavar='playlist_path', type=str, help="path to playlist folder to convert, .m3u file in a flat folder with audio files")
flags = ap.parse_args()

PLAYLIST_PATH = '/Users/kane/Desktop/panako-input' or flags.playlist_path
DOCKER_AUDIO_PATH = '/home/audioinput'
DOCKER_WORKING_DIRECTORY = '/Users/kane/projects/docker-panako'
DOCKER_COMMAND = f'docker run -i --volume {PLAYLIST_PATH}:{DOCKER_AUDIO_PATH} --rm panako bash'

def add_transitions_to_audacity(transitions):
  track = 0
  for i, transition in enumerate(transitions):
    tracks_created = 0
    x_offset = transition['x_offset']
    y_offset = transition['y_offset']
    print('\nadd_transition:')
    print(f'x: {basename(transition["x"])}')
    print(f'y: {basename(transition["y"])}')
    print(f'x_offset: {x_offset}')
    print(f'y_offset: {y_offset}')

    # only load x for first transition
    if i == 0:
      audacity.load_track(
        transition['x'],
        end=x_offset,
        track=track
      )
      track += 1
      tracks_created += 1

    # get y_end from next transition's offset
    if i != len(transitions) - 1:
      next_transition = transitions[i + 1]
      y_end = next_transition['x_offset']
    y_end = 1000 if y_end == None else y_end

    # load y
    y_start = transition['y_offset'] or 0
    if y_end <= y_start:
      print('error with y_start and y_end: ', y_start, y_end)
      audacity.load_track(
        transition['y'],
        start=y_start,
        end=1000,
        track=track
      )
      track += 1
      tracks_created += 1
      audacity.load_track(
        transition['y'],
        end=y_end,
        track=track
      )
      track += 1
      tracks_created += 1
    else:
      audacity.load_track(
        transition['y'],
        start=y_start,
        end=y_end,
        track=track
      )
      track += 1
      tracks_created += 1

    # line up new tracks
    audacity.align_tracks_end_to_end(
      track=max(track - tracks_created - 1, 0),
      track_count=tracks_created + 1
    )

    # confirm correct before proceeding
    audacity.zoom_to_transition(track - 1)
    user_input = input('Press enter to proceed when ready…')

  audacity.close_pipes()


def main():
  # TODO: ensure audacity is running first?
  print(f'PYTHON EXPORT PLAYLIST_PATH: {PLAYLIST_PATH}')

  # find .m3u
  try:
    m3u_file = [f for f in listdir(PLAYLIST_PATH) if Path(f).suffix == '.m3u'][0]
    print(f'Found m3u file: {m3u_file}')
  except:
    raise Exception('{DOCKER_AUDIO_PATH} should contain a .m3u file')

  # parse audio files from .m3u
  m3u_path = join(PLAYLIST_PATH, m3u_file)
  m3u_lines = open(m3u_path, 'r').read().split('\n')
  audio_files = [join(PLAYLIST_PATH, basename(f)) for f in m3u_lines if f]

  # collect audio files into transition pairs
  transitions = []
  for i in range(len(audio_files) - 1):
    x = audio_files[i]
    y = audio_files[i + 1]
    transitions.append({ 'x': x, 'y': y })

  # sync transition pairs in panako
  # transitions = transitions[:10]
  for transition in transitions:
    x_offset, y_offset = sync_pair(transition['x'], transition['y'])
    transition['x_offset'] = x_offset
    transition['y_offset'] = y_offset

  # add synced transitions to audacity project
  add_transitions_to_audacity(transitions)

def sync_pair(x, y, SYNC_MIN_ALIGNED_MATCHES=2):
  print('\nSyncing pair: ')
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


if __name__ == '__main__':
  main()

