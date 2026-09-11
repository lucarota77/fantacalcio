#!/usr/bin/env python3
"""De-vig multi-bookmaker, gol attesi (Poisson), clean sheet. Input: dati.json"""
import json, math, sys
from statistics import mean, pstdev

def solve_lambda(p_over, line):
    k = int(math.floor(line)); lo, hi = .05, 8.
    for _ in range(200):
        m = (lo+hi)/2
        cum = sum(math.exp(-m)*m**i/math.factorial(i) for i in range(k+1))
        if (1-cum) < p_over: lo = m
        else: hi = m
    return (lo+hi)/2

def split_lambda(tot, ph_target):
    lo, hi = .05, tot-.05
    for _ in range(200):
        lh = (lo+hi)/2; la = tot-lh
        ph = sum(math.exp(-lh)*lh**i/math.factorial(i)*math.exp(-la)*la**j/math.factorial(j)
                 for i in range(9) for j in range(9) if i > j)
        if ph < ph_target: lo = lh
        else: hi = lh
    lh = (lo+hi)/2
    return lh, tot-lh

BOOKS = ['bwin', 'snai']
D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'dati.json'))
out = {}
for m in D['matches']:
    p1s, pxs, p2s, lams, margins = [], [], [], [], {}
    for b in BOOKS:
        if b not in m: continue
        q1, qx, q2 = m[b]['odds']; M = 1/q1+1/qx+1/q2; margins[b] = M
        p1s.append((1/q1)/M); pxs.append((1/qx)/M); p2s.append((1/q2)/M)
        o, u, line = m[b]['ou']; Mou = 1/o+1/u
        lams.append(solve_lambda((1/o)/Mou, line))
    p1, px, p2 = mean(p1s), mean(pxs), mean(p2s)
    s = p1+px+p2; p1, px, p2 = p1/s, px/s, p2/s       # rinormalizza dopo la media
    lam = mean(lams)
    lh, la = split_lambda(lam, p1)
    out[m['name']] = dict(p1=p1, px=px, p2=p2, lam=lam, lam_home=lh, lam_away=la,
        cs_home=math.exp(-la), cs_away=math.exp(-lh), home=m['home'], away=m['away'],
        when=m['when'], books=len(p1s),
        spread1=(max(p1s)-min(p1s)) if len(p1s) > 1 else 0.,
        margins={b: round(v, 4) for b, v in margins.items()},
        Mp={b: v**1.8 for b, v in margins.items()})
print(f"{'PARTITA':<22}{'P(1)':>7}{'P(X)':>7}{'P(2)':>7}{'gol':>6}{'CS-c':>7}{'CS-t':>7}{'spread1':>9}")
print('-'*72)
for k, v in out.items():
    w = ' <<' if v['spread1'] > .03 else ''
    print(f"{k:<22}{v['p1']*100:>6.1f}%{v['px']*100:>6.1f}%{v['p2']*100:>6.1f}%{v['lam']:>6.2f}"
          f"{v['cs_home']*100:>6.1f}%{v['cs_away']*100:>6.1f}%{v['spread1']*100:>8.1f}pt{w}")
json.dump(out, open('/tmp/mstate.json', 'w'))
