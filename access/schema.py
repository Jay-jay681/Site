from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import Field, Schema


class MessageSchema(Schema):
    message: str


class AttendanceRecordSchemaIn(Schema):
    site_id: UUID
    employee_id: str
    pin: str = Field(..., pattern=r"^\d{6}$")


class AttendanceRecordSchema(Schema):
    id: UUID
    user_name: str
    site_name: str
    method: str
    entered_at: datetime
    exited_at: Optional[datetime] = None

    @staticmethod
    def resolve_user_name(obj):
        return obj.user.name

    @staticmethod
    def resolve_site_name(obj):
        return obj.site.name
    
    
class LiveBoardSchema(Schema):
    site_name: str
    occupancy: int
    hard_capacity: int
    people: list[AttendanceRecordSchema]
    
class ManualAttendanceRecordSchema(Schema):
    employee_id: str
    exited_at: datetime
    close_reason: str