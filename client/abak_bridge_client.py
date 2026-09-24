#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Abak.IDE & CODESYS V3.5 Automation Bridge CLI Client
================================================================================
Клиент для взаимодействия с сервером автоматизации Abak.IDE по сети (TCP/HTTP)
или через локальный IPC-файл.
================================================================================
"""

import sys
import os
import socket
import json
import argparse
import glob

DEFAULT_HOST = os.environ.get("ABAK_BRIDGE_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("ABAK_BRIDGE_PORT", "11888"))
TIMEOUT = 15.0

def send_request(host, port, req_data, timeout=TIMEOUT):
    """
    Отправляет JSON запрос на сервер Abak.IDE через прямой TCP-сокет HTTP/1.1.
    """
    body = json.dumps(req_data, ensure_ascii=False).encode("utf-8")
    header = (
        f"POST /api HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Content-Type: application/json; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode("utf-8")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.sendall(header + body)

        resp_bytes = bytearray()
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp_bytes.extend(chunk)

        # Разбор ответа HTTP
        sep = b"\r\n\r\n"
        idx = resp_bytes.find(sep)
        if idx != -1:
            body_data = resp_bytes[idx + len(sep):]
        else:
            body_data = resp_bytes

        raw_str = body_data.decode("utf-8", errors="replace")
        return json.loads(raw_str)
    finally:
        s.close()

# ------------------------------------------------------------------------------
# Команды CLI
# ------------------------------------------------------------------------------
def cmd_status(args):
    r = send_request(args.host, args.port, {"action": "status"})
    print(json.dumps(r, indent=2, ensure_ascii=False))

def cmd_save(args):
    r = send_request(args.host, args.port, {"action": "save"})
    print(r.get("message", json.dumps(r)))

def cmd_compile(args):
    print(f"Triggering compilation on {args.host}:{args.port} (clean={args.clean})...")
    r = send_request(args.host, args.port, {"action": "compile", "clean": args.clean}, timeout=60.0)
    
    if r.get("log"):
        print("\n--- SERVER LOG ---")
        print(r["log"].strip())
        print("------------------\n")
    
    success = r.get("success", False)
    errs = r.get("errors_count", 0)
    warns = r.get("warnings_count", 0)
    
    print(f"Compilation finished: Success={success}, Errors={errs}, Warnings={warns}")
    for msg in r.get("messages", []):
        sev = msg.get("severity", "")
        txt = msg.get("text", "")
        if "Error" in sev or "Warning" in sev:
            print(f"  [{sev}] {txt}")

    if not success:
        sys.exit(1)

def cmd_exec(args):
    code_text = args.code
    if os.path.exists(code_text):
        with open(code_text, "r", encoding="utf-8") as f:
            code_text = f.read()

    r = send_request(args.host, args.port, {"action": "exec", "code": code_text}, timeout=60.0)
    if r.get("log"):
        print(r["log"])
    if r.get("status") == "error":
        print(f"ERROR: {r.get('message')}", file=sys.stderr)
        sys.exit(1)

def cmd_map_io(args):
    """
    Привязка канала: --device M1_K3_AI_10_08_00 --channel "Analog Input, channel 1" --var "Application.GVL.myVar"
    """
    req = {
        "action": "map_io",
        "device_name": args.device,
        "mappings": {args.channel: args.var},
        "always_update": True
    }
    r = send_request(args.host, args.port, req)
    print(json.dumps(r, indent=2, ensure_ascii=False))

def cmd_export(args):
    target_dir = os.path.abspath(args.out)
    os.makedirs(target_dir, exist_ok=True)
    print(f"Exporting project from {args.host}:{args.port} to {target_dir}...")
    
    r = send_request(args.host, args.port, {"action": "export"}, timeout=60.0)
    if r.get("status") != "ok":
        print(f"Export error: {r.get('message')}")
        sys.exit(1)

    objs = r.get("objects", {})
    count = 0
    for rel_path, data in objs.items():
        file_path = os.path.join(target_dir, rel_path.replace("/", os.sep) + ".st")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            decl = data.get("declaration", "").strip()
            impl = data.get("implementation", "").strip()
            if decl:
                f.write("// @DECLARATION\n" + decl + "\n\n")
            if impl:
                f.write("// @IMPLEMENTATION\n" + impl + "\n")
        count += 1
    print(f"Successfully exported {count} objects.")

def cmd_import(args):
    src_dir = os.path.abspath(args.src)
    if not os.path.exists(src_dir):
        print(f"Source dir not found: {src_dir}")
        sys.exit(1)

    files_data = {}
    for st_file in glob.glob(os.path.join(src_dir, "**", "*.st"), recursive=True):
        rel = os.path.relpath(st_file, src_dir).replace(os.sep, "/")
        with open(st_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        decl = ""
        impl = ""
        if "// @IMPLEMENTATION" in content:
            parts = content.split("// @IMPLEMENTATION")
            decl_part = parts[0]
            impl = parts[1].strip()
            if "// @DECLARATION" in decl_part:
                decl = decl_part.split("// @DECLARATION")[1].strip()
            else:
                decl = decl_part.strip()
        else:
            decl = content.strip()

        files_data[rel] = {"declaration": decl, "implementation": impl}

    print(f"Importing {len(files_data)} files to {args.host}:{args.port}...")
    r = send_request(args.host, args.port, {"action": "import", "files": files_data}, timeout=60.0)
    print(json.dumps(r, indent=2, ensure_ascii=False))

def cmd_inspect_tree(args):
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
        p, d = dev_stack.pop(0)
        for c in d.get_children(False):
            curr = p + '/' + c.get_name()
            print('  ' + curr + ' [' + str(c.type) + ']')
            dev_stack.append((curr, c))
"""
    r = send_request(args.host, args.port, {"action": "exec", "code": code}, timeout=30.0)
    if r.get("log"):
        print(r["log"])
    else:
        print(json.dumps(r, indent=2, ensure_ascii=False))

