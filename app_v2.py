import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests

# 頁面配置
st.set_page_config(page_title="股票分析策略模板", layout="wide")

st.title("📈 股票分析策略網頁模板")
st.markdown("""
這是一個使用 Streamlit 建立的股票分析模板。您可以輸入股票代碼、選擇日期範圍，並查看技術指標、大盤動量與簡易回測結果。
""")

# --- 側邊欄設定 ---
st.sidebar.header("參數設定")

market = st.sidebar.selectbox("選擇市場", ["美股 (US)", "台股上市 (TWSE)", "台股上櫃 (OTC)"])

# 根據市場預設代碼
default_ticker = "AAPL" if market == "美股 (US)" else "2330"
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
else:
    ticker = raw_ticker

st.sidebar.markdown(f"**實際查詢代碼:** `{ticker}`")

start_date = st.sidebar.date_input("開始日期", value=datetime.now() - timedelta(days=365))
end_date = st.sidebar.date_input("結束日期", value=datetime.now())

st.sidebar.subheader("技術指標參數")
rsi_period = st.sidebar.number_input("RSI 週期", value=14)

st.sidebar.divider()
st.sidebar.subheader("🔑 進階 API 設定")
finmind_token = st.sidebar.text_input("FinMind API Token (選填)", type="password", help="若要解鎖大戶籌碼分布等付費資料，請輸入您的 Token。")

# --- 抓取數據 ---
@st.cache_data
def load_data(symbol, start, end):
    data = yf.download(symbol, start=start, end=end)
    return data

@st.cache_data
def load_info(symbol):
    try:
        ticker_obj = yf.Ticker(symbol)
        return ticker_obj.info
    except Exception:
        return {}

@st.cache_data
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

@st.cache_data
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
def load_tw_chip_distribution(symbol, token=""):
    try:
        stock_id = symbol.split('.')[0]
        start_date_str = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockHoldingSharesPer&data_id={stock_id}&start_date={start_date_str}"
        if token: url += f"&token={token}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res_data = res.json()
        
        if res_data.get('msg') != 'success':
            if 'Your level is free' in res_data.get('msg', ''):
                return {'error_type': 'free_tier', 'msg': 'API 權限不足'}
            else:
                return {'error_type': 'api_error', 'msg': res_data.get('msg')}
            
        data = res_data.get('data', [])
        if not data: 
            return {}
        
        df = pd.DataFrame(data)
        df['HoldingSharesLevel'] = df['HoldingSharesLevel'].astype(int)
        df = df[df['HoldingSharesLevel'] <= 15]
        
        latest_date = df['date'].max()
        df_latest = df[df['date'] == latest_date].copy()
        
        def categorize_level(level):
            if level <= 8: return "散戶 (≤50張)"
            elif level <= 11: return "中實戶 (50~400張)"
            elif level <= 14: return "大戶 (400~1000張)"
            else: return "超級大戶 (>1000張)"
            
        df_latest['Category'] = df_latest['HoldingSharesLevel'].apply(categorize_level)
        dist_grouped = df_latest.groupby('Category')['percent'].sum().reset_index()
        
        df_large = df[df['HoldingSharesLevel'] == 15].sort_values('date').reset_index(drop=True)
        if len(df_large) >= 2:
            latest_pct = float(df_large.iloc[-1]['percent'])
            prev_pct = float(df_large.iloc[-2]['percent'])
        elif len(df_large) == 1:
            latest_pct = float(df_large.iloc[-1]['percent'])
            prev_pct = latest_pct
        else:
            latest_pct = 0.0
            prev_pct = 0.0
            
        return {
            'date': latest_date,
            'distribution': dist_grouped,
            'large_latest_pct': latest_pct,
            'diff_pct': latest_pct - prev_pct
        }
    except Exception as e:
        print(f"Error fetching chip distribution: {e}")
        return {}

@st.cache_data
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

