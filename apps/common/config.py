"""
Common configuration utilities
Loads configuration from YAML files
"""
import os
import yaml
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent.parent / 'configs'


def load_yaml_config(filename):
    """Load a YAML configuration file"""
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")
    
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def get_symbols_config():
    """Get symbols configuration"""
    config = load_yaml_config('symbols.yaml')
    # Filter only enabled symbols
    enabled_symbols = [s for s in config['symbols'] if s.get('enabled', False)]
    return {
        'symbols': enabled_symbols,
        'global': config.get('global', {})
    }


def get_risk_config():
    """Get risk management configuration"""
    return load_yaml_config('risk.yaml')


def get_sources_config():
    """Get data sources configuration"""
    return load_yaml_config('sources.yaml')


def get_enabled_symbols():
    """Get list of enabled symbol names"""
    config = get_symbols_config()
    return [s['symbol'] for s in config['symbols']]


def get_symbol_config(symbol):
    """Get configuration for a specific symbol"""
    config = get_symbols_config()
    for s in config['symbols']:
        if s['symbol'] == symbol:
            return s
    return None