def cmd_online_status(args):
    r = send_request(args.host, args.port, {"action": "online_status"})
    print(json.dumps(r, indent=2, ensure_ascii=False))

def cmd_online_login(args):
    r = send_request(args.host, args.port, {"action": "online_login", "change_option": args.change_option})
    print(json.dumps(r, indent=2, ensure_ascii=False))

def cmd_online_logout(args):
    r = send_request(args.host, args.port, {"action": "online_logout"})
    print(json.dumps(r, indent=2, ensure_ascii=False))

def cmd_online_control(args):
    r = send_request(args.host, args.port, {"action": "online_control", "command": args.command})
    print(json.dumps(r, indent=2, ensure_ascii=False))

def cmd_online_read(args):
    r = send_request(args.host, args.port, {"action": "online_read", "expressions": args.vars})
    print(json.dumps(r, indent=2, ensure_ascii=False))

def cmd_online_write(args):
    val_dict = {}
    for item in args.vars:
        if "=" in item:
            k, v = item.split("=", 1)
            val_dict[k.strip()] = v.strip()
        else:
            print(f"Invalid format '{item}'. Expected KEY=VALUE (e.g. Application.GVL.myVar=123)", file=sys.stderr)
            sys.exit(1)
    r = send_request(args.host, args.port, {"action": "online_write", "values": val_dict, "force": args.force})
    print(json.dumps(r, indent=2, ensure_ascii=False))

def cmd_export_xml(args):
    req = {"action": "export_xml"}
    if args.out:
        req["path"] = os.path.abspath(args.out)
    r = send_request(args.host, args.port, req, timeout=60.0)
    if args.out:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        if r.get("status") == "ok" and "xml" in r:
            print(r["xml"])
        else:
            print(json.dumps(r, indent=2, ensure_ascii=False))

def cmd_import_xml(args):
    file_path = os.path.abspath(args.file)
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    r = send_request(args.host, args.port, {"action": "import_xml", "path": file_path}, timeout=60.0)
    print(json.dumps(r, indent=2, ensure_ascii=False))

