
import json,logging
from logging.handlers import RotatingFileHandler
from datetime import datetime,timezone
from pathlib import Path
from observability.application.context import current_correlation_id

class JsonEventRecorder:
    def __init__(self,log_dir:Path,max_bytes:int=10*1024*1024,backup_count:int=10):
        log_dir.mkdir(parents=True,exist_ok=True)
        self.app=self._logger('control_plane.application',log_dir/'control-plane.jsonl',max_bytes,backup_count)
        self.audit=self._logger('control_plane.audit',log_dir/'audit.jsonl',max_bytes,backup_count)
    def _logger(self,name,path,max_bytes,backup_count):
        logger=logging.getLogger(name);logger.setLevel(logging.INFO);logger.propagate=False
        if not logger.handlers:
            h=RotatingFileHandler(path,maxBytes=max_bytes,backupCount=backup_count,encoding='utf-8');h.setFormatter(logging.Formatter('%(message)s'));logger.addHandler(h)
        return logger
    def record(self,event_name,*,severity='info',attributes=None):
        payload={'timestamp':datetime.now(timezone.utc).isoformat(timespec='milliseconds'),'severity':severity,'event':event_name,'correlation_id':current_correlation_id(),**(attributes or {})}
        logger=self.audit if event_name.startswith('audit.') else self.app
        getattr(logger,severity if severity in {'debug','info','warning','error','critical'} else 'info')(json.dumps(payload,ensure_ascii=False,default=str))
