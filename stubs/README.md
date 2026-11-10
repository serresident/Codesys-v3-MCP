# База типизации и справочник API ScriptEngine (Stubs & API Reference)

В данном каталоге собрана исчерпывающая база знаний и типов для работы с интерпретатором **IronPython 2.7 / ScriptEngine** в среде **CODESYS V3.5** и **Abak.IDE**.

---

## 1. Содержимое каталога

| Файл / Каталог | Назначение |
|---|---|
| [`scriptDoc.txt`](scriptDoc.txt) | Полный текстовый справочник API CODESYS ScriptEngine (8 679 строк, 244 КБ). Содержит сигнатуры, методы, свойства, перечисления (Enum) и официальные docstrings всех классов среды. |
| [`scriptengine/`](scriptengine/) | 48 типизированных интерфейсных файлов Python (`.pyi`) для автодополнения (IntelliSense) и статического анализа в современных IDE (VS Code, PyCharm, Cursor). |

---

## 2. Происхождение и связь с апстрим-репозиториями

CODESYS V3.5 исторически не публикует открытые спецификации своего внутреннего скриптового API в виде стандартных пакетов Python — официальная документация обычно поставляется в виде закрытой Windows-справки (`.chm`) или компилируется через пакет *CODESYS Library Documentation Support*.

* **Первоисточник**:
  Данный текстовый дамп и заготовки стабов созданы сообществом разработчиков промышленной автоматизации методом интроспекции (Python Reflection над внутренним модулем `scriptengine` внутри запущенного процесса CODESYS) и заимствованы из репозиториев:
  - [**johannesPettersson80/codesys-mcp-toolkit**](https://github.com/johannesPettersson80/codesys-mcp-toolkit) — базовый тулкит MCP для CODESYS.
  - [**johannesPettersson80/codesys-api**](https://github.com/johannesPettersson80/codesys-api) — концепция постоянной сессии (persistent session) и REST-обёртки над ScriptEngine.
  - [**serresident/codesys-mcp-toolkit**](https://github.com/serresident/codesys-mcp-toolkit) — форк-исходник для адаптации под российские контроллеры АБАК и среду Abak.IDE.
  - [**serresident/Codesys-v3-MCP**](https://github.com/serresident/Codesys-v3-MCP.git) — текущий рабочий репозиторий с расширенным сетевым мостом, быстрым параллельным опросом портов, поддержкой PLCopen XML и Cyberpunk GUI.

---

## 3. Как использовать разработчику в VS Code / PyCharm

Чтобы в вашей внешней IDE работало автодополнение при написании скриптов автоматизации:

### VS Code (`settings.json`):
```json
{
  "python.analysis.extraPaths": [
    "./stubs"
  ],
  "python.analysis.stubPath": "./stubs"
}
```

После этого в любом Python-файле работает автодополнение:
```python
import scriptengine
# IDE подскажет методы: projects.primary, system, online, etc.
```

---

## 4. Как это используют ИИ-агенты (LLM / Antigravity / Claude)

Файл `scriptDoc.txt` используется ИИ-ассистентами как локальный автономный источник истины:
* Перед написанием сложных вызовов (например, настройка каналов Modbus в `io_mapping`, вызовы `online.login` или чтение параметров компиляции) агент проверяет точные сигнатуры и имена аргументов по `scriptDoc.txt`.
* Это исключает галлюцинации несуществующих функций и гарантирует совместимость с ядром CODESYS V3.5 SP16+ и Abak.IDE.
