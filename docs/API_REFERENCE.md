# Спецификация API (JSON RPC через HTTP)

Базовый эндпоинт: `http://<IP_ИНЖЕНЕРНОГО_ПК>:11888/api`  
Метод HTTP: `POST`  
Заголовки: `Content-Type: application/json; charset=utf-8`

---

## 1. Действие: `status`
Получение текущего состояния IDE, имени и пути открытого проекта.

**Запрос**:
```json
{
  "action": "status"
}
```

**Ответ**:
```json
{
  "status": "ok",
  "project_open": true,
  "project_path": "D:\\Projects\\PLC\\my_plc_project.project",
  "app_name": "Application",
  "server_time": "2026-09-24 13:30:00"
}
```

---

## 2. Действие: `compile`
Запуск компиляции проекта с получением результатов и сообщений сборки.

**Запрос**:
```json
{
  "action": "compile",
  "clean": false
}
```
* `clean` (boolean, optional): если `true`, перед сборкой вызывается `app.clean()` (чистая сборка).

**Ответ**:
```json
{
  "status": "ok",
  "success": true,
  "errors_count": 0,
  "warnings_count": 2,
  "messages": [
    {
      "severity": "Warning",
      "text": "Task_Bus: Не задан POU для задачи 'Task_Bus'"
    }
  ]
}
```

---

## 3. Действие: `save`
Сохранение открытого проекта на диск.

**Запрос**:
```json
{
  "action": "save"
}
```

**Ответ**:
```json
{
  "status": "ok",
  "message": "Project saved successfully"
}
```

---

## 4. Действие: `map_io`
Аппаратная привязка физических каналов модуля к переменным программы (I/O Mapping).

**Запрос**:
```json
{
  "action": "map_io",
  "device_name": "M1_K3_AI_10_08_00",
  "mappings": {
    "Analog Input, channel 1": "Application.GVL_Raw.raw_Level49",
    "Analog Input, channel 2": "Application.GVL_Raw.raw_Level603b",
    "Analog Input, channel 3": "Application.GVL_Raw.raw_Press"
  },
  "always_update": true
}
```

**Ответ**:
```json
{
  "status": "ok",
  "mapped": {
    "Analog Input, channel 1": "Application.GVL_Raw.raw_Level49",
    "Analog Input, channel 2": "Application.GVL_Raw.raw_Level603b",
    "Analog Input, channel 3": "Application.GVL_Raw.raw_Press"
  }
}
```

---

## 5. Действие: `exec`
Выполнение произвольного кода IronPython внутри среды CODESYS с перехватом вывода (stdout/stderr) и возвратом структурированных данных через переменную `result`.

**Параметры запроса**:
- `code` *(string, optional)*: Текст исполняемого Python-скрипта.
- `script_path` *(string, optional)*: Путь к `.py` файлу на диске инженерной станции (если не передан `code`).
- `params` *(object, optional)*: Словарь параметров, пробрасываемый в область видимости скрипта как `params`.
- `args` *(array, optional)*: Список аргументов, доступный в скрипте как `args`.

**Переменные в области видимости (scope)**:
- `projects.primary` / `active_project`: Ссылка на активный открытый проект.
- `system`: Системный API CODESYS (`ScriptSystem`).
- `online`: Онлайн API CODESYS (`ScriptOnline`).
- `System`: Пространство имен .NET CLR.
- `params`: Переданный словарь параметров.
- `result`: Переменная для возврата структурированного JSON-ответа (например: `result = {"count": 10}`).

**Запрос**:
```json
{
  "action": "exec",
  "code": "proj = projects.primary\nprint('Project: ' + proj.get_name())\nresult = {'name': proj.get_name(), 'objects_count': len(proj.find('', True))}",
  "params": {"custom_tag": "test"}
}
```

**Ответ**:
```json
{
  "status": "ok",
  "log": "Project: MyControllerProject\n",
  "result": {
    "name": "MyControllerProject",
    "objects_count": 84
  }
}
```

---

## 6. Действие: `export`
Полная выгрузка всех исходных текстов из проекта.

**Запрос**:
```json
{
  "action": "export"
}
```

**Ответ**:
```json
{
  "status": "ok",
  "count": 12,
  "objects": {
    "PRGs/PLC_PRG": {
      "declaration": "PROGRAM PLC_PRG\nVAR ...\nEND_VAR",
      "implementation": "PRG_Analog();",
      "type": "6fde0630-ccfa-444d-978a-b4e8e42f6869"
    }
  }
}
```

---

## 7. Действие: `import`
Пакетное обновление или создание объектов из переданных исходных текстов.

