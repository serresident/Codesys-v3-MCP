# Abak.IDE & CODESYS V3.5 Automation Bridge
**Выделенный проект и инструмент сетевого взаимодействия с Abak.IDE (CODESYS V3.5 ScriptEngine) в реальном времени**

---

## 1. Назначение и контекст
Среда разработки **Abak.IDE** (на базе **CODESYS V3.5**) традиционно требует ручной работы оператора в графическом интерфейсе (GUI) при редактировании кода, настройке конфигурации задач, соотнесении каналов модулей ввода-вывода (I/O Mapping) и компиляции.

Данный проект (**`abak-ide-bridge`**) представляет собой полнофункциональный программный комплекс, позволяющий внешним системам (ИИ-ассистентам Antigravity / Gemini, CI/CD-пайплайнам, внешним IDE типа VS Code) **в реальном времени подключаться к уже запущенной Abak.IDE по сети (TCP/HTTP) или через локальный IPC и выполнять любые операции автоматизации**:
- Выгрузка (Export) и загрузка (Import) Structured Text (.st) исходников в иерархию проекта.
- Программное редактирование AST, POU, DUT, GVL, типов данных и задач.
- Программная аппаратная привязка (I/O Mapping) физических каналов модулей ввода/вывода (CANopen, Modbus, Profinet) к переменным IEC 61131-3 без ручных кликов мыши.
- Удаленная инкрементальная и чистая компиляция (Clean & Build) с получением диагностических сообщений, ошибок и предупреждений компилятора в формате JSON.
- **Онлайн-мониторинг и управление ПЛК**: чтение (`online_read`) и запись/форсирование (`online_write`) переменных в реальном времени, опрос статуса выполнения программы (`online_status`: RUN/STOP), удаленный пуск, останов и сброс (`online_control`).
- **Экспорт и импорт PLCopen XML**: резервное копирование и перенос логики программ в международном стандарте PLCopen XML (`export_xml`, `import_xml`).
- Выполнение произвольных сценариев автоматизации на IronPython внутри адресного пространства CODESYS.
- **Полная база типизации ScriptEngine**: каталог `stubs/scriptengine/` с 48 официальными файлами `.pyi` и исчерпывающим справочником API `stubs/scriptDoc.txt` для идеального автодополнения (IntelliSense) и работы LLM.
- **Главная особенность**: среда Abak.IDE не блокируется, интерфейс (GUI) остается на 100% отзывчивым благодаря интеграции в цикл обработки событий через `System.Windows.Forms.Timer`.

---

## 2. Архитектура решения

