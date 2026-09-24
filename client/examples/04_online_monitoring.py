#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример 4: Онлайн-мониторинг и чтение/запись переменных ПЛК в реальном времени.
"""
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from abak_bridge_client import send_request

HOST = os.environ.get("ABAK_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("ABAK_BRIDGE_PORT", "11888"))

def main():
    print(f"1. Проверка онлайн-статуса на {HOST}:{PORT}...")
    res = send_request(HOST, PORT, {"action": "online_status"})
    print("Статус подключения:", res)

    print("\n2. Онлайн-подключение к ПЛК (Login)...")
    res_login = send_request(HOST, PORT, {"action": "online_login", "change_option": "Try"})
    print("Результат логина:", res_login)

    # Список переменных для мониторинга
    vars_to_read = [
        "Application.GVL_Raw.raw_Sensor1",
        "Application.GVL_Raw.raw_Sensor2",
        "Application.GVL_Raw.raw_Pressure",
    ]

    print("\n3. Чтение живых значений переменных из памяти ПЛК...")
    res_read = send_request(HOST, PORT, {"action": "online_read", "expressions": vars_to_read})
    print("Прочитанные значения:")
    for k, v in res_read.get("values", {}).items():
        print(f"  {k} = {v}")

    print("\n4. Пример записи уставки в ПЛК...")
    res_write = send_request(HOST, PORT, {
        "action": "online_write",
        "values": {"Application.GVL.SP_Temp": "75.0"},
        "force": False
    })
    print("Результат записи:", res_write)

if __name__ == "__main__":
    main()
