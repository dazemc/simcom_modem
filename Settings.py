import asyncio
import sys
from datetime import datetime

import serial

from .AT import AT
from .Globals import BAUDRATE, COM, EXIT_FAILURE_CODE, TIMEOUT
from .Utils import SingletonMeta, py_version_check


class Settings(metaclass=SingletonMeta):
    def __init__(self, com: str = COM, baudrate: int = BAUDRATE) -> None:
        """Create the modem settings object without performing serial I/O.

        Call :meth:`initialize` from an async context to query the modem for
        its current SMS data mode and clock.
        """
        self.at = AT(com=com, baudrate=baudrate)
        self.first_run = True
        self.pdu_mode: bool | None = None
        self.datetime: datetime | None = None
        self.timezone: int | None = None

    def __getattr__(self, name):
        try:
            return getattr(self.at, name)
        except AttributeError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from None

    async def initialize(self) -> None:
        """Open the serial port and load the modem state."""
        self.at.open()
        self.pdu_mode = await self.get_data_mode()
        await self.get_datetime()
        self.first_run = False

    async def close(self) -> None:
        """Close the underlying serial connection."""
        await self.at.close()

    async def perform_initial_checks(self) -> None:
        """Run startup checks, exiting when a hard requirement is not met."""
        failures = []
        if not py_version_check():
            failures.append("Python version requirements not met")
        if not await self.sim_ready_check():
            failures.append("SIM device not ready")
        if failures:
            for failure in failures:
                print(failure)
            sys.exit(EXIT_FAILURE_CODE)
        self.first_run = False

    async def enable_verbose_logging(self) -> bool:
        response = await self.send_at("AT+CMEE=2", "OK", TIMEOUT)
        return not self.at.is_error(response)

    async def sim_ready_check(self) -> bool:
        response = await self.send_at("AT+CPIN?", "READY", TIMEOUT)
        return not self.at.is_error(response)

    async def get_config(self) -> str | bool:
        response = await self.send_at("AT&V", "OK", TIMEOUT)
        if self.at.is_error(response):
            return False
        return response

    async def set_usb_os(self, os: str) -> bool:
        """
        USB setting for RNDIS, OS specific. "WIN" or "UNIX".
        :param os: str
        :return: bool
        """
        if os == "WIN":
            await self.send_at("AT+CUSBPIDSWITCH=9001,1,1", "OK", TIMEOUT)
        elif os == "UNIX":
            await self.send_at("AT+CUSBPIDSWITCH=9011,1,1", "OK", TIMEOUT)
        for _ in range(6):  # Wait up to 3 mins for reboot
            await asyncio.sleep(30)
            try:
                self.at.reopen()
                if not self.at.is_error(await self.send_at("AT", "OK", TIMEOUT)):
                    print(f"Set usb for {os}")
                    return True
            except (OSError, serial.SerialException):
                print("Waiting for device to reboot...")
        print("Failed to set USB mode.")
        return False

    async def set_sms_storage(self, mode: str) -> bool:
        """
        Set SMS storage location
        :param mode: str
        :return: bool
        """
        response = await self.send_at(
            f'AT+CPMS="{mode}","{mode}","{mode}"', "OK", TIMEOUT
        )  # Store messages on SIM(SM), "ME"/"MT" is flash
        return not self.at.is_error(response)

    async def set_data_mode(self, mode: int) -> None:
        """
        HEX is automatically used if there is data issues, such as low signal quality.
        :param mode: int
        :return: None
        """
        if mode == 1:
            await self.send_at("AT+CMGF=1", "OK", TIMEOUT)  # Set to text mode
        if mode == 0:
            await self.send_at("AT+CMGF=0", "OK", TIMEOUT)  # Set to hex mode

    async def set_encoding_mode(self, mode: int) -> None:
        """
        Set encoding mode. 0=IRA, 1=GSM, 2=UCS2
        :param mode: int
        :return: None
        """
        if mode == 2:
            await self.send_at('AT+CSCS="UCS2"', "OK", TIMEOUT)
        if mode == 1:
            await self.send_at('AT+CSCS="GSM"', "OK", TIMEOUT)
        if mode == 0:
            await self.send_at('AT+CSCS="IRA"', "OK", TIMEOUT)

    async def get_data_mode(self) -> bool | None:
        """Return ``True`` when the modem is in PDU mode, ``False`` for text."""
        response = await self.send_at("AT+CMGF?", "OK", TIMEOUT)
        if self.at.is_error(response):
            print("Error reading sms data mode")
            return None
        for line in response.splitlines():
            if "+CMGF:" in line:
                try:
                    value = int(line.split(":", 1)[1].strip())
                except (IndexError, ValueError):
                    print("Error parsing sms data mode")
                    return None
                return value == 0
        print("Error reading sms data mode")
        return None

    async def get_datetime(self) -> None:
        """Read the modem clock and timezone offset (in hours)."""
        response = await self.send_at("AT+CCLK?", "OK", TIMEOUT)
        if self.at.is_error(response):
            return
        for line in response.splitlines():
            if "+CCLK:" not in line:
                continue
            try:
                raw_datetime = line.split('"')[1]
                date_part, time_part = raw_datetime.split(",")
                sign = time_part[8]
                offset_hours = int(time_part[9:]) // 4
                self.timezone = offset_hours if sign == "+" else -offset_hours
                formatted = f"{date_part} {time_part[:8]}"
                self.datetime = datetime.strptime(formatted, "%y/%m/%d %H:%M:%S")
            except (IndexError, ValueError):
                print(f"Unable to parse modem datetime: {line}")
            return
