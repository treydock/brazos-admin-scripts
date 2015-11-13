import os
import yaml

CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "etc"))

def load_config():
    if os.getenv('CONFIG_YML'):
        config_path = os.getenv('CONFIG_YML')
    else:
        config_path = os.path.join(CONFIG_DIR, "settings.yml")

    with open(config_path, 'r') as f:
        config = yaml.load(f)

    return config
