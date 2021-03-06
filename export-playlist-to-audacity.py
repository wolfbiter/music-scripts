import argparse
import subprocess

from os import listdir
from os.path import isfile, join, basename
from pathlib import Path
from datetime import datetime
import concurrent.futures

import untangle
import librosa
import pyrubberband
import soundfile

import audacity.pipe_client as audacity

ap = argparse.ArgumentParser()
ap.add_argument('playlist_path', metavar='playlist_path', type=str, help="path to playlist folder to convert, .m3u file in a flat folder with audio files")
flags = ap.parse_args()

PLAYLIST_PATH = '/Users/kane/Desktop/panako-input' or flags.playlist_path
DOCKER_AUDIO_PATH = '/home/audioinput'
DOCKER_WORKING_DIRECTORY = '/Users/kane/projects/docker-panako'
DOCKER_COMMAND = f'docker run -i --volume {PLAYLIST_PATH}:{DOCKER_AUDIO_PATH} --rm panako bash'

TRANSITION_START_INDEX = 0
TRANSITION_END_INDEX = None # None for last element in array

def add_transitions_to_audacity(transitions):

  # start by zooming to last transition if any
  audacity.zoom_to_transition(len(audacity.get_tracks_info()) - 1)

  i = 0
  while i < len(transitions):
    transition = transitions[i]
    x_offset = transition['x_offset']
    y_offset = transition['y_offset']
    offset = transition['offset'] or 0

    y_start = y_offset or 0
    if i != len(transitions) - 1:
      next_transition = transitions[i + 1]
      y_end = next_transition['x_offset']
    else:
      y_end = None

    print(f'\nTransition {i + 1 + TRANSITION_START_INDEX}/{len(transitions) + TRANSITION_START_INDEX}')
    print(f'x: {basename(transition["x"]["absolute_path"])}')
    print(f'y: {basename(transition["y"]["absolute_path"])}')
    print(f'x_offset: {x_offset}')
    print(f'y_offset: {y_offset}')
    print(f'offset: {offset}')
    print(f'y_start: {y_start}')
    print(f'y_end: {y_end}')
    if (y_end != None) and (y_start >= y_end):
      print('WARNING y_start >= y_end')
      y_end = None

    # prompt user if they want to add this transition
    should_add_transition = None
    while should_add_transition == None:
      user_input = input('Would you like to add this transition, or go back? (y/n/b): ').lower().strip()
      if user_input == 'y':
        should_add_transition = True
        print('ADDING TRANSITION')
      elif user_input == 'n':
        should_add_transition = False
        print('NOT ADDING TRANSITION')
      elif user_input == 'b':
        should_add_transition = False
        i -= (1 if i == 0 else 2)
        print(f'GOING BACK')

    # proceed to next iteration if we are not adding tracks
    if not should_add_transition:
      i += 1
      continue

    # refresh info in case user modified during input step
    tracks_info = audacity.get_tracks_info()
    next_track = len(tracks_info)

    # only load x for first transition
    if next_track == 0:
      # create duplicate with overlap for clarity
      # audacity.load_track(
      #   transition['x'],
      #   track=next_track
      # )
      # audacity.mute_track(track=next_track)
      # next_track += 1

      audacity.load_track(
        transition['x'],
        track=next_track
      )
      audacity.trim_track(
        end=x_offset,
        track=next_track
      )
      next_track += 1

    # load y, line up transition and trim
    audacity.load_track(
      transition['y'],
      track=next_track
    )
    audacity.trim_track(
      start=y_start,
      end=y_end,
      track=next_track
    )
    audacity.align_tracks_end_to_end(
      track=next_track - 1,
      track_count=2
    )
    next_track += 1

    # create duplicate with overlap for clarity
    if y_offset != None:
      prev_track_info = audacity.get_tracks_info()[next_track - 1]
      audacity.load_track(
        transition['y'],
        track=next_track
      )
      audacity.trim_track(
        start=0,
        end=y_end,
        track=next_track
      )
      audacity.move_clip(
        at=0,
        start=prev_track_info['start'] - y_offset,
        track=next_track
      )
      audacity.mute_track(track=next_track)
      next_track += 1

      # focus newly made transition
      audacity.zoom_to_transition(next_track - 2)
    else:
      audacity.zoom_to_transition(next_track - 1)

    i += 1

  audacity.close_pipes()


