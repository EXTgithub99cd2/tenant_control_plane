
from fastapi.testclient import TestClient
from app import app,inbox
client=TestClient(app)
def upload(name,data):return client.post('/inbox/upload',files={'file':(name,data,'text/csv')},follow_redirects=False)
def test_inbox_decision_matrix():
    a=upload('customers.csv',b'id,name\n1,Ada\n');assert a.status_code==303 and 'decision=accepted' in a.headers['location']
    b=upload('customers.csv',b'id,name\n1,Ada\n');assert 'decision=already_present' in b.headers['location']
    c=upload('copy.csv',b'id,name\n1,Ada\n');assert '/inbox/approvals/' in c.headers['location']
    token=c.headers['location'].rsplit('/',1)[-1];page=client.get(c.headers['location']);assert page.status_code==200 and 'Approve alias' in page.text
    approved=client.post(f'/inbox/approvals/{token}/approve',follow_redirects=False);assert approved.status_code==303
    d=upload('customers.csv',b'id,name\n2,Grace\n');assert 'decision=name_conflict' in d.headers['location']
def test_pages_and_api():
    assert client.get('/inbox').status_code==200
    files=client.get('/api/inbox/files');assert files.status_code==200 and len(files.json())>=2
    assert client.get(f"/inbox/files/{files.json()[0]['id']}").status_code==200
