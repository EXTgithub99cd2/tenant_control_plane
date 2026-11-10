
from pathlib import Path
from configuration import load_server_settings,load_inbox_settings
from app import inbox

def test_configuration_files_are_loaded():
    base=Path(__file__).resolve().parents[1]
    server=load_server_settings(base);settings=load_inbox_settings(base)
    assert server.host=='127.0.0.1' and server.port==8000
    assert '.csv' in settings.allowed_extensions and settings.chunk_size_bytes>0

def test_uploaded_object_can_be_physically_verified():
    files=inbox.list_files()
    if files:
        result=inbox.verify_file(files[0]['id']);assert result['ok'] is True