def review_transitions():
  num_transitions = len(audacity.get_tracks_info()) - 1

  i = 1
  while i < num_transitions:
    audacity.zoom_to_transition(i)
    print(f'\nTransition {i}/{num_transitions}')

    # prompt user to move forward or backward
    valid_input = None
    while valid_input == None:
      user_input = input('Would you to go forward or back? (y/b): ').lower().strip()
      if user_input == 'y':
        valid_input = True
      elif user_input == 'b':
        valid_input = True
        i -= (1 if i == 0 else 2)
        print(f'GOING BACK')


def main():
  print(f'PYTHON EXPORT PLAYLIST_PATH: {PLAYLIST_PATH}')

  # parse audio objects from playlist
  audio_objects = parse_playlist(PLAYLIST_PATH)
  print(f'PARSED {len(audio_objects)} AUDIO OBJECTS FROM PLAYLIST')

  # collect audio_objects into transition pairs
  transitions = []
  for i in range(len(audio_objects) - 1):
    x = audio_objects[i]
    y = audio_objects[i + 1]
    transitions.append({ 'x': x, 'y': y })

  # sync transition pairs in panako
  print(f'ALIGNING TRANSITIONS\n')
  transitions = transitions[TRANSITION_START_INDEX:TRANSITION_END_INDEX]
  print('_set_transition_offset', len(transitions))
  with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(lambda t: _set_transition_offset(transitions, t), transitions)

  # add synced transitions to audacity project
  print(f'ADDING TRANSITIONS TO AUDACITY FROM {TRANSITION_START_INDEX} to {TRANSITION_END_INDEX}')
  print('If nothing happens, check to make sure Docker is running and Audacity is open and running')
  add_transitions_to_audacity(transitions)


def _set_transition_offset(transitions, transition):
  i = transitions.index(transition)
  xPath = transition['x']['end_bpm_shifted_path']
  yPath = transition['y']['start_bpm_shifted_path']
  print('_set_transition_offset', xPath, yPath)
  x_offset, y_offset, offset = sync_pair(xPath, yPath)
  transition['x_offset'] = x_offset
  transition['y_offset'] = y_offset
  transition['offset'] = offset

  print(f'Synced pair {i + 1 + TRANSITION_START_INDEX}/{len(transitions) + TRANSITION_START_INDEX}: ')
  print(basename(xPath))
  print(basename(yPath))
  print(f'x_offset: {x_offset}')
  print(f'y_offset: {y_offset}')
  print(f'offset: {offset}')
  print()


def sync_pair(x, y, SYNC_MIN_ALIGNED_MATCHES=2):

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
    print(f'ERROR RUNNING DOCKER_COMMAND: "{stderr}"')
    return None, None, None

  if stdout.find('No alignment found') != -1:
    return None, None, None

  print(stdout)

  # parse x_offset
  start_string = f'{basename(x)} ['
  start_index = stdout.find(start_string) + len(start_string)
  end_string = 's - '
  end_index = stdout.find(end_string, start_index)
  x_offset = stdout[start_index:end_index]

  # parse y_offset
  start_string = f'{basename(y)} ['
  start_index = stdout.find(start_string) + len(start_string)
  end_string = 's - '
  end_index = stdout.find(end_string, start_index)
  y_offset = stdout[start_index:end_index]

  # parse offset
  start_string = 'with an offset of '
  start_index = stdout.find(start_string) + len(start_string)
  end_string = 's ('
  end_index = stdout.find(end_string, start_index)
  offset = stdout[start_index:end_index]

  return float(x_offset), float(y_offset), float(offset)


