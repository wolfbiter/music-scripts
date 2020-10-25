import argparse
import subprocess
import os
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('playlist_path', metavar='playlist_path', type=str, help="path to playlist folder to convert, .nml file in a flat folder with audio files")
flags = ap.parse_args()

PLAYLIST_PATH = '/Users/kane/Desktop/panako-input' or flags.playlist_path
DOCKER_AUDIO_PATH = '/home/audioinput'
DOCKER_WORKING_DIRECTORY = '/Users/kane/projects/docker-panako'
DOCKER_COMMAND = f'docker run -i --volume {PLAYLIST_PATH}:{DOCKER_AUDIO_PATH} --rm panako bash'

print(f'PYTHON EXPORT PLAYLIST_PATH: {PLAYLIST_PATH}')


# start docker command
process = subprocess.Popen([DOCKER_COMMAND], 
  stdin=subprocess.PIPE,
  stdout=subprocess.PIPE,
  stderr=subprocess.PIPE,
  universal_newlines=True,
  bufsize=0,
  shell=True,
  cwd=DOCKER_WORKING_DIRECTORY)


# get input file paths
process.stdin.write(f'ls {DOCKER_AUDIO_PATH}')
process.stdin.close()
file_paths = [f'{DOCKER_AUDIO_PATH}/{line.strip()}'
  for line in process.stdout.readlines()]


# find .nml file
nml_files = [path for path in file_paths if Path(path).suffix == '.nml']
if len(nml_files):
  nml_file = nml_files[0]
  print(f'Found NML file: {nml_file}')
else:
  raise Error(f'.nml file not found in: {DOCKER_AUDIO_PATH}')

