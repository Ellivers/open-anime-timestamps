import args

def logprint(message: str, require_verbose=True):
  if args.parsed_args.verbose or not require_verbose:
    print(message)

def get_timestamp_template(episode_number, source=None):
  data = {
		"episode_number": episode_number,
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
		"preview_start": -1
	}
  if source:
    data['source'] = source
  return data