**Запрос**:
```json
{
  "action": "import",
  "files": {
    "PRGs/PLC_PRG.st": {
      "declaration": "PROGRAM PLC_PRG\nVAR ...\nEND_VAR",
      "implementation": "PRG_Analog();"
    }
  }
}
```

**Ответ**:
```json
{
  "status": "ok",
  "results": {
    "PLC_PRG": "Updated"
  }
}
```

---

## 8. Действие: `online_status`
Проверка онлайн-подключения к целевому ПЛК и статуса выполнения (RUN, STOP, etc.).

**Запрос**:
```json
{
  "action": "online_status"
}
```

**Ответ**:
```json
{
  "status": "ok",
  "is_logged_in": true,
  "application_state": "run",
  "operation_state": "none"
}
```

---

## 9. Действие: `online_login`
Подключение (Login) к ПЛК через сконфигурированный шлюз и коммуникационный канал проекта.

**Запрос**:
```json
{
  "action": "online_login",
  "change_option": "Try"
}
```
* `change_option` (string, optional, по умолчанию `"Try"`): режим загрузки изменений (`"Try"`, `"Never"`, `"Force"`, `"Keep"`).

**Ответ**:
```json
{
  "status": "ok",
  "is_logged_in": true,
  "application_state": "run"
}
```

---

## 10. Действие: `online_logout`
Корректное отключение (Logout) от ПЛК.

**Запрос**:
```json
{
  "action": "online_logout"
}
```

**Ответ**:
```json
{
  "status": "ok",
  "is_logged_in": false
}
```

---

## 11. Действие: `online_control`
Управление жизненным циклом выполнения приложения на ПЛК (запуск, останов, сброс).

**Запрос**:
```json
{
  "action": "online_control",
  "command": "start"
}
```
* `command` (string, required): одна из команд — `"start"` (RUN), `"stop"` (STOP), `"reset_warm"`, `"reset_cold"`.

**Ответ**:
```json
{
  "status": "ok",
  "command": "start",
  "application_state": "run"
}
```

---

## 12. Действие: `online_read`
Чтение значений переменных программы из памяти ПЛК в реальном времени.

**Запрос**:
```json
{
  "action": "online_read",
  "expressions": [
    "Application.PLC_PRG.iCycleCount",
    "Application.GVL.rMotorSpeed",
    "Application.GVL.bSafetyOk"
  ]
}
```

**Ответ**:
```json
{
  "status": "ok",
  "values": {
    "Application.PLC_PRG.iCycleCount": "10482",
    "Application.GVL.rMotorSpeed": "1450.5",
    "Application.GVL.bSafetyOk": "TRUE"
  }
}
```

---

## 13. Действие: `online_write`
Запись или принудительное форсирование (Force) значений переменных в ПЛК.

**Запрос**:
```json
{
  "action": "online_write",
  "values": {
    "Application.GVL.rTargetSpeed": "1500.0",
    "Application.GVL.bManualOverride": "TRUE"
  },
  "force": false
}
```
* `values` (object, required): словарь пар `"ИмяПеременной": "ЗначениеВВидеСтроки"`.
* `force` (boolean, optional, по умолчанию `false`): если `true`, значения форсируются (`force_prepared_values()`).

**Ответ**:
```json
{
  "status": "ok",
  "written": {
    "Application.GVL.rTargetSpeed": "1500.0",
    "Application.GVL.bManualOverride": "TRUE"
  },
  "forced": false
}
```

---

## 14. Действие: `export_xml`
Экспорт приложения в промышленный стандарт PLCopen XML (с сохранением структуры папок и POUs).

**Запрос**:
```json
{
  "action": "export_xml",
  "path": "C:\\Projects\\Export\\application_backup.xml"
}
```
* `path` (string, optional): если указан путь, сохраняет XML в файл на сервере. Если не указан, возвращает полное XML-содержимое в поле `"xml"`.

**Ответ**:
```json
{
  "status": "ok",
  "path": "C:\\Projects\\Export\\application_backup.xml"
}
```

---

## 15. Действие: `import_xml`
Импорт программных компонентов из файла стандарта PLCopen XML в активный проект.

**Запрос**:
```json
{
  "action": "import_xml",
  "path": "C:\\Projects\\Export\\application_backup.xml"
}
```
* `path` (string, optional): путь к XML-файлу на диске сервера.
* `xml` (string, optional): альтернативно — строка с содержимым XML.

**Ответ**:
```json
{
  "status": "ok",
  "imported_from": "C:\\Projects\\Export\\application_backup.xml"
}
```
