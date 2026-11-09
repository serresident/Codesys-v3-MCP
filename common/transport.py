# -*- coding: utf-8 -*-
"""
================================================================================
CODESYS & Abak.IDE Automation Bridge: Unified Network Transport
================================================================================
Обеспечивает быстрое обнаружение активного порта, неблокирующий параллельный
опрос (concurrent port probe), кэширование активного порта и отправку
HTTP/JSON запросов к bridge-серверу CODESYS.
================================================================================
"""

import os
import sys
import json
import time
import socket
import concurrent.futures
from typing import Tuple, List, Optional, Dict, Any

BRIDGE_PORTS = [11888, 11889, 11890, 11891, 12888]
DEFAULT_HOST = os.environ.get("ABAK_BRIDGE_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("ABAK_BRIDGE_PORT", "11888"))
DEFAULT_TIMEOUT = 15.0

_cached_port_by_host: Dict[str, int] = {}


class BridgeTransport:
    """Унифицированный легковесный транспорт для взаимодействия с CODESYS Bridge."""

    def __init__(self, host: str = DEFAULT_HOST, default_port: int = DEFAULT_PORT):
        self.host = host
        self.default_port = default_port

    def _probe_single_port(self, port: int, timeout: float) -> Optional[Tuple[socket.socket, int]]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((self.host, port))
            return s, port
        except Exception:
            s.close()
            return None

    def discover_active_connection(self, initial_port: Optional[int] = None, timeout: float = 1.5) -> Tuple[socket.socket, int]:
        """
        Адаптивное обнаружение активного порта:
        1. Оптимистичная быстрая проверка кэшированного или начального порта.
        2. При неудаче — параллельный опрос всего пула портов с дедлайном.
        """
        global _cached_port_by_host
        is_local = self.host in ("127.0.0.1", "localhost", "::1")
        quick_timeout = 0.15 if is_local else 0.40

        preferred_port = initial_port or _cached_port_by_host.get(self.host) or self.default_port

        # 1. Быстрый опрос предпочтительного порта
        quick_probe = self._probe_single_port(preferred_port, quick_timeout)
        if quick_probe:
            _cached_port_by_host[self.host] = quick_probe[1]
            return quick_probe

        # 2. Параллельный опрос всех портов пула
        candidates = [p for p in BRIDGE_PORTS if p != preferred_port]
        candidates.insert(0, preferred_port)
        probe_timeout = 0.6 if is_local else min(timeout, 1.5)

        connected_socket: Optional[socket.socket] = None
        active_port: Optional[int] = None

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(candidates)) as executor:
            futures = {executor.submit(self._probe_single_port, p, probe_timeout): p for p in candidates}
            for fut in concurrent.futures.as_completed(futures, timeout=timeout):
                try:
                    res = fut.result()
                    if res:
                        sock, p = res
                        if connected_socket is None:
                            connected_socket = sock
                            active_port = p
                            _cached_port_by_host[self.host] = p
                        else:
                            # Закрываем сокеты, если другой порт ответил чуть позже
                            sock.close()
                except Exception:
                    pass

        if connected_socket and active_port:
            return connected_socket, active_port

        raise ConnectionError(
            f"Could not connect to CODESYS Automation Bridge on {self.host} "
            f"(probed ports {candidates} with total timeout {timeout}s)"
        )

    def send_request(self, req_data: Dict[str, Any], port: Optional[int] = None, timeout: float = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Отправка JSON-RPC / REST запроса на сервер моста и парсинг HTTP-ответа."""
        data = json.dumps(req_data, ensure_ascii=False).encode("utf-8")
        s, active_port = self.discover_active_connection(initial_port=port, timeout=min(2.0, timeout))
        s.settimeout(timeout)

        header = (
            f"POST /api HTTP/1.1\r\n"
            f"Host: {self.host}:{active_port}\r\n"
            f"Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(data)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("utf-8")

        chunks = []
        try:
            s.sendall(header + data)
            while True:
                try:
                    chunk = s.recv(16384)
                    if not chunk:
                        break
                    chunks.append(chunk)
                except socket.timeout:
                    break
        finally:
            s.close()

        resp_bytes = b"".join(chunks)
        header_end = resp_bytes.find(b"\r\n\r\n")
        body_bytes = resp_bytes[header_end + 4:] if header_end != -1 else resp_bytes
        raw_text = body_bytes.decode("utf-8", errors="replace").strip()
        if not raw_text:
            return {"status": "error", "error": "Empty response from bridge server"}

        try:
            return json.loads(raw_text)
        except Exception as ex:
            return {"status": "error", "error": "Decode error: %s" % ex, "raw": raw_text}


def send_request(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, req_data: Optional[Dict[str, Any]] = None, timeout: float = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Глобальный фасад send_request для прямой совместимости с abak_bridge_client."""
    if req_data is None:
        req_data = {}
    transport = BridgeTransport(host=host, default_port=port)
    return transport.send_request(req_data, port=port, timeout=timeout)


def send_tcp_request(host: str, port: int, payload: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
    """Глобальный фасад send_tcp_request для прямой совместимости с abak_mcp_server."""
    transport = BridgeTransport(host=host, default_port=port)
    return transport.send_request(payload, port=port, timeout=timeout)
