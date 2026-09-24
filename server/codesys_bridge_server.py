# -*- coding: utf-8 -*-
"""
================================================================================
Abak.IDE & CODESYS V3.5 Automation Bridge Server
================================================================================
Запуск внутри среды CODESYS V3.5 / Abak.IDE:
Tools -> Scripting -> Run Script... -> codesys_bridge_server.py

Особенности:
- Полностью неблокирующий UI-поток (System.Windows.Forms.Timer 100 мс)
- Двойной режим работы:
  1. TCP HTTP сервер (порт 11888, с автоперебором 11889, 11890, 12888)
  2. Локальный IPC файл обмена (codesys_ipc_req.json -> codesys_ipc_resp.json)
- Автономный диспетчер команд: status, export, import, compile, exec, map_io, save
================================================================================
"""

import sys
import os
import io
import time
import json
import traceback

import System
from System import Array, Byte, Int32
from System.IO import File, FileInfo, Directory, Path, MemoryStream
from System.Windows.Forms import Timer, Application
from System.Net import IPAddress
from System.Net.Sockets import TcpListener, SocketException

# ------------------------------------------------------------------------------
# Конфигурация сервера
# ------------------------------------------------------------------------------
TCP_PORTS = [11888, 11889, 11890, 12888]
TIMER_INTERVAL_MS = 100
IPC_REQ_FILE = os.path.join(System.IO.Path.GetTempPath(), "codesys_ipc_req.json")
IPC_RESP_FILE = os.path.join(System.IO.Path.GetTempPath(), "codesys_ipc_resp.json")

# Очистка старых экземпляров таймеров при повторном запуске скрипта
if "CODESYS_BRIDGE_TIMER" in globals() and globals()["CODESYS_BRIDGE_TIMER"] is not None:
    try:
        globals()["CODESYS_BRIDGE_TIMER"].Stop()
        globals()["CODESYS_BRIDGE_TIMER"].Dispose()
        print("Previous Timer stopped and disposed.")
    except Exception as e:
        print("Warning stopping old timer: %s" % e)

if "CODESYS_TCP_LISTENER" in globals() and globals()["CODESYS_TCP_LISTENER"] is not None:
    try:
        globals()["CODESYS_TCP_LISTENER"].Stop()
        print("Previous TCP Listener stopped.")
    except Exception as e:
        print("Warning stopping old TCP listener: %s" % e)

# ------------------------------------------------------------------------------
# Вспомогательные классы перехвата вывода
# ------------------------------------------------------------------------------
class OutputCapture(object):
    def __init__(self):
        self.buffer = []
        self.old_stdout = sys.stdout

    def start(self):
        sys.stdout = self

    def stop(self):
        sys.stdout = self.old_stdout
        return "".join(self.buffer)

    def write(self, s):
        self.buffer.append(s)
        self.old_stdout.write(s)

    def flush(self):
        self.old_stdout.flush()

# ------------------------------------------------------------------------------
# Обработчики действий (Actions)
# ------------------------------------------------------------------------------
def action_status(req):
    proj = projects.primary
    if not proj:
        return {"status": "ok", "project_open": False}
    
    app_name = None
    apps = proj.find("Application", True)
    if apps:
        app_name = apps[0].get_name()

    return {
        "status": "ok",
        "project_open": True,
        "project_path": proj.path,
        "app_name": app_name,
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

def action_save(req):
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}
    proj.save()
    return {"status": "ok", "message": "Project saved successfully"}

