from .Globals import PHONE_TIMEOUT
from .Settings import Settings


class Phone:
    """Place and manage voice calls."""

    def __init__(self) -> None:
        self.settings = Settings()

    def __getattr__(self, name):
        try:
            return getattr(self.settings, name)
        except AttributeError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from None

    async def hangup_call(self) -> bool:
        response = await self.send_at("AT+CHUP", "OK", PHONE_TIMEOUT)
        return not self.at.is_error(response)

    async def active_calls(self) -> str | None:
        """
        Returns information on any active calls.
        :return: str | None
        """
        response = await self.send_at("AT+CLCC", "OK", PHONE_TIMEOUT)
        if self.at.is_error(response):
            return None
        return response

    async def call(self, contact_number: str, retry: int = 0) -> bool:
        """
        Start an outgoing call without blocking for user input.

        A ``True`` return means the dial command was accepted, not that the
        call was answered. Use :meth:`hangup_call` to end it.
        :param contact_number: str
        :param retry: int
        :return: bool
        """
        attempt = 1
        while True:
            print(
                f"Attempting to call {contact_number}; "
                f"Attempt: {attempt}; Retry: {retry}"
            )
            response = await self.send_at(f"ATD{contact_number};", "OK", PHONE_TIMEOUT)
            if not self.at.is_error(response):
                return True
            if retry == 0 or attempt >= retry:
                return False
            print(f"Retrying call to {contact_number}; Attempt: {attempt}/{retry}")
            attempt += 1
