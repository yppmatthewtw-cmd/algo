# -*- coding: utf-8 -*-
"""config_loader.py — 讀 config.json, 組出 Params 與標的資訊 (三平台共用)"""
import json, os
from macd_momentum_core import Params

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get('MACD_CONFIG', os.path.join(HERE, 'config.json'))

def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def params_from_config(cfg: dict, overrides: dict | None = None) -> Params:
    market = cfg['symbol']['market']
    sess = {k: v for k, v in cfg['session'][market].items() if k != 'tz'}
    kw = {**cfg['strategy'], **sess, 'tick': cfg['symbol'].get('tick', 0.01)}
    tf = cfg.get('timeframe', {})
    preset = tf.get('presets', {}).get(tf.get('current', ''), {})
    kw.update(preset)
    kw['initial_capital'] = cfg.get('backtest', {}).get('initial_capital', 100000.0)
    if overrides:
        kw.update({k: v for k, v in overrides.items() if v is not None})
    return Params(**kw)

def describe(cfg: dict) -> str:
    s = cfg['symbol']
    return f"{s['name']} | 牛牛 {s['futu_code']} | Webull {s['webull_symbol']}({s['webull_category']}) | TV {s['tradingview']} | 市場 {s['market']}"

CFG = load_config()
