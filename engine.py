# -*- coding: utf-8 -*-
"""
Easy/Hard Money 50年月度制度引擎 (work-from-back-end)
數據: Fama-French市場報酬1926-2018 + 文檔化SPX 2019-2025 + 工作簿NDX代理2026
     信用利差BAA-AAA 1919-2018 / HY OAS 2016-2026(工作簿真實數據)
     核心CPI、Fed政策步階(07表方法論)、10Y-3M倒掛episode
判區: 合成分 >=70 EASY / 40-70 UNCERTAIN / <=40 HARD (沿用附件刻度)
策略: 進入EASY買入, 離開EASY賣出 (月末訊號, 次月初執行等價於月末執行)
"""
import pandas as pd, numpy as np

D = 'data/'

# ---------------- 1. spliced monthly market return series ----------------
ff = pd.read_csv(D+'ff_market_monthly.csv'); ff['ym'] = pd.PeriodIndex(ff['ym'], freq='M')
sp = pd.read_csv(D+'spx_recent_monthly.csv'); sp['ym'] = pd.PeriodIndex(sp['ym'], freq='M')
wbm = pd.read_csv(D+'workbook_monthly.csv'); wbm['ym'] = pd.PeriodIndex(wbm['ym'], freq='M')

sp['spx_ret'] = sp['spx'].pct_change()
rets = []
for ym in pd.period_range('1926-08', '2026-07', freq='M'):
    if ym <= pd.Period('2018-11'):
        r = ff.loc[ff.ym == ym, 'mkt_ret']
        src = 'FF_market_TR'
    elif ym <= pd.Period('2025-12'):
        r = sp.loc[sp.ym == ym, 'spx_ret']
        src = 'SPX_documented' if ym < pd.Period('2025-10') else 'SPX_approx'
    else:
        r = wbm.loc[wbm.ym == ym, 'ndx_ret']
        src = 'NDX_proxy(workbook)'
    if len(r) and pd.notna(r.iloc[0]):
        rets.append({'ym': ym, 'ret': float(r.iloc[0]), 'src': src})
mkt = pd.DataFrame(rets)
mkt['index'] = 100.0 * (1.0 + mkt['ret']).cumprod()

# ---------------- 2. indicators (month-end, no lookahead) ----------------
mkt['sma10'] = mkt['index'].rolling(10).mean()
mkt['above_sma'] = mkt['index'] / mkt['sma10'] - 1.0
mkt['sma_rising'] = mkt['sma10'].diff() > 0
mkt['ret12'] = mkt['index'].pct_change(12)
mkt['vol6'] = mkt['ret'].rolling(6).std() * np.sqrt(12) * 100  # annualized %

cred = pd.read_csv(D+'credit_monthly.csv'); cred['ym'] = pd.PeriodIndex(cred['ym'], freq='M')
cred['baa_aaa_chg6'] = cred['baa_aaa'].diff(6)
cpi = pd.read_csv(D+'corecpi_monthly.csv'); cpi['ym'] = pd.PeriodIndex(cpi['ym'], freq='M')
cpix = pd.read_csv(D+'cpi_extension_monthly.csv'); cpix['ym'] = pd.PeriodIndex(cpix['ym'], freq='M')
cpi_all = pd.concat([cpi[cpi.ym <= pd.Period('2018-11')][['ym','cpi_yoy']], cpix[['ym','cpi_yoy']]])
cpi_all = cpi_all.drop_duplicates('ym').sort_values('ym')
cpi_all['cpi_chg6'] = cpi_all['cpi_yoy'].diff(6)
pol = pd.read_csv(D+'fed_policy_steps.csv'); pol['ym'] = pd.PeriodIndex(pol['ym'], freq='M')
curve = pd.read_csv(D+'curve_monthly.csv'); curve['ym'] = pd.PeriodIndex(curve['ym'], freq='M')
wbm['hyoas_chg6'] = wbm['hyoas'].diff(6) if 'hyoas' in wbm else np.nan

