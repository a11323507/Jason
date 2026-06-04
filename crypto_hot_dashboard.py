import streamlit as st
import requests
import pandas as pd
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- CORE DATA ENGINE v8 ---

@st.cache_data(ttl=300)
def get_indicators_v8(symbol, interval):
    """Refactored to be 100% free of side-effect expressions."""
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit=100"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if not isinstance(data, list) or len(data) < 60: return None
        
        df = pd.DataFrame(data, columns=['ot','o','h','l','c','v','ct','qv','count','tbb','tbq','i'])
        for col in ['o','h','l','c','v','tbb']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # MACD & MA60
        ma60 = float(df['c'].iloc[-60:].mean())
        exp12 = df['c'].ewm(span=12, adjust=False).mean()
        exp26 = df['c'].ewm(span=26, adjust=False).mean()
        dif = exp12 - exp26
        dea = dif.ewm(span=9, adjust=False).mean()
        hist = dif - dea
        
        # CVD & Stats
        tf_ret = float(((df['c'].iloc[-1] - df['c'].iloc[-2]) / df['c'].iloc[-2]) * 100)
        df['delta'] = 2 * df['tbb'] - df['volume'] if 'volume' in df else 2 * df['tbb'] - df['v']
        cvd_recent = float(df['delta'].iloc[-5:].sum())
        
        # Hist history - explicit loop
        h_hist = []
        for v in hist.iloc[-5:].fillna(0).tolist():
            h_hist.append(float(v))
            
        # Candles - explicit construction
        c_list = []
        raw_rows = df.iloc[-5:][['o','h','l','c']].values.tolist()
        for r in raw_rows:
            c_list.append({'open':r[0], 'high':r[1], 'low':r[2], 'close':r[3]})
        
        return {
            'ma60': ma60, 'dif': float(dif.iloc[-1]), 'dea': float(dea.iloc[-1]),
            'hist': float(hist.iloc[-1]), 'hist_history': h_hist, 'candles': c_list,
            'cvd': cvd_recent, 'tf_ret': tf_ret
        }
    except: return None

def batch_fetch_indicators_v8(symbols):
    intervals = {'H1':'1h','H2':'2h','H4':'4h','H6':'6h','H8':'8h','H12':'12h','D1':'1d'}
    tasks = []
    sym_list = list(symbols)
    if 'BTCUSDT' not in sym_list: sym_list.append('BTCUSDT')
    for s in sym_list:
        for k, v in intervals.items():
            tasks.append((s, k, v))
            
    results = {}
    for s in sym_list: results[s] = {}
    
    with ThreadPoolExecutor(max_workers=40) as executor:
        f_to_t = {executor.submit(get_indicators_v8, t[0], t[2]): t for t in tasks}
        for f in f_to_t:
            t = f_to_t[f]
            try:
                r = f.result()
                results[t[0]][t[1]] = r
            except:
                results[t[0]][t[1]] = None
    return results

def get_top_30_hot_coins():
    try:
        resp = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr", timeout=3)
        d = resp.json(); df = pd.DataFrame(d)
        df['quoteVolume'] = pd.to_numeric(df['quoteVolume'])
        df['lastPrice'] = pd.to_numeric(df['lastPrice'])
        df['priceChangePercent'] = pd.to_numeric(df['priceChangePercent'])
        return df[df['symbol'].str.endswith('USDT')].sort_values(by='quoteVolume', ascending=False).head(30)
    except: return pd.DataFrame()

def format_volume(vol):
    if vol is None: return "--"
    a = abs(vol); s = "-" if vol < 0 else ""
    if a >= 1e9: return f"{s}{a/1e9:.2f}B"
    if a >= 1e6: return f"{s}{a/1e6:.1f}M"
    if a >= 1e3: return f"{s}{a/1e3:.0f}K"
    return f"{s}{a:.1f}"

# --- CHARTING ---

