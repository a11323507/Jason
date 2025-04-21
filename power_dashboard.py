import numpy
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- 必須最先設定頁面參數 ---
# st.set_page_config(layout="wide")

# --- 使用者登入驗證 ---
# def login():
#     st.title("🔐 請先登入")
#     username = st.text_input("使用者名稱")
#     password = st.text_input("密碼", type="password")
#     if st.button("登入"):
#         if username == "family" and password == "123456":
#             st.session_state['authenticated'] = True
#         else:
#             st.error("帳號或密碼錯誤")
#
# if 'authenticated' not in st.session_state:
#     login()
#     st.stop()

# --- Streamlit Web App ---
st.image("logo.PNG", width=800)
st.markdown("## 📊 用電趨勢異常分析系統")
# st.title("📊 用電趨勢異常分析系統")

# --- 檔案上傳區 ---
uploaded_file = st.file_uploader("請上傳用電資料 Excel 檔案", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    selected_sheet = st.selectbox("請選擇要分析的工作表 (Sheet)", sheet_names)
    df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=None)

    results = []

    # 修改為每一欄都做配對（比對所有相鄰欄）
    for i in range(df.shape[1] - 1):
        col_time = df.iloc[:, i]
        col_value = df.iloc[:, i + 1]

        for row_idx in range(len(col_time)):
            t = col_time.iloc[row_idx]
            v = col_value.iloc[row_idx]
            timestamp = None
            try:
                timestamp = pd.to_datetime(t, errors='coerce')
                if timestamp and timestamp.year < 2000:
                    continue
            except:
                timestamp = None

            if timestamp and isinstance(v, (float, int, np.integer)):
                results.append({'時間': timestamp, '累積用電量': v})

    data = pd.DataFrame(results)
    if '時間' not in data.columns:
        st.error("❌ 無法找到任何有效時間資料，請檢查上傳的 Excel 結構是否正確")
        st.stop()
    data = data.dropna(subset=['時間'])
    st.info(f"📅 資料時間範圍：{data['時間'].min()} ~ {data['時間'].max()}")
    data = data.sort_values('時間').reset_index(drop=True)
    data['日期'] = data['時間'].dt.date

    # 修正用電量：保留首筆，從第二筆開始做 diff（首筆為 NaN）
    def mark_diff(group):
        group = group.sort_values('時間').reset_index(drop=True)
        group['用電量'] = group['累積用電量'].diff()
        return group

    data = data.groupby('日期', group_keys=False).apply(mark_diff)
    data_for_calc = data.dropna(subset=['用電量'])
    data_for_calc = data_for_calc[data_for_calc['用電量'] >= 0]  # 避免異常負值

    # 日期選擇器
    available_dates = sorted(data['日期'].unique())
    selected_date = st.selectbox("請選擇查詢日期：", available_dates)

    # 異常偵測（只對已計算用電量的資料進行）
    matched = data_for_calc[data_for_calc['日期'] == selected_date].copy()
    median = matched['用電量'].median()
    mad = (matched['用電量'] - median).abs().mean()
    min_val = numpy.min(matched['用電量'])
    max_val = numpy.max(matched['用電量'])
    avg_val = numpy.mean(matched['用電量'])
    mad_threshold = st.slider("MAD 閾值倍數", 1.0, 5.0, 3.0, 0.5)

    matched['狀態'] = '正常'
    matched.loc[(matched['用電量'] - median).abs() > mad_threshold * mad, '狀態'] = '異常'

    # 顯示統計資訊
    st.subheader(f"📆 {selected_date} 統計資料")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("總用電量 (KWH)", f"{matched['用電量'].sum():,.2f}")
    col2.metric("最小用電量", f"{min_val:,.2f}")
    col3.metric("最大用電量", f"{max_val:,.2f}")
    col4.metric("平均用電量", f"{avg_val:,.2f}")
    # col2.metric("中位數", f"{median:,.2f}")
    # col3.metric("MAD", f"{mad:,.2f}")
    col5.metric("異常點數量", f"{(matched['狀態'] == '異常').sum()}")

    # 顯示異常時間範圍
    st.subheader("⏱️ 異常時間區段")
    outliers = matched[matched['狀態'] == '異常']
    if not outliers.empty:
        time_ranges = outliers['時間'].sort_values().reset_index(drop=True)
        for i, t in enumerate(time_ranges):
            st.write(f"{i+1}. {t.strftime('%Y-%m-%d %H:%M:%S')} (用電量: {outliers.iloc[i]['用電量']:.2f})")
    else:
        st.info("此日未偵測到異常用電時段。")

    # 合併狀態資訊到原始 daily data
    full_day_data = data[data['日期'] == selected_date].copy()
    full_day_data = full_day_data.merge(matched[['時間', '狀態']], on='時間', how='left')
    full_day_data['狀態'] = full_day_data['狀態'].fillna('無紀錄')

    # 互動圖表（使用原始資料以顯示首筆時間）
    fig = px.scatter(
        full_day_data,
        x='時間',
        y='用電量',
        color='狀態',
        color_discrete_map={'正常': 'blue', '異常': 'red', '無紀錄': 'gray'},
        hover_data={"時間": True, "用電量": True},
        title=f"{selected_date} 用電趨勢（滑鼠可查看詳細資料）"
    )

    fig.update_layout(
        xaxis_title="",
        yaxis_title="用電量 (KWH)",
        hovermode='closest',
        showlegend=True,
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("請先上傳一個 Excel 檔案 (.xlsx)，格式為多欄的時間與累積用電量資料。")
