
from abc import ABC, abstractmethod
from typing import Any

class EventRecorder(ABC):
    @abstractmethod
    def record(self,event_name:str,*,severity:str='info',attributes:dict[str,Any]|None=None)->None: ...

class MetricsRecorder(ABC):
    @abstractmethod
    def increment(self,name:str,labels:dict[str,str]|None=None,value:int=1)->None: ...
    @abstractmethod
    def observe(self,name:str,value:float,labels:dict[str,str]|None=None)->None: ...
    @abstractmethod
    def render_prometheus(self)->str: ...