try:
    df = load_data(ticker, start_date, end_date)
    bm_df = load_data(benchmark_ticker, start_date, end_date) # 抓取對應大盤數據
    info = load_info(ticker)
    fund_data = load_fundamentals(ticker)

    if df.empty:
        st.error("找不到該股票代碼的數據，請檢查輸入是否正確。")
    else:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        if not bm_df.empty and isinstance(bm_df.columns, pd.MultiIndex):
            bm_df.columns = [col[0] for col in bm_df.columns]
            
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

        # --- 顯示最新價格 ---
        if not df.empty:
            latest_data = df.iloc[-1]
            prev_data = df.iloc[-2] if len(df) > 1 else latest_data
            
            try:
                latest_close = float(latest_data['Close'].iloc[0]) if isinstance(latest_data['Close'], pd.Series) else float(latest_data['Close'])
                prev_close = float(prev_data['Close'].iloc[0]) if isinstance(prev_data['Close'], pd.Series) else float(prev_data['Close'])
                latest_open = float(latest_data['Open'].iloc[0]) if isinstance(latest_data['Open'], pd.Series) else float(latest_data['Open'])
                latest_high = float(latest_data['High'].iloc[0]) if isinstance(latest_data['High'], pd.Series) else float(latest_data['High'])
                latest_low = float(latest_data['Low'].iloc[0]) if isinstance(latest_data['Low'], pd.Series) else float(latest_data['Low'])
                
                price_change = latest_close - prev_close
                price_change_pct = (price_change / prev_close) * 100 if prev_close != 0 else 0
                
                latest_date_str = latest_data.name.strftime('%Y-%m-%d')
                
                st.subheader(f"即時報價: {ticker} (最後更新: {latest_date_str})")
                pc1, pc2, pc3, pc4 = st.columns(4)
                pc1.metric("最新收盤價", f"{latest_close:.2f}", f"{price_change:.2f} ({price_change_pct:.2f}%)")
                pc2.metric("開盤價", f"{latest_open:.2f}")
                pc3.metric("最高價", f"{latest_high:.2f}")
                pc4.metric("最低價", f"{latest_low:.2f}")
                st.divider()
            except Exception as e:
                pass 

        # --- 顯示個股資訊 ---
        if info and ('shortName' in info or 'longName' in info):
            with st.expander("ℹ️ 個股基本資料", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                name = info.get('shortName') or info.get('longName', 'N/A')
                c1.metric("公司名稱", name)
                c2.metric("產業板塊", info.get('sector', 'N/A'))
                c3.metric("行業別", info.get('industry', 'N/A'))
                
                mcap = info.get('marketCap', 0)
                if mcap and mcap >= 1e12:
                    mcap_str = f"{mcap/1e12:.2f} 兆"
                elif mcap and mcap >= 1e8:
                    mcap_str = f"{mcap/1e8:.2f} 億"
                else:
                    mcap_str = str(mcap) if mcap else "N/A"
                c4.metric("市值", mcap_str)

        # --- 產業與相對動量 ---
        with st.expander("🏢 所屬產業與相對大盤動量", expanded=True):
            sector = info.get('sector', 'N/A')
            industry = info.get('industry', 'N/A')
            
            st.markdown(f"**產業定位:** `{sector}` ➔ `{industry}`")
            st.markdown(f"**對標基準 (Benchmark):** `{benchmark_name}`")
            st.caption("透過比較個股與大盤的漲跌幅，判斷該股票所屬產業鏈的相對強弱（資金動能）。超額報酬 > 0 代表打敗大盤，資金流入跡象明顯。")
            
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
            else:
                st.info("無法獲取對標大盤資料，暫無法計算相對動量。")

        # --- 顯示基本面資訊 ---
        if fund_data or market in ["台股上市 (TWSE)", "台股上櫃 (OTC)"]:
            with st.expander("📊 基本面資訊", expanded=True):
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
                                if val >= 1e12:
                                    val_str = f"{val/1e12:.2f} 兆"
                                elif val >= 1e8:
                                    val_str = f"{val/1e8:.2f} 億"
                                elif val >= 1e4:
                                    val_str = f"{val/1e4:.2f} 萬"
                                else:
                                    val_str = f"{val:,.2f}"
                                    
                                yoy_val = data['YoY']
                                mom_val = data['MoM']
                                yoy_str = f"YoY: {yoy_val:+.2f}%" if pd.notna(yoy_val) else "YoY: N/A"
                                mom_str = f"MoM: {mom_val:+.2f}%" if pd.notna(mom_val) else "MoM: N/A"
                                
                                st.markdown(f"- **{month_str}**: `{val_str}`  `({yoy_str}, {mom_str})`")
                        else:
                            st.markdown("**月營收 (Revenue)**\n\n查無資料")
                    else:
                        if fund_data and 'Revenue' in fund_data and not fund_data['Revenue'].empty:
                            st.markdown("**總營收 (Revenue) 增長率** (近四季)")
                            for idx, val in fund_data['Revenue'].items():
                                if val >= 1e12:
                                    val_str = f"{val/1e12:.2f} 兆"
                                elif val >= 1e8:
                                    val_str = f"{val/1e8:.2f} 億"
                                elif val >= 1e4:
                                    val_str = f"{val/1e4:.2f} 萬"
                                else:
                                    val_str = f"{val:,.2f}"
                                    
                                yoy_val = fund_data.get('Revenue_YoY', pd.Series()).get(idx)
                                qoq_val = fund_data.get('Revenue_QoQ', pd.Series()).get(idx)
                                
                                yoy_str = f"YoY: {yoy_val:+.2f}%" if pd.notna(yoy_val) else "YoY: N/A"
                                qoq_str = f"QoQ: {qoq_val:+.2f}%" if pd.notna(qoq_val) else "QoQ: N/A"
                                    
                                st.markdown(f"- **{idx}**: `{val_str}`  `({yoy_str}, {qoq_str})`")

        # --- 顯示籌碼面分析 (台股專屬) ---
        if market in ["台股上市 (TWSE)", "台股上櫃 (OTC)"]:
            total_vol = float(latest_data['Volume'].iloc[0]) if isinstance(latest_data['Volume'], pd.Series) else float(latest_data['Volume'])
            chip_data = load_tw_chip_data(ticker, total_vol, finmind_token)
            chip_dist = load_tw_chip_distribution(ticker, finmind_token)
            
            if chip_data:
                with st.expander(f"🎯 主力法人籌碼 (最後更新: {chip_data['date']})", expanded=True):
                    st.markdown("#### 近一日動向 (單日買賣超)")
                    c1, c2, c3, c4 = st.columns(4)
                    
                    with c1:
                        st.markdown("**主力 (三大法人)**")
                        st.metric("單日", f"{chip_data['mf_net']:,.0f} 張", f"{chip_data['mf_pct']:.2f}% (佔成交)")
                        st.markdown(f"**力道:** {chip_data['mf_momentum']}")
                        
                    with c2:
                        st.markdown("**外資**")
                        st.metric("單日", f"{chip_data['fi_net']:,.0f} 張", f"{chip_data['fi_pct']:.2f}% (佔成交)")
                        st.markdown(f"**力道:** {chip_data['fi_momentum']}")
                        
                    with c3:
                        st.markdown("**投信**")
                        st.metric("單日", f"{chip_data['it_net']:,.0f} 張", f"{chip_data['it_pct']:.2f}% (佔成交)")
                        st.markdown(f"**力道:** {chip_data['it_momentum']}")
                        
                    with c4:
                        st.markdown("**自營商**")
                        st.metric("單日", f"{chip_data['dl_net']:,.0f} 張", f"{chip_data['dl_pct']:.2f}% (佔成交)")
                        st.markdown(f"**力道:** {chip_data['dl_momentum']}")

                    st.divider()
                    
                    st.markdown("#### 近五日動向 (五日累計)")
                    c5_1, c5_2, c5_3, c5_4 = st.columns(4)
                    
                    with c5_1:
                        st.metric("主力 (三大法人) 累計", f"{chip_data['mf_5d']:,.0f} 張")
                    with c5_2:
                        st.metric("外資累計", f"{chip_data['fi_5d']:,.0f} 張")
                    with c5_3:
                        st.metric("投信累計", f"{chip_data['it_5d']:,.0f} 張")
                    with c5_4:
                        st.metric("自營商累計", f"{chip_data['dl_5d']:,.0f} 張")
            
            # --- 獨立的大戶籌碼分布區塊 ---
            if chip_dist and chip_dist.get('error_type') == 'free_tier':
                with st.expander("📊 主力籌碼分布", expanded=True):
                    st.warning("⚠️ **FinMind API 限制**：目前使用的免費額度無法抓取「集保戶股權分散表」。\n\n若您有 FinMind 贊助會員，請在左側面板輸入您的 **API Token** 來解鎖大戶籌碼分布圖表。")
            elif chip_dist and chip_dist.get('error_type') == 'api_error':
                with st.expander("📊 主力籌碼分布", expanded=True):
                    st.error(f"獲取資料失敗: {chip_dist.get('msg')}")
            elif chip_dist and not chip_dist.get('distribution', pd.DataFrame()).empty:
                with st.expander(f"📊 主力籌碼分布 (集保更新日期: {chip_dist['date']})", expanded=True):
                    col_dist_text, col_dist_chart = st.columns([1, 1.5])
                    
                    with col_dist_text:
                        st.markdown("#### 股權分散狀況")
                        st.info("台股集保戶股權資料每週更新一次。")
                        
                        st.metric("超級大戶 (>1000張) 比例", 
                                f"{chip_dist['large_latest_pct']:.2f}%", 
                                f"{chip_dist['diff_pct']:+.2f}% (較上週)")
                        
                        st.markdown("---")
                        dist_df = chip_dist['distribution']
                        for index, row in dist_df.iterrows():
                            st.markdown(f"- **{row['Category']}**: `{row['percent']:.2f}%`")
                            
                    with col_dist_chart:
                        dist_df = chip_dist['distribution']
                        colors = {
                            "散戶 (≤50張)": "#26a69a",
                            "中實戶 (50~400張)": "#42a5f5",
                            "大戶 (400~1000張)": "#ffa726",
                            "超級大戶 (>1000張)": "#ef5350"
                        }
                        
                        fig_pie = go.Figure(data=[go.Pie(
                            labels=dist_df['Category'], 
                            values=dist_df['percent'],
                            hole=0.4,
                            marker=dict(colors=[colors.get(c, '#888888') for c in dist_df['Category']])
                        )])
                        
                        fig_pie.update_layout(
                            margin=dict(t=0, b=0, l=0, r=0),
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
            else:
                with st.expander("📊 主力籌碼分布", expanded=True):
                    st.info("目前暫無集保籌碼分布資料。")

        # --- 計算指標 (新增乖離率 Bias) ---
        ma_periods = [5, 10, 20, 60, 120]
        for ma in ma_periods:
            df.ta.sma(length=ma, append=True)
            # 新增計算乖離率 (Bias Ratio)
            if f'SMA_{ma}' in df.columns:
                df[f'Bias_{ma}'] = (df['Close'] - df[f'SMA_{ma}']) / df[f'SMA_{ma}'] * 100
                
        df.ta.rsi(length=rsi_period, append=True)
        df.ta.macd(append=True)

        # --- 策略邏輯 ---
        df['Signal'] = 0.0
        if 'SMA_5' in df.columns and 'SMA_20' in df.columns:
            df.loc[df['SMA_5'] > df['SMA_20'], 'Signal'] = 1.0
        df['Position'] = df['Signal'].diff()

        # --- 乖離率分析面板 ---
        try:
            latest_row = df.iloc[-1]
            with st.expander("📏 價格乖離率 (Bias Ratio)", expanded=True):
                st.caption("乖離率衡量股價偏離均線的程度。當正乖離率過大時，代表股價短線可能過熱；當負乖離率過大時，代表股價短線可能超跌。")
                b1, b2, b3, b4 = st.columns(4)
                
                # 取得最新乖離率
                bias_5 = float(latest_row.get('Bias_5', 0))
                bias_10 = float(latest_row.get('Bias_10', 0))
                bias_20 = float(latest_row.get('Bias_20', 0))
                bias_60 = float(latest_row.get('Bias_60', 0))
                
                b1.metric("5日乖離率 (周線)", f"{bias_5:.2f}%")
                b2.metric("10日乖離率", f"{bias_10:.2f}%")
                b3.metric("20日乖離率 (月線)", f"{bias_20:.2f}%")
                b4.metric("60日乖離率 (季線)", f"{bias_60:.2f}%")
        except Exception as e:
            pass

        # --- 策略建議 ---
        st.markdown("### 💡 趨勢與策略建議")
        try:
            latest_row = df.iloc[-1]
            c_price = float(latest_row['Close'].iloc[0]) if isinstance(latest_row['Close'], pd.Series) else float(latest_row['Close'])
            ma5 = float(latest_row['SMA_5'])
            ma10 = float(latest_row['SMA_10'])
            ma20 = float(latest_row['SMA_20'])
            ma60 = float(latest_row['SMA_60'])
            ma120 = float(latest_row['SMA_120'])
            
            latest_rsi = float(latest_row[f'RSI_{rsi_period}']) if f'RSI_{rsi_period}' in latest_row else 50
            latest_macd = float(latest_row['MACD_12_26_9']) if 'MACD_12_26_9' in latest_row else 0
            
            col_s1, col_s2, col_s3 = st.columns(3)
            
            with col_s1:
                if c_price > ma5 > ma20 > ma60:
                    st.success("🟢 **短線偏多**: 價格 > 5日線 > 20日線 > 60日線")
                elif c_price < ma5 < ma20 < ma60:
                    st.error("🔴 **短線偏空**: 價格 < 5日線 < 20日線 < 60日線")
                else:
                    st.warning("🟡 **短線盤整**: 短期均線糾結或未達明確多空排列")
                    
            with col_s2:
                if c_price > ma60 > ma120:
                    st.success("🟢 **長線偏多**: 價格 > 60日線 > 120日線")
                elif c_price < ma60 < ma120:
                    st.error("🔴 **長線偏空**: 價格 < 60日線 < 120日線")
                else:
                    st.warning("🟡 **長線盤整**: 長期均線未達明確多空排列")
                    
            with col_s3:
                if latest_rsi > 50 and latest_macd > 0:
                    st.success(f"🟢 **動能偏多**: RSI({latest_rsi:.1f}) > 50 且 MACD > 0")
                elif latest_rsi < 50 and latest_macd < 0:
                    st.error(f"🔴 **動能偏空**: RSI({latest_rsi:.1f}) < 50 且 MACD < 0")
                else:
                    st.warning(f"🟡 **動能盤整**: RSI({latest_rsi:.1f}) 與 MACD 無強勢方向")
                    
            # --- 多頭進場區間 ---
            st.markdown("#### 🎯 多頭進場區間參考")
            
            short_upper = max(ma5, ma10)
            short_lower = min(ma5, ma10)
            short_stop = ma10 * 0.98
            
            long_upper = max(ma20, ma60)
            long_lower = min(ma20, ma60)
            long_stop = ma60 * 0.98
            
            col_in1, col_in2 = st.columns(2)
            
            with col_in1:
                st.info(f"**⚡ 短線進場區間**\n\n建議佈局: **{short_lower:.2f} ~ {short_upper:.2f}** \n\n防守停損: **{short_stop:.2f}** ")
                
            with col_in2:
                st.info(f"**🐢 長線進場區間**\n\n建議佈局: **{long_lower:.2f} ~ {long_upper:.2f}** \n\n防守停損: **{long_stop:.2f}** ")

        except Exception:
            st.info("資料不足以計算長短線趨勢與進場區間，請確認所選日期範圍大於 120 天。")
            
        st.divider()

        # --- 顯示主要圖表 ---
        st.subheader(f"{ticker} 股價與技術指標")
        
        tab1, tab2, tab3 = st.tabs(["📊 綜合分析", "🕯️ 純 K 線圖", "📈 數據與回測"])
        
        with tab1:
            fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.05, 
                               row_heights=[0.4, 0.2, 0.2, 0.2],
                               subplot_titles=('K線圖與均線 (5/10/20/60/120)', '成交量 (Volume)', 'RSI', 'MACD'))

            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                        low=df['Low'], close=df['Close'], name='K線'), row=1, col=1)
            
            ma_colors = {5: 'orange', 10: 'blue', 20: 'green', 60: 'red', 120: 'purple'}
            for ma, color in ma_colors.items():
                if f'SMA_{ma}' in df.columns:
                    fig.add_trace(go.Scatter(x=df.index, y=df[f'SMA_{ma}'], name=f'SMA {ma}', line=dict(color=color, width=1)), row=1, col=1)

            buy_signals = df[df['Position'] == 1]
            sell_signals = df[df['Position'] == -1]
            
            fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Low'] * 0.98, mode='markers', 
                                    marker=dict(symbol='triangle-up', size=10, color='green'), name='買入訊號'), row=1, col=1)
            fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['High'] * 1.02, mode='markers', 
                                    marker=dict(symbol='triangle-down', size=10, color='red'), name='賣出訊號'), row=1, col=1)

            _close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
            _open = df['Open'].iloc[:, 0] if isinstance(df['Open'], pd.DataFrame) else df['Open']
            _volume = df['Volume'].iloc[:, 0] if isinstance(df['Volume'], pd.DataFrame) else df['Volume']
            
            vol_colors = ['#ef5350' if c >= o else '#26a69a' for c, o in zip(_close, _open)]
            fig.add_trace(go.Bar(x=df.index, y=_volume, name='成交量', marker_color=vol_colors), row=2, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df[f'RSI_{rsi_period}'], name='RSI', line=dict(color='purple')), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

            fig.add_trace(go.Bar(x=df.index, y=df[f'MACDh_{12}_{26}_{9}'], name='Histogram'), row=4, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[f'MACD_{12}_{26}_{9}'], name='MACD'), row=4, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[f'MACDs_{12}_{26}_{9}'], name='Signal'), row=4, col=1)

            fig.update_layout(height=1000, xaxis_rangeslider_visible=False, showlegend=True)
            fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.markdown("### 專屬 K 線圖 (Candlestick Chart)")
            fig_k = go.Figure(data=[go.Candlestick(x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'],
                            name='K線')])
            
            for ma, color in ma_colors.items():
                if f'SMA_{ma}' in df.columns:
                    fig_k.add_trace(go.Scatter(x=df.index, y=df[f'SMA_{ma}'], name=f'SMA {ma}', line=dict(color=color, width=1)))
            
            fig_k.update_layout(height=600, xaxis_rangeslider_visible=False, showlegend=True)
            fig_k.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
            st.plotly_chart(fig_k, use_container_width=True)

        with tab3:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("最近數據")
                st.write(df.tail(10))
                
            with col2:
                st.subheader("簡易策略回測結果")
                df['Daily_Return'] = df['Close'].pct_change()
                df['Strategy_Return'] = df['Daily_Return'] * df['Signal'].shift(1)
                
                cumulative_market = (1 + df['Daily_Return']).cumprod() - 1
                cumulative_strategy = (1 + df['Strategy_Return']).cumprod() - 1
                
                st.metric("市場累積報酬率", f"{cumulative_market.iloc[-1]*100:.2f}%")
                st.metric("策略累積報酬率", f"{cumulative_strategy.iloc[-1]*100:.2f}%")
                
                st.line_chart(pd.DataFrame({
                    'Market': cumulative_market,
                    'Strategy': cumulative_strategy
                }))

except Exception as e:
    st.error(f"發生錯誤: {e}")

st.sidebar.markdown("---")
st.sidebar.info("這只是一個模板，投資有風險，請謹慎評估。")