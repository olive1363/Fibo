from pathlib import Path
import json, time
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
SYMBOLS = {"MSTR":"MSTR", "AAPL":"AAPL", "TSLA":"TSLA", "GLD":"GLD", "SP500":"^GSPC"}

def rows_from_df(df):
    if df is None or df.empty:
        return []
    if getattr(df.columns, "nlevels", 1) > 1:
        df.columns = df.columns.get_level_values(0)
    out=[]
    for idx, r in df.iterrows():
        try:
            ts = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
            if ts.tzinfo is None:
                import datetime as _dt
                ts = ts.replace(tzinfo=_dt.timezone.utc)
            ms=int(ts.timestamp()*1000)
            o=float(r["Open"]); h=float(r["High"]); l=float(r["Low"]); c=float(r["Close"])
            v=float(r.get("Volume",0) or 0)
            if all(map(lambda x: x==x, [o,h,l,c])):
                out.append({"ms":ms,"open":o,"high":h,"low":l,"close":c,"volume":v})
        except Exception:
            continue
    return out

def download(symbol, interval, period):
    last=None
    for attempt in range(3):
        try:
            df=yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False, threads=False, prepost=False)
            rows=rows_from_df(df)
            if len(rows)>=20:
                return rows
            last=RuntimeError(f"only {len(rows)} rows")
        except Exception as e:
            last=e
        time.sleep(3*(attempt+1))
    raise last or RuntimeError("download failed")

errors=[]
for asset,symbol in SYMBOLS.items():
    for kind,interval,period in [("1h","1h","2y"),("1d","1d","10y")]:
        try:
            rows=download(symbol,interval,period)
            payload={"asset":asset,"symbol":symbol,"interval":kind,"market_mode":"regular_session","prepost":False,"updated_at":__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),"rows":rows}
            (DATA/f"{asset}_{kind}.json").write_text(json.dumps(payload,separators=(",",":")),encoding="utf-8")
            print(asset,kind,len(rows))
        except Exception as e:
            errors.append(f"{asset} {kind}: {e}")
if errors:
    raise SystemExit("\n".join(errors))
