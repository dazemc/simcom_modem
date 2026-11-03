from datetime import datetime, timedelta

from smspdudecoder.easy import read_incoming_sms

from .Models import Messages


def status(value: str) -> str:
    match value:
        case "0":
            return "REC UNREAD"
        case "1":
            return "REC READ"
        case "2":
            return "STO UNSENT"
        case "3":
            return "STO SENT"
        case _:
            return "UNKNOWN"


class Parser:
    def __init__(self, timezone: int | None = None) -> None:
        self.timezone = timezone

    def parse_sms(
        self,
        sms_buffer: str,
        pdu_mode: bool = False,
    ) -> list[Messages]:
        """
        Parses the modem sms buffer into a list of messages.
        :param sms_buffer: str
        :return: list<Messages>
        """
        if pdu_mode:
            return self.parse_pdu(sms_buffer)

        try:
            read_messages = sms_buffer[
                sms_buffer.find("+CMGL") : sms_buffer.rfind("\r\n\r\nOK\r\n")
            ]
            read_messages = read_messages.split("+CMGL: ")[1:]

            message_list = []
            for msg in read_messages:
                msg_header = msg[: msg.find("\r\n")].replace('"', "").split(",")
                msg_contents = msg[msg.find("\r\n") :][2:]
                msg_contents = (
                    msg_contents[:-2] if msg_contents.endswith("\r\n") else msg_contents
                )
                msg_time = msg_header[5][:-3]
                raw_datetime = f"{msg_header[4]} {msg_time}"
                parsed_datetime = datetime.strptime(raw_datetime, "%y/%m/%d %H:%M:%S")
                formatted_date = parsed_datetime.strftime("%Y-%m-%d")
                formatted_time = parsed_datetime.strftime("%H:%M:%S")
                message_list.append(
                    Messages(
                        message_index=msg_header[0],
                        message_type=msg_header[1],
                        message_originating_address=msg_header[2],
                        message_destination_address=msg_header[3],
                        message_date=formatted_date,
                        message_time=formatted_time,
                        message_contents=msg_contents,
                        is_partial=False,
                        in_sim_memory=True,
                    )
                )
            return message_list
        except Exception as e:
            print(
                f"ERROR: Parsing SMS: pdu_mode: {pdu_mode}, "
                f"sms_buffer: {sms_buffer}\n{e}"
            )
            return []

    def parse_pdu(self, pdu: str) -> list[Messages]:
        if not pdu:
            return []

        pdu_split = pdu.split("+CMGL: ")[1:]
        if not pdu_split:
            return []

        msgs = []
        for entry in pdu_split:
            lines = entry.split("\n")
            if len(lines) < 2:
                continue

            msg_head = lines[0].split(",")
            msg_idx = msg_head[0]
            msg_status = status(msg_head[1])
            pdu_encoded = lines[1].strip()
            pdu_decoded = read_incoming_sms(pdu_encoded)
            msg_contents = pdu_decoded["content"]
            fulldate = pdu_decoded["date"].replace(tzinfo=None)
            timezone_offset = timedelta(hours=self.timezone or 0)
            fulldate += timezone_offset
            msg_sender = pdu_decoded["sender"]
            is_partial = isinstance(pdu_decoded.get("partial"), dict)
            partial_key = None
            partial_count = None
            partial_index = None
            if is_partial:
                partial_dict = pdu_decoded["partial"]
                partial_key = partial_dict["reference"]
                partial_count = int(partial_dict["parts_count"])
                partial_index = int(partial_dict["part_number"])
            formatted_date = fulldate.strftime("%Y-%m-%d")
            formatted_time = fulldate.strftime("%H:%M:%S")
            msgs.append(
                Messages(
                    message_index=msg_idx,
                    message_type=msg_status,
                    message_contents=msg_contents,
                    message_originating_address=msg_sender,
                    message_date=formatted_date,
                    message_time=formatted_time,
                    partial_key=partial_key,
                    partial_count=partial_count,
                    partial_index=partial_index,
                    is_partial=is_partial,
                    in_sim_memory=True,
                )
            )
        return msgs
