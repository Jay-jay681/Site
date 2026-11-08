from typing import Optional

from ninja import schema
from datetime import datetime
from uuid import UUID
from pydantic import ConfigDict 

class InputSchema(schema.Schema):
    model_config = ConfigDict(str_strip_whitespace=True)
class CertificationSchemaOut(InputSchema):
    id : UUID
    name: str
    description: str
    organisation: str
    created_at: datetime
    created_by: str
    
    @staticmethod
    def resolve_organisation(obj):
        return obj.organisation.name
    
    @staticmethod
    def resolve_created_by(obj):
        return obj.created_by.name


class MessageSchema(InputSchema):
    message: str
    
class CertificationSchemaIn(InputSchema):
    name: str
    required_for_trade : str = ""
    description: str
    

class CertifiactionResponseSchemaIn(InputSchema):
    name :str
    expiration_date :datetime
    type : str 
    certificate_number : str 
    
class CertifiactionResponseSchemaOut(InputSchema):
    name :str
    certification :str
    expiration_date :datetime
    type : str 
    status : str
    certificate_number : str 
    
    @staticmethod
    def resolve_certification(obj):
        return obj.certification.name
    
    @staticmethod
    def resolve_name(obj):
        return obj.name.name

class acceptIn(InputSchema):
    id : UUID
    
    
    
    
        

    


        