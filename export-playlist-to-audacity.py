import argparse
import subprocess

ap = argparse.ArgumentParser()
ap.add_argument('playlist_file_path', metavar='playlist_file_path', type=str, help=".nml path to playlist file to convert, in a flat folder with audio files")
flags = ap.parse_args()

print(f'PYTHON {flags.playlist_file_path}')
