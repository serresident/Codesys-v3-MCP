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

    args = parser.parse_args()

    cmd_map = {
        "status": cmd_status,
        "save": cmd_save,
        "compile": cmd_compile,
        "exec": cmd_exec,
        "map-io": cmd_map_io,
        "export": cmd_export,
        "import": cmd_import,
    }

    handler = cmd_map.get(args.cmd)
    if handler:
        handler(args)

if __name__ == "__main__":
    main()