df = mkt.merge(cred[['ym','baa_aaa','baa_aaa_chg6']], on='ym', how='left') \
        .merge(cpi_all, on='ym', how='left') \
        .merge(curve, on='ym', how='left') \
        .merge(wbm[['ym','hyoas','hyoas_chg6','vix','breadth']], on='ym', how='left')
# policy step -> monthly code (LOOKUP style like 07 sheet)
pol = pol.sort_values('ym')
df['policy'] = np.nan
for _, row in pol.iterrows():
    df.loc[df.ym >= row['ym'], 'policy'] = row['code']

# ---------------- 3. sub-scores 0/50/100 (work-from-back-end calibrated) ----------------
def s_trend(r):
    if pd.isna(r['above_sma']): return np.nan
    if r['above_sma'] > 0.02 and r['sma_rising']: return 100
    if r['above_sma'] > -0.02: return 50
    return 0

def s_mom(r):
    if pd.isna(r['ret12']): return np.nan
    if r['ret12'] > 0.05: return 100
    if r['ret12'] > 0.0: return 50
    return 0

def s_credit(r):
    # era B: HY OAS (workbook thresholds) from 2019-01; era A: BAA-AAA
    if r['ym'] >= pd.Period('2019-01') and pd.notna(r['hyoas']):
        lvl, chg = r['hyoas'], r['hyoas_chg6']
        if lvl < 350 and (pd.isna(chg) or chg < 50): return 100
        if lvl <= 450: return 50
        return 0
    if pd.isna(r['baa_aaa']): return np.nan
    lvl, chg = r['baa_aaa'], r['baa_aaa_chg6']
    if lvl < 0.95 and (pd.isna(chg) or chg < 0.20): return 100
    if lvl <= 1.35 and (pd.isna(chg) or chg < 0.40): return 50
    return 0

def s_policy(r):
    return {1: 100, 0: 50, -1: 0}.get(r['policy'], np.nan)

def s_curve(r):
    if pd.isna(r['curve_inverted']): return np.nan
    return 0 if r['curve_inverted'] == 1 else 100

def s_infl(r):
    y, c = r['cpi_yoy'], r['cpi_chg6']
    if pd.isna(y): return np.nan
    falling = pd.notna(c) and c < -0.3
    if y < 4.0 or (y < 6.0 and falling): return 100
    if y <= 6.0 or falling: return 50
    return 0

def s_vol(r):
    if pd.isna(r['vol6']): return np.nan
    if r['vol6'] < 15: return 100
    if r['vol6'] <= 25: return 50
    return 0

SUBS = {'TREND': (s_trend, 30), 'MOM': (s_mom, 10), 'CREDIT': (s_credit, 20),
        'POLICY': (s_policy, 15), 'CURVE': (s_curve, 10), 'INFL': (s_infl, 10),
        'VOL': (s_vol, 5)}

for k, (fn, w) in SUBS.items():
    df['s_'+k] = df.apply(fn, axis=1)

def composite(r):
    num = den = 0.0
    for k, (fn, w) in SUBS.items():
        v = r['s_'+k]
        if pd.notna(v):
            num += w * v; den += w
    return num/den if den >= 60 else np.nan  # dynamic denominator like workbook T5 rule

df['score'] = df.apply(composite, axis=1)
df['zone'] = np.where(df['score'] >= 70, 'EASY', np.where(df['score'] > 40, 'UNCERTAIN', 'HARD'))
df.loc[df['score'].isna(), 'zone'] = 'NA'

df.to_csv(D+'engine_monthly.csv', index=False)

# ---------------- 4. work-from-back-end validation: good-period capture ----------------
df['fwd12'] = df['index'].shift(-12) / df['index'] - 1.0
bt = df[(df.ym >= pd.Period('1976-07')) & (df.ym <= pd.Period('2026-07'))].copy()
gp = bt.dropna(subset=['fwd12'])
print('=== 好表現月份 (fwd12m>+10%) 的判區分布 ===')
print(gp[gp.fwd12 > 0.10].zone.value_counts(normalize=True).round(3).to_dict())
print('=== 壞表現月份 (fwd12m<-10%) 的判區分布 ===')
print(gp[gp.fwd12 < -0.10].zone.value_counts(normalize=True).round(3).to_dict())
print('=== 各判區的平均前瞻12月報酬 ===')
print(gp.groupby('zone').fwd12.agg(['mean','median','count']).round(4))

