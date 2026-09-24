#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример 3: Программная привязка каналов модуля ввода/вывода (I/O Mapping)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abak_bridge_client import send_request

HOST = os.environ.get("ABAK_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("ABAK_BRIDGE_PORT", "11888"))

def main():
    device_name = "M1_K3_AI_10_08_00"
    mappings = {
        "Analog Input, channel 1": "Application.GVL_Raw.raw_Sensor1",
        "Analog Input, channel 2": "Application.GVL_Raw.raw_Sensor2",
        "Analog Input, channel 3": "Application.GVL_Raw.raw_Pressure",
    }
    
    print(f"Applying I/O mapping for device '{device_name}'...")
    req = {
        "action": "map_io",
        "device_name": device_name,
        "mappings": mappings,
        "always_update": True
    }
    
    res = send_request(HOST, PORT, req)
    print("Result:")
    print(res)

if __name__ == "__main__":
    main()
