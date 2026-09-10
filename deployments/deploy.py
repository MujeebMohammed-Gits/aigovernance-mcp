#!/usr/bin/env python3
import os, sys, json
from pathlib import Path
os.chdir('C:/AI Projects/research-agent')
PROJECT_ROOT = Path('.')
for d in [PROJECT_ROOT/'logs', PROJECT_ROOT/'config', PROJECT_ROOT/'deployments']:
    d.mkdir(parents=True, exist_ok=True)
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT/'.env', override=True)
except:
    pass
sys.path.insert(0, str(PROJECT_ROOT))
from config import validate_config, get_config_summary, validate_required_keys
print('Deployment script ready')
