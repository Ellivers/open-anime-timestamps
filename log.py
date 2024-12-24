import args

def logprint(message: str, require_verbose=True):
  if args.parsed_args.verbose or not require_verbose:
    print(message)
