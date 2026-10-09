import os
from pathlib import Path

BASE = Path(__file__).parent
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./omni.db')
PUBLIC_URL = os.getenv('PUBLIC_URL', 'http://localhost:8000').rstrip('/')
SECRET = os.getenv('APP_SECRET', '')
REDIS_URL = os.getenv('REDIS_URL', '')
RENDERER_URL = os.getenv('RENDERER_URL', '')
PRODUCTION = os.getenv('ENVIRONMENT') == 'production'
CONTROLLER = os.getenv('CONTROLLER_NAME', '')
CONTACT = os.getenv('CONTACT_EMAIL', '')
if PRODUCTION and (len(SECRET) < 32 or not CONTROLLER or not CONTACT or not PUBLIC_URL.startswith('https://') or not REDIS_URL):
    raise RuntimeError('Production requires APP_SECRET (32+ characters), HTTPS PUBLIC_URL, REDIS_URL, CONTROLLER_NAME and CONTACT_EMAIL.')
SECRET = SECRET or 'development-only-do-not-deploy-this-secret'