def action_compile(req):
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}
    
    apps = proj.find("Application", True)
    if not apps:
        return {"status": "error", "message": "No Application found in project"}
    
    app = apps[0]
    clean_first = req.get("clean", False)
    if clean_first:
        print("Cleaning application before build...")
        app.clean()
    
    print("Building application...")
    app.build()

    # Сбор сообщений компиляции
    messages = []
    errors_count = 0
    warnings_count = 0
    
    try:
        msg_objs = system.get_message_objects()
        for m in msg_objs:
            sev_str = str(m.Severity) if hasattr(m, "Severity") else "Unknown"
            txt = str(m.Text) if hasattr(m, "Text") else str(m)
            if "Error" in sev_str:
                errors_count += 1
            elif "Warning" in sev_str:
                warnings_count += 1
            messages.append({"severity": sev_str, "text": txt})
    except Exception as ex:
        messages.append({"severity": "Info", "text": "Message retrieval fallback: %s" % ex})

    is_success = (errors_count == 0)
    return {
        "status": "ok" if is_success else "compile_error",
        "success": is_success,
        "errors_count": errors_count,
        "warnings_count": warnings_count,
        "messages": messages[:50]  # первые 50 сообщений
    }

def action_exec(req):
    code_str = req.get("code", "")
    if not code_str:
        return {"status": "error", "message": "No code provided"}

    cap = OutputCapture()
    cap.start()
    err = None
    try:
        # IronPython exec
        scope = {
            "script_engine": sys.modules["__main__"],
            "projects": projects,
            "system": system,
            "online": online,
            "System": System
        }
        exec(code_str, scope)
    except Exception as ex:
        err = traceback.format_exc()
        print("SCRIPT_ERROR: " + str(ex))
    finally:
        out_text = cap.stop()

    if err:
        return {"status": "error", "message": str(err), "log": out_text}
    return {"status": "ok", "log": out_text}

def action_map_io(req):
    """
    Программная привязка аппаратных каналов модуля ввода/вывода к переменным GVL.
    req = {
        "device_name": "M1_K3_AI_10_08_00",
        "mappings": {
            "Analog Input, channel 1": "Application.GVL_Raw.raw_Level49",
            ...
        },
        "always_update": True
    }
    """
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}

    dev_name = req.get("device_name")
    devs = proj.find(dev_name, True)
    if not devs:
        return {"status": "error", "message": "Device not found: %s" % dev_name}

    dev = devs[0]
    if not hasattr(dev, "connectors") or len(dev.connectors) == 0:
        return {"status": "error", "message": "Device has no connectors: %s" % dev_name}

    con = dev.connectors[0]
    mappings = req.get("mappings", {})
    results = {}

    for p in con.host_parameters:
        if p.is_mappable_io and p.name in mappings:
            target_var = mappings[p.name]
            try:
                p.io_mapping.variable = target_var
                results[p.name] = str(p.io_mapping.variable)
            except Exception as ex:
                results[p.name] = "ERROR: " + str(ex)

    if req.get("always_update", True):
        con.io_always_mapping = True

    proj.save()
    return {"status": "ok", "mapped": results}

def action_export(req):
    """
    Экспорт всех объектов ST из Application.
    """
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}

    apps = proj.find("Application", True)
    if not apps:
        return {"status": "error", "message": "Application not found"}

    app = apps[0]
    exported = {}

    def recurse(node, rel_path=""):
        for c in node.get_children(False):
            name = c.get_name()
            curr_path = (rel_path + "/" + name) if rel_path else name
            
            decl = c.textual_declaration.text if hasattr(c, "textual_declaration") and c.textual_declaration else ""
            impl = c.textual_implementation.text if hasattr(c, "textual_implementation") and c.textual_implementation else ""
            
            if decl or impl:
                exported[curr_path] = {
                    "declaration": decl,
                    "implementation": impl,
                    "type": str(c.type)
                }
            recurse(c, curr_path)

    recurse(app)
    return {"status": "ok", "count": len(exported), "objects": exported}

def action_import(req):
    """
    Пакетный импорт файлов в проект.
    """
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}

    apps = proj.find("Application", True)
    if not apps:
        return {"status": "error", "message": "Application not found"}

    app = apps[0]
    files = req.get("files", {})
    results = {}

    for rel_path, data in files.items():
        name = rel_path.split("/")[-1].replace(".st", "").replace(".prg", "").replace(".dut", "").replace(".gvl", "").replace(".fb", "").replace(".func", "")
        decl = data.get("declaration", "")
        impl = data.get("implementation", "")

        found = app.find(name, True)
        if found:
            obj = found[0]
            if decl and hasattr(obj, "textual_declaration") and obj.textual_declaration:
                obj.textual_declaration.replace(decl)
            if impl and hasattr(obj, "textual_implementation") and obj.textual_implementation:
                obj.textual_implementation.replace(impl)
            results[name] = "Updated"
        else:
            results[name] = "Not found (new creation requires container path)"

    proj.save()
    return {"status": "ok", "results": results}

