# -*- coding: utf-8 -*-
"""make_sample_data.py — 生成『合成』港股 1 分鐘 K 線, 只用來驗證引擎機制 (不是真實 07709 數據!)
真實數據請用 futu_niuniu/futu_fetch_and_backtest.py 或 webull/webull_fetch_and_backtest.py 抓取。"""
import numpy as np, pandas as pd, os

def make_day(day: str, start_px: float, rng: np.random.Generator) -> pd.DataFrame:
    times = list(pd.date_range(f'{day} 09:30', f'{day} 11:59', freq='1min')) + list(pd.date_range(f'{day} 13:00', f'{day} 15:59', freq='1min'))
    n = len(times)
    # 慢波(趨勢) + 中波(30-60分鐘擺動) + 雜訊, 貼近附圖那種一日內數個波段
    t = np.arange(n)
    drift = rng.normal(0, 0.0004, n).cumsum()
    swing = 0.012 * np.sin(2 * np.pi * t / rng.integers(70, 110)) + 0.006 * np.sin(2 * np.pi * t / rng.integers(25, 45) + rng.uniform(0, 6))
    noise = rng.normal(0, 0.0012, n)
    px = start_px * (1 + drift + swing + noise)
    o = np.r_[px[0], px[:-1]]
    hi = np.maximum(o, px) * (1 + np.abs(rng.normal(0, 0.0006, n)))
    lo = np.minimum(o, px) * (1 - np.abs(rng.normal(0, 0.0006, n)))
    vol = rng.integers(5000, 60000, n)
    return pd.DataFrame({'datetime': times, 'open': o.round(3), 'high': hi.round(3), 'low': lo.round(3), 'close': px.round(3), 'volume': vol})

if __name__ == '__main__':
    rng = np.random.default_rng(7)
    days = pd.bdate_range('2026-09-01', '2026-09-18')
    px = 43.0; frames = []
    for dday in days:
        f = make_day(str(dday.date()), px, rng); frames.append(f); px = float(f['close'].iloc[-1]) * (1 + rng.normal(0, 0.01))
    df = pd.concat(frames, ignore_index=True)
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/SYNTHETIC_HK_1min.csv', index=False)
    print('寫出 data/SYNTHETIC_HK_1min.csv', len(df), '根, 日數', len(days), '(合成數據, 僅供引擎自測)')