# ---------------- 5. backtest: buy on entering EASY, sell on leaving EASY ----------------
def backtest(bt, entry_zone='EASY', exit_when=lambda z: z != 'EASY', label=''):
    pos = False; trades = []; entry_idx = None; entry_ym = None; entry_val = None
    eq = []; equity = 1.0
    rows = bt.reset_index(drop=True)
    for i in range(len(rows) - 1):
        z = rows.loc[i, 'zone']
        nxt_ret = rows.loc[i+1, 'ret']
        if not pos and z == entry_zone:
            pos = True; entry_ym = rows.loc[i, 'ym']; entry_val = equity
        elif pos and exit_when(z):
            trades.append({'entry': str(entry_ym), 'exit': str(rows.loc[i, 'ym']),
                           'ret': equity/entry_val - 1.0})
            pos = False
        if pos:
            equity *= (1.0 + nxt_ret)
        eq.append({'ym': rows.loc[i, 'ym'], 'equity': equity, 'in_mkt': pos})
    if pos:
        trades.append({'entry': str(entry_ym), 'exit': str(rows.loc[len(rows)-1,'ym'])+'(open)',
                       'ret': equity/entry_val - 1.0})
    tr = pd.DataFrame(trades)
    eqd = pd.DataFrame(eq)
    yrs = len(eqd)/12
    bh = (1+rows['ret'].iloc[1:]).prod()
    strat_cagr = equity**(1/yrs) - 1
    bh_cagr = bh**(1/yrs) - 1
    roll = eqd['equity'].cummax(); mdd = (eqd['equity']/roll - 1).min()
    bh_eq = (1+rows['ret'].iloc[1:]).cumprod(); bh_mdd = (bh_eq/bh_eq.cummax()-1).min()
    win = (tr['ret'] > 0).mean() if len(tr) else np.nan
    pf = tr.loc[tr.ret>0,'ret'].sum() / abs(tr.loc[tr.ret<=0,'ret'].sum()) if (tr.ret<=0).any() else np.inf
    print(f"\n===== 回測 {label} ({rows.ym.iloc[0]}..{rows.ym.iloc[-1]}, {yrs:.1f}年) =====")
    print(f"交易次數: {len(tr)} | WIN RATE: {win:.1%} | 平均每筆: {tr.ret.mean():.2%} | 中位: {tr.ret.median():.2%}")
    print(f"平均獲利: {tr.loc[tr.ret>0,'ret'].mean():.2%} | 平均虧損: {tr.loc[tr.ret<=0,'ret'].mean() if (tr.ret<=0).any() else 0:.2%} | 盈虧因子: {pf:.2f}")
    print(f"策略總報酬: {equity-1:.1%} | CAGR: {strat_cagr:.2%} | MaxDD: {mdd:.1%} | 在市場時間: {eqd.in_mkt.mean():.1%}")
    print(f"買入持有 CAGR: {bh_cagr:.2%} | 買入持有 MaxDD: {bh_mdd:.1%}")
    return tr, eqd

tr1, eq1 = backtest(bt, exit_when=lambda z: z != 'EASY', label='主策略: 離開EASY即賣出')
tr2, eq2 = backtest(bt, exit_when=lambda z: z == 'HARD', label='對照: 跌入HARD才賣出')
tr1.to_csv(D+'trades_main.csv', index=False)
tr2.to_csv(D+'trades_hard_exit.csv', index=False)
eq1.to_csv(D+'equity_main.csv', index=False)

print('\n=== 全期判區分布 (1976-07..2026-07) ===')
print(bt.zone.value_counts().to_dict())
print('\n=== 主策略逐筆交易 ===')
print(tr1.to_string())