def action_online_status(req):
    """
    Проверка онлайн-статуса подключения к ПЛК и состояния выполнения (RUN / STOP).
    """
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}
    apps = proj.find("Application", True)
    if not apps:
        return {"status": "error", "message": "Application not found"}
    app = apps[0]
    
    try:
        online_app = app.create_online_application()
        is_logged = bool(online_app.is_logged_in)
        state_str = str(online_app.application_state) if is_logged else "offline"
        op_state = str(online_app.operation_state) if is_logged else "none"
        return {
            "status": "ok",
            "is_logged_in": is_logged,
            "application_state": state_str,
            "operation_state": op_state
        }
    except Exception as ex:
        return {"status": "error", "message": str(ex)}

def action_online_login(req):
    """
    Подключение (Login) к ПЛК через настроенный шлюз.
    Параметры:
      change_option: 'Try' (default), 'Never', 'Force', 'Keep'
    """
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}
    apps = proj.find("Application", True)
    if not apps:
        return {"status": "error", "message": "Application not found"}
    app = apps[0]

    opt_str = req.get("change_option", "Try")
    opt = getattr(script_engine.OnlineChangeOption, opt_str, script_engine.OnlineChangeOption.Try)

    try:
        online_app = app.create_online_application()
        online_app.login(opt, False)
        return {
            "status": "ok",
            "is_logged_in": bool(online_app.is_logged_in),
            "application_state": str(online_app.application_state)
        }
    except Exception as ex:
        return {"status": "error", "message": str(ex)}

def action_online_logout(req):
    """
    Отключение (Logout) от ПЛК.
    """
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}
    apps = proj.find("Application", True)
    if not apps:
        return {"status": "error", "message": "Application not found"}
    app = apps[0]
    try:
        online_app = app.create_online_application()
        online_app.logout()
        return {"status": "ok", "is_logged_in": False}
    except Exception as ex:
        return {"status": "error", "message": str(ex)}

def action_online_control(req):
    """
    Управление состоянием ПЛК: start (RUN), stop (STOP), reset_warm, reset_cold.
    """
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}
    apps = proj.find("Application", True)
    if not apps:
        return {"status": "error", "message": "Application not found"}
    app = apps[0]
    cmd = req.get("command", "").lower()

    try:
        online_app = app.create_online_application()
        if not online_app.is_logged_in:
            online_app.login(script_engine.OnlineChangeOption.Try, False)

        if cmd in ("start", "run"):
            online_app.start()
        elif cmd == "stop":
            online_app.stop()
        elif cmd == "reset_warm":
            online_app.reset(script_engine.ResetOption.Warm)
        elif cmd == "reset_cold":
            online_app.reset(script_engine.ResetOption.Cold)
        else:
            return {"status": "error", "message": "Unknown command: %s (expected start, stop, reset_warm, reset_cold)" % cmd}

        return {
            "status": "ok",
            "command": cmd,
            "application_state": str(online_app.application_state)
        }
    except Exception as ex:
        return {"status": "error", "message": str(ex)}

def action_online_read(req):
    """
    Чтение живых значений переменных из памяти ПЛК в реальном времени.
    Параметры:
      expressions: list[str] (список полных путей к переменным, напр. ['Application.GVL.rTemp'])
    """
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}
    apps = proj.find("Application", True)
    if not apps:
        return {"status": "error", "message": "Application not found"}
    app = apps[0]

    exprs = req.get("expressions", [])
    if isinstance(exprs, (str, unicode)):
        exprs = [exprs]

    try:
        online_app = app.create_online_application()
        if not online_app.is_logged_in:
            online_app.login(script_engine.OnlineChangeOption.Try, False)

        values = {}
        for expr in exprs:
            try:
                v = online_app.read_value(str(expr))
                values[expr] = str(v)
            except Exception as ve:
                values[expr] = "ERROR: " + str(ve)

        return {"status": "ok", "values": values}
    except Exception as ex:
        return {"status": "error", "message": str(ex)}

