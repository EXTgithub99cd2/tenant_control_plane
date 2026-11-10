from fastapi.testclient import TestClient
from app import app
client=TestClient(app)
def test_observability_endpoints():
    for path in ('/','/health/live','/health/ready','/metrics','/observability'):
        response=client.get(path);assert response.status_code==200,(path,response.text)
        assert response.headers.get('x-correlation-id')
def test_metrics_after_labeled_request():
    client.get('/health/live',headers={'X-Correlation-ID':'test-correlation'})
    response=client.get('/metrics');assert 'controlplane_http_requests_total{' in response.text
