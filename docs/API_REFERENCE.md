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
Выполнение произвольного кода IronPython внутри среды CODESYS с перехватом стандартного вывода (stdout).

**Запрос**:
```json
{
  "action": "exec",
  "code": "print('Open project: ' + script_engine.projects.primary.path)"
}
```

**Ответ**:
```json
{
  "status": "ok",
  "log": "Open project: D:\\Projects\\PLC\\my_plc_project.project\n"
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
