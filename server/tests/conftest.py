import os,tempfile
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db')
os.environ['PUBLIC_URL']='http://localhost:8000'
os.environ['BENCHMARK_SIGNING_KEY']='AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=' # Test fixture only.
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.security import local
@pytest.fixture(scope="session")
def client():
    with TestClient(app,base_url='http://localhost:8000') as c:yield c
@pytest.fixture(autouse=True)
def clear_limits():
    local.clear()
