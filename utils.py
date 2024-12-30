import args

def is_not_silent():
	return not args.parsed_args.silent

def logprint(message: str, ignore_silent=False):
  if is_not_silent() or ignore_silent:
    print(message)

def get_timestamp_template(episode_number, source=None):
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
	handle_merge(merge_from, merge_to, ('recap','start'), depth=2)
	handle_merge(merge_from, merge_to, ('recap','end'), depth=2)
	handle_merge(merge_from, merge_to, ('opening','start'), depth=2)
	handle_merge(merge_from, merge_to, ('opening','end'), depth=2)
	handle_merge(merge_from, merge_to, ('ending','start'), depth=2)
	handle_merge(merge_from, merge_to, ('ending','end'), depth=2)
     
	handle_merge(merge_from, merge_to, ('preview_start'))
  
	if 'sources' in merge_from:
		for src in merge_from['sources']:
			if src not in merge_to['sources']:
				merge_to['sources'].append(src)
	
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
	
	return merge_to
	
def handle_merge(f: dict, t: dict, keys: tuple[str], depth=1):
	if depth == 1 and f.get(keys[0]) != None and t[keys[0]] == -1:
		t[keys[0]] = f[keys[0]]
		return
	if depth == 2 and f.get(keys[0],{}).get(keys[1]) != None and t[keys[0]][keys[1]] == -1:
		t[keys[0]][keys[1]] = f[keys[0]][keys[1]]
		return
