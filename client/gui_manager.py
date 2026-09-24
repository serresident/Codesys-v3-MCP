#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
CODESYS & Abak.IDE Sync, Network Bridge & Git Manager (PyQt6 / PyQt5)
================================================================================
Адаптированная версия gui_manager_ipc.py:
- Сохраняет 100% любимого Cyberpunk-интерфейса, QSS-стилей, вкладок и функционала Git.
- Поддерживает ДВА режима связи:
  1. 🌐 Сетевой мост TCP/HTTP (порт 11888) — для удаленной инженерной станции
  2. 💻 Локальный файл IPC (codesys_ipc_req.json) — для локальной работы на одном ПК
- Добавлены функции: Чистая сборка (Clean & Build), сохранение проекта, расширенная диагностика.
================================================================================
"""

import sys
import os
import json
import socket
import subprocess
import tempfile
import time
import glob

DEFAULT_HOST = os.environ.get("ABAK_BRIDGE_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("ABAK_BRIDGE_PORT", "11888"))

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

temp_dir = tempfile.gettempdir()
req_path = os.path.join(temp_dir, "codesys_ipc_req.json")
res_path = os.path.join(temp_dir, "codesys_ipc_res.json")
alt_res_path = os.path.join(temp_dir, "codesys_ipc_resp.json")
log_path = os.path.join(temp_dir, "codesys_ipc.log")

# --- QSS Dark Cyberpunk Theme Stylesheet ---
DARK_THEME = """
QMainWindow {
    background-color: #121214;
}

QWidget {
    color: #e3e3e6;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #2d2d34;
    background-color: #18181b;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #1f1f23;
    border: 1px solid #2d2d34;
    border-bottom: none;
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
    color: #a1a1aa;
}

QTabBar::tab:hover {
    background-color: #27272a;
    color: #f4f4f5;
}

QTabBar::tab:selected {
    background-color: #18181b;
    border-color: #2d2d34;
    border-bottom: 2px solid #00f0ff;
    color: #00f0ff;
    font-weight: bold;
}

QGroupBox {
    border: 1px solid #2d2d34;
    border-radius: 8px;
    margin-top: 12px;
    font-weight: bold;
    color: #00f0ff;
    padding: 10px;
    background-color: #18181b;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    background-color: #121214;
}

QLineEdit, QComboBox {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    padding: 6px;
    color: #f4f4f5;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #00f0ff;
}

QPushButton {
    background-color: #2563eb;
    border: none;
    border-radius: 4px;
    padding: 8px 14px;
    font-weight: bold;
    color: white;
}

QPushButton:hover {
    background-color: #3b82f6;
}

QPushButton:pressed {
    background-color: #1d4ed8;
}

QPushButton:disabled {
    background-color: #3f3f46;
    color: #a1a1aa;
}

QPushButton#btn_browse {
    background-color: #3f3f46;
    color: #f4f4f5;
}

QPushButton#btn_browse:hover {
    background-color: #52525b;
}

QPushButton#btn_action_sync {
    background-color: #0d9488;
}

QPushButton#btn_action_sync:hover {
    background-color: #14b8a6;
}

QPushButton#btn_action_compile {
    background-color: #7c3aed;
}

QPushButton#btn_action_compile:hover {
    background-color: #8b5cf6;
}

QPushButton#btn_action_clean {
    background-color: #b45309;
}

QPushButton#btn_action_clean:hover {
    background-color: #d97706;
}

QPushButton#btn_git_commit {
    background-color: #10b981;
}

QPushButton#btn_git_commit:hover {
    background-color: #34d399;
}

QListWidget {
    background-color: #18181b;
    border: 1px solid #2d2d34;
    border-radius: 6px;
    padding: 5px;
    color: #e3e3e6;
}

QListWidget::item {
    padding: 6px;
    border-bottom: 1px solid #27272a;
}

QListWidget::item:hover {
    background-color: #27272a;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #3b82f6;
    color: white;
    border-radius: 4px;
}

