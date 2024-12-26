import json
import subprocess
import re
import os
import ffmpeg
from utils import logprint, get_timestamp_template

def parse_chapters(filename: str, anidb_id: str, episode_number: float) -> dict:
  chapters = get_chapters(filename)
  if len(chapters) == 0:
    return
  logprint(f"[chapters.py] [INFO] Found chapter data in {filename.rsplit('/')[1]}")
  local_database_file = open("timestamps.json", "r+")
  local_database = json.load(local_database_file)

  if anidb_id not in local_database:
    local_database[anidb_id] = []

  series = local_database[anidb_id]
  
  indices = [i for i in range(len(series)) if series[i]['episode_number'] == episode_number]
  if len(indices) == 0:
    timestamp_data = get_timestamp_template(episode_number, source="chapter_data")
  else:
    timestamp_data = series[indices[0]]

  op_lengths = []
  ed_lengths = []
  for file in os.scandir('./openings'):
    info: dict = ffmpeg.probe(file)
    duration = info.get('format',{}).get('duration') or info.get('streams',[{}])[0].get('duration')
    if not duration:
      continue
    op_lengths.append(float(duration))

  for file in os.scandir('./endings'):
    info: dict = ffmpeg.probe(file)
    duration = info.get('format',{}).get('duration') or info.get('streams',[{}])[0].get('duration')
    if not duration:
      continue
    ed_lengths.append(float(duration))

  for i in range(len(chapters)):
    chapter = chapters[i]
    if i+1 < len(chapters):
      next_chapter = chapters[i+1]
    else:
      next_chapter = None

    start = float(chapter['start'])
    end = float(chapter['end'])

    duration = end - start

    results = check_op_ed(duration, i / len(chapters), op_lengths, ed_lengths)
    if next_chapter:
      results_next = check_op_ed(float(next_chapter['end'])-float(next_chapter['start']), (i+1) / len(chapters), op_lengths, ed_lengths)
    else:
      results_next = None

    if results == 'op' and results_next not in ['op','ed']:
      timestamp_data['opening']['start'] = round(start)
      timestamp_data['opening']['end'] = round(end)

    if results == 'ed' and results_next not in ['op','ed']:
      timestamp_data['ending']['start'] = round(start)
      timestamp_data['ending']['end'] = round(end)

  if len(indices) == 0:
    series.append(timestamp_data)

  local_database_file.seek(0)
  json.dump(local_database, local_database_file, indent=4)
  local_database_file.truncate()
  local_database_file.close()

  return timestamp_data

def check_op_ed(duration: float, position: float, op_lengths: list, ed_lengths: list) -> str:
  if position < 0.35 and any(abs(duration - l) <= 1.5 for l in op_lengths): # It might be at the beginning (an opening)
    return 'op'
  if position > 0.6 and any(abs(duration - l) <= 1.5 for l in ed_lengths): # It might be at the end (an ending)
    return 'ed'
  
  return None

# From https://gist.github.com/dcondrey/469e2850e7f88ac198e8c3ff111bda7c
def get_chapters(filename: str) -> list[dict]:
  chapters = []
  command = [ "ffmpeg", '-i', filename]
  output = ""
  try:
    # ffmpeg requires an output file and so it errors 
    # when it does not get one so we need to capture stderr, 
    # not stdout.
    output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
  except subprocess.CalledProcessError as e:
    output = e.output
   
  for line in iter(output.splitlines()):
    m = re.match(r".*Chapter #(\d+:\d+): start (\d+\.\d+), end (\d+\.\d+).*", line)
    if m != None:
      chapters.append({ "name": m.group(1), "start": m.group(2), "end": m.group(3)})
  return chapters
