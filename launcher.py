
from pathlib import Path
import uvicorn
from configuration import load_server_settings
BASE=Path(__file__).resolve().parent
if __name__=='__main__':
    settings=load_server_settings(BASE)
    print(f'Starting Tenant Control Plane at http://{settings.host}:{settings.port}')
    uvicorn.run('app:app',host=settings.host,port=settings.port,log_level=settings.log_level,reload=settings.reload)
