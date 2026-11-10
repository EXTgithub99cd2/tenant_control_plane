import json,os,re,sqlite3,time
from uuid import uuid4
from pathlib import Path
from fastapi import FastAPI,Form,HTTPException,Request,UploadFile,File
from fastapi.responses import RedirectResponse,PlainTextResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from control_plane.infrastructure.catalog import Catalog
from provisioning.domain.models import DatabaseRequest,DatabaseEngine
from provisioning.application.registry import ProvisionerRegistry
from provisioning.application.service import ProvisioningService
from provisioning.infrastructure.sqlite.adapter import SQLiteProvisioner
from data_management.domain.models import ColumnDefinition,TableDefinition,LogicalType
from data_management.application.registry import DataStoreRegistry
from data_management.application.service import DataManagementService
from data_management.infrastructure.sqlite.adapter import SQLiteDataStore
from observability.application.context import correlation_id
from observability.application.service import ObservabilityService
from observability.infrastructure.json_recorder import JsonEventRecorder
from observability.infrastructure.metrics import InMemoryPrometheusMetrics
from observability.infrastructure.readiness import ReadinessChecker
from observability.application.query_service import ObservabilityQueryService
from observability.infrastructure.http_middleware import ObservabilityMiddleware
from file_inbox.infrastructure.local_store import LocalInboxObjectStore
from file_inbox.infrastructure.repository import InboxRepository
from file_inbox.application.service import InboxService
from file_inspection.infrastructure.csv_reader import CsvReader
from file_inspection.infrastructure.xlsx_reader import XlsxReader
from file_inspection.application.registry import ReaderRegistry
from file_inspection.application.service import FileInspectionService
from statement_import.infrastructure.repository import ImportRepository
from statement_import.application.analyzer import StatementAnalyzer
from statement_import.application.service import StatementImportService
from statement_import.domain.models import StatementStructure,MappingColumn
from configuration import load_inbox_settings,load_inspection_settings
B=Path(__file__).parent;catalog=Catalog(B/'control_plane.db')
provisioners=[SQLiteProvisioner(B/'tenant_databases')];stores=[SQLiteDataStore()]
if os.getenv('POSTGRES_ADMIN_DSN'):
 from provisioning.infrastructure.postgresql.adapter import PostgreSQLProvisioner
 from data_management.infrastructure.postgresql.adapter import PostgreSQLDataStore
 provisioners.append(PostgreSQLProvisioner(os.environ['POSTGRES_ADMIN_DSN'],os.getenv('POSTGRES_HOST','localhost'),int(os.getenv('POSTGRES_PORT','5432')),os.getenv('PG_DUMP_PATH','pg_dump')));stores.append(PostgreSQLDataStore())
provisioner_registry=ProvisionerRegistry(provisioners);data_store_registry=DataStoreRegistry(stores)
ps=ProvisioningService(provisioner_registry,catalog,B/'backups');dm=DataManagementService(data_store_registry,catalog)
obs=ObservabilityService(JsonEventRecorder(B/'logs'),InMemoryPrometheusMetrics());ready=ReadinessChecker(catalog,provisioner_registry,data_store_registry);obs_query=ObservabilityQueryService(B/'logs',obs.metrics,ready)
inbox_settings=load_inbox_settings(B);inbox_repo=InboxRepository(inbox_settings.metadata_database);inbox=InboxService(inbox_repo,LocalInboxObjectStore(inbox_settings.root),obs,max_bytes=inbox_settings.max_upload_bytes,chunk_size=inbox_settings.chunk_size_bytes,allowed_extensions=inbox_settings.allowed_extensions)
inspection_settings=load_inspection_settings(B);reader_registry=ReaderRegistry([CsvReader(inspection_settings.csv_encoding_candidates,inspection_settings.csv_delimiters),XlsxReader(inspection_settings.maximum_worksheets)]);inspection=FileInspectionService(inbox,reader_registry,inspection_settings,obs)
import_repo=ImportRepository(B/'imports.db');statement_import=StatementImportService(inbox,inspection,reader_registry,data_store_registry,catalog,import_repo,StatementAnalyzer(inspection_settings.empty_header_prefix),obs)
app=FastAPI(title='Tenant Control Plane',version='5.0');app.mount('/static',StaticFiles(directory=B/'static'),name='static');tpl=Jinja2Templates(directory=B/'templates')
def render_template(request,name,context):
 context={'request':request,**context}
 try:return tpl.TemplateResponse(request=request,name=name,context=context)
 except TypeError:return tpl.TemplateResponse(name,context)