def parse_playlist(playlist):
  try:
    nml_file = [f for f in listdir(PLAYLIST_PATH) if Path(f).suffix == '.nml'][0]
    print(f'Found nml file: {nml_file}')
  except:
    raise Exception('{DOCKER_AUDIO_PATH} should contain a .nml file')

  # parse audio objects from .nml
  nml_path = join(PLAYLIST_PATH, nml_file)
  nml_dict = untangle.parse(nml_path)
  entries = nml_dict.NML.COLLECTION.ENTRY
  audio_objects = [{
    'file': e.LOCATION['FILE'],
    'absolute_path': join(PLAYLIST_PATH, e.LOCATION['FILE']),
    'auto_gain': e.LOUDNESS['PERCEIVED_DB'],
    'bpm': float(e.TEMPO['BPM']),
    'pitch_semitones': _get_pitch_semitones(e),
    'is_recorded_mix': _is_recorded_mix(e)
  } for e in entries]

  # determine reference bpms
  for i in range(len(audio_objects)):
    audio_object = audio_objects[i]
    bpm = audio_object['bpm']

    if i == 0:
      audio_object['start_bpm'] = bpm
    else:
      prev_bpm = audio_objects[i - 1]['bpm']
      audio_object['start_bpm'] = (bpm + prev_bpm) / 2.0

    if i == len(audio_objects) - 1:
      audio_object['end_bpm'] = bpm
    else:
      next_bpm = audio_objects[i + 1]['bpm']
      audio_object['end_bpm'] = (bpm + next_bpm) / 2.0

  print()
  print('audio object BPMs')
  print([a['start_bpm'] for a in audio_objects])


  # pitch-shift audio files as needed
  with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(_set_pitch_shifted_path, audio_objects)

  # tempo-shift audio files as needed
  with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    tempo_shifts = [(obj, 'start_bpm') for obj in audio_objects] + [(obj, 'end_bpm') for obj in audio_objects]
    executor.map(_set_tempo_shifted_path, tempo_shifts)

  return audio_objects


def _set_pitch_shifted_path(audio_object):
  pitch_semitones = audio_object['pitch_semitones']
  file = audio_object['file']
  pitch_shifted_path = audio_object['absolute_path']

  # pitch shift audio as needed
  if pitch_semitones:
    shifted_file = f'PITCH SHIFTED {pitch_semitones}: {Path(file).stem}.wav'
    pitch_shifted_path = join(PLAYLIST_PATH, shifted_file)

    # create new pitch shifted file if not exists
    if not Path(pitch_shifted_path).is_file():
      y, sr = librosa.load(audio_object['absolute_path'])
      print(f'shifting file by {pitch_semitones}: "{file}"')
      y_shift = pyrubberband.pitch_shift(y, sr, pitch_semitones)
      soundfile.write(pitch_shifted_path, y_shift, sr)
    else:
      print(f'CACHED SHIFT: "{shifted_file}"')

  audio_object['pitch_shifted_path'] = pitch_shifted_path


def _set_tempo_shifted_path(info):
  (audio_object, path) = info
  base_bpm = audio_object['bpm']
  target_bpm = audio_object[path]
  file = audio_object['file']
  audio_path = audio_object['pitch_shifted_path']
  tempo_shifted_path = audio_path
  target_rate = target_bpm / base_bpm

  # tempo shift audio as needed
  # TODO: fix this: currently broken because
  # the tempo-shifted version sounds awful
  if False and target_rate != 1:
    shifted_file = f'BPM SHIFTED {target_rate}: {Path(file).stem}.wav'
    tempo_shifted_path = join(PLAYLIST_PATH, shifted_file)

    # create new tempo shifted file if not exists
    if not Path(tempo_shifted_path).is_file():
      y, sr = librosa.load(audio_path)
      print(f'shifting file from {base_bpm}bpm to {target_bpm}bpm: "{file}"')
      y_shift = librosa.effects.time_stretch(y, 1 / target_rate)
      soundfile.write(tempo_shifted_path, y_shift, sr)
    else:
      print(f'CACHED SHIFT: "{shifted_file}"')

  audio_object[f'{path}_shifted_path'] = tempo_shifted_path


def _get_pitch_semitones(entry):
  # 'rating' is weirdly 'comment2' in traktor
  # if rating is an integer, interpret as pitch shift
  try:
    rating = entry.INFO['RATING']
    return int(rating)
  except:
    return 0

def _is_recorded_mix(entry):
  # if title is in this date format, it's probably a traktor recording
  try:
    datetime.strptime(entry['TITLE'], '%Y-%m-%d_%Hh%Mm%S')
    return True
  except Exception as e:
    return False


if __name__ == '__main__':
  main()
