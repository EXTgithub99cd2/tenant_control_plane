import time
from uuid import uuid4
from observability.application.context import correlation_id

class ObservabilityMiddleware:
    def __init__(self,app,observability): self.app=app;self.obs=observability
    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        headers={k.decode('latin1').lower():v.decode('latin1') for k,v in scope.get('headers',[])}
        cid=headers.get('x-correlation-id') or str(uuid4());token=correlation_id.set(cid);started=time.perf_counter();status=500
        async def send_with_headers(message):
            nonlocal status
            if message['type']=='http.response.start':
                status=message['status'];response_headers=list(message.get('headers',[]));response_headers.append((b'x-correlation-id',cid.encode('ascii','ignore')));message={**message,'headers':response_headers}
            await send(message)
        try:
            await self.app(scope,receive,send_with_headers)
        except Exception as exc:
            self.obs.event('http.request.failed',severity='error',method=scope.get('method'),path=scope.get('path'),error_type=type(exc).__name__)
            raise
        finally:
            elapsed=time.perf_counter()-started;labels={'method':scope.get('method',''),'path':scope.get('path',''),'status':str(status)}
            self.obs.count('controlplane_http_requests_total',labels);self.obs.duration('controlplane_http_request_duration_seconds',elapsed,{'method':labels['method'],'path':labels['path']});self.obs.event('http.request.completed',method=labels['method'],path=labels['path'],status=status,duration_ms=round(elapsed*1000,2));correlation_id.reset(token)
