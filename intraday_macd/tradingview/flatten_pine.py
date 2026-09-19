# -*- coding: utf-8 -*-
"""flatten_pine.py — 把 Pine 檔的「延續行」全部合併回前一行, 令檔案可以任意複製貼上而不會斷句。
Pine 規則: 縮排不是 4 的倍數的行 = 上一行的延續。某些複製路徑會改動這種縮排 → "Missing closing parenthesis"。
攤平後語意完全相同 (Pine 不在乎一行多長), 但不再依賴延續行縮排。
用法: python3 flatten_pine.py <in.pine> <out.pine> [--restamp MM.DD;HH:MM]"""
import io, re, sys

def flatten(src: str) -> str:
    out = []
    for ln in src.split('\n'):
        stripped = ln.lstrip(' ')
        ind = len(ln) - len(stripped)
        is_cont = ind > 0 and ind % 4 != 0 and stripped != '' and not stripped.startswith('//')
        if is_cont and out:
            # 往回找最近一個非空、非純註解的行, 接上去
            j = len(out) - 1
            while j >= 0 and (out[j].strip() == '' or out[j].lstrip().startswith('//')):
                j -= 1
            out[j] = out[j].rstrip() + ' ' + stripped.rstrip()
        else:
            out.append(ln.rstrip())
    return '\n'.join(out)

def verify(src: str) -> list[str]:
    """回傳問題清單; 空 = 通過"""
    probs = []
    L = src.split('\n')
    for i, ln in enumerate(L, 1):
        s = ln.lstrip(' '); ind = len(ln) - len(s)
        if ind > 0 and ind % 4 != 0 and s and not s.startswith('//'):
            probs.append(f'L{i}: 仍有延續行 ({ind}格)')
    if '\t' in src: probs.append('含 tab')
    if '\u00a0' in src: probs.append('含 NBSP')
    for i, ln in enumerate(L, 1):
        body = re.sub(r'"(?:[^"\\]|\\.)*"', '""', ln.split('//')[0] if not ln.lstrip().startswith('//') else '')
        if body.count('(') != body.count(')') or body.count('[') != body.count(']'):
            probs.append(f'L{i}: 括號不配對 → {ln.strip()[:70]}')
    return probs

if __name__ == '__main__':
    src_p, dst_p = sys.argv[1], sys.argv[2]
    stamp = sys.argv[sys.argv.index('--restamp') + 1] if '--restamp' in sys.argv else None
    s = io.open(src_p, encoding='utf-8').read()
    flat = flatten(s)
    if stamp:
        old = re.search(r'\((\d\d\.\d\d;\d\d:\d\d)\)', flat).group(1)
        flat = flat.replace(old, stamp)
        hh, mm = stamp.split(';')[1].split(':')
        flat = re.sub(r'建於 2026-\d\d-\d\d \d\d:\d\d HKT', f'建於 2026-{stamp[:2]}-{stamp[3:5]} {hh}:{mm} HKT', flat)
    io.open(dst_p, 'w', encoding='utf-8').write(flat)
    probs = verify(flat)
    print(f'{src_p} → {dst_p}: {len(s.splitlines())} 行 → {len(flat.splitlines())} 行')
    print('驗證:', 'PASS ✓' if not probs else '\n  ' + '\n  '.join(probs))
    sys.exit(0 if not probs else 1)