app.add_middleware(ObservabilityMiddleware,observability=obs)
@app.get('/observability')
def observability_page(request:Request,limit:int=100):
 data=obs_query.dashboard(limit);return render_template(request,'observability.html',{'data':data,'limit':max(1,min(limit,500))})
@app.get('/inbox')
def inbox_page(request:Request,decision:str|None=None,message:str|None=None): return render_template(request,'inbox.html',{'files':inbox.list_files(),'decision':decision,'message':message,'settings':inbox_settings})
@app.post('/inbox/upload')
async def inbox_upload(file:UploadFile=File(...)):
 try: result=await inbox.upload(file)
 except Exception as exc: raise HTTPException(422,str(exc))
 if result.decision.value=='approval_required': return RedirectResponse(f'/inbox/approvals/{result.approval_token}',303)
 return RedirectResponse(f'/inbox?decision={result.decision.value}&message={result.message}',303)
@app.get('/inbox/files/{file_id}')
def inbox_metadata(request:Request,file_id:int):
 item=inbox.get_file(file_id)
 if not item:raise HTTPException(404,'Inbox file not found')
 return render_template(request,'inbox_file.html',{'file':item,'show_storage_reference':inbox_settings.show_storage_reference,'verification':None})
@app.post('/inbox/files/{file_id}/verify')
def inbox_verify(request:Request,file_id:int):
 item=inbox.get_file(file_id)
 if not item:raise HTTPException(404,'Inbox file not found')
 result=inbox.verify_file(file_id)
 return render_template(request,'inbox_file.html',{'file':item,'show_storage_reference':inbox_settings.show_storage_reference,'verification':result})
@app.get('/inbox/files/{file_id}/inspect')
def inspect_select(request:Request,file_id:int):
 try:item,datasets=inspection.datasets(file_id)
 except Exception as exc:raise HTTPException(422,str(exc))
 if len(datasets)==1:return RedirectResponse(f'/inbox/files/{file_id}/inspect/report?dataset={datasets[0].name}',303)
 return render_template(request,'inspect_select.html',{'file':item,'datasets':datasets})
@app.get('/inbox/files/{file_id}/inspect/report')
def inspect_report(request:Request,file_id:int,dataset:str|None=None):
 try:report=inspection.inspect(file_id,dataset)
 except Exception as exc:raise HTTPException(422,str(exc))
 return render_template(request,'inspect_report.html',{'report':report})
@app.get('/api/inbox/files/{file_id}/datasets')
def api_datasets(file_id:int):
 item,datasets=inspection.datasets(file_id);return {'file_id':file_id,'filename':item['original_filename'],'datasets':[x.__dict__ for x in datasets]}
@app.get('/api/inbox/files/{file_id}/inspection')
def api_inspection(file_id:int,dataset:str|None=None):return inspection.inspect(file_id,dataset).__dict__
@app.get('/inbox/files/{file_id}/structure')
def structure_page(request:Request,file_id:int,dataset:str):
 data=statement_import.analyze(file_id,dataset);return render_template(request,'structure.html',{'data':data})
