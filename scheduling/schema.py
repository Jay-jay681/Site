from uuid import UUID

from ninja import Schema
from datetime import datetime

class MessageSchema(Schema):
    message: str

class ScheduleSchemaIn(Schema):
    name: str
    description: str
    start_time: datetime
    end_time: datetime
 
class ScheduleSchemaOut(Schema):
    id: UUID
    name: str
    description: str
    start_time: datetime
    end_time: datetime
    organisation: str
    site : str 
    created_at: datetime
    created_by: str
    
    @staticmethod
    def resolve_organisation(obj):
        return obj.organisation.name
    
    @staticmethod
    def resolve_site(obj):
        return obj.site.name
    
    @staticmethod
    def resolve_created_by(obj):
        return obj.created_by.name
    
class mySchedule(Schema):
    name: str
    site: str
    start_time: datetime
    end_time: datetime
    
    @staticmethod
    def resolve_site(obj):
        return obj.site.name

class ScheduleLinksSchemaIn(Schema):
    user_id: UUID
    
     
class scheduleLinksSchemaOut(Schema):
    schedule: ScheduleSchemaOut
    user: str
    assigned_by: str
    assigned_at: datetime
    
    @staticmethod
    def resolve_user(obj):
        return obj.user.name
    
    @staticmethod
    def resolve_assigned_by(obj):
        return obj.assigned_by.name
    
