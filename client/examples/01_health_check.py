#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример 1: Проверка связи с сервером автоматизации Abak.IDE
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abak_bridge_client import send_request

HOST = os.environ.get("ABAK_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("ABAK_BRIDGE_PORT", "11888"))

def main():
    print(f"Checking connection to Abak.IDE at {HOST}:{PORT}...")
    try:
        res = send_request(HOST, PORT, {"action": "status"})
        print("Response received successfully:")
        print(f"  Project open: {res.get('project_open', False)}")
        print(f"  Project path: {res.get('status', {}).get('path') or res.get('project_path')}")
        print(f"  Server log:   {res.get('log', '').strip()}")
    except Exception as ex:
        print(f"Error connecting: {ex}")

if __name__ == "__main__":
    main()
