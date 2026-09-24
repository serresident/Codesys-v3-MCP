# Руководство по программному соотнесению входов/выходов (I/O Mapping)

## 1. Введение
В CODESYS существует два способа связать аппаратный канал ввода/вывода (например, 4..20 мА) с программой:
1. **Прямая адресация через память `%I` / `%Q`**:
   ```iec
   raw_Channel1 AT %IW0 : UINT;
   ```
2. **Табличное соотнесение входов/выходов в дереве устройств (I/O Mapping)**:
   Переменная связывается с каналом драйвера модуля (`Analog Input, channel 1` $\rightarrow$ `Application.GVL_Raw.raw_Level49`).

Второй способ является **стандартом промышленного программирования в CODESYS/Abak.IDE**, так как исключает конфликты адресов `%IW` при перестановке модулей в корзине и автоматически генерирует драйверный обмен.

---

## 2. Программное управление соотнесением через ScriptEngine

### Шаг 1: Поиск устройства в дереве
```python
proj = script_engine.projects.primary
devs = proj.find('M1_K3_AI_10_08_00', True)
dev = devs[0]
con = dev.connectors[0]
```

### Шаг 2: Итерация по параметрам и поиск маппируемых каналов
Канал может иметь два представления: описание типа параметра и фактический экземпляр канала. Проверять нужно свойство `is_mappable_io`:
```python
for p in con.host_parameters:
    if p.is_mappable_io and p.name == 'Analog Input, channel 1':
        # Привязка переменной
        p.io_mapping.variable = 'Application.GVL_Raw.raw_Level49'
```

### Шаг 3: Правила именования переменных (КРИТИЧЕСКИ ВАЖНО)
Драйвер CODESYS принимает **только скалярные идентификаторы**:
- **Правильно**: `'Application.GVL_Raw.raw_Level49'`
- **Правильно**: `'Application.GVL.raw_Press'`
- **ОШИБКА**: `'Application.GVL_Raw.M1_AI_Raw[0]'`  
  *(Приведет к ошибке: `Некорректное имя переменной: 'M1_AI_Raw[0]' не является идентификатором`)*.

Если значения должны группироваться, в `GVL_Raw` объявляются отдельные скалярные переменные:
```iec
{attribute 'qualified_only'}
VAR_GLOBAL
    raw_Level49   : UINT; // Канал 1
    raw_Level603b : UINT; // Канал 2
    raw_Press     : UINT; // Канал 3
END_VAR
```

### Шаг 4: Настройка задачи обновления шины
Чтобы переменные считывались непрерывно даже без прямого вызова в задачах:
```python
con.io_always_mapping = True # 'Всегда обновлять переменные'
proj.save()
```

---

## 3. Использование через CLI-клиент
С хоста разработчика:
```bash
python client/abak_bridge_client.py --host 192.168.1.100 map-io \
    --device M1_K3_AI_10_08_00 \
    --channel "Analog Input, channel 1" \
    --var "Application.GVL_Raw.raw_Sensor1"
```
