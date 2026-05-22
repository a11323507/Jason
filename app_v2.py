import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
import requests
import json

# 頁面配置
st.set_page_config(page_title="股票交易計畫儀表板", layout="wide")

# --- 自定義 CSS ---
st.markdown("""
<style>
    /* 全體背景與文字 */
    .stApp {
        background-color: #0e1117;
        color: #d1d4dc;
    }
    
    /* 頂部標頭樣式 */
    .header-box {
        background-color: #1e222d;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #2b2b43;
        margin-bottom: 20px;
    }
    .price-box {
        background-color: #ef5350;
        color: white;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .price-val {
        font-size: 3rem;
        font-weight: bold;
        line-height: 1;
    }
    .price-change {
        font-size: 1.2rem;
        margin-top: 5px;
    }
    
    /* 區塊卡片樣式 */
    .plan-card {
        background-color: #1e222d;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #2b2b43;
        height: 100%;
        margin-bottom: 15px;
    }
    .plan-title {
        color: #42a5f5;
        font-size: 1.3rem;
        font-weight: bold;
        border-bottom: 1px solid #2b2b43;
        padding-bottom: 8px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
    }
    
    /* 表格樣式優化 */
    .stTable {
        font-size: 0.9rem;
    }
    
    /* 側邊欄優化 */
    section[data-testid="stSidebar"] {
        background-color: #131722;
        border-right: 1px solid #2b2b43;
    }
    
    /* 隱藏預設元件 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("📈 股票分析策略網頁模板")
st.markdown("""
這是一個使用 Streamlit 建立的股票分析模板。您可以輸入股票代碼、選擇日期範圍，並查看技術指標、大盤動量與簡易回測結果。
""")

# --- 全球市場熱力圖 ---
with st.expander("🇺🇸 美股市場熱力圖 (S&P 500)", expanded=False):
    components.html("""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
          {
          "exchanges": [],
          "dataSource": "SPX500",
          "grouping": "sector",
          "blockSize": "market_cap_basic",
          "blockColor": "change",
          "locale": "zh_TW",
          "symbolUrl": "",
          "colorTheme": "dark",
          "hasTopBar": false,
          "isDataSetEnabled": false,
          "isZoomEnabled": true,
          "hasSymbolTooltip": true,
          "width": "100%",
          "height": "600"
        }
          </script>
        </div>
    """, height=600)

with st.expander("🇹🇼 台股市場熱力圖 (Taiwan)", expanded=False):
    components.html("""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
          {
          "exchanges": ["TWSE", "TPEX"],
          "dataSource": "all_stocks",
          "grouping": "sector",
          "blockSize": "market_cap_basic",
          "blockColor": "change",
          "locale": "zh_TW",
          "symbolUrl": "",
          "colorTheme": "dark",
          "hasTopBar": true,
          "isDataSetEnabled": false,
          "isZoomEnabled": true,
          "hasSymbolTooltip": true,
          "width": "100%",
          "height": "600"
        }
          </script>
        </div>
    """, height=600)

with st.expander("₿ 虛擬貨幣熱力圖 (Crypto)", expanded=False):
    components.html("""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-crypto-coins-heatmap.js" async>
          {
          "dataSource": "crypto",
          "blockSize": "market_cap_calc",
          "blockColor": "change",
          "locale": "zh_TW",
          "symbolUrl": "",
          "colorTheme": "dark",
          "hasTopBar": false,
          "isDataSetEnabled": false,
          "isZoomEnabled": true,
          "hasSymbolTooltip": true,
          "width": "100%",
          "height": "600"
        }
          </script>
        </div>
    """, height=600)

st.sidebar.header("參數設定")

market = st.sidebar.selectbox("選擇市場", ["美股 (US)", "台股上市 (TWSE)", "台股上櫃 (OTC)", "虛擬貨幣 (Crypto)"])

# 根據市場預設代碼
if market == "美股 (US)":
    default_ticker = "AAPL"
elif market == "虛擬貨幣 (Crypto)":
    default_ticker = "BTCUSDT"
else:
    default_ticker = "2330"
raw_ticker = st.sidebar.text_input("輸入股票代碼 (不需輸入後綴)", value=default_ticker)

# 自動處理股票代碼後綴與選擇對應的 Benchmark
benchmark_ticker = "SPY"
benchmark_name = "標普 500 ETF (SPY)"

raw_ticker = raw_ticker.upper().strip()

if market == "台股上市 (TWSE)":
    clean_ticker = raw_ticker.split('.')[0] 
    ticker = f"{clean_ticker}.TW"
    benchmark_ticker = "^TWII"
    benchmark_name = "台灣加權指數 (^TWII)"
elif market == "台股上櫃 (OTC)":
    clean_ticker = raw_ticker.split('.')[0]
    ticker = f"{clean_ticker}.TWO"
    benchmark_ticker = "^TWOII"
    benchmark_name = "櫃檯買賣指數 (^TWOII)"
elif market == "虛擬貨幣 (Crypto)":
    ticker = raw_ticker.replace(" ", "").upper()
    if not ticker.endswith("USDT"):
        ticker = ticker + "USDT"
    benchmark_ticker = "BTCUSDT"
    benchmark_name = "比特幣永續合約 (BTCUSDT)"
else:
    ticker = raw_ticker

st.sidebar.markdown(f"**實際查詢代碼:** `{ticker}`")

now_tw = datetime.utcnow() + timedelta(hours=8)
today_date = now_tw.date()

start_date = st.sidebar.date_input("開始日期", value=today_date - timedelta(days=365))
end_date = st.sidebar.date_input("結束日期", value=today_date)

st.sidebar.subheader("技術指標參數")
interval_options = ["15m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "2d", "3d"]
interval_labels = ["15M", "1H", "2H", "4H", "6H", "8H", "12H", "1D", "2D", "3D"]
selected_interval_label = st.sidebar.selectbox(
    "選擇 K 線時間週期", 
    interval_labels, 
    index=7,  # 預設 1D
    help="注意：美股/台股使用 yfinance，短週期 (< 1D) 僅支援近 60 天資料；虛擬貨幣透過 Binance API 支援完整歷史。"
)
selected_interval = interval_options[interval_labels.index(selected_interval_label)]
rsi_period = st.sidebar.number_input("RSI 週期", value=14)

st.sidebar.divider()
st.sidebar.subheader("🔑 進階 API 設定")
finmind_token = st.sidebar.text_input("FinMind API Token (選填)", type="password", help="若要解鎖大戶籌碼分布等付費資料，請輸入您的 Token。")

st.sidebar.divider()
# --- 新增：手動清除快取按鈕 ---
if st.sidebar.button("🔄 手動更新資料 (清除快取)"):
    st.cache_data.clear()
    st.sidebar.success("快取已清除！網頁將載入最新資料。")

# --- 抓取數據 ---
@st.cache_data(ttl=60)
def load_chart_data_binance(symbol, start, end, interval):
    """從 Binance 永續合約抓取指定週期 K 線"""
    try:
        # Binance 不支援 2d 週期，進行修正
        if interval == "2d":
            interval = "1d"
            
        all_data = []
        # 使用 pd.Timestamp 處理日期並轉為 UTC 時間戳 (毫秒)
        start_ts = int(pd.Timestamp(start).timestamp() * 1000)
        # 使用 pd.Timestamp.now() 獲取正確的當前 UTC 時間戳
        now_ts = int(pd.Timestamp.now().timestamp() * 1000)
        
        # 結束時間設為該日期的 23:59:59
        end_ts = int((pd.Timestamp(end) + timedelta(days=1)).timestamp() * 1000) - 1
        request_end_ts = min(end_ts, now_ts)
        
        # 如果開始時間大於結束時間，調整開始時間以確保能抓到資料 (例如抓最近 100 根)
        if start_ts >= request_end_ts:
            start_ts = request_end_ts - (100 * 24 * 3600 * 1000) # 預設抓 100 天前
        
        while start_ts < request_end_ts:
            url = "https://fapi.binance.com/fapi/v1/klines"
            params = {
                "symbol": symbol.strip().upper(),
                "interval": interval,
                "startTime": start_ts,
                "endTime": request_end_ts,
                "limit": 1500
            }
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if not data or isinstance(data, dict):
                # 如果有錯誤訊息，印出以便調試 (Streamlit log)
                if isinstance(data, dict):
                    print(f"Binance API Error: {data}")
                break
            
            all_data.extend(data)
            start_ts = data[-1][0] + 1
            
            if len(data) < 1500:
                break
        
        if not all_data:
            return pd.DataFrame()
            
        df_chart = pd.DataFrame(all_data, columns=[
            'Open_time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close_time', 'Quote_volume', 'Trades', 'Taker_buy_base',
            'Taker_buy_quote', 'Ignore'
        ])
        
        df_chart['Date'] = pd.to_datetime(df_chart['Open_time'], unit='ms')
        df_chart = df_chart.set_index('Date')
        df_chart = df_chart[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
        
        return df_chart
    except Exception as e:
        print(f"Binance chart API error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_chart_data_yf(symbol, start, end, interval):
    """從 yfinance 抓取指定週期資料 (短週期僅支援近期)"""
    try:
        # yf.download 的 end date 是不包含的
        end_plus_one = end + timedelta(days=1)
        data = yf.download(symbol.strip(), start=start, end=end_plus_one, interval=interval)
        return data
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=10) # 極短快取用於即時價格
def get_binance_realtime_data(symbol):
    """獲取幣安永續合約即時價格與 24h 變動"""
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        params = {"symbol": symbol}
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if isinstance(data, dict) and 'lastPrice' in data:
            return {
                'currentPrice': float(data['lastPrice']),
                'priceChange': float(data['priceChange']),
                'priceChangePercent': float(data['priceChangePercent']),
                'high': float(data['highPrice']),
                'low': float(data['lowPrice']),
                'volume': float(data['volume'])
            }
    except Exception:
        pass
    return {}

@st.cache_data(ttl=3600)
def load_info(symbol):
    try:
        ticker_obj = yf.Ticker(symbol)
        return ticker_obj.info
    except Exception:
        return {}

def render_lightweight_chart(df, height=600):
    """使用 TradingView Lightweight Charts 渲染 K 線圖 (指定版本與穩定載入版)"""
    if df.empty:
        st.warning("無數據可顯示圖表")
        return

    try:
        # 1. 數據清洗
        chart_df = df.copy()
        chart_df.index = pd.to_datetime(chart_df.index)
        chart_df = chart_df.sort_index()
        chart_df = chart_df[~chart_df.index.duplicated(keep='last')].reset_index()
        chart_df['time'] = chart_df['Date'].apply(lambda x: int(x.timestamp()))
        
        # 準備 JSON 數據
        ohlc_data = chart_df.dropna(subset=['Open', 'High', 'Low', 'Close'])[['time', 'Open', 'High', 'Low', 'Close']].rename(columns={
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'
        }).to_dict(orient='records')
        
        volume_records = []
        for _, row in chart_df.dropna(subset=['Volume', 'Close', 'Open']).iterrows():
            volume_records.append({
                'time': int(row['time']),
                'value': float(row['Volume']),
                'color': 'rgba(239, 83, 80, 0.5)' if row['Close'] < row['Open'] else 'rgba(38, 166, 154, 0.5)'
            })
        # 均線與指標
        indicators_data = {}
        for col in ['EMA_8', 'EMA_13', 'EMA_21', 'EMA_55', 'EMA_100', 'EMA_200', 'bb_upper', 'bb_lower']:
            if col in chart_df.columns:
                target_df = chart_df[['time', col]].dropna()
                if not target_df.empty:
                    indicators_data[col] = target_df.rename(columns={col: 'value'}).to_dict(orient='records')


        markers = []
        if 'Position' in chart_df.columns:
            for _, row in chart_df[chart_df['Position'] == 1].iterrows():
                markers.append({'time': int(row['time']), 'position': 'belowBar', 'color': '#26a69a', 'shape': 'arrowUp', 'text': 'BUY'})
            for _, row in chart_df[chart_df['Position'] == -1].iterrows():
                markers.append({'time': int(row['time']), 'position': 'aboveBar', 'color': '#ef5350', 'shape': 'arrowDown', 'text': 'SELL'})

        # 序列化為 JSON
        js_ind = json.dumps(indicators_data)

        # 2. 構建 HTML (使用指定版本 v4.1.1)
        html_content = f"""
        <style>
            html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background: #131722; overflow: hidden; }}
            #chart-container {{ width: 100%; height: {height}px; }}
            #legend {{
                position: absolute; left: 12px; top: 12px; z-index: 100;
                font-family: sans-serif; font-size: 12px; color: #d1d4dc;
                background: rgba(19, 23, 34, 0.7); padding: 6px; border-radius: 4px; pointer-events: none;
            }}
            .l-val {{ color: #2962ff; font-weight: bold; margin-right: 6px; }}
        </style>
        <div id="legend">準備載入圖表...</div>
        <div id="chart-container"></div>
        <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
        <script>
            // 等待函式庫載入完成
            function initChart() {{
                console.log("Checking LightweightCharts library...");
                if (typeof LightweightCharts === 'undefined') {{
                    console.log("Library not ready, retrying in 100ms...");
                    setTimeout(initChart, 100);
                    return;
                }}
                
                console.log("Library ready, initializing chart...");
                const container = document.getElementById('chart-container');
                const legend = document.getElementById('legend');
                
                try {{
                    const chart = LightweightCharts.createChart(container, {{
                        layout: {{ background: {{ type: 'solid', color: '#131722' }}, textColor: '#d1d4dc' }},
                        grid: {{ vertLines: {{ color: '#242733' }}, horzLines: {{ color: '#242733' }} }},
                        rightPriceScale: {{ borderColor: '#2b2b43' }},
                        timeScale: {{ borderColor: '#2b2b43', timeVisible: true }},
                        crosshair: {{ mode: 0 }}
                    }});

                    const candleSeries = chart.addCandlestickSeries({{
                        upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
                        wickUpColor: '#26a69a', wickDownColor: '#ef5350'
                    }});
                    
                    const ohlcData = {json.dumps(ohlc_data)};
                    if (ohlcData.length > 0) {{
                        candleSeries.setData(ohlcData);
                        candleSeries.setMarkers({json.dumps(markers)});
                    }}

                    const volSeries = chart.addHistogramSeries({{
                        color: '#26a69a', priceFormat: {{ type: 'volume' }}, priceScaleId: ''
                    }});
                    volSeries.priceScale().applyOptions({{ scaleMargins: {{ top: 0.8, bottom: 0 }} }});
                    volSeries.setData({json.dumps(volume_records)});

                    const indData = {js_ind};
                    const colors = {{ 'EMA_8': 'orange', 'EMA_13': 'skyblue', 'EMA_21': 'lime', 'EMA_55': 'green', 'EMA_100': 'red', 'EMA_200': 'purple', 'bb_upper': 'rgba(128,128,128,0.4)', 'bb_lower': 'rgba(128,128,128,0.4)' }};

                    
                    Object.keys(indData).forEach(key => {{
                        const series = chart.addLineSeries({{
                            color: colors[key] || '#ccc',
                            lineWidth: key.includes('bb') ? 1 : 1,
                            lineStyle: key.includes('bb') ? 2 : 0,
                            title: key
                        }});
                        series.setData(indData[key]);
                    }});

                    chart.subscribeCrosshairMove(param => {{
                        if (!param.time || param.point.x < 0) {{
                            legend.innerHTML = '{ticker}';
                            return;
                        }}
                        const data = param.seriesData.get(candleSeries);
                        if (data) {{
                            legend.innerHTML = `O <span class="l-val">${{data.open.toFixed(2)}}</span> H <span class="l-val">${{data.high.toFixed(2)}}</span> L <span class="l-val">${{data.low.toFixed(2)}}</span> C <span class="l-val">${{data.close.toFixed(2)}}</span>`;
                        }}
                    }});

                    chart.timeScale().fitContent();
                    window.addEventListener('resize', () => chart.applyOptions({{ width: container.clientWidth }}));
                    console.log("Chart initialization successful.");
                    
                }} catch (err) {{
                    console.error("Chart Error:", err);
                    legend.innerHTML = "圖表渲染錯誤: " + err.message;
                }}
            }}
            initChart();
        </script>
        """
        components.html(html_content, height=height)
    except Exception as e:
        st.error(f"準備圖表數據時發生錯誤: {e}")

@st.cache_data(ttl=3600)
def load_fundamentals(symbol):
    try:
        ticker_obj = yf.Ticker(symbol)
        income_stmt = ticker_obj.quarterly_income_stmt
        fund_data = {}
        
        if not income_stmt.empty:
            if 'Basic EPS' in income_stmt.index:
                eps_data = income_stmt.loc['Basic EPS'].dropna().head(4)
                fund_data['EPS'] = eps_data.rename(lambda x: x.strftime('%Y-%m-%d'))
            elif 'Diluted EPS' in income_stmt.index:
                eps_data = income_stmt.loc['Diluted EPS'].dropna().head(4)
                fund_data['EPS'] = eps_data.rename(lambda x: x.strftime('%Y-%m-%d'))
                
            if 'Total Revenue' in income_stmt.index:
                rev_data = income_stmt.loc['Total Revenue'].dropna()
                rev_yoy = (rev_data / rev_data.shift(-4) - 1) * 100
                rev_qoq = (rev_data / rev_data.shift(-1) - 1) * 100
                
                fund_data['Revenue'] = rev_data.head(4).rename(lambda x: x.strftime('%Y-%m-%d'))
                fund_data['Revenue_YoY'] = rev_yoy.head(4).rename(lambda x: x.strftime('%Y-%m-%d'))
                fund_data['Revenue_QoQ'] = rev_qoq.head(4).rename(lambda x: x.strftime('%Y-%m-%d'))
                
        return fund_data
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def load_tw_monthly_revenue(symbol, token=""):
    try:
        stock_id = symbol.split('.')[0]
        start_date_str = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockMonthRevenue&data_id={stock_id}&start_date={start_date_str}"
        if token: url += f"&token={token}"
        
        res = requests.get(url)
        data = res.json().get('data', [])
        if not data: return {}
        
        df_rev = pd.DataFrame(data)
        df_rev['date'] = pd.to_datetime(df_rev['date'])
        df_rev = df_rev.sort_values('date').reset_index(drop=True)
        
        df_rev['MoM'] = df_rev['revenue'].pct_change() * 100
        df_rev['YoY'] = df_rev['revenue'].pct_change(periods=12) * 100
        
        recent_4 = df_rev.tail(4).iloc[::-1]
        
        result = {}
        for _, row in recent_4.iterrows():
            month_str = f"{int(row['revenue_year'])}-{int(row['revenue_month']):02d}"
            result[month_str] = {
                'revenue': row['revenue'],
                'MoM': row['MoM'],
                'YoY': row['YoY']
            }
        return result
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def get_full_tdcc_data():
    """下載並快取完整的集保全市場資料 (檔案約 20-30MB)"""
    try:
        url = "https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5"
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        if '證券代號' in df.columns:
            df['證券代號'] = df['證券代號'].astype(str).str.strip()
        return df
    except Exception as e:
        print(f"Error downloading TDCC data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_tw_chip_distribution(symbol, token=""):
    try:
        stock_id = symbol.split('.')[0]
        # 從快取的全局數據中獲取，避免重複下載大檔案
        df = get_full_tdcc_data()
        
        if df.empty:
            return {'error_type': 'api_error', 'msg': '無法獲取集保結算所開放資料'}
            
        if '證券代號' in df.columns:
            df_stock = df[df['證券代號'] == stock_id].copy()
            
            if not df_stock.empty:
                data_date = str(df_stock['資料日期'].iloc[0])
                df_stock['持股分級'] = df_stock['持股分級'].astype(int)
                
                df_stock = df_stock[df_stock['持股分級'] <= 15]
                
                def categorize_level(level):
                    if level <= 8: return "散戶 (≤50張)"
                    elif level <= 11: return "中實戶 (50~400張)"
                    elif level <= 14: return "大戶 (400~1000張)"
                    else: return "超級大戶 (>1000張)"
                    
                df_stock['Category'] = df_stock['持股分級'].apply(categorize_level)
                
                ratio_cols = [col for col in df.columns if '比例' in col]
                target_col = ratio_cols[0] if ratio_cols else '占集保庫存數比例%'
                
                df_stock['percent'] = df_stock[target_col]
                dist_grouped = df_stock.groupby('Category')['percent'].sum().reset_index()
                
                df_large = df_stock[df_stock['持股分級'] == 15]
                latest_pct = float(df_large['percent'].sum()) if not df_large.empty else 0.0
                
                return {
                    'date': data_date,
                    'distribution': dist_grouped,
                    'large_latest_pct': latest_pct,
                    'diff_pct': 0.0
                }
            else:
                return {'error_type': 'api_error', 'msg': f'找不到 {stock_id} 的集保資料'}
        else:
            return {'error_type': 'api_error', 'msg': '資料格式錯誤 (找不到證券代號)'}
            
    except Exception as e:
        print(f"Error processing chip distribution: {e}")
        return {}


@st.cache_data(ttl=3600)
def load_tw_chip_data(symbol, total_volume_latest, token=""):
    try:
        stock_id = symbol.split('.')[0]
        start_date_str = (datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d')
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={stock_id}&start_date={start_date_str}"
        if token: url += f"&token={token}"
        
        res = requests.get(url)
        data = res.json().get('data', [])
        if not data: return {}
        
        df_chip = pd.DataFrame(data)
        df_chip['net'] = df_chip['buy'] - df_chip['sell']
        
        df_pivot = df_chip.pivot(index='date', columns='name', values='net').fillna(0)
        df_pivot.index = pd.to_datetime(df_pivot.index)
        df_pivot = df_pivot.sort_index()
        
        target_cols = ['Foreign_Investor', 'Investment_Trust', 'Dealer_self', 'Dealer_Hedging', 'Dealer']
        for col in target_cols:
            if col not in df_pivot.columns:
                df_pivot[col] = 0
                
        df_pivot['Main_Force'] = df_pivot[['Foreign_Investor', 'Investment_Trust', 'Dealer_self', 'Dealer_Hedging', 'Dealer']].sum(axis=1)
                
        if len(df_pivot) >= 2:
            latest_chip = df_pivot.iloc[-1]
            prev_chip = df_pivot.iloc[-2]
        else:
            latest_chip = df_pivot.iloc[-1]
            prev_chip = pd.Series(0, index=df_pivot.columns)

        fi_net = latest_chip['Foreign_Investor'] / 1000 
        it_net = latest_chip['Investment_Trust'] / 1000
        dl_net = (latest_chip['Dealer_self'] + latest_chip['Dealer_Hedging'] + latest_chip['Dealer']) / 1000
        mf_net = latest_chip['Main_Force'] / 1000
        
        fi_net_prev = prev_chip['Foreign_Investor'] / 1000
        it_net_prev = prev_chip['Investment_Trust'] / 1000
        dl_net_prev = (prev_chip['Dealer_self'] + prev_chip['Dealer_Hedging'] + prev_chip['Dealer']) / 1000
        mf_net_prev = prev_chip['Main_Force'] / 1000

        def calc_momentum(today, yesterday):
            if today > 0:
                return "📈 買盤轉強" if today > yesterday else "📉 買盤縮減"
            elif today < 0:
                return "📉 賣壓減緩" if today > yesterday else "📈 賣壓增加"
            else:
                return "📉 買盤縮減" if yesterday > 0 else ("📉 賣壓減緩" if yesterday < 0 else "⚖️ 力道持平")

        fi_momentum = calc_momentum(fi_net, fi_net_prev)
        it_momentum = calc_momentum(it_net, it_net_prev)
        dl_momentum = calc_momentum(dl_net, dl_net_prev)
        mf_momentum = calc_momentum(mf_net, mf_net_prev)
        
        vol_shares = total_volume_latest / 1000 if total_volume_latest > 0 else 1
        
        df_5d = df_pivot.tail(5)
        fi_5d = df_5d['Foreign_Investor'].sum() / 1000
        it_5d = df_5d['Investment_Trust'].sum() / 1000
        dl_5d = (df_5d['Dealer_self'].sum() + df_5d['Dealer_Hedging'].sum() + df_5d['Dealer'].sum()) / 1000
        mf_5d = df_5d['Main_Force'].sum() / 1000
        
        return {
            'date': latest_chip.name.strftime('%Y-%m-%d'),
            'fi_net': fi_net, 'it_net': it_net, 'dl_net': dl_net, 'mf_net': mf_net,
            'fi_pct': (fi_net / vol_shares) * 100, 
            'it_pct': (it_net / vol_shares) * 100,
            'dl_pct': (dl_net / vol_shares) * 100,
            'mf_pct': (mf_net / vol_shares) * 100,
            'fi_momentum': fi_momentum, 'it_momentum': it_momentum,
            'dl_momentum': dl_momentum, 'mf_momentum': mf_momentum,
            'fi_5d': fi_5d, 'it_5d': it_5d, 'dl_5d': dl_5d, 'mf_5d': mf_5d
        }
    except Exception as e:
        print(f"Error fetching chip data: {e}")
        return {}

# 輔助函數：計算區間報酬率
def calc_return(df, days):
    if len(df) >= days + 1:
        latest = float(df['Close'].iloc[-1].iloc[0]) if isinstance(df['Close'], pd.DataFrame) else float(df['Close'].iloc[-1])
        past = float(df['Close'].iloc[-(days+1)].iloc[0]) if isinstance(df['Close'], pd.DataFrame) else float(df['Close'].iloc[-(days+1)])
        return ((latest - past) / past) * 100
    return 0.0

def find_key_levels(df):
    """識別支撐與壓力位，標準：(均線與高點重合) 或 (均線與低點重合)"""
    if df.empty or len(df) < 120: # 增加到 120 以便計算 MA120
        return {}
    
    latest = df.iloc[-1]
    current_price = float(latest['Close'].iloc[0]) if isinstance(latest['Close'], pd.Series) else float(latest['Close'])
    
    ma_values = {
        'MA5': float(latest['MA5']),
        'MA10': float(latest['MA10']),
        'MA20': float(latest['MA20']),
        'MA60': float(latest['MA60']),
        'MA120': float(latest['MA120'])
    }
    
    # 尋找最近 120 根 K 線的局部高低點
    recent_df = df.tail(120)
    local_highs = recent_df['High'].rolling(window=10, center=True).max().dropna().unique()
    local_lows = recent_df['Low'].rolling(window=10, center=True).min().dropna().unique()
    
    key_resistances = []
    key_supports = []
    
    tolerance = 0.018 # 1.8% 的重合容許誤差
    
    for ma_name, ma_val in ma_values.items():
        # 檢查與高點重合 (壓力)
        for h in local_highs:
            if abs(ma_val - h) / h < tolerance:
                key_resistances.append({'val': round((ma_val + h) / 2, 2), 'desc': f"{ma_name} + 高點重合"})
        
        # 檢查與低點重合 (支撐)
        for l in local_lows:
            if abs(ma_val - l) / l < tolerance:
                key_supports.append({'val': round((ma_val + l) / 2, 2), 'desc': f"{ma_name} + 低點重合"})

    # 確保壓力在現價之上，支撐在現價之下，並依距離排序
    valid_res = sorted([r for r in key_resistances if r['val'] > current_price], key=lambda x: x['val'])
    valid_sup = sorted([s for s in key_supports if s['val'] < current_price], key=lambda x: x['val'], reverse=True)
    
    # 備用邏輯：若無重合點
    if not valid_res:
        valid_res = [{'val': round(ma_values['MA20'], 2), 'desc': 'MA20 壓力'}]
        if ma_values['MA60'] > current_price:
            valid_res.append({'val': round(ma_values['MA60'], 2), 'desc': 'MA60 壓力'})
        valid_res.append({'val': round(max(local_highs), 2), 'desc': '波段高點壓力'})
        valid_res = sorted([r for r in valid_res if r['val'] > current_price], key=lambda x: x['val'])

    if not valid_sup:
        valid_sup = [{'val': round(ma_values['MA20'], 2), 'desc': 'MA20 支撐'}]
        if ma_values['MA60'] < current_price:
            valid_sup.append({'val': round(ma_values['MA60'], 2), 'desc': 'MA60 支撐'})
        valid_sup.append({'val': round(min(local_lows), 2), 'desc': '波段低點支撐'})
        valid_sup = sorted([s for s in valid_sup if s['val'] < current_price], key=lambda x: x['val'], reverse=True)

    res1 = valid_res[0] if valid_res else {'val': round(current_price * 1.05, 2), 'desc': '預估壓力1'}
    res2 = valid_res[1] if len(valid_res) > 1 else {'val': round(res1['val'] * 1.05, 2), 'desc': '預估壓力2'}
    
    # 支撐 1 邏輯
    sup1 = valid_sup[0] if valid_sup else {'val': round(current_price * 0.95, 2), 'desc': '預估支撐1'}
    
    # 支撐 2 邏輯：檢查支撐 1 與支撐 2 距離
    dist_threshold = 0.03 # 距離小於 3% 視為太近
    
    potential_sup2 = None
    if len(valid_sup) > 1:
        s2 = valid_sup[1]
        if (sup1['val'] - s2['val']) / sup1['val'] < dist_threshold:
            # 太近了，嘗試尋找更遠的點 (特別是包含 MA120 的)
            for s in valid_sup[2:]:
                if (sup1['val'] - s['val']) / sup1['val'] >= dist_threshold:
                    potential_sup2 = s
                    break
        else:
            potential_sup2 = s2

    # 如果還是沒找到合適的支撐 2，或者原本就沒有足夠的 valid_sup，則採用 MA120 相關邏輯
    if potential_sup2 is None:
        ma120_val = ma_values['MA120']
        # 尋找靠近 MA120 的波段低點
        coincident_l = [l for l in local_lows if abs(ma120_val - l) / l < 0.05]
        if coincident_l:
            target_val = round((ma120_val + min(coincident_l)) / 2, 2)
            potential_sup2 = {'val': target_val, 'desc': 'MA120 + 波段低點 (遠端)'}
        else:
            potential_sup2 = {'val': round(ma120_val, 2), 'desc': 'MA120 強力支撐'}
            
    # 最後檢查：如果 MA120 支撐還是跟支撐 1 太近 (例如股價剛好在均線糾結處)，則強行下調
    if (sup1['val'] - potential_sup2['val']) / sup1['val'] < dist_threshold:
        potential_sup2 = {'val': round(sup1['val'] * 0.93, 2), 'desc': '深層波段支撐 (預估)'}

    return {
        'res1': res1['val'], 'res1_desc': res1['desc'],
        'res2': res2['val'], 'res2_desc': res2['desc'],
        'sup1': sup1['val'], 'sup1_desc': sup1['desc'],
        'sup2': potential_sup2['val'], 'sup2_desc': potential_sup2['desc']
    }

def calculate_indicators(df_in, ema_periods, rsi_period):
    if df_in.empty:
        return df_in
        
    df_res = df_in.copy()
    
    # 確保 Close 是 Series
    close_series = df_res['Close'].iloc[:, 0] if isinstance(df_res['Close'], pd.DataFrame) else df_res['Close']
    
    # 均線: 採用台股常用的 5, 10, 20, 60, 120
    df_res['MA5'] = close_series.rolling(window=5).mean()
    df_res['MA10'] = close_series.rolling(window=10).mean()
    df_res['MA20'] = close_series.rolling(window=20).mean()
    df_res['MA60'] = close_series.rolling(window=60).mean()
    df_res['MA120'] = close_series.rolling(window=120).mean()
    
    # EMA & Bias (保留原本的 EMA 用於乖離分析)
    for ma in ema_periods:
        df_res[f'EMA_{ma}'] = close_series.ewm(span=ma, adjust=False).mean()
        df_res[f'Bias_{ma}'] = (close_series - df_res[f'EMA_{ma}']) / df_res[f'EMA_{ma}'] * 100
        
    # Bollinger Bands (20, 2)
    df_res['ma20'] = close_series.rolling(window=20).mean()
    df_res['std20'] = close_series.rolling(window=20).std()
    df_res['bb_upper'] = df_res['ma20'] + (2 * df_res['std20'])
    df_res['bb_lower'] = df_res['ma20'] - (2 * df_res['std20'])
    df_res['bb_width'] = (df_res['bb_upper'] - df_res['bb_lower']) / df_res['ma20']
    df_res['ma20_slope'] = df_res['ma20'].diff()
    
    # Volume MA
    volume_series = df_res['Volume'].iloc[:, 0] if isinstance(df_res['Volume'], pd.DataFrame) else df_res['Volume']
    df_res['vol_ma'] = volume_series.rolling(window=20).mean()
    
    # BB Width Rank
    widths = df_res['bb_width']
    df_res['bb_width_rank'] = widths.rolling(window=1080, min_periods=50).apply(lambda x: (x <= x[-1]).mean() if len(x) > 0 else 0.5, raw=True)

    # RSI
    delta = close_series.diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1/rsi_period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/rsi_period, adjust=False).mean()
    rs = avg_gain / avg_loss
    df_res[f'RSI_{rsi_period}'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = close_series.ewm(span=12, adjust=False).mean()
    exp2 = close_series.ewm(span=26, adjust=False).mean()
    df_res['MACD_12_26_9'] = exp1 - exp2
    df_res['MACDs_12_26_9'] = df_res['MACD_12_26_9'].ewm(span=9, adjust=False).mean()
    df_res['MACDh_12_26_9'] = df_res['MACD_12_26_9'] - df_res['MACDs_12_26_9']
    
    # Signal
    df_res['Signal'] = 0.0
    df_res.loc[df_res['MA5'] > df_res['MA20'], 'Signal'] = 1.0
    df_res['Position'] = df_res['Signal'].diff()
    
    return df_res

try:
    if market == "虛擬貨幣 (Crypto)":
        # 使用選擇的時間週期來讀取主數據
        df = load_chart_data_binance(ticker, start_date, end_date, selected_interval)
        if ticker != benchmark_ticker:
            bm_df = load_chart_data_binance(benchmark_ticker, start_date, end_date, selected_interval)
        else:
            bm_df = df.copy()
        
        # 獲取即時價格資訊
        crypto_realtime = get_binance_realtime_data(ticker)
        
        info = {
            'shortName': f"{ticker} 永續合約", 
            'sector': '加密貨幣', 
            'industry': 'DeFi / Blockchain',
            'currentPrice': crypto_realtime.get('currentPrice'),
            'regularMarketPrice': crypto_realtime.get('currentPrice'),
            'dayHigh': crypto_realtime.get('high'),
            'dayLow': crypto_realtime.get('low')
        }
        fund_data = {}
    else:
        # yfinance 處理
        yf_interval_map = {"15m": "15m", "1h": "1h", "2h": "2h", "4h": "4h",
                           "6h": "6h", "8h": "8h", "12h": "12h", "2d": "5d", "3d": "1wk"}
        yf_interval = yf_interval_map.get(selected_interval, "1d")
        yf_valid = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
        
        if yf_interval not in yf_valid:
            yf_interval = "1d"
            
        df = load_chart_data_yf(ticker, start_date, end_date, yf_interval)
        bm_df = load_chart_data_yf(benchmark_ticker, start_date, end_date, yf_interval)
        info = load_info(ticker)
        fund_data = load_fundamentals(ticker)

    if df.empty:
        st.error(f"找不到股票代碼 `{ticker}` 的數據。可能原因：yfinance 暫時無法獲取該資料、代碼輸入錯誤、或該時段無交易數據。")
        st.info("提示：若為台股，請確保選擇正確的『上市』或『上櫃』市場。台股上市代碼後綴應為 `.TW`，上櫃為 `.TWO`。")
    else:
        # 處理 MultiIndex columns (yfinance 新版常見問題)
        if isinstance(df.columns, pd.MultiIndex):
            # 嘗試尋找包含技術指標名稱的那一層
            found = False
            for i in range(df.columns.nlevels):
                levels = df.columns.get_level_values(i)
                if 'Close' in levels:
                    df.columns = levels
                    found = True
                    break
            # 若沒找到，嘗試傳統的第 0 層
            if not found:
                df.columns = [col[0] for col in df.columns]
        
        if not bm_df.empty and isinstance(bm_df.columns, pd.MultiIndex):
            for i in range(bm_df.columns.nlevels):
                levels = bm_df.columns.get_level_values(i)
                if 'Close' in levels:
                    bm_df.columns = levels
                    break
            
        df = df.loc[:, ~df.columns.duplicated()]
        if not bm_df.empty:
            bm_df = bm_df.loc[:, ~bm_df.columns.duplicated()]
        
        if not df.empty and pd.isna(df['Close'].iloc[-1]):
            c_price = info.get('currentPrice', info.get('regularMarketPrice'))
            c_open = info.get('open', info.get('regularMarketOpen'))
            c_high = info.get('dayHigh', info.get('regularMarketDayHigh'))
            c_low = info.get('dayLow', info.get('regularMarketDayLow'))
            
            if c_price: df.iloc[-1, df.columns.get_loc('Close')] = c_price
            if c_open: df.iloc[-1, df.columns.get_loc('Open')] = c_open
            if c_high: df.iloc[-1, df.columns.get_loc('High')] = c_high
            if c_low: df.iloc[-1, df.columns.get_loc('Low')] = c_low

        df = df.dropna(subset=['Close', 'Open', 'High', 'Low'])
        if not bm_df.empty:
            bm_df = bm_df.dropna(subset=['Close', 'Open', 'High', 'Low'])

        # --- 計算指標 ---
        ema_periods = [8, 13, 21, 55, 100, 200]
        df = calculate_indicators(df, ema_periods, rsi_period)
        levels = find_key_levels(df)

        # --- 獲取數據 ---
        latest_data = df.iloc[-1]
        prev_data = df.iloc[-2] if len(df) > 1 else latest_data
        
        latest_close = float(latest_data['Close'].iloc[0]) if isinstance(latest_data['Close'], pd.Series) else float(latest_data['Close'])
        prev_close = float(prev_data['Close'].iloc[0]) if isinstance(prev_data['Close'], pd.Series) else float(prev_data['Close'])
        price_change = latest_close - prev_close
        price_change_pct = (price_change / prev_close) * 100 if prev_close != 0 else 0
        latest_date_str = latest_data.name.strftime('%Y-%m-%d')

        # --- 定義趨勢描述 ---
        trend_dir = "多頭排列" if latest_data['MA5'] > latest_data['MA20'] > latest_data['MA60'] else "回調整理中"
        ma_msg = "均線多頭排列" if latest_data['MA5'] > latest_data['MA10'] > latest_data['MA20'] else "均線糾結或空頭"
        
        # --- 1. 頁面標題與核心數據 (Header) ---
        st.markdown(f"""
        <div class="header-box">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 style="margin:0; color:white;">{info.get('shortName', ticker)} <span style="font-size:1.5rem; color:#888;">交易計畫</span></h1>
                    <div style="background:#2b2b43; padding:4px 10px; border-radius:4px; display:inline-block; margin-top:8px;">市 {ticker.split('.')[0]}</div>
                </div>
                <div class="price-box" style="background-color: {'#ef5350' if price_change >= 0 else '#26a69a'}; min-width: 200px;">
                    <div style="font-size:0.9rem; opacity:0.8;">目前股價</div>
                    <div class="price-val">{latest_close:.2f}</div>
                    <div class="price-change">{'▲' if price_change >= 0 else '▼'} {abs(price_change):.2f} ({price_change_pct:.2f}%)</div>
                </div>
                <div style="display: flex; gap: 40px; text-align: center;">
                    <div><div style="color:#888; font-size:0.9rem;">趨勢方向</div><div style="font-size:1.2rem; font-weight:bold;">{trend_dir}</div></div>
                    <div><div style="color:#888; font-size:0.9rem;">總量</div><div style="font-size:1.2rem; font-weight:bold;">{int(latest_data['Volume']):,}</div></div>
                    <div><div style="color:#888; font-size:0.9rem;">RSI</div><div style="font-size:1.2rem; font-weight:bold;">{latest_data[f'RSI_{rsi_period}']:.1f}</div></div>
                </div>
            </div>
            <div style="margin-top:15px; font-size:0.9rem; color:#888;">更新日期：{latest_date_str}</div>
        </div>
        """, unsafe_allow_html=True)

        # --- 主內容區 (3 欄佈局) ---
        col_left, col_mid, col_right = st.columns([1, 2, 1])

        with col_left:
            # 1. 趨勢判斷
            st.markdown(f"""
            <div class="plan-card">
                <div class="plan-title">1. 趨勢判斷</div>
                <ul style="padding-left:20px; line-height:1.8;">
                    <li>前波壓力 ({levels.get('res1')}) 測試中</li>
                    <li>{ma_msg}</li>
                    <li>量能配合：{'放量' if latest_data['Volume'] > df['Volume'].tail(20).mean() else '縮量'}整理中</li>
                    <li>趨勢方向：{trend_dir}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            # 2. 關鍵價位
            st.markdown(f"""
            <div class="plan-card">
                <div class="plan-title">2. 關鍵價位</div>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <div style="display:flex; justify-content:space-between;"><span>壓力 2</span><span style="color:#ef5350; font-weight:bold;">{levels.get('res2')}</span></div>
                    <div style="font-size:0.8rem; color:#888; margin-bottom:4px;">({levels.get('res2_desc')})</div>
                    <div style="display:flex; justify-content:space-between;"><span>壓力 1</span><span style="color:#ef5350; font-weight:bold;">{levels.get('res1')}</span></div>
                    <div style="font-size:0.8rem; color:#888; margin-bottom:4px;">({levels.get('res1_desc')})</div>
                    <div style="display:flex; justify-content:space-between; background:#2b2b43; padding:5px; border-radius:4px;"><span>現價</span><span style="font-weight:bold;">{latest_close:.2f}</span></div>
                    <div style="display:flex; justify-content:space-between; margin-top:5px;"><span>支撐 1</span><span style="color:#26a69a; font-weight:bold;">{levels.get('sup1')}</span></div>
                    <div style="font-size:0.8rem; color:#888; margin-bottom:4px;">({levels.get('sup1_desc')})</div>
                    <div style="display:flex; justify-content:space-between;"><span>支撐 2</span><span style="color:#26a69a; font-weight:bold;">{levels.get('sup2')}</span></div>
                    <div style="font-size:0.8rem; color:#888; margin-bottom:4px;">({levels.get('sup2_desc')})</div>
                    <div style="display:flex; justify-content:space-between; border-top:1px solid #2b2b43; pt:5px;"><span>多頭防守線</span><span style="color:#ffb300;">{levels.get('sup1')}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_mid:
            # 3. 技術圖表
            with st.container(border=True):
                st.subheader("3. 技術圖表 (日線)")
                # 使用 subplots 
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                   vertical_spacing=0.03, 
                                   row_heights=[0.7, 0.3])
                
                # K 線
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'), row=1, col=1)
                
                # 均線色彩依圖片調整
                colors = {'MA5': 'gold', 'MA10': 'cyan', 'MA20': 'magenta', 'MA60': 'lime', 'MA120': 'white'}
                for ma in colors:
                    if ma in df.columns:
                        fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma, line=dict(color=colors[ma], width=1)), row=1, col=1)
                
                # 繪製關鍵價位水平線
                fig.add_hline(y=levels.get('res1'), line_dash="dash", line_color="#ef5350", annotation_text="壓力1", row=1, col=1)
                fig.add_hline(y=levels.get('sup1'), line_dash="dash", line_color="#26a69a", annotation_text="支撐1", row=1, col=1)
                
                _close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
                _open = df['Open'].iloc[:, 0] if isinstance(df['Open'], pd.DataFrame) else df['Open']
                vol_colors = ['#ef5350' if c < o else '#26a69a' for c, o in zip(_close, _open)]
                fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=vol_colors), row=2, col=1)
                
                fig.update_layout(height=550, margin=dict(l=10, r=10, t=10, b=10), showlegend=True, 
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                  xaxis_rangeslider_visible=False, template="plotly_dark",
                                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

            # 5. 進場計畫
            st.markdown('<div class="plan-card"><div class="plan-title">5. 進場計畫 (範例)</div>', unsafe_allow_html=True)
            plan_data = [
                ["多頭回測", f"在 {levels.get('sup1')} 整理", f"{levels.get('sup1')}~{latest_close:.2f}", f"{levels.get('sup2')}", f"{levels.get('res1')}", "≥2:1"],
                ["突破進場", f"放量突破 {levels.get('res1')}", f"{levels.get('res1')}~{levels.get('res1')*1.02:.2f}", f"{latest_close:.2f}", f"{levels.get('res2')}", "≥2:1"],
            ]
            df_plan = pd.DataFrame(plan_data, columns=["情境", "進場條件", "進場價位", "停損值", "目標", "盈虧比"])
            st.table(df_plan)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_right:
            # 4. 交易策略
            st.markdown(f"""
            <div class="plan-card">
                <div class="plan-title">4. 交易策略</div>
                <div style="margin-bottom:15px;">
                    <div style="color:#ef5350; font-weight:bold; margin-bottom:5px;">多頭回測</div>
                    <div style="font-size:0.85rem; line-height:1.6;">
                        • 條件：在 {levels.get('sup1')} 支撐附近分批<br>
                        • 進場：{levels.get('sup1')} ~ {latest_close:.2f} 承接<br>
                        • 目標：{levels.get('res1')} / {levels.get('res2')}<br>
                        • 停損：跌破 {levels.get('sup2')}
                    </div>
                </div>
                <div style="border-top: 1px solid #2b2b43; padding-top:15px; margin-bottom:15px;">
                    <div style="color:#42a5f5; font-weight:bold; margin-bottom:5px;">突破進場</div>
                    <div style="font-size:0.85rem; line-height:1.6;">
                        • 條件：放量突破壓力1 ({levels.get('res1')})<br>
                        • 進場：突破後回測不破 {levels.get('res1')}<br>
                        • 目標：{levels.get('res2')} / 以上<br>
                        • 停損：跌破 {latest_close:.2f}
                    </div>
                </div>
                <div style="border-top: 1px solid #2b2b43; padding-top:15px;">
                    <div style="color:#26a69a; font-weight:bold; margin-bottom:5px;">空頭避險</div>
                    <div style="font-size:0.85rem; line-height:1.6;">
                        • 條件：跌破強力支撐 {levels.get('sup2')}<br>
                        • 動作：減碼或反手放空避險
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # --- 底部區 (風險與紀律) ---
        st.divider()
        b_col1, b_col2, b_col3 = st.columns(3)
        with b_col1:
            st.markdown("""
            <div class="plan-card">
                <div class="plan-title">6. 風險管理</div>
                <ul style="padding-left:20px; font-size:0.9rem; line-height:1.8;">
                    <li>單筆風險：不超過總資金 2%</li>
                    <li>停損嚴格執行，不攤平、不加碼</li>
                    <li>盈虧比建議 ≥ 1:2</li>
                    <li>避免重大消息發布前後重倉操作</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with b_col2:
            st.markdown("""
            <div class="plan-card">
                <div class="plan-title">7. 執行紀律</div>
                <div style="font-size:0.9rem; line-height:2;">
                    ✅ 進場前確認條件達成<br>
                    ✅ 嚴格執行停損停利<br>
                    ✅ 不預設立場，順勢操作<br>
                    ✅ 每日檢討，優化交易計畫
                </div>
            </div>
            """, unsafe_allow_html=True)

        with b_col3:
            st.markdown(f"""
            <div class="plan-card">
                <div class="plan-title">8. 備註</div>
                <div style="font-size:0.9rem; line-height:1.8;">
                    • 前波高點壓力位：{levels.get('res2')}<br>
                    • 關注 {levels.get('sup1')} 平台支撐力度<br>
                    • 站回 {levels.get('res1')} 才能確認轉強<br>
                    • 注意量能是否能有效放大
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='text-align: center; margin-top: 30px;'><h2 style='color: #ffb300; letter-spacing: 5px;'>🎯 順勢操作 · 嚴設停損 · 控管風險 · 紀律執行</h2></div>", unsafe_allow_html=True)
        st.divider()

        # --- 保留原本的基本面與籌碼面資料 ---
        with st.expander("ℹ️ 詳細數據與基本面分析", expanded=False):
            # 顯示個股資訊
            if info and ('shortName' in info or 'longName' in info):
                c1, c2, c3, c4 = st.columns(4)
                name = info.get('shortName') or info.get('longName', 'N/A')
                c1.metric("公司名稱", name)
                c2.metric("產業板塊", info.get('sector', 'N/A'))
                c3.metric("行業別", info.get('industry', 'N/A'))
                mcap = info.get('marketCap', 0)
                mcap_str = f"{mcap/1e12:.2f} 兆" if mcap >= 1e12 else (f"{mcap/1e8:.2f} 億" if mcap >= 1e8 else str(mcap))
                c4.metric("市值", mcap_str)

            # 產業與相對動量
            st.markdown("### 🏢 產業與相對大盤動量")
            if not df.empty and not bm_df.empty:
                c_m1, c_m2, c_m3 = st.columns(3)
                
                stock_5d = calc_return(df, 5)
                bm_5d = calc_return(bm_df, 5)
                alpha_5d = stock_5d - bm_5d
                
                stock_20d = calc_return(df, 20)
                bm_20d = calc_return(bm_df, 20)
                alpha_20d = stock_20d - bm_20d
                
                stock_60d = calc_return(df, 60)
                bm_60d = calc_return(bm_df, 60)
                alpha_60d = stock_60d - bm_60d
                
                with c_m1:
                    st.metric("近 5 日動量 (短期)", f"{stock_5d:.2f}%", f"{alpha_5d:+.2f}% (超額報酬)")
                with c_m2:
                    st.metric("近 20 日動量 (中期)", f"{stock_20d:.2f}%", f"{alpha_20d:+.2f}% (超額報酬)")
                with c_m3:
                    st.metric("近 60 日動量 (長期)", f"{stock_60d:.2f}%", f"{alpha_60d:+.2f}% (超額報酬)")
            
            # 基本面資訊
            if fund_data or market in ["台股上市 (TWSE)", "台股上櫃 (OTC)"]:
                st.markdown("### 📊 基本面數據")
                f_col1, f_col2 = st.columns(2)
                
                with f_col1:
                    if fund_data and 'EPS' in fund_data and not fund_data['EPS'].empty:
                        st.markdown("**每股盈餘 (EPS)** (近四季)")
                        for idx, val in fund_data['EPS'].items():
                            st.markdown(f"- **{idx}**: `{val:.2f}`")
                        
                with f_col2:
                    if market in ["台股上市 (TWSE)", "台股上櫃 (OTC)"]:
                        tw_rev_data = load_tw_monthly_revenue(ticker, finmind_token)
                        if tw_rev_data:
                            st.markdown("**月營收 (Revenue) 增長率** (近四月)")
                            for month_str, data in tw_rev_data.items():
                                val = data['revenue']
                                val_str = f"{val/1e12:.2f} 兆" if val >= 1e12 else (f"{val/1e8:.2f} 億" if val >= 1e8 else (f"{val/1e4:.2f} 萬" if val >= 1e4 else f"{val:,.2f}"))
                                yoy_str = f"YoY: {data['YoY']:+.2f}%" if pd.notna(data['YoY']) else "YoY: N/A"
                                mom_str = f"MoM: {data['MoM']:+.2f}%" if pd.notna(data['MoM']) else "MoM: N/A"
                                st.markdown(f"- **{month_str}**: `{val_str}`  `({yoy_str}, {mom_str})`")
                    elif fund_data and 'Revenue' in fund_data and not fund_data['Revenue'].empty:
                        st.markdown("**總營收 (Revenue) 增長率** (近四季)")
                        for idx, val in fund_data['Revenue'].items():
                            val_str = f"{val/1e12:.2f} 兆" if val >= 1e12 else (f"{val/1e8:.2f} 億" if val >= 1e8 else (f"{val/1e4:.2f} 萬" if val >= 1e4 else f"{val:,.2f}"))
                            yoy_val = fund_data.get('Revenue_YoY', pd.Series()).get(idx)
                            qoq_val = fund_data.get('Revenue_QoQ', pd.Series()).get(idx)
                            yoy_str = f"YoY: {yoy_val:+.2f}%" if pd.notna(yoy_val) else "YoY: N/A"
                            qoq_str = f"QoQ: {qoq_val:+.2f}%" if pd.notna(qoq_val) else "QoQ: N/A"
                            st.markdown(f"- **{idx}**: `{val_str}`  `({yoy_str}, {qoq_str})`")

        # --- 籌碼面分析 (台股專屬) ---
        if market in ["台股上市 (TWSE)", "台股上櫃 (OTC)"]:
            total_vol = float(latest_data['Volume'].iloc[0]) if isinstance(latest_data['Volume'], pd.Series) else float(latest_data['Volume'])
            chip_data = load_tw_chip_data(ticker, total_vol, finmind_token)
            chip_dist = load_tw_chip_distribution(ticker, finmind_token)
            
            if chip_data:
                with st.expander("🎯 主力法人籌碼動向", expanded=False):
                    st.markdown("#### 近一日與近五日動向")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.metric("主力單日", f"{chip_data['mf_net']:,.0f} 張", f"{chip_data['mf_pct']:.2f}%"); st.write(f"累計: {chip_data['mf_5d']:,.0f}")
                    with c2: st.metric("外資單日", f"{chip_data['fi_net']:,.0f} 張", f"{chip_data['fi_pct']:.2f}%"); st.write(f"累計: {chip_data['fi_5d']:,.0f}")
                    with c3: st.metric("投信單日", f"{chip_data['it_net']:,.0f} 張", f"{chip_data['it_pct']:.2f}%"); st.write(f"累計: {chip_data['it_5d']:,.0f}")
                    with c4: st.metric("自營商單日", f"{chip_data['dl_net']:,.0f} 張", f"{chip_data['dl_pct']:.2f}%"); st.write(f"累計: {chip_data['dl_5d']:,.0f}")

            if chip_dist and not chip_dist.get('distribution', pd.DataFrame()).empty:
                with st.expander(f"📊 主力籌碼分布 (集保: {chip_dist['date']})", expanded=False):
                    col_dist_text, col_dist_chart = st.columns([1, 1])
                    with col_dist_text:
                        st.metric("超級大戶 (>1000張) 比例", f"{chip_dist['large_latest_pct']:.2f}%")
                        dist_df = chip_dist['distribution']
                        for _, row in dist_df.iterrows():
                            st.markdown(f"- **{row['Category']}**: `{row['percent']:.2f}%`")
                    with col_dist_chart:
                        fig_pie = go.Figure(data=[go.Pie(labels=dist_df['Category'], values=dist_df['percent'], hole=0.4)])
                        fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
                        st.plotly_chart(fig_pie, use_container_width=True)

except Exception as e:
    import traceback
    with open('/tmp/streamlit_traceback.log', 'w') as f:
        f.write(traceback.format_exc())
    st.error(f"發生錯誤: {e}")

st.sidebar.markdown("---")
st.sidebar.info("這只是一個模板，投資有風險，請謹慎評估。")
