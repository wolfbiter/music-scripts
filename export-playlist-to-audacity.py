import argparse
import subprocess
import math

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
  for i, transition in enumerate(transitions):
    print('add_transition_to_audacity', transition)

    # only load x for first transition
    if i == 0:
      audacity.load_track(transition['x'], start=0, end=transition['offset'], track=i)

    # get y_end from next transition's offset
    y_end = 100
    if i != len(transitions) - 1:
      next_transition = transitions[i + 1]
      y_end = next_transition['offset']

    # load y
    audacity.load_track(transition['y'], start=transition['offset'], end=y_end, track=i)

  audacity.close_pipes()


def sync_pair(x, y):
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
    input=f'panako sync SYNC_MIN_ALIGNED_MATCHES=1 "{xPath}" "{yPath}"')
  if stderr:
    raise Exception(stderr)

  # parse offset from stdout
  if stdout.find('No alignment found') != -1:
    print('NO ALIGNMENT FOUND')
    return 0
  else:
    start_string = 'with an offset of '
    start_index = stdout.find(start_string) + len(start_string)
    end_string = 's ('
    end_index = stdout.find(end_string, start_index)
    offset = stdout[start_index:end_index]
    print(f'offset: {offset}')
    return float(offset)


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
    transitions.append({ 'x': x, 'y': y, 'offset': math.inf })

  # sync transition pairs in panako
  transitions = transitions[:1]
  for transition in transitions:
    transition['offset'] = sync_pair(transition['x'], transition['y'])

  # add synced transitions to audacity project
  add_transitions_to_audacity(transitions)


if __name__ == '__main__':
  main()
