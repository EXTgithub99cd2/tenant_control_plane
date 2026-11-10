
from fastapi.testclient import TestClient
from app import app
client=TestClient(app)
def test_blank_rows_preserved_and_atomic_import():
    data=b'Statement October\nCustomer,Contoso\n\nDate,Description,Amount\n2026-10-01,Opening,100\n2026-10-02,Invoice,-20\n'
    response=client.post('/inbox/upload',files={'file':('statement.csv',data,'text/csv')},follow_redirects=False);files=client.get('/api/inbox/files').json();fid=next(x['id'] for x in files if x['original_filename']=='statement.csv')
    # create tenant/database
    client.post('/tenants',data={'name':'Import Tenant','slug':'import-tenant'});home=client.get('/').text
    client.post('/databases',data={'tenant_id':1,'name':'statements','engine':'sqlite','owner_password':''})
    structure=client.get(f'/inbox/files/{fid}/structure?dataset=CSV');assert structure.status_code==200 and 'Blank' in structure.text
    mapping=client.post(f'/inbox/files/{fid}/structure',data={'dataset':'CSV','document_header_end':'2','header_row':'4','data_start_row':'5','data_end_row':'6'});assert mapping.status_code==200
    form={'file_id':str(fid),'dataset':'CSV','header_row':'4','data_start_row':'5','data_end_row':'6','document_header_end':'2','column_count':'3','database_id':'1','target_table':'statement_lines','save_template':'true','template_name':'Monthly statement','auto_process_allowed':'true'}
    for i,(s,t,typ) in enumerate([('Date','date','datetime'),('Description','description','string'),('Amount','amount','integer')]):form.update({f'source_{i}':s,f'target_{i}':t,f'type_{i}':typ,f'nullable_{i}':'true'})
    result=client.post('/imports/create-table',data=form);assert result.status_code==200 and '2 rows inserted' in result.text
    history=client.get('/imports/history');assert history.status_code==200 and 'Monthly statement' in history.text and 'allowed' in history.text
