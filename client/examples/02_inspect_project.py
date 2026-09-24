#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример 2: Детальный дамп дерева устройств и логики из активного проекта
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abak_bridge_client import send_request

HOST = os.environ.get("ABAK_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("ABAK_BRIDGE_PORT", "11888"))

REMOTE_SCRIPT = """
proj = script_engine.projects.primary
app = proj.find('Application', True)[0]

print('=== APPLICATION TREE ===')
stack = [('', app)]
while stack:
    p, n = stack.pop(0)
    for c in n.get_children(False):
        curr = p + '/' + c.get_name()
        print(curr)
        stack.append((curr, c))

print('\\n=== CANOPEN / HARDWARE DEVICES ===')
devs = proj.find('Device', True)
if devs:
    dev_stack = [('', devs[0])]
    while dev_stack:
        p, n = dev_stack.pop(0)
        for c in n.get_children(False):
            curr = p + '/' + c.get_name()
            print(curr)
            dev_stack.append((curr, c))
"""

def main():
    print(f"Inspecting project tree on {HOST}:{PORT}...")
    res = send_request(HOST, PORT, {"action": "exec", "code": REMOTE_SCRIPT})
    if res.get("log"):
        print(res["log"])
    if res.get("status") == "error":
        print(f"Error: {res.get('message')}")

if __name__ == "__main__":
    main()