@app.post('/inbox/files/{file_id}/structure')
async def structure_confirm(request:Request,file_id:int):
 form=await request.form();dataset=form['dataset'];structure=StatementStructure(int(form['header_row']),int(form['data_start_row']),int(form['data_end_row']) if form.get('data_end_row') else None,1,int(form['document_header_end']) if form.get('document_header_end') else None);signature,columns,preview=statement_import.preview_mapping(file_id,dataset,structure);return render_template(request,'mapping.html',{'file_id':file_id,'dataset':dataset,'structure':structure,'signature':signature,'columns':columns,'preview':preview,'databases':catalog.databases(),'default_auto':True})
@app.post('/imports/create-table')
async def create_from_file(request:Request):
 form=await request.form();file_id=int(form['file_id']);dataset=form['dataset'];structure=StatementStructure(int(form['header_row']),int(form['data_start_row']),int(form['data_end_row']) if form.get('data_end_row') else None,1,int(form['document_header_end']) if form.get('document_header_end') else None);count=int(form['column_count']);columns=[MappingColumn(i,form[f'source_{i}'],form[f'target_{i}'],form[f'type_{i}'],form.get(f'nullable_{i}')=='true') for i in range(count)];template_id=None
 if form.get('save_template')=='true':template_id=statement_import.save_template(form['template_name'],file_id,dataset,structure,columns,form.get('auto_process_allowed')=='true')
 try:job,inserted=statement_import.import_new_table(file_id,int(form['database_id']),dataset,form['target_table'],structure,columns,template_id)
 except Exception as exc:raise HTTPException(422,str(exc))
 return render_template(request,'import_result.html',{'job_id':job,'inserted':inserted,'target_table':form['target_table']})
@app.get('/imports/history')
def import_history(request:Request):return render_template(request,'import_history.html',{'jobs':import_repo.jobs(),'templates':import_repo.templates()})
@app.get('/inbox/approvals/{token}')
def inbox_approval(request:Request,token:str):
 item=inbox.get_approval(token)
 if not item:raise HTTPException(404,'Approval not found or already resolved')
 return render_template(request,'inbox_approval.html',{'approval':dict(item)})
@app.post('/inbox/approvals/{token}/approve')
def inbox_approve(token:str): fid=inbox.approve_alias(token);return RedirectResponse(f'/inbox/files/{fid}',303)
@app.post('/inbox/approvals/{token}/reject')
def inbox_reject(token:str): inbox.reject_alias(token);return RedirectResponse('/inbox?decision=rejected&message=Alias registration rejected.',303)
@app.get('/api/inbox/files')
def api_inbox_files():return inbox.list_files()
@app.get('/api/inbox/files/{file_id}')
def api_inbox_file(file_id:int):
 item=inbox.get_file(file_id)
 if not item:raise HTTPException(404,'Inbox file not found')
 return item
@app.get('/health/live')
def live(): return {'status':'alive'}
@app.get('/health/ready')
def readiness():
 result=ready.check();return JSONResponse(result,status_code=200 if result['status']=='ready' else 503)
@app.get('/metrics',response_class=PlainTextResponse)
def metrics(): return PlainTextResponse(obs.metrics.render_prometheus(),media_type='text/plain; version=0.0.4')
@app.get('/')
def home(request:Request):return render_template(request,'index.html',{'tenants':catalog.tenants(),'databases':catalog.databases(),'engines':[x.engine_name for x in provisioners]})
@app.post('/tenants')
def tenant(name:str=Form(...),slug:str=Form(...)):
 try:
  tenant_id=catalog.create_tenant(name,slug);obs.event('audit.tenant.created',tenant_id=tenant_id,slug=slug);obs.count('controlplane_tenants_created_total')
 except sqlite3.IntegrityError:raise HTTPException(409,'Tenant exists')
 return RedirectResponse('/',303)
