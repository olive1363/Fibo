#!/usr/bin/env python3
import json, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DATA.mkdir(parents=True, exist_ok=True)
ASSETS = {'BTC': ('BTCUSDT', 4000), 'ETH': ('ETHUSDT', 2200)}

def get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 FiboSwanny/1.0','Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def norm(rows):
    d={int(x['ms']):x for x in rows if x.get('close',0)>0}
    return [d[k] for k in sorted(d)]

def binance(symbol, target):
    out=[]; end_ms=int(time.time()*1000)
    while len(out)<target:
        lim=min(1000,target-len(out))
        q=urllib.parse.urlencode({'symbol':symbol,'interval':'4h','limit':lim,'endTime':end_ms})
        j=get_json('https://api.binance.com/api/v3/klines?'+q)
        if not isinstance(j,list) or not j: break
        batch=[{'ms':int(r[0]),'open':float(r[1]),'high':float(r[2]),'low':float(r[3]),'close':float(r[4]),'volume':float(r[5])} for r in j]
        out=batch+out
        end_ms=int(j[0][0])-1
        if len(j)<lim: break
        time.sleep(.15)
    return norm(out)[-target:]

def cryptocompare(asset, target):
    out=[]; to_ts=None
    while len(out)<target:
        lim=min(1800,target-len(out))
        params={'fsym':asset,'tsym':'USD','limit':lim,'aggregate':4,'e':'CCCAGG'}
        if to_ts is not None: params['toTs']=to_ts
        j=get_json('https://min-api.cryptocompare.com/data/v2/histohour?'+urllib.parse.urlencode(params))
        arr=((j or {}).get('Data') or {}).get('Data') or []
        if not arr: break
        batch=[{'ms':int(r['time'])*1000,'open':float(r['open']),'high':float(r['high']),'low':float(r['low']),'close':float(r['close']),'volume':float(r.get('volumefrom') or 0)} for r in arr if float(r.get('close') or 0)>0]
        out=batch+out
        to_ts=int(arr[0]['time'])-1
        if len(arr)<lim: break
        time.sleep(.15)
    return norm(out)[-target:]

def load(asset, symbol, target):
    errors=[]
    for fn in (lambda:binance(symbol,target), lambda:cryptocompare(asset,target)):
        try:
            rows=fn()
            if len(rows)>=100:
                return rows
        except Exception as e:
            errors.append(str(e))
    raise RuntimeError(asset+': '+' | '.join(errors))

def main():
    for asset,(symbol,target) in ASSETS.items():
        rows=load(asset,symbol,target)
        payload={'asset':asset,'timeframe':'4h','updatedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'rows':rows}
        path=DATA/f'{asset}_4h.json'
        path.write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
        start=time.strftime('%Y-%m-%d',time.gmtime(rows[0]['ms']/1000)) if rows else 'n/a'
        end=time.strftime('%Y-%m-%d',time.gmtime(rows[-1]['ms']/1000)) if rows else 'n/a'
        print(f'{asset}: {len(rows)} candles, {start} -> {end}')

if __name__=='__main__': main()
