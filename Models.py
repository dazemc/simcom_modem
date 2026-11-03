from pydantic import BaseModel, ConfigDict


class Messages(BaseModel):
    id: int | None = None
    message_index: str | None = None
    message_type: str
    message_originating_address: str | None = None
    message_destination_address: str | None = None
    message_date: str
    message_time: str
    message_contents: str
    partial_key: str | None = None
    partial_count: int | None = None
    partial_index: int | None = None
    is_partial: bool
    in_sim_memory: bool
    is_sent: bool | None = None

    model_config = ConfigDict(from_attributes=True)
