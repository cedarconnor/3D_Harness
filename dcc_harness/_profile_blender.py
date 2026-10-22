"""Enable an explicit profile before the worker opens or evaluates its input."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bpy
from dcc_harness.evidence import read_json, write_json
from dcc_harness.environments import load_profile
from dcc_harness.data.bridge import addons

action, request_path = sys.argv[sys.argv.index('--') + 1:]
request = read_json(request_path)
if not bpy.app.background and not (request.get('owned_gui') is True and action in ('recipe_apply','recipe_verify')):
    raise ValueError('This bootstrap only controls an owned qualification/worker process')
profile = load_profile(request['profile'])
attempts = addons.NETWORK_ATTEMPTS
def offline_audit(event, args, attempts=attempts, folder=Path(request_path).parent, action=action, writer=write_json):
    if event == 'socket.connect':
        attempts.append(str(args[1]))
        writer(folder / (action + '-network-attempts') / (str(len(attempts)) + '.json'),
                   {'event':event, 'destination':attempts[-1]})
        raise RuntimeError('Offline profile refused an outbound connection')
sys.addaudithook(offline_audit)
try:
    addons.enable_profile(profile)
finally:
    state = addons.LAST_ACTIVATION or {'state':'FAILED_BEFORE_ACTIVATION'}
    if state['state'] == 'STARTED':
        state['state'] = 'FAILED_OR_PARTIAL'
    write_json(Path(request_path).with_name(action + '-environment.json'), {**state, 'outbound_attempts':attempts})
