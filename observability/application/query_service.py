import json
from collections import Counter
from pathlib import Path

class ObservabilityQueryService:
    def __init__(self,log_dir:Path,metrics,readiness): self.log_dir=log_dir;self.metrics=metrics;self.readiness=readiness
    def _read(self,name,limit=100):
        path=self.log_dir/name
        if not path.exists(): return []
        lines=path.read_text(encoding="utf-8",errors="replace").splitlines()[-max(1,min(limit,500)):]
        out=[]
        for line in reversed(lines):
            try: out.append(json.loads(line))
            except json.JSONDecodeError: out.append({"severity":"warning","event":"unparseable.log.line","message":line[:500]})
        return out
    def dashboard(self,limit=100):
        events=self._read("control-plane.jsonl",limit);audit=self._read("audit.jsonl",limit);ready=self.readiness.check()
        status_counts=Counter(str(x.get("status")) for x in events if x.get("event")=="http.request.completed")
        errors=[x for x in events if x.get("severity") in {"error","critical"} or (isinstance(x.get("status"),int) and x["status"]>=500)]
        return {"readiness":ready,"events":events,"audit":audit,"event_count":len(events),"audit_count":len(audit),"error_count":len(errors),"status_counts":dict(status_counts),"metrics":self.metrics.render_prometheus()}
