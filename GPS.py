import asyncio

from .Globals import GPS_RETRY, GPS_TIMEOUT, TIMEOUT
from .Settings import Settings


class GPS:
    """Query and manage the modem GPS session."""

    def __init__(self) -> None:
        self.settings = Settings()
        self.loc = ""
        self.is_running = False

    def __getattr__(self, name):
        try:
            return getattr(self.settings, name)
        except AttributeError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from None

    async def session_check(self) -> bool:
        check = await self.send_at("AT+CGPS?", "+CGPS", TIMEOUT)
        self.is_running = not self.at.is_error(check) and "+CGPS: 1,1" in check
        return self.is_running

    async def gps_session(self, start: bool) -> bool:
        """
        True to start session. False to close session.
        :param start: bool
        :return: bool
        """
        await self.session_check()
        if start:
            if self.is_running:
                return True
            print("Starting GPS session...")
            # Best-effort reset before starting the session.
            await self.send_at("AT+CGPS=0,1", "OK", GPS_TIMEOUT)
            response = await self.send_at("AT+CGPS=1,1", "OK", GPS_TIMEOUT)
            if self.at.is_error(response):
                print(f"Unable to start GPS session: {response}")
                return False
            await asyncio.sleep(2)
            self.is_running = True
            print("Started successfully")
            return True

        print("Closing GPS session...")
        response = await self.send_at("AT+CGPS=0,1", "OK", GPS_TIMEOUT)
        if self.at.is_error(response):
            print("Error closing GPS, is it open?")
            return False
        self.is_running = False
        return True

    async def get_gps_position(self, retries: int = GPS_RETRY) -> str | None:
        """Return the raw ``+CGPSINFO`` response, or ``None`` on failure."""
        if not await self.session_check():
            print(
                "Attempting to get location without an open GPS session, "
                "trying to open one now..."
            )
            if not await self.gps_session(True):
                return None

        for _ in range(max(1, retries)):
            answer = await self.send_at("AT+CGPSINFO", "+CGPSINFO: ", GPS_TIMEOUT)
            if self.at.is_error(answer):
                print("Error accessing GPS, attempting to close session")
                await self.gps_session(False)
                return None
            if ",,,,,," in answer:
                return "GPS is active but no signal was found"
            return answer

        print("Retry limit reached; GPS signal not found...")
        return None