# ------------------------------------------------------------------------------
# Точка входа CLI
# ------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Abak.IDE & CODESYS V3.5 Bridge Client")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Target host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Target port (default: {DEFAULT_PORT})")

    sub = parser.add_subparsers(dest="cmd", required=True)

    # status
    sub.add_parser("status", help="Get IDE and active project status")

    # save
    sub.add_parser("save", help="Save active project in IDE")

    # compile
    p_comp = sub.add_parser("compile", help="Compile project")
    p_comp.add_argument("--clean", action="store_true", help="Perform Clean before Build")

    # inspect-tree
    sub.add_parser("inspect-tree", help="Inspect project Application POUs and Hardware tree")

    # exec
    p_exec = sub.add_parser("exec", help="Execute Python code on IDE ScriptEngine")
    p_exec.add_argument("code", help="Code string or path to .py file")

    # map-io
    p_map = sub.add_parser("map-io", help="Map device channel to variable")
    p_map.add_argument("--device", required=True, help="Device name in tree (e.g. M1_K3_AI_10_08_00)")
    p_map.add_argument("--channel", required=True, help="Channel name (e.g. 'Analog Input, channel 1')")
    p_map.add_argument("--var", required=True, help="Full variable path (e.g. 'Application.GVL.myVar')")

    # export
    p_exp = sub.add_parser("export", help="Export ST sources from project")
    p_exp.add_argument("--out", required=True, help="Target output folder")

    # import
    p_imp = sub.add_parser("import", help="Import ST sources into project")
    p_imp.add_argument("--src", required=True, help="Source folder with .st files")

    # online-status
    sub.add_parser("online-status", help="Check PLC online connection and RUN/STOP state")

    # online-login
    p_login = sub.add_parser("online-login", help="Connect (Login) to PLC")
    p_login.add_argument("--change-option", default="Try", choices=["Try", "Never", "Force", "Keep"], help="Online change option")

    # online-logout
    sub.add_parser("online-logout", help="Disconnect (Logout) from PLC")

    # online-control
    p_ctrl = sub.add_parser("online-control", help="Control PLC execution state")
    p_ctrl.add_argument("command", choices=["start", "stop", "reset_warm", "reset_cold"], help="Control command")

    # online-read
    p_read = sub.add_parser("online-read", help="Read PLC variable values in real-time")
    p_read.add_argument("--vars", nargs="+", required=True, help="Expressions to read (e.g. Application.PLC_PRG.iCounter)")

    # online-write
    p_write = sub.add_parser("online-write", help="Write or Force PLC variable values")
    p_write.add_argument("--vars", nargs="+", required=True, help="Assignments in format VAR=VALUE")
    p_write.add_argument("--force", action="store_true", help="Force value instead of regular write")

    # export-xml
    p_expxml = sub.add_parser("export-xml", help="Export application to standard PLCopen XML")
    p_expxml.add_argument("--out", help="Optional output XML file path. If omitted, prints XML to stdout.")

    # import-xml
    p_impxml = sub.add_parser("import-xml", help="Import PLCopen XML into active project")
    p_impxml.add_argument("--file", required=True, help="Path to PLCopen XML file to import")

    args = parser.parse_args()

    cmd_map = {
        "status": cmd_status,
        "save": cmd_save,
        "compile": cmd_compile,
        "inspect-tree": cmd_inspect_tree,
        "exec": cmd_exec,
        "map-io": cmd_map_io,
        "export": cmd_export,
        "import": cmd_import,
        "online-status": cmd_online_status,
        "online-login": cmd_online_login,
        "online-logout": cmd_online_logout,
        "online-control": cmd_online_control,
        "online-read": cmd_online_read,
        "online-write": cmd_online_write,
        "export-xml": cmd_export_xml,
        "import-xml": cmd_import_xml,
    }

    handler = cmd_map.get(args.cmd)
    if handler:
        handler(args)

if __name__ == "__main__":
    main()
