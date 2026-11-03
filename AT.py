import asyncio
import time

import serial


class AT:
    def __init__(self, com: str, baudrate: int) -> None:
        self.com = com
        self.baudrate = baudrate
        self.ser: serial.Serial | None = None
        self.rec_buff = ""
        self._lock = asyncio.Lock()

    def init_serial(self, baud: int, com: str) -> serial.Serial:
        return serial.Serial(com, baud, rtscts=True, timeout=0.5)

    def open(self) -> None:
        """Open the serial port if it is not already open."""
        if self.ser is None or not self.ser.is_open:
            self.ser = self.init_serial(self.baudrate, self.com)

    def reopen(self) -> None:
        self.close_serial()
        self.open()

    def _serial(self) -> serial.Serial:
        if self.ser is None:
            raise RuntimeError("Serial port is not open; call open() first")
        return self.ser

    @staticmethod
    def is_error(response: str | None) -> bool:
        """Return True when a modem response represents a failure."""
        return not response or "ERROR" in response

    async def send_at(self, command: str, back: str, timeout_seconds: int) -> str:
        """Send an AT command and wait for the expected response."""
        async with self._lock:
            self.clear_buffer()
            self._serial().write((command + "\r\n").encode())
            start_time = time.monotonic()
            while True:
                if self.ser.in_waiting > 0:
                    self.rec_buff += self.ser.read(self.ser.in_waiting).decode(
                        errors="ignore"
                    )
                if back in self.rec_buff:
                    response = self.rec_buff
                    self.clear_buffer()
                    return response
                if "ERROR" in self.rec_buff and back != "ERROR":
                    response = self.rec_buff
                    self.clear_buffer()
                    return response
                if time.monotonic() - start_time > timeout_seconds:
                    self.clear_buffer()
                    return f"ERROR: Timeout while waiting for response to '{command}'"
                await asyncio.sleep(0.05)

    async def read_until(self, back: str, timeout_seconds: int) -> str:
        """Read from the modem without writing a command."""
        async with self._lock:
            start_time = time.monotonic()
            while True:
                if self.ser.in_waiting > 0:
                    self.rec_buff += self.ser.read(self.ser.in_waiting).decode(
                        errors="ignore"
                    )
                if back in self.rec_buff:
                    response = self.rec_buff
                    self.clear_buffer()
                    return response
                if "ERROR" in self.rec_buff:
                    response = self.rec_buff
                    self.clear_buffer()
                    return response
                if time.monotonic() - start_time > timeout_seconds:
                    self.clear_buffer()
                    return f"ERROR: Timeout while waiting for '{back}'"
                await asyncio.sleep(0.05)

    async def write_data(self, data: bytes) -> None:
        """Write raw bytes to the modem while holding the serial lock."""
        async with self._lock:
            self._serial().write(data)

    async def send_raw(self, command: str, timeout_seconds: int = 10) -> str:
        """Send an arbitrary AT command and return the raw response."""
        async with self._lock:
            self.clear_buffer()
            self._serial().write((command + "\r\n").encode())
            start_time = time.monotonic()
            while True:
                if self.ser.in_waiting > 0:
                    self.rec_buff += self.ser.read(self.ser.in_waiting).decode(
                        errors="ignore"
                    )
                if "OK" in self.rec_buff or "ERROR" in self.rec_buff:
                    response = self.rec_buff
                    self.clear_buffer()
                    return response
                if time.monotonic() - start_time > timeout_seconds:
                    self.clear_buffer()
                    return f"ERROR: Timeout while waiting for response to '{command}'"
                await asyncio.sleep(0.05)

    def close_serial(self) -> None:
        if self.ser is None:
            return
        try:
            self.ser.close()
        except serial.SerialException:
            print("Failed to close serial: Already closed or inaccessible")
        finally:
            self.ser = None

    async def close(self) -> None:
        self.close_serial()

    def clear_buffer(self) -> None:
        if self.ser is not None:
            try:
                self.ser.reset_input_buffer()
            except (AttributeError, serial.SerialException):
                pass
        self.rec_buff = ""
