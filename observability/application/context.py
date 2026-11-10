
from contextvars import ContextVar
from uuid import uuid4
correlation_id:ContextVar[str]=ContextVar('correlation_id',default='')
def current_correlation_id()->str:
    value=correlation_id.get()
    return value or str(uuid4())
