#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Abak.IDE & CODESYS Bridge MCP Server
================================================================================
Model Context Protocol (MCP) server providing tools for AI agents to interact
directly with Abak.IDE / CODESYS PLC projects over the network or local IPC.

Author: Antigravity Automation Suite
================================================================================
"""

import sys
import os
import json
import socket
from typing import Optional, Dict, Any, List

from mcp.server.mcpserver import MCPServer

# Initialize MCP Server
app = MCPServer("abak-ide-bridge")

DEFAULT_HOST = os.environ.get("ABAK_BRIDGE_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("ABAK_BRIDGE_PORT", "11888"))

def send_tcp_request(host: str, port: int, payload: dict, timeout: float = 30.0) -> dict:
    """Send JSON-RPC/dict payload to CODESYS Bridge server and return parsed response."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.sendall(data)
        
        chunks = []
        while True:
            try:
                chunk = s.recv(16384)
                if not chunk:
                    break
                chunks.append(chunk)
            except socket.timeout:
                break
        
        raw_res = b"".join(chunks).decode("utf-8", errors="replace").strip()
        if not raw_res:
            return {"status": "error", "error": "Empty response from bridge"}
        
        # If wrapped in HTTP header (Simple HTTP response)
        if "\r\n\r\n" in raw_res:
            raw_res = raw_res.split("\r\n\r\n", 1)[1]
        elif "\n\n" in raw_res:
            raw_res = raw_res.split("\n\n", 1)[1]
            
        return json.loads(raw_res)
    except Exception as ex:
        return {"status": "error", "error": str(ex)}
    finally:
        s.close()


@app.tool()
def abak_status(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Dict[str, Any]:
    """Check connectivity to Abak.IDE CODESYS Bridge, active project, and environment status.
    
    Args:
        host: IP address of the engineering station running Abak.IDE (default: 127.0.0.1).
        port: TCP port where codesys_bridge_server.py is listening (default: 11888).
    """
    return send_tcp_request(host, port, {"action": "status"}, timeout=3.0)


@app.tool()
def abak_build_project(clean: bool = False, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Dict[str, Any]:
    """Compile the active PLC project in Abak.IDE.
    
    Args:
        clean: If True, performs a deep clean & build (rebuild all). If False, does incremental build.
        host: IP address of the engineering station.
        port: TCP port of the bridge server.
    """
    return send_tcp_request(host, port, {"action": "compile", "clean": clean}, timeout=60.0)


@app.tool()
def abak_map_io(
    device_name: str,
    mappings: Dict[str, str],
    always_update: bool = True,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT
) -> Dict[str, Any]:
    """Programmatically map hardware I/O channels of a module to GVL variables.
    
    Args:
        device_name: Name of the hardware device node in CODESYS tree (e.g. 'M1_K3_AI_10_08_00').
        mappings: Dictionary mapping channel parameter name to full variable identifier.
                  Example: {"Analog Input, channel 1": "Application.GVL_Raw.raw_Level49"}
                  NOTE: Target variables must be scalar identifiers in GVL, not array subscripts!
        always_update: If True, sets io_always_mapping = True (Always update variables in bus cycle).
        host: IP address of the engineering station.
        port: TCP port of the bridge server.
    """
    req = {
        "action": "map_io",
        "device_name": device_name,
        "mappings": mappings,
        "always_update": always_update
    }
    return send_tcp_request(host, port, req, timeout=30.0)


@app.tool()
def abak_inspect_device_tree(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Dict[str, Any]:
    """Inspect the full project tree: Application POUs, tasks, and hardware devices.
    
    Args:
        host: IP address of the engineering station.
        port: TCP port of the bridge server.
    """
    code = """
proj = script_engine.projects.primary
print('=== APPLICATION OBJECTS ===')
apps = proj.find('Application', True)
if apps:
    app = apps[0]
    stack = [('', app)]
    while stack:
        p, n = stack.pop(0)
        for c in n.get_children(False):
            curr = p + '/' + c.get_name()
            print('  ' + curr + ' [' + str(c.type) + ']')
            stack.append((curr, c))

print('\\n=== HARDWARE DEVICES ===')
devs = proj.find('Device', True)
if devs:
    dev_stack = [('', devs[0])]
    while dev_stack:
        p, n = dev_stack.pop(0)
        for c in n.get_children(False):
            curr = p + '/' + c.get_name()
            print('  ' + curr + ' [' + str(c.type) + ']')
            dev_stack.append((curr, c))
"""
    return send_tcp_request(host, port, {"action": "exec", "code": code}, timeout=30.0)


@app.tool()
def abak_inspect_device_parameters(device_name: str, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Dict[str, Any]:
    """Inspect all parameters, connector channels, and current I/O mappings of a specific hardware device.
    
    Args:
        device_name: Device node name in project (e.g. 'M1_K3_AI_10_08_00').
        host: IP address of the engineering station.
        port: TCP port of the bridge server.
    """
    code = """
devs = script_engine.projects.primary.find('%s', True)
if not devs:
    print('DEVICE_NOT_FOUND: %s')
else:
    dev = devs[0]
    print('Device: ' + dev.get_name())
    if hasattr(dev, 'connectors') and len(dev.connectors) > 0:
        con = dev.connectors[0]
        print('always_mapping: ' + str(getattr(con, 'io_always_mapping', False)))
        for p in con.host_parameters:
            if p.is_mappable_io:
                var = p.io_mapping.variable if hasattr(p, 'io_mapping') else 'None'
                print('  [MAPPABLE] ' + p.name + ' --> ' + str(var))
            else:
                print('  [PARAM] ' + p.name + ' = ' + str(getattr(p, 'value', '')))
""" % (device_name, device_name)
    return send_tcp_request(host, port, {"action": "exec", "code": code}, timeout=30.0)


@app.tool()
def abak_export_sources(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Dict[str, Any]:
    """Export all ST source objects (POUs, GVLs, DUTs) from the active CODESYS Application as JSON.
    
    Args:
        host: IP address of the engineering station.
        port: TCP port of the bridge server.
    """
    return send_tcp_request(host, port, {"action": "export"}, timeout=30.0)


@app.tool()
def abak_save_project(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Dict[str, Any]:
    """Save the active project in Abak.IDE.
    
    Args:
        host: IP address of the engineering station.
        port: TCP port of the bridge server.
    """
    return send_tcp_request(host, port, {"action": "save"}, timeout=15.0)


@app.tool()
def abak_exec_python(code: str, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Dict[str, Any]:
    """Execute arbitrary Python 2.7 / IronPython code directly inside CODESYS / Abak.IDE ScriptEngine.
    
    The script has access to:
      - `script_engine.projects.primary` (Active project)
      - `system`
      - `print` (captured and returned in response log)
    
    Args:
        code: Python code string to execute inside CODESYS.
        host: IP address of the engineering station.
        port: TCP port of the bridge server.
    """
    return send_tcp_request(host, port, {"action": "exec", "code": code}, timeout=60.0)


def main():
    # Run MCP server using standard IO transport
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