QTextEdit, QTextBrowser {
    background-color: #09090b;
    border: 1px solid #2d2d34;
    border-radius: 6px;
    color: #e3e3e6;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}

QScrollBar:vertical {
    border: none;
    background: #18181b;
    width: 10px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #3f3f46;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #52525b;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

def send_tcp_request(host, port, req_data, timeout=15.0):
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

        sep = b"\r\n\r\n"
        idx = resp_bytes.find(sep)
        body_data = resp_bytes[idx + len(sep):] if idx != -1 else resp_bytes
        return json.loads(body_data.decode("utf-8", errors="replace"))
    finally:
        s.close()


class NetworkWorker(QtCore.QThread):
    finished_signal = Signal(dict)

    def __init__(self, host, port, req_data, timeout=30.0):
        super().__init__()
        self.host = host
        self.port = port
        self.req_data = req_data
        self.timeout = timeout

    def run(self):
        try:
            res = send_tcp_request(self.host, self.port, self.req_data, timeout=self.timeout)
            self.finished_signal.emit(res)
        except Exception as ex:
            self.finished_signal.emit({"status": "error", "success": False, "error": str(ex), "message": str(ex)})


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CODESYS & Abak.IDE Sync, Network Bridge & Git Manager")
        self.resize(1150, 780)
        self.setStyleSheet(DARK_THEME)

        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui_ipc_config.json")
        self.log_offset = 0
        self.net_worker = None

        self.poll_timer = QtCore.QTimer()
        self.poll_timer.timeout.connect(self.poll_ipc)

        self.status_timer = QtCore.QTimer()
        self.status_timer.timeout.connect(self.check_environment_status)
        self.status_timer.start(2500)
        self.waiting_for_ping = False

        self.init_ui()
        self.load_config()
        self.refresh_git_status()

    def init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # --- Sidebar / Left Panel ---
        sidebar = QtWidgets.QWidget()
        sidebar.setFixedWidth(360)
        sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)

        # 1. Режим связи и пути
        grp_paths = QtWidgets.QGroupBox("Режим связи и пути")
        paths_layout = QtWidgets.QVBoxLayout(grp_paths)
        paths_layout.setSpacing(8)

        # Селектор режима: Сеть или Локальный IPC
        lay_mode = QtWidgets.QHBoxLayout()
        lay_mode.addWidget(QtWidgets.QLabel("Режим связи:"))
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems(["🌐 Сетевой TCP/HTTP Bridge", "💻 Локальный файл IPC"])
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        lay_mode.addWidget(self.combo_mode)
        paths_layout.addLayout(lay_mode)

        # Параметры сети (IP и порт)
        self.frame_net = QtWidgets.QWidget()
        lay_net = QtWidgets.QHBoxLayout(self.frame_net)
        lay_net.setContentsMargins(0, 0, 0, 0)
        lay_net.addWidget(QtWidgets.QLabel("Хост:"))
        self.txt_net_host = QtWidgets.QLineEdit(DEFAULT_HOST)
        self.txt_net_host.setFixedWidth(130)
        lay_net.addWidget(self.txt_net_host)

        lay_net.addWidget(QtWidgets.QLabel("Порт:"))
        self.txt_net_port = QtWidgets.QLineEdit(str(DEFAULT_PORT))
        self.txt_net_port.setFixedWidth(65)
        lay_net.addWidget(self.txt_net_port)
        paths_layout.addWidget(self.frame_net)

        paths_layout.addWidget(QtWidgets.QLabel("CODESYS Project Folder or File:"))
        lay_proj = QtWidgets.QHBoxLayout()
        self.txt_project_path = QtWidgets.QLineEdit()
        btn_browse_proj = QtWidgets.QPushButton("...")
        btn_browse_proj.setObjectName("btn_browse")
        btn_browse_proj.setFixedWidth(35)
        btn_browse_proj.clicked.connect(self.browse_project_file)
        lay_proj.addWidget(self.txt_project_path)
        lay_proj.addWidget(btn_browse_proj)
        paths_layout.addLayout(lay_proj)

        paths_layout.addWidget(QtWidgets.QLabel("Structured Text (.st) Sources Directory:"))
        lay_src = QtWidgets.QHBoxLayout()
        self.txt_sources_path = QtWidgets.QLineEdit()
        btn_browse_src = QtWidgets.QPushButton("...")
        btn_browse_src.setObjectName("btn_browse")
        btn_browse_src.setFixedWidth(35)
        btn_browse_src.clicked.connect(self.browse_sources_dir)
        lay_src.addWidget(self.txt_sources_path)
        lay_src.addWidget(btn_browse_src)
        paths_layout.addLayout(lay_src)

        h_open = QtWidgets.QHBoxLayout()
        self.btn_open_src = QtWidgets.QPushButton("📂 Папка ST")
        self.btn_open_src.setObjectName("btn_browse")
        self.btn_open_src.clicked.connect(self.open_sources_dir)
        h_open.addWidget(self.btn_open_src)

        self.btn_open_ide = QtWidgets.QPushButton("💻 В Antigravity/VSCode")
        self.btn_open_ide.setObjectName("btn_browse")
        self.btn_open_ide.clicked.connect(self.open_sources_ide)
        h_open.addWidget(self.btn_open_ide)
        paths_layout.addLayout(h_open)

        sidebar_layout.addWidget(grp_paths)

        # 2. Статус окружения
        grp_status = QtWidgets.QGroupBox("Статус окружения")
        status_layout = QtWidgets.QVBoxLayout(grp_status)
        status_layout.setSpacing(6)

        self.lbl_ide_status = QtWidgets.QLabel("Abak.IDE: Проверка...")
        self.lbl_proj_status = QtWidgets.QLabel("Проект: Проверка...")
        self.lbl_script_status = QtWidgets.QLabel("Мост / IPC: Проверка...")
        
        status_layout.addWidget(self.lbl_ide_status)
        status_layout.addWidget(self.lbl_proj_status)
        status_layout.addWidget(self.lbl_script_status)

        h_ctrl_ide = QtWidgets.QHBoxLayout()
        self.btn_launch_ide = QtWidgets.QPushButton("💻 Открыть проект")
        self.btn_launch_ide.setObjectName("btn_browse")
        self.btn_launch_ide.clicked.connect(self.launch_ide_only)
        h_ctrl_ide.addWidget(self.btn_launch_ide)

        self.btn_login = QtWidgets.QPushButton("🔌 Онлайн (Login)")
        self.btn_login.setObjectName("btn_browse")
        self.btn_login.clicked.connect(self.action_online_login)
        h_ctrl_ide.addWidget(self.btn_login)

        self.btn_save_proj = QtWidgets.QPushButton("💾 Сохранить")
        self.btn_save_proj.setObjectName("btn_browse")
        self.btn_save_proj.clicked.connect(self.action_save_project)
        h_ctrl_ide.addWidget(self.btn_save_proj)
        status_layout.addLayout(h_ctrl_ide)

        sidebar_layout.addWidget(grp_status)

        # 3. Синхронизация и компиляция
        grp_actions = QtWidgets.QGroupBox("Синхронизация и компиляция")
        actions_layout = QtWidgets.QVBoxLayout(grp_actions)
        actions_layout.setSpacing(8)

        self.chk_add_context = QtWidgets.QCheckBox("Добавить сервер и контекст (.context)")
        self.chk_add_context.setChecked(True)
        self.chk_add_context.setStyleSheet("font-weight: normal; color: #e3e3e6;")
        actions_layout.addWidget(self.chk_add_context)

        self.btn_export = QtWidgets.QPushButton("⬇ Быстрый экспорт (ST + XML)")
        self.btn_export.setObjectName("btn_action_sync")
        self.btn_export.clicked.connect(lambda: self.run_action("export"))
        actions_layout.addWidget(self.btn_export)

        self.btn_import = QtWidgets.QPushButton("⬆ Мгновенный импорт в среду")
        self.btn_import.setObjectName("btn_action_sync")
        self.btn_import.clicked.connect(lambda: self.run_action("import"))
        actions_layout.addWidget(self.btn_import)

        h_xml = QtWidgets.QHBoxLayout()
        self.btn_export_xml = QtWidgets.QPushButton("📦 Экспорт XML")
        self.btn_export_xml.setObjectName("btn_browse")
        self.btn_export_xml.clicked.connect(self.action_export_xml)
        h_xml.addWidget(self.btn_export_xml)

        self.btn_import_xml = QtWidgets.QPushButton("📥 Импорт XML")
        self.btn_import_xml.setObjectName("btn_browse")
        self.btn_import_xml.clicked.connect(self.action_import_xml)
        h_xml.addWidget(self.btn_import_xml)
        actions_layout.addLayout(h_xml)

        h_compiles = QtWidgets.QHBoxLayout()
        self.btn_compile = QtWidgets.QPushButton("🔨 Сборка (Build)")
        self.btn_compile.setObjectName("btn_action_compile")
        self.btn_compile.clicked.connect(lambda: self.run_action("compile", clean=False))
        h_compiles.addWidget(self.btn_compile)

        self.btn_clean_compile = QtWidgets.QPushButton("🧹 Clean & Build")
        self.btn_clean_compile.setObjectName("btn_action_clean")
        self.btn_clean_compile.clicked.connect(lambda: self.run_action("compile", clean=True))
        h_compiles.addWidget(self.btn_clean_compile)
        actions_layout.addLayout(h_compiles)

        self.btn_tree = QtWidgets.QPushButton("🌲 Инспекция дерева проекта")
        self.btn_tree.setObjectName("btn_browse")
        self.btn_tree.clicked.connect(self.action_inspect_tree)
        actions_layout.addWidget(self.btn_tree)

        sidebar_layout.addWidget(grp_actions)
        sidebar_layout.addStretch()

        main_layout.addWidget(sidebar)

        # --- Right Panel (Tabs) ---
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Logs Console
        self.tab_logs = QtWidgets.QWidget()
        lay_tab_logs = QtWidgets.QVBoxLayout(self.tab_logs)
        lay_tab_logs.setContentsMargins(10, 10, 10, 10)
        
        self.txt_console = QtWidgets.QTextBrowser()
        self.txt_console.setOpenExternalLinks(True)
        lay_tab_logs.addWidget(self.txt_console)

        lay_console_ctrl = QtWidgets.QHBoxLayout()
        btn_clear_console = QtWidgets.QPushButton("Очистить лог")
        btn_clear_console.setFixedWidth(120)
        btn_clear_console.clicked.connect(self.txt_console.clear)
        lay_console_ctrl.addWidget(btn_clear_console)
        lay_console_ctrl.addStretch()
        lay_tab_logs.addLayout(lay_console_ctrl)

        self.tabs.addTab(self.tab_logs, "📟 Лог IPC / Моста")

        # Tab 2: Git Control
        self.tab_git = QtWidgets.QWidget()
        lay_tab_git = QtWidgets.QVBoxLayout(self.tab_git)
        lay_tab_git.setContentsMargins(10, 10, 10, 10)

        git_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        lay_tab_git.addWidget(git_splitter)

        git_left_panel = QtWidgets.QWidget()
        lay_git_left = QtWidgets.QVBoxLayout(git_left_panel)
        lay_git_left.setContentsMargins(0, 0, 0, 0)
        
        lay_git_left.addWidget(QtWidgets.QLabel("Измененные файлы (Git Status):"))
        self.lst_git_changes = QtWidgets.QListWidget()
        self.lst_git_changes.itemSelectionChanged.connect(self.show_selected_diff)
        lay_git_left.addWidget(self.lst_git_changes)

        lay_commit = QtWidgets.QVBoxLayout()
        lay_commit.setSpacing(6)
        lay_commit.addWidget(QtWidgets.QLabel("Сообщение коммита:"))
        self.txt_commit_msg = QtWidgets.QLineEdit()
        self.txt_commit_msg.setPlaceholderText("Например: Добавлен блок IPC...")
        lay_commit.addWidget(self.txt_commit_msg)

        lay_git_btns = QtWidgets.QHBoxLayout()
        self.btn_git_commit = QtWidgets.QPushButton("Зафиксировать (Commit)")
        self.btn_git_commit.setObjectName("btn_git_commit")
        self.btn_git_commit.clicked.connect(self.run_git_commit)
        
        self.btn_git_refresh = QtWidgets.QPushButton("🔄 Обновить")
        self.btn_git_refresh.setFixedWidth(90)
        self.btn_git_refresh.clicked.connect(self.refresh_git_status)

        lay_git_btns.addWidget(self.btn_git_commit)
        lay_git_btns.addWidget(self.btn_git_refresh)
        lay_commit.addLayout(lay_git_btns)

        lay_push_pull = QtWidgets.QHBoxLayout()
        self.btn_git_push = QtWidgets.QPushButton("🚀 Отправить (Push)")
        self.btn_git_push.clicked.connect(self.run_git_push)
        self.btn_git_pull = QtWidgets.QPushButton("📥 Стянуть (Pull)")
        self.btn_git_pull.clicked.connect(self.run_git_pull)
        lay_push_pull.addWidget(self.btn_git_pull)
        lay_push_pull.addWidget(self.btn_git_push)
        lay_commit.addLayout(lay_push_pull)

        lay_git_left.addLayout(lay_commit)
        git_splitter.addWidget(git_left_panel)

        git_right_panel = QtWidgets.QWidget()
        lay_git_right = QtWidgets.QVBoxLayout(git_right_panel)
        lay_git_right.setContentsMargins(0, 0, 0, 0)
        lay_git_right.addWidget(QtWidgets.QLabel("Просмотр изменений (Diff):"))
        self.txt_diff = QtWidgets.QTextBrowser()
        lay_git_right.addWidget(self.txt_diff)
        git_splitter.addWidget(git_right_panel)

        git_splitter.setStretchFactor(0, 2)
        git_splitter.setStretchFactor(1, 3)

        self.tabs.addTab(self.tab_git, "🌿 Git Версионирование")

        # Tab 3: Script Runner (Выполнение произвольных скриптов)
        self.tab_scripts = QtWidgets.QWidget()
        lay_tab_scripts = QtWidgets.QVBoxLayout(self.tab_scripts)
        lay_tab_scripts.setContentsMargins(10, 10, 10, 10)
        lay_tab_scripts.setSpacing(8)

        # Панель инструментов запуска скрипта
        lay_script_tb = QtWidgets.QHBoxLayout()
        lay_script_tb.addWidget(QtWidgets.QLabel("Шаблоны:"))
        self.combo_script_templates = QtWidgets.QComboBox()
        self.combo_script_templates.addItems([
            "--- Выберите шаблон ---",
            "1. Информация о проекте (Project Info)",
            "2. Дерево объектов Application",
            "3. Список оборудования (Device Tree)",
            "4. Онлайн статус контроллера (Online Status)",
            "5. Пользовательский расчет и возврат JSON (result = ...)"
        ])
        self.combo_script_templates.currentIndexChanged.connect(self.on_script_template_selected)
        lay_script_tb.addWidget(self.combo_script_templates)

        self.btn_load_script = QtWidgets.QPushButton("📂 Открыть .py")
        self.btn_load_script.setObjectName("btn_browse")
        self.btn_load_script.clicked.connect(self.load_script_file)
        lay_script_tb.addWidget(self.btn_load_script)

        self.btn_save_script = QtWidgets.QPushButton("💾 Сохранить .py")
        self.btn_save_script.setObjectName("btn_browse")
        self.btn_save_script.clicked.connect(self.save_script_file)
        lay_script_tb.addWidget(self.btn_save_script)

        lay_script_tb.addStretch()

        self.btn_run_script_tab = QtWidgets.QPushButton("▶ Запустить скрипт в CODESYS")
        self.btn_run_script_tab.setObjectName("btn_action_compile")
        self.btn_run_script_tab.clicked.connect(self.run_editor_script)
        lay_script_tb.addWidget(self.btn_run_script_tab)
        lay_tab_scripts.addLayout(lay_script_tb)

        # Разделитель: Редактор кода / Вывод исполнения
        script_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        
        script_edit_panel = QtWidgets.QWidget()
        lay_edit_panel = QtWidgets.QVBoxLayout(script_edit_panel)
        lay_edit_panel.setContentsMargins(0, 0, 0, 0)
        lay_edit_panel.addWidget(QtWidgets.QLabel("Код скрипта (IronPython 2.7 / ScriptEngine):"))
        self.txt_script_editor = QtWidgets.QTextEdit()
        self.txt_script_editor.setPlaceholderText("# Введите произвольный код IronPython 2.7 или выберите шаблон выше\n# В скоупе доступны: projects, system, online, active_project, params, args\n# Присвойте результат в переменную 'result = {...}', чтобы вернуть структурированный JSON!\nprint(projects.primary.get_name() if projects.primary else 'No project')")
        lay_edit_panel.addWidget(self.txt_script_editor)
        script_splitter.addWidget(script_edit_panel)

        script_out_panel = QtWidgets.QWidget()
        lay_out_panel = QtWidgets.QVBoxLayout(script_out_panel)
        lay_out_panel.setContentsMargins(0, 0, 0, 0)
        
        h_out_title = QtWidgets.QHBoxLayout()
        h_out_title.addWidget(QtWidgets.QLabel("Вывод скрипта (Stdout / Stderr / Result):"))
        btn_clear_script_out = QtWidgets.QPushButton("Очистить")
        btn_clear_script_out.setFixedWidth(80)
        btn_clear_script_out.setObjectName("btn_browse")
        btn_clear_script_out.clicked.connect(lambda: self.txt_script_output.clear())
        h_out_title.addWidget(btn_clear_script_out)
        h_out_title.addStretch()
        lay_out_panel.addLayout(h_out_title)

        self.txt_script_output = QtWidgets.QTextBrowser()
        lay_out_panel.addWidget(self.txt_script_output)
        script_splitter.addWidget(script_out_panel)

        script_splitter.setStretchFactor(0, 3)
        script_splitter.setStretchFactor(1, 2)
        lay_tab_scripts.addWidget(script_splitter)

        self.tabs.addTab(self.tab_scripts, "🐍 Скрипты (Script Runner)")

        # Tab 4: Help Section
        self.tab_help = QtWidgets.QWidget()
        lay_tab_help = QtWidgets.QVBoxLayout(self.tab_help)
        lay_tab_help.setContentsMargins(10, 10, 10, 10)
        self.txt_help = QtWidgets.QTextBrowser()
        self.txt_help.setOpenExternalLinks(True)
        lay_tab_help.addWidget(self.txt_help)
        self.tabs.addTab(self.tab_help, "❓ Справка")
        self.load_help_content()

    def on_mode_changed(self, idx):
        is_net = (idx == 0)
        self.frame_net.setVisible(is_net)
        self.check_environment_status()

    # --- Config Management ---
    def load_config(self):
        default_proj = ""
        default_src = ""

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.txt_project_path.setText(data.get("project_path", default_proj))
                    self.txt_sources_path.setText(data.get("sources_path", default_src))
                    self.chk_add_context.setChecked(data.get("add_context", True))
                    self.txt_net_host.setText(data.get("net_host", DEFAULT_HOST))
                    self.txt_net_port.setText(str(data.get("net_port", DEFAULT_PORT)))
                    self.combo_mode.setCurrentIndex(data.get("mode_index", 0))
                    return
            except:
                pass

        self.txt_project_path.setText(default_proj)
        self.txt_sources_path.setText(default_src)
        self.chk_add_context.setChecked(True)

    def save_config(self):
        data = {
            "project_path": self.txt_project_path.text(),
            "sources_path": self.txt_sources_path.text(),
            "add_context": self.chk_add_context.isChecked(),
            "net_host": self.txt_net_host.text(),
            "net_port": self.txt_net_port.text(),
            "mode_index": self.combo_mode.currentIndex()
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.write_log(f"<span style='color:#ef4444;'>[ERROR] Failed to save config: {e}</span>")

    # --- Path Dialogs ---
    def browse_project_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Выберите файл проекта CODESYS", "", "CODESYS Projects (*.project);;All Files (*)"
        )
        if not file_path:
            file_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Или выберите папку проекта")
        if file_path:
            self.txt_project_path.setText(os.path.normpath(file_path))
            self.save_config()

    def browse_sources_dir(self):
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите папку с исходниками Structured Text (.st)")
        if dir_path:
            self.txt_sources_path.setText(os.path.normpath(dir_path))
            self.save_config()
            self.refresh_git_status()

    def open_sources_dir(self):
        dir_path = self.txt_sources_path.text().strip()
        if os.path.exists(dir_path):
            try:
                os.startfile(dir_path)
            except Exception as e:
                self.write_log(f"<span style='color:#ef4444;'>Не удалось открыть папку: {e}</span>")
        else:
            QtWidgets.QMessageBox.warning(self, "Предупреждение", "Указанная папка ST не существует!")

    def open_sources_ide(self):
        dir_path = self.txt_sources_path.text().strip()
        if os.path.exists(dir_path):
            try:
                user_home = os.path.expanduser("~")
                antigravity_path = os.path.join(user_home, "AppData", "Local", "Programs", "Antigravity IDE", "Antigravity IDE.exe")
                if os.path.exists(antigravity_path):
                    subprocess.Popen(f'start "" "{antigravity_path}" "{dir_path}"', shell=True)
                else:
                    subprocess.Popen(f'start "" code "{dir_path}"', shell=True)
            except Exception as e:
                self.write_log(f"<span style='color:#ef4444;'>Не удалось открыть в IDE: {e}</span>")
        else:
            QtWidgets.QMessageBox.warning(self, "Предупреждение", "Указанная папка ST не существует!")

    def write_log(self, text):
        import re
        formatted_line = text
        if "SCRIPT_SUCCESS" in text or "УСПЕШНО" in text or "completed successfully" in text:
            formatted_line = f"<span style='color:#10b981; font-weight:bold;'>{text}</span>"
        elif "SCRIPT_ERROR" in text or "ERROR" in text or "failed" in text or "Exception" in text or "ОШИБКА" in text:
            formatted_line = f"<span style='color:#ef4444; font-weight:bold;'>{text}</span>"
        elif "WARN" in text or "WARNING" in text:
            formatted_line = f"<span style='color:#f59e0b;'>{text}</span>"
        elif "DEBUG" in text:
            formatted_line = f"<span style='color:#06b6d4;'>{text}</span>"
        
        formatted_line = re.sub(
            r'(file:///[^\s<>\'\"]+)',
            r'<a href="\1" style="color:#00f0ff; text-decoration:underline;">\1</a>',
            formatted_line
        )
        self.txt_console.append(formatted_line)
        self.txt_console.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def set_buttons_enabled(self, enabled):
        self.btn_export.setEnabled(enabled)
        self.btn_import.setEnabled(enabled)
        self.btn_export_xml.setEnabled(enabled)
        self.btn_import_xml.setEnabled(enabled)
        self.btn_login.setEnabled(enabled)
        self.btn_compile.setEnabled(enabled)
        self.btn_clean_compile.setEnabled(enabled)
        self.btn_tree.setEnabled(enabled)
        self.btn_git_commit.setEnabled(enabled)
        self.btn_git_push.setEnabled(enabled)
        self.btn_git_pull.setEnabled(enabled)

    def action_online_login(self):
        self.tabs.setCurrentIndex(0)
        self.write_log("\n<span style='color:#00f0ff; font-weight:bold;'>=== 🔌 ПОДКЛЮЧЕНИЕ К ПЛК (ONLINE LOGIN) ===</span>")
        self.run_action("online_login")

    def action_export_xml(self):
        self.tabs.setCurrentIndex(0)
        self.write_log("\n<span style='color:#00f0ff; font-weight:bold;'>=== 📦 ЭКСПОРТ PLCOPEN XML ===</span>")
        self.run_action("export_xml")

    def action_import_xml(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Выберите файл PLCopen XML для импорта", self.txt_sources_path.text(), "PLCopen XML (*.xml);;All Files (*)"
        )
        if file_path:
            self.tabs.setCurrentIndex(0)
            self.write_log(f"\n<span style='color:#00f0ff; font-weight:bold;'>=== 📥 ИМПОРТ PLCOPEN XML: {file_path} ===</span>")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    xml_content = f.read()
                self.run_action("import_xml", code=xml_content)
            except Exception as e:
                self.write_log(f"<span style='color:#ef4444;'>Ошибка чтения XML: {e}</span>")

    def resolve_project_path(self, provided):
        if os.path.isdir(provided):
            project_files = []
            try:
                for file in os.listdir(provided):
                    if file.endswith('.project'):
                        fpath = os.path.join(provided, file)
                        project_files.append((fpath, os.path.getmtime(fpath)))
                project_files.sort(key=lambda x: x[1], reverse=True)
                if project_files:
                    return project_files[0][0]
            except:
                pass
        return provided

    def launch_ide_only(self):
        proj_path = self.txt_project_path.text().strip()
        resolved_proj = self.resolve_project_path(proj_path) if proj_path else ""
        
        possible_exes = [
            r"C:\Program Files (x86)\Abak.IDE.1.0.0\CODESYS\Common\abak.ide.exe",
            r"C:\Program Files\CODESYS 3.5.21.0\CODESYS\Common\CODESYS.exe",
            r"C:\Program Files\CODESYS 3.5.19.0\CODESYS\Common\CODESYS.exe",
            r"C:\Program Files (x86)\3S CODESYS\CODESYS\Common\CODESYS.exe"
        ]
        ide_exe = None
        for p in possible_exes:
            if os.path.exists(p):
                ide_exe = p
                break
                
        if not ide_exe:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Исполняемый файл Abak.IDE / CODESYS не найден по стандартным путям.")
            return

        profile = "Abak.IDE V1.0.0.0" if "abak" in ide_exe.lower() else ""
        server_script = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server", "codesys_bridge_server.py"))
        
        cmd_parts = [f'start "" "{ide_exe}"']
        if profile:
            cmd_parts.append(f'--profile="{profile}"')
        if resolved_proj and os.path.exists(resolved_proj):
            cmd_parts.append(f'"{resolved_proj}"')
        cmd_parts.append(f'--runscript="{server_script}"')
        
        cmd = " ".join(cmd_parts)
        try:
            subprocess.Popen(cmd, shell=True)
            self.write_log(f"<span style='color:#00f0ff;'>Запуск среды с автоматическим стартом моста...</span>\nКоманда: {cmd}")
        except Exception as e:
            self.write_log(f"<span style='color:#ef4444;'>Ошибка запуска: {e}</span>")

    def action_save_project(self):
        self.run_action("save")

    def action_inspect_tree(self):
        self.tabs.setCurrentIndex(0)
        self.write_log("\n<span style='color:#00f0ff; font-weight:bold;'>=== ИНСПЕКЦИЯ ДЕРЕВА ПРОЕКТА ===</span>")
        code = """
proj = script_engine.projects.primary
app = proj.find('Application', True)[0]
print('=== ОБЪЕКТЫ APPLICATION ===')
stack = [('', app)]
while stack:
    p, n = stack.pop(0)
    for c in n.get_children(False):
        curr = p + '/' + c.get_name()
        print('  ' + curr)
        stack.append((curr, c))

print('\\n=== АППАРАТНЫЕ УСТРОЙСТВА ===')
devs = proj.find('Device', True)
if devs:
    dev_stack = [('', devs[0])]
    while dev_stack:
        p, n = dev_stack.pop(0)
        for c in n.get_children(False):
            curr = p + '/' + c.get_name()
            print('  ' + curr)
            dev_stack.append((curr, c))
"""
        self.run_action("exec", code=code)

    # --- Управление вкладкой запуска скриптов ---
    def on_script_template_selected(self, idx):
        templates = {
            1: (
                "# 1. Информация об активном проекте\n"
                "proj = projects.primary\n"
                "if proj:\n"
                "    print('Проект: ' + str(proj.get_name()))\n"
                "    print('Путь: ' + str(proj.path))\n"
                "    print('Модифицирован (dirty): ' + str(proj.is_dirty))\n"
                "    result = {'name': proj.get_name(), 'path': proj.path, 'is_dirty': proj.is_dirty}\n"
                "else:\n"
                "    print('Нет активного открытого проекта')\n"
                "    result = {'error': 'No active project'}\n"
            ),
            2: (
                "# 2. Дерево объектов Application\n"
                "proj = projects.primary\n"
                "apps = proj.find('Application', True)\n"
                "if apps:\n"
                "    app = apps[0]\n"
                "    print('Application: ' + app.get_name())\n"
                "    for obj in app.get_children(True):\n"
                "        print('  - ' + obj.get_name() + ' [' + str(obj.type) + ']')\n"
                "else:\n"
                "    print('Application не найден')\n"
            ),
            3: (
                "# 3. Список оборудования (Device Tree)\n"
                "proj = projects.primary\n"
                "devs = proj.find('Device', True)\n"
                "if devs:\n"
                "    dev = devs[0]\n"
                "    print('Главное устройство: ' + dev.get_name())\n"
                "    for d in dev.get_children(True):\n"
                "        print('  - ' + d.get_name() + ' [' + str(d.type) + ']')\n"
                "else:\n"
                "    print('Устройства Device не найдены')\n"
            ),
            4: (
                "# 4. Онлайн статус контроллера\n"
                "if online:\n"
                "    print('Online state: ' + str(online.current_state))\n"
                "    print('Is logged in: ' + str(online.is_logged_in))\n"
                "    result = {'state': str(online.current_state), 'is_logged_in': online.is_logged_in}\n"
                "else:\n"
                "    print('Онлайн интерфейс недоступен')\n"
            ),
            5: (
                "# 5. Пользовательский расчет и возврат структурированного JSON\n"
                "proj = projects.primary\n"
                "objs = proj.find('', True) if proj else []\n"
                "print('Всего объектов в проекте: ' + str(len(objs)))\n"
                "result = {\n"
                "    'total_objects': len(objs),\n"
                "    'timestamp': str(System.DateTime.Now),\n"
                "    'params_received': params\n"
                "}\n"
            )
        }
        code = templates.get(idx)
        if code:
            self.txt_script_editor.setText(code)

    def load_script_file(self):
        fpath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Выберите файл Python скрипта", "", "Python Script (*.py);;All Files (*)"
        )
        if fpath:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    self.txt_script_editor.setText(f.read())
            except Exception as ex:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удалось прочитать файл:\n%s" % ex)

    def save_script_file(self):
        fpath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Сохранить Python скрипт", "custom_script.py", "Python Script (*.py);;All Files (*)"
        )
        if fpath:
            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(self.txt_script_editor.toPlainText())
            except Exception as ex:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удалось сохранить файл:\n%s" % ex)

    def run_editor_script(self):
        code = self.txt_script_editor.toPlainText().strip()
        if not code:
            QtWidgets.QMessageBox.information(self, "Инфо", "Введите код скрипта для выполнения.")
            return
        self.txt_script_output.clear()
        self.txt_script_output.append("<span style='color:#00f0ff;'>▶ Отправка скрипта на исполнение в среду...</span>\n")
        self.run_action("exec", code=code, switch_tab=False)

    # --- Проверка статуса окружения ---
    def check_environment_status(self):
        is_net = (self.combo_mode.currentIndex() == 0)
        
        if is_net:
            # Сетевой опрос через TCP/HTTP
            host = self.txt_net_host.text().strip()
            port = int(self.txt_net_port.text().strip() or "11888")
            
            def check_thread():
                try:
                    res = send_tcp_request(host, port, {"action": "status"}, timeout=2.0)
                    return True, res
                except Exception as ex:
                    return False, str(ex)

            # Выполняем быстрый опрос в неблокирующем потоке
            def on_net_status_done(ok, data):
                if ok and isinstance(data, dict):
                    proj_name = data.get("status", {}).get("project_name") or os.path.basename(data.get("project_path", "")) or "Открыт"
                    self.lbl_ide_status.setText(f"Abak.IDE: {host}:{port} 🟢")
                    self.lbl_ide_status.setStyleSheet("color: #10b981; font-weight: bold;")
                    self.lbl_proj_status.setText(f"Проект: {proj_name} 🟢")
                    self.lbl_proj_status.setStyleSheet("color: #10b981; font-weight: bold;")
                    self.lbl_script_status.setText("Сетевой Мост: Активен 🟢")
                    self.lbl_script_status.setStyleSheet("color: #10b981; font-weight: bold;")
                else:
                    self.lbl_ide_status.setText(f"Abak.IDE: Нет ответа 🔴")
                    self.lbl_ide_status.setStyleSheet("color: #ef4444; font-weight: bold;")
                    self.lbl_proj_status.setText("Проект: Неизвестно 🔴")
                    self.lbl_proj_status.setStyleSheet("color: #ef4444; font-weight: bold;")
                    self.lbl_script_status.setText("Сетевой Мост: Офлайн 🔴")
                    self.lbl_script_status.setStyleSheet("color: #ef4444; font-weight: bold;")

            worker = NetworkStatusChecker(host, port)
            worker.done_signal.connect(on_net_status_done)
            worker.start()
            self._status_worker = worker

        else:
            # Классический опрос локальных процессов и файла .~u
            ide_running = False
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq abak.ide.exe", "/NH"], capture_output=True, text=True, startupinfo=startupinfo, timeout=1.0)
                if "abak.ide.exe" in res.stdout.lower():
                    ide_running = True
            except Exception:
                pass

            proj_path = self.txt_project_path.text().strip()
            resolved = self.resolve_project_path(proj_path)
            proj_locked = os.path.exists(resolved + ".~u") if (resolved and os.path.exists(resolved)) else False

            if ide_running:
                self.lbl_ide_status.setText("Abak.IDE: Запущена 🟢")
                self.lbl_ide_status.setStyleSheet("color: #10b981; font-weight: bold;")
            else:
                self.lbl_ide_status.setText("Abak.IDE: Не запущена 🔴")
                self.lbl_ide_status.setStyleSheet("color: #ef4444; font-weight: bold;")

            if proj_locked:
                self.lbl_proj_status.setText("Проект: Открыт 🟢")
                self.lbl_proj_status.setStyleSheet("color: #10b981; font-weight: bold;")
            else:
                self.lbl_proj_status.setText("Проект: Не открыт 🔴")
                self.lbl_proj_status.setStyleSheet("color: #ef4444; font-weight: bold;")

            if ide_running and proj_locked:
                self.lbl_script_status.setText("IPC файл: Готов 🟢")
                self.lbl_script_status.setStyleSheet("color: #10b981; font-weight: bold;")
            else:
                self.lbl_script_status.setText("IPC файл: Нет среды 🔴")
                self.lbl_script_status.setStyleSheet("color: #ef4444; font-weight: bold;")

    # --- Диспетчеризация действий (Сеть или Файл) ---
    def run_action(self, action, clean=False, code=None, switch_tab=True):
        self.save_config()
        if switch_tab:
            self.tabs.setCurrentIndex(0)
        is_net = (self.combo_mode.currentIndex() == 0)

        if is_net:
            self.run_network_action(action, clean=clean, code=code)
        else:
            self.run_file_ipc_action(action, clean=clean, code=code)

    def run_network_action(self, action, clean=False, code=None):
        host = self.txt_net_host.text().strip()
        port = int(self.txt_net_port.text().strip() or "11888")
        src_dir = self.txt_sources_path.text().strip()

        self.write_log(f"\n<span style='color:#00f0ff; font-weight:bold;'>=== 🌐 СЕТЕВАЯ ОПЕРАЦИЯ: {action.upper()} ({host}:{port}) ===</span>")
        self.set_buttons_enabled(False)

        req_data = {"action": action, "add_context": self.chk_add_context.isChecked()}
        if action == "compile":
            req_data["clean"] = clean
        elif action == "exec":
            req_data["code"] = code
        elif action == "import_xml":
            req_data["xml"] = code
        elif action == "online_login":
            req_data["change_option"] = "Try"
        elif action == "import":
            files_data = {}
            for st_file in glob.glob(os.path.join(src_dir, "**", "*.st"), recursive=True):
                rel = os.path.relpath(st_file, src_dir).replace(os.sep, "/")
                with open(st_file, "r", encoding="utf-8") as f:
                    content = f.read()
                decl, impl = "", ""
                guid = None
                for line in content.splitlines():
                    if line.startswith("// @OBJECT_ID:"):
                        guid = line.split(":", 1)[1].strip()
                        break
                if "// @IMPLEMENTATION" in content:
                    parts = content.split("// @IMPLEMENTATION")
                    decl_raw = parts[0].replace("// @DECLARATION", "").strip()
                    decl = "\n".join([l for l in decl_raw.splitlines() if not l.startswith("// @OBJECT_ID:")]).strip()
                    impl = parts[1].strip()
                else:
                    decl_raw = content.strip()
                    decl = "\n".join([l for l in decl_raw.splitlines() if not l.startswith("// @OBJECT_ID:")]).strip()
                files_data[rel] = {"declaration": decl, "implementation": impl, "guid": guid}
            req_data["files"] = files_data
            self.write_log(f"Подготовлено {len(files_data)} файлов для передачи в среду...")

        def on_net_done(res):
            self.set_buttons_enabled(True)
            if res.get("log"):
                self.write_log(res["log"].strip())

            if res.get("status") == "error":
                self.write_log(f"<span style='color:#ef4444; font-weight:bold;'>ОШИБКА: {res.get('message', res.get('error'))}</span>")
                return

            if action == "export":
                objs = res.get("objects", {})
                count = 0
                os.makedirs(src_dir, exist_ok=True)

                # Сохранение project_sources.xml
                xml_content = res.get("xml")
                if xml_content:
                    xml_file = os.path.join(src_dir, "project_sources.xml")
                    try:
                        with open(xml_file, "w", encoding="utf-8") as f:
                            f.write(xml_content)
                        self.write_log(f"<span style='color:#10b981;'>✓ Сохранен PLCopen XML: {xml_file}</span>")
                    except Exception as ex:
                        self.write_log(f"<span style='color:#ef4444;'>Ошибка сохранения XML: {ex}</span>")

                    if self.chk_add_context.isChecked():
                        ctx_dir = os.path.join(src_dir, ".context")
                        os.makedirs(ctx_dir, exist_ok=True)
                        try:
                            with open(os.path.join(ctx_dir, "project_sources.xml"), "w", encoding="utf-8") as f:
                                f.write(xml_content)
                            self.write_log(f"<span style='color:#06b6d4;'>✓ Скопирован в контекст: {os.path.join(ctx_dir, 'project_sources.xml')}</span>")
                        except Exception as ex:
                            pass

                for rel_path, data in objs.items():
                    file_path = os.path.join(src_dir, rel_path.replace("/", os.sep) + ".st")
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "w", encoding="utf-8") as f:
                        if data.get("guid"):
                            f.write(f"// @OBJECT_ID: {data['guid']}\n")
                        decl = data.get("declaration", "").strip()
                        impl = data.get("implementation", "").strip()
                        if decl: f.write("// @DECLARATION\n" + decl + "\n\n")
                        if impl: f.write("// @IMPLEMENTATION\n" + impl + "\n")
                    count += 1
                self.write_log(f"\n<span style='color:#10b981; font-weight:bold;'>=== УСПЕШНО ЭКСПОРТИРОВАНО {count} ОБЪЕКТОВ И PLCOPEN XML В {src_dir} ===</span>")

            elif action == "export_xml":
                xml_content = res.get("xml")
                if xml_content:
                    os.makedirs(src_dir, exist_ok=True)
                    xml_file = os.path.join(src_dir, "project_sources.xml")
                    with open(xml_file, "w", encoding="utf-8") as f:
                        f.write(xml_content)
                    self.write_log(f"\n<span style='color:#10b981; font-weight:bold;'>=== PLCOPEN XML УСПЕШНО СОХРАНЕН: {xml_file} ===</span>")
                    if self.chk_add_context.isChecked():
                        ctx_dir = os.path.join(src_dir, ".context")
                        os.makedirs(ctx_dir, exist_ok=True)
                        with open(os.path.join(ctx_dir, "project_sources.xml"), "w", encoding="utf-8") as f:
                            f.write(xml_content)
                        self.write_log(f"<span style='color:#06b6d4;'>✓ Скопирован в контекст: {os.path.join(ctx_dir, 'project_sources.xml')}</span>")
                else:
                    self.write_log("<span style='color:#ef4444;'>XML не получен от сервера</span>")

            elif action == "import_xml":
                self.write_log("\n<span style='color:#10b981; font-weight:bold;'>=== PLCOPEN XML УСПЕШНО ИМПОРТИРОВАН В ПРОЕКТ ===</span>")
                self.write_log("<span style='color:#f59e0b;'>Подсказка: закройте и откройте дерево проекта в Abak.IDE для обновления.</span>")

            elif action == "online_login":
                is_logged = res.get("is_logged_in", False)
                state = res.get("application_state", "unknown")
                col = "#10b981" if is_logged else "#ef4444"
                self.write_log(f"\n<span style='color:{col}; font-weight:bold;'>=== ОНЛАЙН СТАТУС: Logged In={is_logged}, State={state} ===</span>")

            elif action == "import":
                results = res.get("results", {})
                for name, st in results.items():
                    col = "#10b981" if ("Updated" in st or "Created" in st) else "#f59e0b"
                    self.write_log(f"  - <span style='color:{col};'>{name}: {st}</span>")
                self.write_log(f"\n<span style='color:#10b981; font-weight:bold;'>=== ИМПОРТ ЗАВЕРШЕН, ПРОЕКТ СОХРАНЕН ===</span>")
                self.write_log("<span style='color:#f59e0b;'>Подсказка: если вкладки были открыты в Abak.IDE, закройте их и откройте заново из дерева.</span>")

            elif action == "compile":
                success = res.get("success", False)
                errs = res.get("errors_count", 0)
                warns = res.get("warnings_count", 0)
                for m in res.get("messages", []):
                    sev = m.get("severity", "")
                    txt = m.get("text", "")
                    col = "#ef4444" if "Error" in sev else ("#f59e0b" if "Warning" in sev else "#61afef")
                    self.write_log(f"  <span style='color:{col};'>[{sev}] {txt}</span>")

                if success or errs == 0:
                    self.write_log(f"\n<span style='color:#10b981; font-weight:bold;'>=== КОМПИЛЯЦИЯ УСПЕШНО ЗАВЕРШЕНА (0 ОШИБОК, {warns} ПРЕДУПРЕЖДЕНИЙ) ===</span>")
                else:
                    self.write_log(f"\n<span style='color:#ef4444; font-weight:bold;'>=== НАЙДЕНЫ ОШИБКИ СБОРКИ ({errs} ОШИБОК, {warns} ПРЕДУПРЕЖДЕНИЙ) ===</span>")

            elif action == "save":
                self.write_log(f"\n<span style='color:#10b981; font-weight:bold;'>=== {res.get('message', 'Проект успешно сохранен')} ===</span>")

            elif action == "exec":
                out_txt = res.get("log", "").strip()
                if "result" in res:
                    res_json = json.dumps(res["result"], indent=2, ensure_ascii=False)
                    out_txt += f"\n\n=== РЕЗУЛЬТАТ (JSON) ===\n{res_json}"
                    self.write_log(f"\n<span style='color:#00f0ff; font-weight:bold;'>=== РЕЗУЛЬТАТ СКРИПТА (JSON) ===</span>\n<pre>{res_json}</pre>")
                if hasattr(self, "txt_script_output") and out_txt:
                    self.txt_script_output.append(f"<pre style='color:#e3e3e6;'>{out_txt}</pre>")

            self.refresh_git_status()

        self.net_worker = NetworkWorker(host, port, req_data, timeout=90.0)
        self.net_worker.finished_signal.connect(on_net_done)
        self.net_worker.start()

    def run_file_ipc_action(self, action, clean=False, code=None):
        self.write_log(f"\n<span style='color:#00f0ff; font-weight:bold;'>=== 💻 ЛОКАЛЬНАЯ IPC ОПЕРАЦИЯ: {action.upper()} ===</span>")
        if os.path.exists(res_path):
            try: os.remove(res_path)
            except: pass
        if os.path.exists(alt_res_path):
            try: os.remove(alt_res_path)
            except: pass
        if os.path.exists(log_path):
            try: os.remove(log_path)
            except: pass
        
        req_data = {
            "action": action,
            "sources_path": self.txt_sources_path.text(),
            "add_context": self.chk_add_context.isChecked(),
            "clean": clean
        }
        if code:
            req_data["code"] = code
        
        try:
            with open(req_path, "w", encoding="utf-8") as f:
                json.dump(req_data, f)
        except Exception as e:
            self.write_log(f"ОШИБКА записи запроса IPC: {e}")
            return

        self.set_buttons_enabled(False)
        self.log_offset = 0
        self.poll_timer.start(250)

    def poll_ipc(self):
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    file_len = os.path.getsize(log_path)
                    if file_len < self.log_offset:
                        self.log_offset = 0
                    f.seek(self.log_offset)
                    new_data = f.read()
                    self.log_offset = f.tell()
                if new_data:
                    self.write_log(new_data.strip())
            except Exception:
                pass

        target_res = res_path if os.path.exists(res_path) else (alt_res_path if os.path.exists(alt_res_path) else None)
        if target_res:
            self.poll_timer.stop()
            time.sleep(0.1)
            try:
                with open(target_res, "r", encoding="utf-8") as f:
                    res = json.load(f)
                success = res.get("success", False) or res.get("status") == "ok"
                error = res.get("error", res.get("message", ""))
                if "result" in res:
                    res_json = json.dumps(res["result"], indent=2, ensure_ascii=False)
                    self.write_log(f"\n<span style='color:#00f0ff; font-weight:bold;'>=== РЕЗУЛЬТАТ СКРИПТА (JSON) ===</span>\n<pre>{res_json}</pre>")
                if hasattr(self, "txt_script_output"):
                    out_txt = res.get("log", "").strip()
                    if "result" in res:
                        out_txt += f"\n\n=== РЕЗУЛЬТАТ (JSON) ===\n{json.dumps(res['result'], indent=2, ensure_ascii=False)}"
                    if out_txt:
                        self.txt_script_output.append(f"<pre style='color:#e3e3e6;'>{out_txt}</pre>")
                if success:
                    self.write_log("\n<span style='color:#10b981; font-weight:bold;'>=== IPC ОПЕРАЦИЯ ВЫПОЛНЕНА УСПЕШНО ===</span>")
                else:
                    self.write_log(f"\n<span style='color:#ef4444; font-weight:bold;'>=== ОШИБКА ВНУТРИ IDE: {error} ===</span>")
            except Exception as e:
                self.write_log(f"\n<span style='color:#ef4444; font-weight:bold;'>=== ОШИБКА ЧТЕНИЯ ОТВЕТА IPC: {e} ===</span>")
            finally:
                try: os.remove(res_path)
                except: pass
                try: os.remove(alt_res_path)
                except: pass
                try: os.remove(log_path)
                except: pass
                self.set_buttons_enabled(True)
                self.refresh_git_status()

    # --- Git Functionality ---
    def get_git_repo_path(self):
        repo_dir = self.txt_sources_path.text().strip()
        while repo_dir and not os.path.exists(os.path.join(repo_dir, ".git")):
            parent = os.path.dirname(repo_dir)
            if parent == repo_dir:
                break
            repo_dir = parent

        if repo_dir and os.path.exists(os.path.join(repo_dir, ".git")):
            return repo_dir

        bridge_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if os.path.exists(os.path.join(bridge_root, ".git")):
            return bridge_root
        return os.path.abspath(self.txt_sources_path.text().strip() or os.getcwd())

    def refresh_git_status(self):
        self.lst_git_changes.clear()
        self.txt_diff.clear()
        
        repo_dir = self.get_git_repo_path()

        cmd = ["git", "status", "--porcelain"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', cwd=repo_dir, shell=True)
            if result.returncode == 0:
                lines = result.stdout.splitlines()
                if not lines:
                    self.lst_git_changes.addItem("Нет измененных файлов (Git репозиторий чист)")
                    return
                for line in lines:
                    if len(line) > 3:
                        status = line[:2].strip()
                        filepath = line[3:]
                        item = QtWidgets.QListWidgetItem(f"[{status}] {filepath}")
                        item.setData(QtCore.Qt.ItemDataRole.UserRole, filepath)
                        self.lst_git_changes.addItem(item)
            else:
                self.lst_git_changes.addItem("Ошибка при выполнении git status")
        except Exception as e:
            self.lst_git_changes.addItem(f"Ошибка проверки Git: {e}")

    def show_selected_diff(self):
        self.txt_diff.clear()
        selected_items = self.lst_git_changes.selectedItems()
        if not selected_items:
            return
        
        filepath = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        if not filepath:
            return

        repo_dir = self.get_git_repo_path()

        cmd = ["git", "diff", "--", filepath]
        display_status = selected_items[0].text()
        if "[??]" in display_status:
            cmd = ["git", "diff", "--no-index", "NUL", filepath]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', cwd=repo_dir, shell=True)
            diff_text = result.stdout
            if not diff_text and "[??]" in display_status:
                abs_file_path = os.path.join(repo_dir, filepath)
                if os.path.exists(abs_file_path):
                    try:
                        with open(abs_file_path, "r", encoding="utf-8") as f:
                            diff_text = "".join(f"+ {line}" for line in f.readlines())
                    except:
                        diff_text = "Не удалось прочитать содержимое нового файла."
            
            if not diff_text:
                self.txt_diff.setHtml("<span style='color:#a1a1aa;'>Нет изменений в выбранном файле.</span>")
                return

            html_lines = []
            for line in diff_text.splitlines():
                escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                if escaped.startswith("+") and not escaped.startswith("+++"):
                    html_lines.append(f"<span style='color:#10b981; background-color:#064e3b;'>{escaped}</span>")
                elif escaped.startswith("-") and not escaped.startswith("---"):
                    html_lines.append(f"<span style='color:#ef4444; background-color:#7f1d1d;'>{escaped}</span>")
                elif escaped.startswith("@@"):
                    html_lines.append(f"<span style='color:#3b82f6; font-weight:bold;'>{escaped}</span>")
                else:
                    html_lines.append(escaped)

            self.txt_diff.setHtml("<br>".join(html_lines))
        except Exception as e:
            self.txt_diff.setHtml(f"<span style='color:#ef4444;'>Ошибка при формировании diff: {e}</span>")

    def run_git_commit(self):
        commit_msg = self.txt_commit_msg.text().strip()
        if not commit_msg:
            QtWidgets.QMessageBox.warning(self, "Предупреждение", "Введите сообщение коммита перед фиксацией!")
            return

        self.tabs.setCurrentIndex(0)
        self.txt_console.clear()
        self.write_log("=== ФИКСАЦИЯ ИЗМЕНЕНИЙ В GIT ===")

        repo_dir = self.get_git_repo_path()
        subprocess.run(["git", "add", "."], capture_output=True, text=True, cwd=repo_dir, shell=True)
        res = subprocess.run(["git", "commit", "-m", f'"{commit_msg}"'], capture_output=True, text=True, cwd=repo_dir, shell=True)
        self.write_log(res.stdout)
        self.write_log(res.stderr)
        
        if res.returncode == 0:
            self.write_log("\n=== КОММИТ УСПЕШНО СОЗДАН ===")
            self.txt_commit_msg.clear()
        else:
            self.write_log("\n=== ОШИБКА СОЗДАНИЯ КОММИТА ===")
        self.refresh_git_status()

    def run_git_push(self):
        self.tabs.setCurrentIndex(0)
        self.txt_console.clear()
        self.write_log("=== ОТПРАВКА ИЗМЕНЕНИЙ (PUSH) ===")
        repo_dir = self.get_git_repo_path()
        res = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=repo_dir, shell=True)
        self.write_log(res.stdout)
        self.write_log(res.stderr)
        self.refresh_git_status()

    def run_git_pull(self):
        self.tabs.setCurrentIndex(0)
        self.txt_console.clear()
        self.write_log("=== ПОЛУЧЕНИЕ ИЗМЕНЕНИЙ (PULL) ===")
        repo_dir = self.get_git_repo_path()
        res = subprocess.run(["git", "pull"], capture_output=True, text=True, cwd=repo_dir, shell=True)
        self.write_log(res.stdout)
        self.write_log(res.stderr)
        self.refresh_git_status()

    def load_help_content(self):
        help_html = """
        <h1 style="color:#00f0ff; margin-bottom:5px;">CODESYS & Abak.IDE Automation Manager</h1>
        <p style="color:#a1a1aa;">Универсальный менеджер синхронизации исходных кодов с открытым проектом в среде Abak.IDE.</p>
        <hr style="border: 0; border-top: 1px solid #2d2d34; margin: 15px 0;">

        <h2 style="color:#3b82f6; margin-top:15px;">🌐 Сетевой режим (TCP/HTTP Bridge)</h2>
        <p>Идеально подходит для работы по локальной сети, когда среда Abak.IDE открыта на отдельном инженерном ПК (например, <code>192.168.1.100</code>):</p>
        <ul>
            <li>В Abak.IDE на инженерном ПК запустите скрипт: <b>Tools -> Scripting -> Run Script... -> codesys_bridge_server.py</b>.</li>
            <li>Сервер запустится на порту <b>11888</b> в неблокирующем UI-режиме.</li>
            <li>В этом менеджере выберите режим <b>«🌐 Сетевой TCP/HTTP Bridge»</b>, укажите IP и нажмите нужную команду.</li>
        </ul>

        <h2 style="color:#f59e0b; margin-top:20px;">💻 Локальный IPC режим (файл обмена)</h2>
        <p>Используется, когда этот менеджер и Abak.IDE запущены на одном и том же ПК через <code>codesys_ipc_req.json</code>.</p>

        <h2 style="color:#10b981; margin-top:20px;">🌿 Управление версиями (Git)</h2>
        <p>Вкладка <b>Git Версионирование</b> позволяет в реальном времени просматривать статус файлов, видеть цветной Diff, создавать коммиты, отправлять (Push) и стягивать (Pull) изменения.</p>
        """
        self.txt_help.setHtml(help_html)


class NetworkStatusChecker(QtCore.QThread):
    done_signal = Signal(bool, object)

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port

    def run(self):
        try:
            res = send_tcp_request(self.host, self.port, {"action": "status"}, timeout=2.0)
            self.done_signal.emit(True, res)
        except Exception as ex:
            self.done_signal.emit(False, str(ex))


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
