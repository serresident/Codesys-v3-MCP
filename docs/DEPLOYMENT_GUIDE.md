# Руководство по развертыванию: Abak.IDE Bridge & MCP Server

Данный документ описывает полное пошаговое руководство по развертыванию и настройке сетевого моста автоматизации **Abak.IDE (CODESYS V3.5)** и сервера **Model Context Protocol (MCP)** для работы AI-агентов (Antigravity, Claude Desktop, Cursor, Windsurf, Roo Code / VS Code) как локально, так и между разными компьютерами в локальной сети или через VPN.

---

## 1. Архитектура распределенного взаимодействия

Схема разделения ролей между узлами:

```
┌────────────────────────────────────────────────────────┐
│  Инженерная станция (напр. 192.168.1.100)              │
│  - Установлена среда Abak.IDE (CODESYS V3.5)           │
│  - Открыт проект PLC (*.project)                       │
│  - Запущен сервер: server/codesys_bridge_server.py     │
│  - Слушает порт TCP: 11888                             │
│  * Внешний Python и сторонние библиотеки НЕ ТРЕБУЮТСЯ! │
└───────────────────────────▲────────────────────────────┘
                            │
                     TCP / HTTP :11888
                     (LAN или VPN)
                            │
┌───────────────────────────▼────────────────────────────┐
│  Рабочая станция с AI-агентом (напр. 192.168.1.50)     │
│  - AI-агент: Antigravity / Claude / Cursor / VS Code   │
│  - Python 3.10+ с библиотекой `mcp`                    │
│  - MCP-сервер: mcp_server/abak_mcp_server.py (stdio)   │
│  - Графический менеджер: client/gui_manager.py         │
└────────────────────────────────────────────────────────┘
```

---

## 2. Развертывание на Инженерном ПК (где установлена Abak.IDE)

> [!NOTE]
> На инженерную станцию **НЕ нужно устанавливать Python, pip или Node.js**!  
> Среда Abak.IDE уже содержит встроенный интерпретатор IronPython 2.7 и среду выполнения .NET CLR.

