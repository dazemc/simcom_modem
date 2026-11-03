from .Globals import SMS_SEND_TIMEOUT, TIMEOUT
from .Models import Messages
from .ParserSMS import Parser
from .Settings import Settings


class SMS:
    """Send, receive, and delete SMS messages through the modem."""

    def __init__(self) -> None:
        self.settings = Settings()
        self.parser = Parser(timezone=self.settings.timezone)

    def __getattr__(self, name):
        try:
            return getattr(self.settings, name)
        except AttributeError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from None

    async def receive_messages(self) -> list[Messages]:
        """Read all messages from SIM storage in PDU mode."""
        previous_mode = await self.get_data_mode()
        if previous_mode is not True:
            await self.set_data_mode(0)  # PDU mode
        try:
            answer = await self.send_at("AT+CMGL=4", "OK", TIMEOUT)
            if self.at.is_error(answer):
                print(f"Error reading messages: {answer}")
                return []
            return self.parser.parse_pdu(answer)
        finally:
            if previous_mode is False:
                await self.set_data_mode(1)  # Restore text mode

    async def read_message(self, message_type: str) -> list[Messages]:
        """
        Read messages of the specified type.
        :param message_type: str
        :return: list<Messages>
        """
        return await self.receive_messages()

    async def send_message(self, phone_number: str, text_message: str) -> bool:
        """Send a text message, restoring the previous modem mode afterwards."""
        previous_mode = await self.get_data_mode()
        await self.set_data_mode(1)  # Text mode is required for AT+CMGS
        try:
            answer = await self.send_at(f'AT+CMGS="{phone_number}"', ">", TIMEOUT)
            if self.at.is_error(answer):
                print(f"Error starting SMS send: {answer}")
                return False

            await self.write_data(text_message.encode() + b"\x1a")
            answer = await self.read_until("OK", SMS_SEND_TIMEOUT)
            if self.at.is_error(answer):
                print(
                    f"Error sending message...\n"
                    f"phone_number: {phone_number}\n"
                    f"text_message: {text_message}\n"
                    f"Not sent!"
                )
                return False

            print(f"Number: {phone_number}\nMessage: {text_message}\nMessage sent!")
            return True
        finally:
            if previous_mode is True:
                await self.set_data_mode(0)  # Restore PDU mode

    async def delete_message(self, msg_idx: int) -> dict:
        """Delete a message by its modem index.

        Args:
            msg_idx (int): message to delete

        Returns:
            dict: {"response": "Success" | False}
        """
        response = await self.send_at(f"AT+CMGD={msg_idx}", "OK", TIMEOUT)
        if self.at.is_error(response):
            return {"response": False}
        return {"response": "Success"}