def action_online_write(req):
    """
    Запись или форсирование значений переменных в ПЛК.
    Параметры:
      values: dict[str, str] (словарь {'Application.GVL.myVar': '123.4'})
      force: bool (True для принудительного форсирования, False для обычной записи)
    """
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}
    apps = proj.find("Application", True)
    if not apps:
        return {"status": "error", "message": "Application not found"}
    app = apps[0]

    val_dict = req.get("values", {})
    force = req.get("force", False)

    try:
        online_app = app.create_online_application()
        if not online_app.is_logged_in:
            online_app.login(script_engine.OnlineChangeOption.Try, False)

        for expr, val in val_dict.items():
            online_app.set_prepared_value(str(expr), str(val))

        if force:
            online_app.force_prepared_values()
        else:
            online_app.write_prepared_values()

        return {"status": "ok", "written": val_dict, "forced": force}
    except Exception as ex:
        return {"status": "error", "message": str(ex)}

def action_export_xml(req):
    """
    Экспорт объектов проекта в стандартный формат PLCopen XML.
    """
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}
    apps = proj.find("Application", True)
    if not apps:
        return {"status": "error", "message": "Application not found"}
    app = apps[0]

    target_path = req.get("path")
    try:
        if target_path:
            proj.export_xml([app], path=target_path, recursive=True, export_folder_structure=True)
            return {"status": "ok", "path": target_path}
        else:
            xml_str = proj.export_xml([app], recursive=True, export_folder_structure=True)
            return {"status": "ok", "xml": xml_str}
    except Exception as ex:
        return {"status": "error", "message": str(ex)}

def action_import_xml(req):
    """
    Импорт объектов проекта из стандартного формата PLCopen XML.
    """
    proj = projects.primary
    if not proj:
        return {"status": "error", "message": "No active project"}

    xml_path = req.get("path")
    xml_content = req.get("xml")

    try:
        if not xml_path and xml_content:
            import tempfile
            temp_path = os.path.join(tempfile.gettempdir(), "import_temp.xml")
            with io.open(temp_path, "w", encoding="utf-8") as f:
                f.write(unicode(xml_content))
            xml_path = temp_path

        if not xml_path or not os.path.exists(xml_path):
            return {"status": "error", "message": "XML file not found: %s" % xml_path}

        proj.import_xml(xml_path)
        proj.save()
        return {"status": "ok", "imported_from": xml_path}
    except Exception as ex:
        return {"status": "error", "message": str(ex)}

# ------------------------------------------------------------------------------
# Диспетчер команд
# ------------------------------------------------------------------------------
COMMAND_MAP = {
    "status": action_status,
    "save": action_save,
    "compile": action_compile,
    "exec": action_exec,
    "map_io": action_map_io,
    "export": action_export,
    "import": action_import,
    "online_status": action_online_status,
    "online_login": action_online_login,
    "online_logout": action_online_logout,
    "online_control": action_online_control,
    "online_read": action_online_read,
    "online_write": action_online_write,
    "export_xml": action_export_xml,
    "import_xml": action_import_xml,
}

def dispatch_request(req):
    action = req.get("action", "")
    handler = COMMAND_MAP.get(action)
    if not handler:
        return {"status": "error", "message": "Unknown action: %s" % action}
    
    cap = OutputCapture()
    cap.start()
    try:
        resp = handler(req)
    except Exception as ex:
        resp = {"status": "error", "message": str(ex), "traceback": traceback.format_exc()}
    finally:
        log_text = cap.stop()
    
    if "log" not in resp:
        resp["log"] = log_text
    return resp

