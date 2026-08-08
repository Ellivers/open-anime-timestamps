import args
import ffmpeg

def is_not_silent() -> bool:
	return not args.parsed_args.silent

def logprint(message: str, ignore_silent=False):
  if is_not_silent() or ignore_silent:
    print(message)

def get_media_duration(path) -> float:
	info: dict = ffmpeg.probe(path)
	duration = info.get('format',{}).get('duration') or info.get('streams',[{}])[0].get('duration')
	return float(duration)

def get_timestamp_template(episode_number, source:str = None):
  data = {
		"episode_number": float(episode_number),
		"recap": {
			"start": -1,
			"end": -1
		},
		"opening": {
			"start": -1,
			"end": -1
		},
		"ending": {
			"start": -1,
			"end": -1
		},
		"preview_start": -1,
		"sources": []
	}
  if source:
    data['sources'].append(source)
  return data

def merge_timestamps(merge_from: dict, merge_to: dict) -> dict: # Supports old database format for 'merge_from'
	original = merge_to.copy()
	merged = 0
	merged = merged + handle_merge(merge_from, merge_to, ['recap','start'])
	merged = merged + handle_merge(merge_from, merge_to, ['recap','end'])
	merged = merged + handle_merge(merge_from, merge_to, ['opening','start'])
	merged = merged + handle_merge(merge_from, merge_to, ['opening','end'])
	merged = merged + handle_merge(merge_from, merge_to, ['ending','start'])
	merged = merged + handle_merge(merge_from, merge_to, ['ending','end'])
    
	merged = merged + handle_merge(merge_from, merge_to, ['preview_start'])
	
	# Old format
	if 'recap_start' in merge_from and merge_to['recap']['start'] == -1:
		merge_to['recap']['start'] = merge_from['recap_start']
	if 'opening_start' in merge_from and merge_to['opening']['start'] == -1:
		merge_to['opening']['start'] = merge_from['opening_start']
	if 'ending_start' in merge_from and merge_to['ending']['start'] == -1:
		merge_to['ending']['start'] = merge_from['ending_start']
  
	if 'source' in merge_from and merge_from['source'] not in merge_to['sources']:
		merge_to['sources'].append(merge_from['source'])
	
	merge_to['episode_number'] = float(merge_to['episode_number'])
	# Old format end

	# Make sure no incorrect timestamps make it through
	if merge_to['recap']['start'] > merge_to['recap']['end']:
		merge_to['recap'] = original['recap']
		merged = merged - 1
	if merge_to['opening']['start'] > merge_to['opening']['end']:
		merge_to['opening'] = original['opening']
		merged = merged - 1
	if merge_to['ending']['start'] > merge_to['ending']['end']:
		merge_to['ending'] = original['ending']
		merged = merged - 1

	if 'sources' in merge_from and merged > 0:
		for src in merge_from['sources']:
			if src not in merge_to['sources']:
				merge_to['sources'].append(src)
	
	return merge_to

def handle_merge(f: dict, t: dict, keys: list[str]) -> int:
	depth = len(keys)
	if depth == 1 and f.get(keys[0]) != None and t[keys[0]] == -1 and t[keys[0]] != f[keys[0]]:
		t[keys[0]] = int(f[keys[0]])
		return 1
	if depth == 2 and f.get(keys[0],{}).get(keys[1]) != None and t[keys[0]][keys[1]] == -1 and t[keys[0]][keys[1]] != f[keys[0]][keys[1]]:
		t[keys[0]][keys[1]] = int(f[keys[0]][keys[1]])
		return 1
	return 0