```
┌────────────────────────────────────────────────────────┐
│  Внешняя система / Агент / Хост (напр. 192.168.1.50)   │
│  - Python 3 CLI / REST Client (abak_bridge_client.py) │
│  - Редактор VS Code / ИИ-ассистент Antigravity         │
│  - MCP Server: 16 нативных инструментов автоматизации  │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP JSON (TCP Port 11888)
                            ▼
┌────────────────────────────────────────────────────────┐
│  Инженерная станция (напр. 192.168.1.100)             │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Процесс Abak.IDE (CODESYS V3.5)                  │  │
│  │                                                  │  │
│  │ ┌──────────────────────────────────────────────┐ │  │
│  │ │ codesys_bridge_server.py (IronPython 2.7)   │ │  │
│  │ │ - System.Windows.Forms.Timer (UI Event Loop) │ │  │
│  │ │ - System.Net.Sockets.TcpListener (:11888)    │ │  │
│  │ │ - Dispatcher: status, import, export,        │ │  │
│  │ │               compile, exec, map_io, save,   │ │  │
│  │ │               online_status, online_read,    │ │  │
│  │ │               online_write, online_control,  │ │  │
│  │ │               export_xml, import_xml         │ │  │
│  │ └──────────────────────┬───────────────────────┘ │  │
│  │                        │ ScriptEngine APIs       │  │
│  │ ┌──────────────────────▼───────────────────────┐ │  │
│  │ │ CODESYS Object Model:                        │ │  │
│  │ │ - projects.primary (Active .project)         │ │  │
│  │ │ - Application (POUs, GVLs, DUTs, Tasks)     │ │  │
│  │ │ - Device Tree (CANbus, I/O Modules, Mapping) │ │  │
│  │ │ - Compiler (build, clean, get_messages)      │ │  │
│  │ │ - OnlineManager (login, RUN/STOP, read/write)│ │  │
│  │ └──────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## 3. Быстрый старт

### Шаг 1: Запуск сервера в Abak.IDE
1. Откройте нужный проект в **Abak.IDE** на инженерной станции (`192.168.1.100`).
2. В верхнем меню выберите: **Инструменты (Tools)** $\to$ **Скрипты (Scripting)** $\to$ **Выполнить скрипт (Run Script...)**.
3. Выберите файл: `server/codesys_bridge_server.py`.
4. В панели вывода (Output) появится баннер:
   ```text
   ==================================================
   CODESYS Net Bridge & IPC Server is RUNNING!
   - Network Port: 11888 (http://<ip>:11888)
   - Non-blocking: IDE remains 100% responsive
   ==================================================
   ```

### Шаг 2: Графический интерфейс (GUI Менеджер)
Для удобной визуальной работы запущен обновленный графический менеджер:
- Двойным кликом запустите `run_gui.bat` (или выполните `py client/gui_manager.py`).
- Окно содержит:
  - Светодиодный индикатор статуса соединения (🟢 Онлайн / 🔴 Офлайн).
  - Отображение активного проекта и пути на диске.
  - Кнопки **Экспорт** и **Импорт** файлов `.st`.
  - Кнопки **Компиляция (Build)** и **Чистая сборка (Clean & Build)** с детальным выводом сообщений.
  - Просмотр дерева проекта и сохранение.

### Шаг 3: Проверка статуса через консоль (CLI)
С любого сетевого узла выполните:
```bash
python client/abak_bridge_client.py --host 192.168.1.100 status
```

### Шаг 4: Онлайн-мониторинг переменных ПЛК
```bash
# Чтение текущих значений переменных
python client/abak_bridge_client.py --host 192.168.1.100 online-read --vars Application.PLC_PRG.iCounter Application.GVL.rSpeed

# Запись нового значения
python client/abak_bridge_client.py --host 192.168.1.100 online-write --vars Application.GVL.rSpeed=1200.0

# Проверка состояния ПЛК (RUN/STOP)
python client/abak_bridge_client.py --host 192.168.1.100 online-status
```

---

## 4. Структура репозитория

```
├── README.md                      # Главное описание и руководство по эксплуатации
├── PROJECT_CONTEXT.md             # Сетевые адреса, учетные данные, системный контекст
├── requirements.txt               # Зависимости Python клиента (PyQt6, mcp)
├── run_gui.bat                    # Быстрый запуск Cyberpunk GUI Менеджера
├── server/                        # Скрипты сервера (выполняются внутри Abak.IDE / IronPython)
│   ├── codesys_bridge_server.py   # Сервер моста (15 API-действий: онлайн, ST, XML, сборка)
│   ├── deploy_server.bat          # 1-клик настройка брандмауэра и сети на инженерном ПК
│   └── start_with_project.bat     # Автозапуск Abak.IDE с проектом и сервером в фоне
├── mcp_server/                    # Model Context Protocol (MCP) для AI-агентов
│   └── abak_mcp_server.py         # 16 нативных MCP-инструментов (Antigravity, Claude, Cursor)
├── stubs/                         # Полная официальная база типизации и документация
│   ├── scriptDoc.txt              # Исчерпывающий справочник ScriptEngine API (244 КБ)
│   └── scriptengine/              # 48 официальных .pyi стабов типов CODESYS V3.5
├── client/                        # Клиентские утилиты (выполняются на хосте / агенте)
│   ├── gui_manager.py             # Cyberpunk GUI менеджер (PyQt6) с вкладкой Git
│   ├── abak_bridge_client.py      # Полнофункциональный CLI и Python-модуль
│   └── examples/                  # Готовые примеры автоматизации
│       ├── 01_health_check.py     # Быстрая диагностика связи
│       ├── 02_inspect_project.py  # Полный дамп дерева устройств и логики
│       ├── 03_io_mapping.py       # Программная привязка каналов ввода/вывода
│       ├── 04_online_monitoring.py# Чтение и запись переменных ПЛК онлайн
│       └── inspect_live_mapping.py# Инспекция текущих привязок модуля и GVL
└── docs/                          # Подробная техническая документация
    ├── CAPABILITIES_AND_ROADMAP.md# Текущие возможности и дорожная карта развития
    ├── DEPLOYMENT_GUIDE.md        # Пошаговое руководство по развертыванию на других ПК
    ├── ARCHITECTURE.md            # Устройство сервера, потоковая модель, ScriptEngine
    ├── API_REFERENCE.md           # Спецификация 15 эндпоинтов сетевого протокола
    ├── IO_MAPPING_GUIDE.md        # Руководство по аппаратной привязке каналов
    └── LESSONS_LEARNED.md         # Ошибки, тонкости IronPython/.NET и их решения
```

---

## 5. Интеграция с AI-агентами (Model Context Protocol)

Проект полностью совместим со стандартом **MCP (Model Context Protocol)**. Подробные инструкции по подключению к **Antigravity**, **Claude Desktop**, **Cursor** и **VS Code** смотрите в документе:  
👉 **[docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)**
