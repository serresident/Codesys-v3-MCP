import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from abak_bridge_client import send_request

HOST = os.environ.get("ABAK_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("ABAK_BRIDGE_PORT", "11888"))

code = """
proj = projects.primary
devs = proj.find('M1_K3_AI_10_08_00', True)
if devs:
    dev = devs[0]
    con = dev.connectors[0]
    print('always_mapping: ' + str(con.io_always_mapping))
    for p in con.host_parameters:
        if p.is_mappable_io:
            var_name = p.io_mapping.variable if hasattr(p, 'io_mapping') else 'None'
            print('%s --> %s' % (p.name, var_name))
else:
    print('Device M1_K3_AI_10_08_00 not found!')

gvls = proj.find('GVL_Raw', True)
if gvls:
    print('=== DECLARATION GVL_Raw ===')
    print(gvls[0].textual_declaration.text)
else:
    print('GVL_Raw not found!')
"""

res = send_request(HOST, PORT, {"action": "exec", "code": code})
print(res.get("log", res))
