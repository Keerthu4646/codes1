import os
import yaml
from dotenv import load_dotenv
 
load_dotenv()
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
 
with open(os.path.join(_BASE_DIR, "config.yaml"), encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)
 
 
def env(name, default=None):
    return os.environ.get(name, default)