### Шаг 2.1. Перенос файлов на инженерный ПК
Скопируйте каталог `server/` (или весь репозиторий `abak-ide-bridge`) на целевой ПК, например в папку:
`C:\Tools\abak-bridge-server\`

Содержимое папки:
- `codesys_bridge_server.py` — автономный сервер моста (IronPython);
- `deploy_server.bat` — скрипт автоматической настройки брандмауэра и сети;
- `start_with_project.bat` — ярлык запуска Abak.IDE с автоподключением моста.

### Шаг 2.2. Настройка брандмауэра Windows (1 клик)
Запустите файл `deploy_server.bat` от имени Администратора (скрипт запросит повышение прав автоматически при обычном клике):

```cmd
deploy_server.bat
```

Что делает скрипт:
1. Создает входящее разрешающее правило в Windows Defender Firewall для TCP-портов `11888, 11889, 11890, 12888`.
2. Выводит в консоль точные IPv4-адреса сетевых адаптеров этой машины (например: `192.168.1.100`), чтобы вы знали, какой IP указать агенту.

### Шаг 2.3. Запуск сервера моста внутри Abak.IDE

Выберите один из двух способов запуска:

#### Способ А: Вручную в уже открытом проекте (Рекомендуемый)
1. Откройте нужный `.project` в Abak.IDE.
2. В строке меню выберите:  
   **Инструменты (Tools)** $\to$ **Скрипты (Scripting)** $\to$ **Выполнить скрипт (Run Script...)**.
3. Выберите файл `codesys_bridge_server.py`.
4. В нижней панели *«Сообщения»* среды CODESYS отобразится:
   ```text
   Abak.IDE Automation Bridge Server started on 0.0.0.0:11888
   Background Timer started (interval 100 ms).
   ```
> Сервер работает на неблокирующем системном таймере `System.Windows.Forms.Timer` и **не мешает инженеру редактировать проект**.

#### Способ Б: Автозапуск через ярлык
Перетащите файл проекта `.project` мышкой на батник `start_with_project.bat`:
- Abak.IDE откроет проект и сразу активирует сервер моста в фоновом режиме.

---

## 3. Развертывание на ПК AI-Агента

На компьютере, где запущен AI-ассистент:

### Шаг 3.1. Предварительные требования
- Установлен Python 3.10+ (например, Python 3.12 / 3.14).
- Установлена официальная библиотека MCP:
  ```bash
  pip install mcp
  ```

### Шаг 3.2. Размещение файлов
Склонируйте или скопируйте папку проекта на машину агента, например:
`C:\Projects\abak-ide-bridge\`

---

## 4. Подключение к AI-агентам (Конфигурация MCP)

Сервер `mcp_server/abak_mcp_server.py` поддерживает передачу параметров подключения через переменные окружения:
- `ABAK_BRIDGE_HOST` — IP-адрес инженерной станции (по умолчанию `127.0.0.1`).
- `ABAK_BRIDGE_PORT` — TCP порт (по умолчанию `11888`).

### Вариант 1: Google Antigravity
В конфигурационном файле `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "abak-bridge": {
      "command": "python",
      "args": [
        "C:\\Projects\\abak-ide-bridge\\mcp_server\\abak_mcp_server.py"
      ],
      "env": {
        "ABAK_BRIDGE_HOST": "192.168.1.100",
        "ABAK_BRIDGE_PORT": "11888"
      }
    }
  }
}
```

### Вариант 2: Claude Desktop
В файле `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "abak-bridge": {
      "command": "python",
      "args": [
        "C:\\Projects\\abak-ide-bridge\\mcp_server\\abak_mcp_server.py"
      ],
      "env": {
        "ABAK_BRIDGE_HOST": "192.168.1.100",
        "ABAK_BRIDGE_PORT": "11888"
      }
    }
  }
}
```

### Вариант 3: Cursor / Windsurf / VS Code (Roo Code / Cline)
В файле настроек MCP проекта или глобальном `mcp.json`:

```json
{
  "mcpServers": {
    "abak-bridge": {
      "command": "python",
      "args": [
        "C:/Projects/abak-ide-bridge/mcp_server/abak_mcp_server.py"
      ],
      "env": {
        "ABAK_BRIDGE_HOST": "192.168.1.100",
        "ABAK_BRIDGE_PORT": "11888"
      }
    }
  }
}
```

---

## 5. Доступные инструменты агента (MCP Tools)

После подключения агенту становятся доступны 8 специализированных инструментов:

| MCP Tool | Назначение | Аргументы |
| :--- | :--- | :--- |
| `abak_status` | Проверка связи, статуса моста и имени открытого проекта | `host`, `port` |
| `abak_build_project` | Компиляция проекта (инкрементальная или `clean=True` полная) | `clean`, `host`, `port` |
| `abak_map_io` | Программная привязка каналов ввода/вывода модуля к скалярным переменным GVL | `device_name`, `mappings`, `always_update`, `host`, `port` |
| `abak_inspect_device_tree` | Получение полного дерева проекта (Application POU, Tasks, Device Tree) | `host`, `port` |
| `abak_inspect_device_parameters` | Просмотр параметров и текущей привязки каналов конкретного модуля | `device_name`, `host`, `port` |
| `abak_export_sources` | Экспорт всех ST-исходников открытого проекта в JSON | `host`, `port` |
| `abak_save_project` | Сохранение открытого проекта в Abak.IDE | `host`, `port` |
| `abak_exec_python` | Выполнение произвольного кода IronPython в ScriptEngine CODESYS | `code`, `host`, `port` |

---

## 6. Проверка и диагностика связи

### 1. Проверка сетевого порта с ПК агента
В PowerShell на ПК агента выполните:
```powershell
Test-NetConnection -ComputerName 192.168.1.100 -Port 11888
```
Должно возвращаться:
```text
TcpTestSucceeded : True
```

### 2. Запуск встроенного Health Check
```bash
python client/examples/01_health_check.py
```
При успешном подключении скрипт выведет:
```text
Checking connection to Abak.IDE at 192.168.1.100:11888...
Response received successfully:
  Project open: True
  Project path: D:\Projects\...
```

### 3. Запуск Cyberpunk GUI Менеджера
На ПК агента запустите `run_gui.bat`.  
В выпадающем списке выберите **«🌐 Сетевой TCP/HTTP Bridge»**, введите IP `192.168.1.100` и используйте визуальные кнопки:
- Проверка статуса (зеленый индикатор 🟢);
- Быстрый экспорт/импорт ST-кода;
- Сборка и Clean & Build;
- Вкладка Git-версионирования с цветным Diff.

---

## 7. Решение возможных проблем (Troubleshooting)

### Q1: `TcpTestSucceeded : False` / `Connection refused` / `Timeout`
- Убедитесь, что в Abak.IDE на инженерном ПК запущен скрипт `codesys_bridge_server.py`.
- Убедитесь, что на инженерном ПК запущен `deploy_server.bat` и порт 11888 разрешен в брандмауэре.
- Если ПК находятся в разных подсетях, настройте маршрутизацию или подключите оба ПК к VPN (Tailscale, WireGuard).

### Q2: Ошибка привязки каналов `SCRIPT_ERROR: Некорректное имя переменной`
- По правилам CODESYS ScriptEngine, свойство `io_mapping.variable` принимает **только скалярные переменные-идентификаторы** (например: `'Application.GVL_Raw.raw_Level49'`).
- Запрещено передавать индексы массивов (например: `'Application.GVL_Raw.raw_data[0]'`).

### Q3: В открытом окне Abak.IDE таблица соотнесений осталась пустой после вызова скрипта
- Это особенность кэширования вкладок GUI CODESYS.
- **Решение**: закройте вкладку модуля ввода-вывода в Abak.IDE и откройте её заново двойным кликом из дерева устройств.
