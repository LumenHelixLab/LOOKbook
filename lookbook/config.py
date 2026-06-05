"""lookBOOK configuration loader."""

import os
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

_CONFIG = None


def get_config():
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    config_path = Path(__file__).parent / 'config.yaml'
    defaults = {
        'vision': {
            'provider': 'openai',
            'model': 'gpt-4o',
            'max_tokens': 2048,
            'temperature': 0.3,
        },
        'fallback': {'enabled': True, 'provider': 'classical'}
    }

    if yaml and config_path.exists():
        with open(config_path) as f:
            loaded = yaml.safe_load(f) or {}
        defaults['vision'].update(loaded.get('vision', {}))
        defaults['fallback'].update(loaded.get('fallback', {}))

    # Override with env vars
    if os.getenv('LOOKBOOK_VISION_PROVIDER'):
        defaults['vision']['provider'] = os.getenv('LOOKBOOK_VISION_PROVIDER')
    if os.getenv('LOOKBOOK_VISION_MODEL'):
        defaults['vision']['model'] = os.getenv('LOOKBOOK_VISION_MODEL')

    _CONFIG = defaults
    return _CONFIG


def get_api_key(provider: str) -> str:
    env_map = {
        'openai': 'OPENAI_API_KEY',
        'claude': 'ANTHROPIC_API_KEY',
        'gemini': 'GOOGLE_API_KEY',
    }
    return os.getenv(env_map.get(provider, ''), '')
