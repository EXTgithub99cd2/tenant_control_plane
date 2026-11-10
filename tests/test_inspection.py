
from io import BytesIO
from openpyxl import Workbook
from fastapi.testclient import TestClient
from app import app
client=TestClient(app)
def upload(name,data,media):
    response=client.post('/inbox/upload',files={'file':(name,data,media)},follow_redirects=False)
    location=response.headers['location']
    if '/approvals/' in location:
        token=location.rsplit('/',1)[-1];response=client.post(f'/inbox/approvals/{token}/approve',follow_redirects=False);return int(response.headers['location'].rsplit('/',1)[-1])
    files=client.get('/api/inbox/files').json();return next(x['id'] for x in files if x['original_filename']==name)
def test_csv_inspection():
    fid=upload('inspection.csv',b'Customer ID,Name,Active,Amount,Created\n001,Ada,true,12.50,2026-01-02\n002,,false,10,2026-02-03\n','text/csv')
    response=client.get(f'/api/inbox/files/{fid}/inspection?dataset=CSV');assert response.status_code==200
    report=response.json();assert report['valid'];assert len(report['preview_rows'])==2
    types={x['normalized_name']:x['logical_type'] for x in report['columns']};assert types['customer_id']=='string';assert types['active']=='boolean';assert types['amount']=='decimal';assert types['created']=='datetime'
def test_xlsx_worksheets_and_preview():
    wb=Workbook();ws=wb.active;ws.title='Customers';ws.append(['ID','Full Name']);ws.append([1,'Ada']);orders=wb.create_sheet('Orders');orders.append(['Order ID','Total']);orders.append([10,19.95]);out=BytesIO();wb.save(out)
    fid=upload('inspection.xlsx',out.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    sets=client.get(f'/api/inbox/files/{fid}/datasets').json();assert [x['name'] for x in sets['datasets']]==['Customers','Orders']
    report=client.get(f'/api/inbox/files/{fid}/inspection?dataset=Orders');assert report.status_code==200 and report.json()['preview_rows'][0]['order_id']==10
    assert client.get(f'/inbox/files/{fid}/inspect').status_code==200
