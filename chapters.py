import json
import subprocess
import re
from utils import logprint, get_timestamp_template

def parse_chapters(file_path: str, anidb_id: str, episode_number: float, themes: list[dict]) -> dict:
  chapters = get_chapters(file_path)
  if len(chapters) == 0:
    return
  
  local_database_file = open("timestamps.json", "r")
  local_database = json.load(local_database_file)
  local_database_file.close()

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
  for theme in themes:
    if "OP" in theme['type']:
      op_lengths.append(theme['duration'])
    elif "ED" in theme['type']:
      ed_lengths.append(theme['duration'])
  
  chapters_end = float(chapters[-1]['end'])

  found_data = {
    'op': False,
    'ed': False
  }

  for i in range(len(chapters)):
    chapter = chapters[i]
    if i+1 < len(chapters):
      next_chapter = chapters[i+1]
    else:
      next_chapter = None

    start = float(chapter['start'])
    end = float(chapter['end'])

    duration = end - start

    results = check_op_ed(duration, start / chapters_end, op_lengths, ed_lengths)
    if next_chapter:
      results_next = check_op_ed(float(next_chapter['end'])-float(next_chapter['start']), float(next_chapter['start']) / chapters_end, op_lengths, ed_lengths)
    else:
      results_next = None

    if results == 'op' and results_next not in ['op','ed'] and not found_data['op'] \
      and (timestamp_data['opening']['start'] == -1 or timestamp_data['opening']['end'] == -1):

      logprint(f"[chapters.py] [INFO] Found opening in chapter data of {file_path.rsplit('/', 1)[1]}")
      timestamp_data['opening']['start'] = round(start)
      timestamp_data['opening']['end'] = round(end)
      if 'chapter_data' not in timestamp_data['sources']:
        timestamp_data['sources'].append('chapter_data')
      found_data['op'] = True

    if results == 'ed' and results_next not in ['op','ed'] and not found_data['ed'] \
      and (timestamp_data['ending']['start'] == -1 or timestamp_data['ending']['end'] == -1):

      logprint(f"[chapters.py] [INFO] Found ending in chapter data of {file_path.rsplit('/', 1)[1]}")
      timestamp_data['ending']['start'] = round(start)
      timestamp_data['ending']['end'] = round(end)
      if 'chapter_data' not in timestamp_data['sources']:
        timestamp_data['sources'].append('chapter_data')
      found_data['ed'] = True

  if len(indices) == 0:
    series.append(timestamp_data)

  if True in [found_data['op'],found_data['ed']]:
    local_database_file = open("timestamps.json", 'w')
    json.dump(local_database, local_database_file, indent=4)
    local_database_file.close()

  return timestamp_data

def check_op_ed(duration: float, position: float, op_lengths: list, ed_lengths: list) -> str:
  if position < 0.35 and any(abs(duration - l) <= 1.5 for l in op_lengths): # Check for openings
    return 'op'
  if position > 0.7 and any(abs(duration - l) <= 1.5 for l in ed_lengths): # Check for endings
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