# ------------------------------------------------------------------------------
# Сетевой сервер (TcpListener HTTP/JSON)
# ------------------------------------------------------------------------------
def create_listener():
    for port in TCP_PORTS:
        try:
            listener = TcpListener(IPAddress.Any, port)
            listener.Start()
            print("Successfully bound TCP listener on port %d" % port)
            return listener, port
        except SocketException as ex:
            print("Port %d busy or access denied: %s" % (port, ex.Message))
        except Exception as ex:
            print("Could not bind port %d: %s" % (port, ex))
    return None, None

active_listener, active_port = create_listener()

def process_tcp():
    if not active_listener:
        return
    try:
        while active_listener.Pending():
            client = active_listener.AcceptTcpClient()
            client.ReceiveTimeout = 3000
            client.SendTimeout = 3000
            stream = client.GetStream()

            # Чтение заголовка HTTP
            header_lines = []
            curr_line = []
            while True:
                b = stream.ReadByte()
                if b == -1:
                    break
                ch = chr(b)
                curr_line.append(ch)
                if ch == "\n":
                    line_str = "".join(curr_line).strip()
                    curr_line = []
                    if not line_str:
                        break  # конец заголовков
                    header_lines.append(line_str)

            # Определение Content-Length
            content_length = 0
            for h in header_lines:
                if h.lower().startswith("content-length:"):
                    content_length = int(h.split(":")[1].strip())
                    break

            # Чтение тела JSON
            body_chars = []
            for _ in range(content_length):
                b = stream.ReadByte()
                if b == -1:
                    break
                body_chars.append(chr(b))
            
            raw_body = "".join(body_chars)
            req_data = {}
            if raw_body:
                try:
                    req_data = json.loads(raw_body.decode('utf-8'))
                except:
                    req_data = json.loads(raw_body)
            
            # Выполнение действия
            resp_data = dispatch_request(req_data)
            resp_json = json.dumps(resp_data, ensure_ascii=False)
            resp_bytes = System.Text.Encoding.UTF8.GetBytes(resp_json)

            # Отправка HTTP 200 OK
            http_header = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json; charset=utf-8\r\n"
                "Access-Control-Allow-Origin: *\r\n"
                "Content-Length: %d\r\n"
                "Connection: close\r\n\r\n"
            ) % len(resp_bytes)

            hdr_bytes = System.Text.Encoding.UTF8.GetBytes(http_header)
            stream.Write(hdr_bytes, 0, hdr_bytes.Length)
            stream.Write(resp_bytes, 0, resp_bytes.Length)
            stream.Flush()
            client.Close()
    except Exception as ex:
        print("TCP Process Error: %s" % ex)

# ------------------------------------------------------------------------------
# Локальный IPC файл (Фоллбэк)
# ------------------------------------------------------------------------------
def process_ipc_file():
    if not File.Exists(IPC_REQ_FILE):
        return
    try:
        text = File.ReadAllText(IPC_REQ_FILE, System.Text.Encoding.UTF8)
        File.Delete(IPC_REQ_FILE)
        req = json.loads(text)
        resp = dispatch_request(req)
        File.WriteAllText(IPC_RESP_FILE, json.dumps(resp, ensure_ascii=False), System.Text.Encoding.UTF8)
    except Exception as ex:
        print("IPC File Error: %s" % ex)

# ------------------------------------------------------------------------------
# Главный UI Timer Tick
# ------------------------------------------------------------------------------
def on_timer_tick(sender, args):
    process_tcp()
    process_ipc_file()

bridge_timer = Timer()
bridge_timer.Interval = TIMER_INTERVAL_MS
bridge_timer.Tick += on_timer_tick
bridge_timer.Start()

globals()["CODESYS_BRIDGE_TIMER"] = bridge_timer
globals()["CODESYS_TCP_LISTENER"] = active_listener

print("==================================================")
print("CODESYS Net Bridge & IPC Server is RUNNING!")
if active_port:
    print("- Network Port: %d (http://<this_pc_ip>:%d)" % (active_port, active_port))
print("- Local IPC File: %s" % IPC_REQ_FILE)
print("- Non-blocking: IDE remains 100%% interactive")
print("==================================================")
