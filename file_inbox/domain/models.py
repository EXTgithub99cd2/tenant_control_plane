
from dataclasses import dataclass
from enum import Enum

class UploadDecision(str,Enum):
    ACCEPTED='accepted'
    ALREADY_PRESENT='already_present'
    APPROVAL_REQUIRED='approval_required'
    NAME_CONFLICT='name_conflict'
    REJECTED='rejected'

@dataclass(frozen=True)
class UploadResult:
    decision:UploadDecision
    file_id:int|None=None
    approval_token:str|None=None
    message:str=''
    existing_file_id:int|None=None