@app.post('/databases')
def provision(tenant_id:int=Form(...),name:str=Form(...),engine:str=Form(...),owner_password:str=Form('')):
 t=catalog.tenant(tenant_id)
 if not t:raise HTTPException(404,'Tenant not found')
 try:
  database_id=ps.provision(DatabaseRequest(tenant_id,t['slug'],name,DatabaseEngine(engine),{'owner_password':owner_password}));obs.event('audit.database.provisioned',tenant_id=tenant_id,database_id=database_id,engine=engine);obs.count('controlplane_database_operations_total',{'operation':'provision','engine':engine,'result':'success'})
 except Exception as e:raise HTTPException(422,str(e))
 return RedirectResponse('/',303)
@app.post('/databases/{i}/backup')
def backup(i:int):
 result=ps.backup(i);db=catalog.get_database(i);obs.event('audit.database.backup.created',database_id=i,engine=db.engine.value,size_bytes=result.size_bytes);obs.count('controlplane_database_operations_total',{'operation':'backup','engine':db.engine.value,'result':'success'});return RedirectResponse('/',303)
@app.get('/databases/{i}/manage')
def manage(request:Request,i:int,table:str|None=None,page:int=1):
 ts=dm.list_tables(i);selected=table or (ts[0]['name'] if ts else None);content=dm.read_rows(i,selected,page,50) if selected else None
 return render_template(request,'manage.html',{'database':catalog.get_database(i),'tables':ts,'content':content,'types':[x.value for x in LogicalType],'cap':dm.capabilities(i)})
@app.post('/databases/{i}/tables')
def create_table(i:int,name:str=Form(...),columns_json:str=Form(...)):
 try:
  raw=json.loads(columns_json);cols=[ColumnDefinition(x['name'],LogicalType(x['logical_type']),x.get('nullable',True),x.get('primary_key',False),x.get('generated',False)) for x in raw];dm.create_table(i,TableDefinition(name,cols))
 except Exception as e:
  obs.event('table.creation.failed',severity='error',database_id=i,table=name,error_type=type(e).__name__);raise HTTPException(422,str(e))
 obs.event('audit.table.created',database_id=i,table=name);obs.count('controlplane_data_operations_total',{'operation':'create_table','result':'success'});return RedirectResponse(f'/databases/{i}/manage?table={name}',303)
@app.post('/databases/{i}/tables/{table}/rows')
async def insert(request:Request,i:int,table:str):dm.insert_row(i,table,dict(await request.form()));return RedirectResponse(f'/databases/{i}/manage?table={table}',303)
@app.post('/databases/{i}/tables/{table}/rows/{key}')
async def update(request:Request,i:int,table:str,key:str):dm.update_row(i,table,key,dict(await request.form()));return RedirectResponse(f'/databases/{i}/manage?table={table}',303)
@app.post('/databases/{i}/tables/{table}/rows/{key}/delete')
def delete(i:int,table:str,key:str):dm.delete_row(i,table,key);return RedirectResponse(f'/databases/{i}/manage?table={table}',303)
@app.post('/databases/{i}/tables/{table}/columns')
def addcol(i:int,table:str,name:str=Form(...),logical_type:str=Form(...),nullable:bool=Form(False)):
 dm.add_column(i,table,ColumnDefinition(name,LogicalType(logical_type),nullable));return RedirectResponse(f'/databases/{i}/manage?table={table}',303)
@app.post('/databases/{i}/tables/{table}/columns/{old}/alter')
def alter(i:int,table:str,old:str,new_name:str=Form(...),logical_type:str=Form(...),nullable:bool=Form(False)):
 dm.alter_column(i,table,old,ColumnDefinition(new_name,LogicalType(logical_type),nullable));return RedirectResponse(f'/databases/{i}/manage?table={table}',303)
@app.get('/api/databases/{i}/tables')
def api_tables(i:int):return dm.list_tables(i)
@app.get('/api/databases/{i}/tables/{table}/rows')
def api_rows(i:int,table:str,page:int=1,page_size:int=50):return dm.read_rows(i,table,page,page_size)