def draw_svg_kline(candles):
    if not candles: return ""
    vals = []
    for c in candles:
        vals.append(c['high'])
        vals.append(c['low'])
    v_min, v_max = min(vals), max(vals); rng = max(v_max - v_min, 1e-9)
    h = 35
    svg = f'<svg width="100%" height="{h}" style="background:rgba(0,0,0,0.2); border-radius:3px; margin-top:5px; border:1px solid #ffffff05;">'
    for i, c in enumerate(candles):
        x = 5 + (i * 19)
        yh, yl = h-((c['high']-v_min)/rng*h), h-((c['low']-v_min)/rng*h)
        yo, yc = h-((c['open']-v_min)/rng*h), h-((c['close']-v_min)/rng*h)
        col = "#00ff88" if c['close'] >= c['open'] else "#ff0055"
        svg += f'<line x1="{x+7}%" y1="{yh}" x2="{x+7}%" y2="{yl}" stroke="{col}" stroke-width="1" />'
        svg += f'<rect x="{x}%" y="{min(yo,yc)}" width="14%" height="{max(abs(yo-yc),1)}" fill="{col}" />'
    return svg + '</svg>'

@st.cache_data(ttl=60)
def fetch_detailed_klines(symbol, interval):
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit=100"
        d = requests.get(url).json(); df = pd.DataFrame(d, columns=['t','o','h','l','c','v','ct','qv','count','tbb','tbq','i'])
        df['time'] = pd.to_datetime(df['t'], unit='ms')
        for col in ['o','h','l','c','v','tbb']: df[col] = pd.to_numeric(df[col])
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=10)
def fetch_market_sentiment(symbol):
    res = {'funding': None, 'oi': None, 'ls': None}
    try:
        f = requests.get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}", timeout=3).json()
        res['funding'] = float(f.get('lastFundingRate', 0)) * 100
    except: pass
    try:
        o = requests.get(f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}", timeout=3).json()
        res['oi'] = float(o.get('openInterest', 0))
    except: pass
    try:
        l = requests.get(f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={symbol}&period=5m&limit=1", timeout=3).json()
        if l: res['ls'] = float(l[0]['longShortRatio'])
    except: pass
    return res

def render_timeframe_chart(symbol, interval, label):
    df = fetch_detailed_klines(symbol, interval)
    if df.empty: st.error(f"DATA_LINK_ERROR: {label}"); return
    df['MA60'] = df['c'].rolling(window=60).mean()
    exp12, exp26 = df['c'].ewm(span=12, adjust=False).mean(), df['c'].ewm(span=26, adjust=False).mean()
    df['DIF'] = exp12 - exp26; df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean(); df['HIST'] = df['DIF'] - df['DEA']
    df['delta'] = 2 * df['tbb'] - df['v']; cvd_v = df['delta'].iloc[-5:].sum()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df['time'], open=df['o'], high=df['h'], low=df['l'], close=df['c'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['time'], y=df['MA60'], line=dict(color='#00f2ff', width=1.5), name='MA60'), row=1, col=1)
    clrs = ['#00ff88' if v >= 0 else '#ff0055' for v in df['HIST']]
    fig.add_trace(go.Bar(x=df['time'], y=df['HIST'], name='HIST', marker_color=clrs), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['time'], y=df['DIF'], line=dict(color='#fff', width=1), name='DIF'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['time'], y=df['DEA'], line=dict(color='#ffa500', width=1), name='DEA'), row=2, col=1)
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=500, margin=dict(t=10, b=0, l=0, r=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("DIF", f"{df['DIF'].iloc[-1]:,.2f}")
    with c2: st.metric("DEA", f"{df['DEA'].iloc[-1]:,.2f}")
    with c3: st.metric("HIST", f"{df['HIST'].iloc[-1]:,.2f}")
    with c4: st.metric("CVD_5K", format_volume(cvd_v))
    with c5: st.metric("MA60_PRICE", f"${df['MA60'].iloc[-1]:,.2f}")
    with c6: st.metric("MA60_BIAS", f"{((df['c'].iloc[-1]-df['MA60'].iloc[-1])/df['MA60'].iloc[-1])*100:+.2f}%")

def render_detail_view(symbol):
    st.markdown(f'<div style="border: 2px solid #00f2ff; border-radius: 10px; padding: 20px; background: rgba(0,242,255,0.05); margin-bottom: 20px;"><h2 style="font-family:\'Orbitron\'; color:#00f2ff; text-shadow:0 0 10px #00f2ff;">> DEEP_DIVE: {symbol}</h2>', unsafe_allow_html=True)
    s = fetch_market_sentiment(symbol)
    if s:
        st.markdown('<div style="background:rgba(0,0,0,0.3); padding:10px 15px; border-radius:8px; margin-bottom:15px; border:1px solid #00f2ff33;"><span style="font-family:\'Orbitron\'; color:#00f2ff; font-size:0.8rem;">[ BINANCE_SENTIMENT_CORE ]</span></div>', unsafe_allow_html=True)
        s1, s2, s3 = st.columns(3)
        with s1: st.metric("FUNDING_RATE", f"{s['funding']:.4f}%" if s['funding'] is not None else "OFFLINE")
        with s2:
            p = st.session_state.get(f"lp_{symbol}", 0)
            st.metric("OPEN_INTEREST", f"${s['oi']*p/1e6:,.1f}M" if (s['oi'] and p) else "OFFLINE")
        with s3: st.metric("LONG/SHORT_RATIO", f"{s['ls']:.2f}" if s['ls'] is not None else "OFFLINE")
    tabs = st.tabs(["1H", "4H", "1D"])
    with tabs[0]: render_timeframe_chart(symbol, '1h', "1H")
    with tabs[1]: render_timeframe_chart(symbol, '4h', "4H")
    with tabs[2]: render_timeframe_chart(symbol, '1d', "1D")
    if st.button(f"CLOSE_{symbol}", key=f"cls_{symbol}", use_container_width=True):
        st.session_state.selected_coins.remove(symbol); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- FRAGMENT ---

@st.fragment(run_every=3)
def render_dashboard_fragment():
    top = get_top_30_hot_coins()
    if top.empty: st.write("CONNECTING_TO_DATASTREAM..."); return
    all_res = batch_fetch_indicators_v8(top['symbol'].tolist())
    bh4 = all_res.get('BTCUSDT', {}).get('H4', {}).get('tf_ret', 0)
    bd1 = all_res.get('BTCUSDT', {}).get('D1', {}).get('tf_ret', 0)
    
    for _, row in top.iterrows():
        symbol = row['symbol']; clean = symbol.replace('USDT',''); cp = row['lastPrice']
        st.session_state[f"lp_{symbol}"] = cp
        h4_d, d1_d = all_res.get(symbol, {}).get('H4'), all_res.get(symbol, {}).get('D1')
        vs_btc = ""
        if h4_d and d1_d:
            h4r, d1r = h4_d['tf_ret']-bh4, d1_d['tf_ret']-bd1
            vs_btc = f'<span class="vs-btc-badge {"pos" if h4r>=0 else "neg"}">H4_VS_BTC: {h4r:+.2f}%</span><span class="vs-btc-badge {"pos" if d1r>=0 else "neg"}">D1_VS_BTC: {d1r:+.2f}%</span>'
        
        tfs = []
        for tf in ['H1','H2','H4','H6','H8','H12','D1']:
            d = all_res.get(symbol, {}).get(tf)
            if d and 'ma60' in d:
                m6, cv, bi = d['ma60'], d['cvd'], ((cp - d['ma60'])/d['ma60'])*100
                di, de = d['dif'], d['dea']; dp, ep = abs(di/cp)*100, abs(de/cp)*100
                spk = '<div class="spark-zero"></div>'
                mh = max([abs(x) for x in d['hist_history']] + [1e-9])
                for idx, h in enumerate(d['hist_history']):
                    h_h, h_c = max(int((abs(h)/mh)*45), 2), ("#00ff88" if h>=0 else "#ff0055")
                    spk += f'<div class="spark-bar {"pos-bar" if h>=0 else "neg-bar"}" style="left:{5+(idx*19)}%; height:{h_h}%; background:{h_c};"></div>'
                tfs.append(f'<div class="tf-box"><div class="tf-title">{tf}</div><div class="ind-row"><span class="label">MA60</span><span class="val">{m6:,.1f}</span></div><div class="ind-row"><span class="label">BIAS</span><span class="val {"pos" if bi>=0 else "neg"}">{bi:+.2f}%</span></div><div class="ind-row"><span class="label">CVD</span><span class="val {"pos" if cv>=0 else "neg"}">{format_volume(cv)}</span></div><div class="ind-row"><span class="label">DIF</span><span class="val">{di:,.1f}</span></div><div class="ind-row"><span class="label">DEA</span><span class="val">{de:,.1f}</span></div><div class="ind-row"><span class="label">HIST</span><span class="val {"pos" if d["hist"]>=0 else "neg"}">{d["hist"]:,.1f}</span></div><div class="axis-row"><span class="axis-badge {"bg-pos" if di>=0 else "bg-neg"}">DIF{"↑" if di>=0 else "↓"} {dp:.2f}%</span><span class="axis-badge {"bg-pos" if de>=0 else "bg-neg"}">DEA{"↑" if de>=0 else "↓"} {ep:.2f}%</span></div>{draw_svg_kline(d["candles"])}<div class="spark-container">{spk}</div></div>')
            else: tfs.append(f'<div class="tf-box"><div class="tf-title">{tf}</div><div class="val" style="color:#444; margin-top:30px; font-size:0.7rem;">INITIALIZING...</div></div>')
        
        with st.container():
            c1, c2 = st.columns([0.85, 0.15])
            with c1: st.markdown(f'<div class="card-header-styled"><img src="https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/{clean.lower()}.png" class="coin-icon" onerror="this.src=\'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/generic.png\'"><span class="symbol-text">{clean}</span><span class="price-text">${cp:,.4f}</span>{vs_btc}<div style="margin-left:auto; text-align:right;"><div class="change-text {"pos" if row["priceChangePercent"]>=0 else "neg"}">{row["priceChangePercent"]:+.2f}%</div><div class="vol-text">VOL: {row["quoteVolume"]/1e6:.1f}M</div></div></div>', unsafe_allow_html=True)
            with c2:
                st.write("")
                if st.button("DIVE", key=f"d_{symbol}", use_container_width=True):
                    st.session_state.selected_coins.add(symbol); st.rerun()
            st.markdown(f'<div class="crypto-card-body"><div class="tf-grid">{"".join(tfs)}</div></div><div style="margin-bottom:25px;"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:right; color:#444; margin-bottom:10px; font-family:monospace; font-size:0.8rem;">ENGINE_V8 | HB: {datetime.now().strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)

# --- MAIN ---

def main():
    if 'selected_coins' not in st.session_state: st.session_state.selected_coins = set()
    st.set_page_config(page_title="Future Crypto Dashboard", layout="wide")
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@400;500;600;700&display=swap');
    .stApp { background-color:#050505; color:#e0e0e0; font-family:'Rajdhani',sans-serif; background-image:linear-gradient(rgba(0,242,255,0.05) 1px,transparent 1px),linear-gradient(90deg,rgba(0,242,255,0.05) 1px,transparent 1px); background-size:60px 60px; }
    .stApp::after { content:""; position:fixed; top:0; left:0; width:100%; height:3px; background:linear-gradient(to right,transparent,#00f2ff,transparent); box-shadow:0 0 20px #00f2ff; animation:scan 6s linear infinite; z-index:9999; pointer-events:none; }
    @keyframes scan { 0%{top:-10%;} 100%{top:110%;} }
    .card-header-styled { background:rgba(20,20,20,0.9); border:1px solid #00f2ff44; border-left:8px solid #00f2ff; border-radius:10px 10px 0 0; padding:15px 25px; display:flex; align-items:center; }
    .vs-btc-badge { margin-left: 12px; font-family: 'Orbitron', sans-serif; font-size: 0.8rem; padding: 3px 8px; border-radius: 4px; background: rgba(255,255,255,0.05); border: 1px solid #ffffff11; font-weight: bold; }
    .crypto-card-body { background:rgba(15,15,15,0.85); border:1px solid #00f2ff22; border-top:none; border-radius: 0 0 10px 10px; padding:15px; }
    .coin-icon { width:45px; height:45px; margin-right:20px; filter:drop-shadow(0 0 8px #00f2ff44); }
    .symbol-text { font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 700; color: #00f2ff; }
    .price-text { font-size: 1.5rem; color: #ffffff; font-weight: 500; margin-left: 15px; }
    .change-text { font-size:1.4rem; font-weight:700; }
    .vol-text { font-size:0.9rem; color:#888; text-transform:uppercase; }
    .tf-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 12px; }
    .tf-box { background: rgba(0, 242, 255, 0.02); border: 1px solid #ffffff08; border-radius: 6px; padding: 12px; text-align: center; }
    .tf-title { font-family: 'Orbitron', sans-serif; font-size: 1rem; color: #00f2ff; font-weight: 700; margin-bottom: 10px; border-bottom: 1px solid #00f2ff22; }
    .ind-row { display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 4px; }
    .axis-badge { padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; }
    .spark-container { position:relative; margin-top:8px; height:40px; background:rgba(0,0,0,0.4); border-radius:4px; overflow:hidden; }
    .spark-zero { position:absolute; top:50%; left:0; width:100%; height:1px; background:rgba(255,255,255,0.2); }
    .spark-bar { position:absolute; width:14%; }
    .spark-bar.pos-bar { bottom:50%; border-radius:1px 1px 0 0; }
    .spark-bar.neg-bar { top:50%; border-radius:0 0 1px 1px; }
    .pos { color:#00ff88; }
    .neg { color:#ff0055; }
    .bg-pos { background:rgba(0, 255, 136, 0.1); color:#00ff88; border: 1px solid #00ff8833; }
    .bg-neg { background:rgba(255, 0, 85, 0.1); color:#ff0055; border: 1px solid #ff005533; }
    div.stButton > button { background-color: transparent; color: #00f2ff; border: 1px solid #00f2ff; font-family: 'Orbitron', sans-serif; font-weight: bold; border-radius: 5px; transition: all 0.3s ease; text-transform: uppercase; letter-spacing: 2px; }
    div.stButton > button:hover { background-color: #00f2ff; color: #000; box-shadow: 0 0 20px #00f2ff; }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-family: 'Orbitron', sans-serif; font-size: 1.8rem !important; }
    [data-testid="stMetricLabel"] { color: #00f2ff !important; font-weight: bold !important; font-size: 1rem !important; text-transform: uppercase; }
    button[data-baseweb="tab"] p { color: #888 !important; font-weight: bold !important; font-size: 1.1rem !important; }
    button[aria-selected="true"] p { color: #00f2ff !important; text-shadow: 0 0 10px #00f2ff; }
    .neon-title { font-family:'Orbitron',sans-serif; font-size:3rem; text-align:center; color:#00f2ff; text-shadow:0 0 20px #00f2ff; margin:30px 0; letter-spacing:8px; }
    [data-testid="stSidebar"] { background-color:#0a0a0a; border-right:1px solid #00f2ff33; }
    .sidebar-text { color:#00f2ff; font-family:'Orbitron',sans-serif; font-size:1rem; margin-bottom:10px; }
    #MainMenu, footer, header, .stDeployButton { visibility:hidden; display:none; }
</style>
""", unsafe_allow_html=True)
    st.sidebar.markdown('<div class="sidebar-text">SYSTEM_CORE</div>', unsafe_allow_html=True)
    if st.sidebar.button("HARD_CACHE_RESET"): st.cache_data.clear(); st.rerun()
    if st.sidebar.button("CLEAR_ALL_DIVES"): st.session_state.selected_coins.clear(); st.rerun()
    auto = st.sidebar.toggle("AUTO_SYNC (3s)", value=True)
    st.sidebar.divider()
    for sym in list(st.session_state.selected_coins): render_detail_view(sym); st.divider()
    st.markdown('<h1 class="neon-title">CORE MONITOR</h1>', unsafe_allow_html=True)
    if auto: render_dashboard_fragment()
    else: render_dashboard_fragment.__wrapped__()

if __name__ == "__main__":
    main()
