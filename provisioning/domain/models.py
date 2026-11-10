from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class DatabaseEngine(str, Enum):
    SQLITE='sqlite'
    POSTGRESQL='postgresql'

@dataclass(frozen=True)
class DatabaseRequest:
    tenant_id:int
    tenant_slug:str
    database_name:str
    engine:DatabaseEngine
    options:dict[str,Any]=field(default_factory=dict)

@dataclass(frozen=True)
class DatabaseReference:
    id:int|None
    tenant_id:int
    requested_name:str
    physical_name:str
    engine:DatabaseEngine
    connection_reference:str
    metadata:dict[str,Any]

@dataclass(frozen=True)
class BackupResult:
    reference:str
    size_bytes:int
    metadata:dict[str,Any]
