import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime

# 1. הגדרות בסיס ותצוגה מימין לשמאל (RTL)
st.set_page_config(page_title="הדאשבורד הפיננסי שלי", layout="wide", page_icon="💰")
st.markdown("""
    <style>
        .block-container { direction: rtl; text-align: right; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        p, div, h1, h2, h3, h4, h5, h6, table { text-align: right; }
        .stMetric { direction: rtl; }
        th { text-align: right !important; }
        
        /* עיצוב מיוחד לשורות סיכום קבועות/משתנות */
        .summary-box-fixed { background-color: rgba(31, 119, 180, 0.1); padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 20px; border-right: 5px solid #1f77b4; }
        .summary-box-var { background-color: rgba(255, 127, 14, 0.1); padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 20px; border-right: 5px solid #ff7f0e; }
        
        /* העלמת החץ הדיפולטיבי של הדפדפן כדי לשים חץ מעוצב שלנו */
        details > summary::-webkit-details-marker { display: none; }
        details > summary { list-style: none; outline: none; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 הדאשבורד הפיננסי שלי")

# 2. פונקציות עזר 
def clean_amount(val):
    if pd.isna(val): return 0.0
    val_str = str(val).replace(',', '').strip()
    try: return float(val_str)
    except: return 0.0

def is_date(val):
    val_str = str(val).strip()
    return bool(re.search(r'\d{2,4}[-/]\d{2}[-/]\d{2,4}', val_str)) or (isinstance(val, (int, float)) and 30000 < val < 100000)

def get_category(desc, mapping_dict):
    desc_clean = str(desc).strip()
    if desc_clean in mapping_dict:
        return mapping_dict[desc_clean], False 
    
    desc_lower = " " + desc_clean.lower() + " "
    auto_cat = "כללי / אחר"
    
    if any(w in desc_lower for w in [" שופרסל", " פרשמרקט", " רמי לוי", " מגה ", " יינות ביתן", " ויקטורי", " אושר עד", " מחסני השוק", " חצי חינם", " וולט", " wolt", " תן ביס", " משלוחה", " מכולת", " מסעד", " קפה", " אוכל"]):
        auto_cat = "מזון ומסעדות"
    elif any(w in desc_lower for w in [" דלק", " פז ", " סונול", " דור אלון", " מיקה", " פנגו", " pango", " רב קו", " רכבת", " gett", " yango", " כביש 6", " חניה", " רכב", " תחבורה"]):
        auto_cat = "תחבורה ורכב"
    elif any(w in desc_lower for w in [" הראל", " מנורה", " כללית", " מכבי", " הפניקס", " מגדל", " מאוחדת", " ביטוח", " סופר פארם", " be ", " פארם"]):
        auto_cat = "בריאות וביטוח"
    elif any(w in desc_lower for w in [" פרטנר", " סלקום", " הוט ", " פלאפון", " yes ", " partner", " cellcom", " netflix", " spotify", " תקשורת"]):
        auto_cat = "תקשורת ופנאי"
    elif any(w in desc_lower for w in [" חשמל", " מים", " ארנונה", " גז", " תאגיד", " ועד בית"]):
        auto_cat = "חשבונות בית"
        
    return auto_cat, True

# 3. קריאת קבצים נקיים (קבצי בנק גולמיים)
def process_osh_raw(file):
    try: df = pd.read_csv(file, header=None, encoding='utf-8')
    except: 
        file.seek(0)
        df = pd.read_csv(file, header=None, encoding='windows-1255') if file.name.endswith('.csv') else pd.read_excel(file, header=None)
    
    start_idx = next((i for i in range(min(30, len(df))) if is_date(df.iloc[i, 0])), None)
    if start_idx is None: return pd.DataFrame()
    df = df.iloc[start_idx:].reset_index(drop=True)
    parsed = pd.DataFrame()
    parsed['Date'] = pd.to_datetime(df[0], errors='coerce', dayfirst=True)
    parsed['Desc'] = df[2].astype(str).str.strip()
    parsed['Income'] = df[3].apply(clean_amount)
    parsed['Expense'] = df[4].apply(clean_amount)
    parsed['Balance'] = df[5].apply(clean_amount) if df.shape[1] > 5 else 0.0
    return parsed.dropna(subset=['Date'])

def process_ash_raw(file):
    try: df = pd.read_csv(file, header=None, encoding='utf-8')
    except: 
        file.seek(0)
        df = pd.read_csv(file, header=None, encoding='windows-1255') if file.name.endswith('.csv') else pd.read_excel(file, header=None)
    
    start_idx = next((i for i in range(min(20, len(df))) if is_date(df.iloc[i, 0]) or is_date(df.iloc[i, 1])), None)
    if start_idx is None: return pd.DataFrame()
    df = df.iloc[start_idx:].reset_index(drop=True)
    parsed = pd.DataFrame()
    date_col = df[1].copy()
    date_col[date_col.isna()] = df[0][date_col.isna()]
    parsed['Date'] = pd.to_datetime(date_col, errors='coerce', dayfirst=True)
    parsed['Desc'] = df[2].astype(str).str.strip()
    exp_col = 4 if df.shape[1] >= 5 else df.shape[1] - 1
    parsed['Expense'] = df[exp_col].apply(clean_amount)
    return parsed.dropna(subset=['Date'])

# קריאת קבצי מאסטר קיימים
def process_master(file):
    try: 
        df = pd.read_csv(file, encoding='utf-8-sig')
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        return df.dropna(subset=['Date'])
    except:
        st.sidebar.error("שגיאה בקריאת קובץ המאסטר.")
        return pd.DataFrame()

# 4. ממשק המשתמש - סרגל צד וניהול מאגר נתונים
st.sidebar.header("🗄️ ניהול מאגר נתונים")

# קבצי מאסטר (היסטוריה)
st.sidebar.markdown("**1. טען היסטוריה קיימת (מאסטר):**")
master_osh_file = st.sidebar.file_uploader("קובץ מאסטר - עו\"ש", type=['csv'], key="master_osh")
master_ash_file = st.sidebar.file_uploader("קובץ מאסטר - אשראי", type=['csv'], key="master_ash")

st.sidebar.markdown("---")

# קבצים חדשים מהבנק
st.sidebar.markdown("**2. הוסף קבצים חדשים מהבנק:**")
new_osh_files = st.sidebar.file_uploader("קבצי עו\"ש חדשים", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)
new_ash_files = st.sidebar.file_uploader("קבצי כרטיס אשראי חדשים", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)

st.sidebar.markdown("---")

st.sidebar.markdown("**3. קובץ סיווג אישי (רשות):**")
tagging_file = st.sidebar.file_uploader("בחר קובץ תיוג הוצאות (אקסל)", type=['xlsx', 'xls', 'csv'])

# אם יש מידע כלשהו לעבוד איתו (מאסטר או חדש)
if master_osh_file or master_ash_file or new_osh_files or new_ash_files:
    with st.spinner('מעבד, מאחד ומנקה נתונים...'):
        
        # טעינת תיוגים
        category_map = {}
        if tagging_file is not None:
            try:
                if tagging_file.name.endswith('.csv'): tags_df = pd.read_csv(tagging_file)
                else: tags_df = pd.read_excel(tagging_file)
                if "הוצאה" in tags_df.columns and "קטגוריה" in tags_df.columns:
                    tags_df = tags_df.dropna(subset=['הוצאה', 'קטגוריה'])
                    category_map = dict(zip(tags_df['הוצאה'].astype(str).str.strip(), tags_df['קטגוריה'].astype(str).str.strip()))
            except Exception as e: st.sidebar.error(f"שגיאה בקריאת קובץ התיוג: {e}")

        # --- איחוד וניקוי עו"ש ---
        osh_dfs = []
        if master_osh_file: osh_dfs.append(process_master(master_osh_file))
        if new_osh_files:
            for f in new_osh_files: osh_dfs.append(process_osh_raw(f))
        
        if osh_dfs:
            osh_df = pd.concat(osh_dfs, ignore_index=True)
            osh_df = osh_df.drop_duplicates(subset=['Date', 'Desc', 'Income', 'Expense'], keep='last').sort_values('Date').reset_index(drop=True)
        else:
            osh_df = pd.DataFrame(columns=['Date', 'Desc', 'Income', 'Expense', 'Balance'])

        # --- איחוד וניקוי אשראי ---
        ash_dfs = []
        if master_ash_file: ash_dfs.append(process_master(master_ash_file))
        if new_ash_files:
            for f in new_ash_files: ash_dfs.append(process_ash_raw(f))
            
        if ash_dfs:
            ash_df = pd.concat(ash_dfs, ignore_index=True)
            ash_df = ash_df.drop_duplicates(subset=['Date', 'Desc', 'Expense'], keep='last').sort_values('Date').reset_index(drop=True)
        else:
            ash_df = pd.DataFrame(columns=['Date', 'Desc', 'Expense'])
        
        # --- יצירת כפתורי הורדה למאסטרים המעודכנים ---
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📥 הורדת מאסטר מעודכן")
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        if not osh_df.empty:
            csv_osh = osh_df.to_csv(index=False).encode('utf-8-sig')
            st.sidebar.download_button(label="הורד מאסטר עו\"ש עדכני", data=csv_osh, file_name=f"Master_Osh_{today_str}.csv", mime="text/csv")
            
        if not ash_df.empty:
            csv_ash = ash_df.to_csv(index=False).encode('utf-8-sig')
            st.sidebar.download_button(label="הורד מאסטר אשראי עדכני", data=csv_ash, file_name=f"Master_Ashray_{today_str}.csv", mime="text/csv")

        cc_keywords = ["ישראכרט", "ויזה", "לאומי קארד", "מקס", "כאל", "מסטרקרד", "אמריקן אקספרס"]
        is_cc = osh_df['Desc'].str.contains('|'.join(cc_keywords), na=False) if not osh_df.empty else pd.Series(dtype=bool)
        osh_filtered = osh_df[~is_cc] if not osh_df.empty else pd.DataFrame()
        
        all_expenses = pd.concat([
            osh_filtered[osh_filtered['Expense'] > 0][['Date', 'Desc', 'Expense']] if not osh_filtered.empty else pd.DataFrame(), 
            ash_df[ash_df['Expense'] > 0] if not ash_df.empty else pd.DataFrame()
        ], ignore_index=True)
        
        if not all_expenses.empty:
            tagging_results = all_expenses['Desc'].apply(lambda x: get_category(x, category_map))
            all_expenses['Category'] = [res[0] for res in tagging_results]
            all_expenses['Auto_Classified'] = [res[1] for res in tagging_results]
            all_expenses['Month'] = all_expenses['Date'].dt.to_period('M').astype(str)
            
            fixed_cats = ["בריאות וביטוח", "תקשורת ופנאי", "חשבונות בית"]
            all_expenses['Type'] = all_expenses['Category'].apply(lambda c: 'קבועות' if c in fixed_cats else 'משתנות')
        
        all_incomes = osh_df[osh_df['Income'] > 0][['Date', 'Desc', 'Income']].copy() if not osh_df.empty else pd.DataFrame()
        if not all_incomes.empty:
            all_incomes['Month'] = all_incomes['Date'].dt.to_period('M').astype(str)

        # --- תמונת מצב כללית ---
        st.markdown("---")
        st.header("🌍 מבט על: מגמות היסטוריות")
        
        if not all_expenses.empty or not all_incomes.empty:
            months_inc = all_incomes['Month'] if not all_incomes.empty else pd.Series()
            months_exp = all_expenses['Month'] if not all_expenses.empty else pd.Series()
            all_months = pd.concat([months_inc, months_exp]).unique()
            
            monthly_summary = pd.DataFrame({'Month': all_months}).sort_values('Month')
            monthly_summary['Income'] = monthly_summary['Month'].map(all_incomes.groupby('Month')['Income'].sum() if not all_incomes.empty else {}).fillna(0)
            monthly_summary['Expense'] = monthly_summary['Month'].map(all_expenses.groupby('Month')['Expense'].sum() if not all_expenses.empty else {}).fillna(0)
            
            col1, col2 = st.columns(2)
            fig_cf = go.Figure()
            fig_cf.add_trace(go.Bar(x=monthly_summary['Month'], y=monthly_summary['Income'], name='הכנסות', marker_color='green'))
            fig_cf.add_trace(go.Bar(x=monthly_summary['Month'], y=monthly_summary['Expense'], name='הוצאות', marker_color='red'))
            fig_cf.update_layout(barmode='group', title="תזרים מזומנים חודשי (הכנסות מול הוצאות)", hovermode="x unified")
            col1.plotly_chart(fig_cf, use_container_width=True)
            
            osh_bal = osh_df[osh_df['Balance'] != 0].sort_values('Date') if not osh_df.empty else pd.DataFrame()
            if not osh_bal.empty:
                fig_bal = px.line(osh_bal, x='Date', y='Balance', title='מגמת יתרת העו"ש לאורך זמן', markers=True)
                fig_bal.update_traces(line_color='blue')
                col2.plotly_chart(fig_bal, use_container_width=True)
            elif not all_expenses.empty:
                cat_sum = all_expenses.groupby('Category')['Expense'].sum().reset_index()
                fig_pie_all = px.pie(cat_sum, values='Expense', names='Category', title='התפלגות הוצאות (כל התקופה)')
                col2.plotly_chart(fig_pie_all, use_container_width=True)

            # --- חיתוך חודשי ממוקד ---
            st.markdown("---")
            st.header("🔎 צלילה לעומק: ניתוח חודשי ממוקד")
            
            selected_month = st.selectbox("📅 בחר חודש לניתוח:", reversed(monthly_summary['Month'].tolist()))
            
            exp_m = all_expenses[all_expenses['Month'] == selected_month].copy() if not all_expenses.empty else pd.DataFrame()
            inc_m = all_incomes[all_incomes['Month'] == selected_month].copy() if not all_incomes.empty else pd.DataFrame()
            
            m_col1, m_col2, m_col3 = st.columns(3)
            inc_total = inc_m['Income'].sum() if not inc_m.empty else 0
            exp_total = exp_m['Expense'].sum() if not exp_m.empty else 0
            m_col1.metric("סה\"כ הכנסות", f"{inc_total:,.0f} ₪")
            m_col2.metric("סה\"כ הוצאות", f"{exp_total:,.0f} ₪")
            m_col3.metric("נטו (חיסכון)", f"{(inc_total - exp_total):,.0f} ₪")
            
            # --- ניתוח הכנסות ---
            st.markdown("#### 💵 ניתוח הכנסות")
            inc_col1, inc_col2 = st.columns([1, 1.5])
            if not inc_m.empty:
                inc_sum_m = inc_m.groupby('Desc')['Income'].sum().reset_index()
                fig_inc_pie = px.pie(inc_sum_m, values='Income', names='Desc', title='מקורות הכנסה', hole=0.3)
                fig_inc_pie.update_traces(textposition='inside', textinfo='percent+label')
                inc_col1.plotly_chart(fig_inc_pie, use_container_width=True)
                
                inc_pivot = inc_sum_m.sort_values('Income', ascending=False)
                inc_pivot.columns = ['מקור הכנסה', 'סה"כ (₪)']
                inc_col2.markdown(f"**פירוט הכנסות - {selected_month}**")
                inc_col2.dataframe(inc_pivot.style.format({'סה"כ (₪)': "{:,.2f}"}), use_container_width=True, hide_index=True)
            else:
                st.info("אין הכנסות לחודש זה.")

            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- ניתוח הוצאות ---
            st.markdown("#### 💳 פירוט הוצאות חכם (לחץ על שורה לפירוט מלא)")
            exp_col1, exp_col2 = st.columns([1, 1.5])
            
            if not exp_m.empty:
                cat_sum_m = exp_m.groupby('Category')['Expense'].sum().reset_index()
                fig_exp_pie = px.pie(cat_sum_m, values='Expense', names='Category', title='פילוח הוצאות לפי קטגוריות', hole=0.3)
                fig_exp_pie.update_traces(textposition='inside', textinfo='percent+label')
                exp_col1.plotly_chart(fig_exp_pie, use_container_width=True)
                
                with exp_col2:
                    exp_m['Display_Desc'] = exp_m.apply(lambda row: f"{row['Desc']} ⚠️" if row['Auto_Classified'] else row['Desc'], axis=1)
                    pivot_m = exp_m.groupby(['Category', 'Display_Desc'])['Expense'].sum().reset_index()
                    pivot_m = pivot_m.sort_values(['Category', 'Expense'], ascending=[True, False])
                    
                    html_table = "<div style='border: 1px solid #ddd; border-radius: 5px; background-color: white;'>"
                    html_table += "<div style='display: grid; grid-template-columns: 30px 2fr 3fr 1.5fr; padding: 12px; font-weight: bold; background-color: #f0f2f6; border-bottom: 2px solid #ddd; border-radius: 5px 5px 0 0;'>"
                    html_table += "<div></div><div>קטגוריה</div><div>בית עסק</div><div style='text-align: left;'>סה\"כ (₪)</div></div>"
                    
                    for cat, cat_group in pivot_m.groupby('Category', sort=False):
                        for _, row in cat_group.iterrows():
                            biz = row['Display_Desc']
                            amt = row['Expense']
                            raw_tx = exp_m[(exp_m['Category'] == cat) & (exp_m['Display_Desc'] == biz)].copy()
                            
                            inner_html = "<table style='width: 100%; border-collapse: collapse; font-size: 0.9em; margin-bottom: 5px;'>"
                            inner_html += "<tr><th style='text-align: right; border-bottom: 1px solid #ddd; padding: 6px; color: #555;'>תאריך</th><th style='text-align: right; border-bottom: 1px solid #ddd; padding: 6px; color: #555;'>תיאור מקורי</th><th style='text-align: left; border-bottom: 1px solid #ddd; padding: 6px; color: #555;'>סכום</th></tr>"
                            for _, tx in raw_tx.iterrows():
                                dt_str = tx['Date'].strftime('%d/%m/%Y')
                                inner_html += f"<tr><td style='border-bottom: 1px solid #eee; padding: 6px;'>{dt_str}</td><td style='border-bottom: 1px solid #eee; padding: 6px;'>{tx['Desc']}</td><td style='text-align: left; border-bottom: 1px solid #eee; padding: 6px; direction: ltr;'>₪ {tx['Expense']:,.2f}</td></tr>"
                            inner_html += "</table>"
                            
                            html_table += "<details style='border-bottom: 1px solid #eee;'>"
                            html_table += "<summary style='display: grid; grid-template-columns: 30px 2fr 3fr 1.5fr; padding: 12px; cursor: pointer; transition: background-color 0.2s; list-style: none;'>"
                            html_table += "<div style='color: #1f77b4; font-size: 0.8em; align-self: center;'>▼</div>"
                            html_table += f"<div>{cat}</div><div style='font-weight: bold;'>{biz}</div>"
                            html_table += f"<div style='text-align: left; font-weight: bold; direction: ltr;'>₪ {amt:,.2f}</div>"
                            html_table += "</summary>"
                            html_table += f"<div style='padding: 10px 40px 10px 20px; background-color: #fafafa; border-top: 1px dashed #eee;'>{inner_html}</div>"
                            html_table += "</details>"
                            
                    html_table += "</div>"
                    st.markdown(html_table, unsafe_allow_html=True)
                    
                    if exp_m['Auto_Classified'].any():
                        st.caption("הוצאות עם ⚠️ תויגו ע\"י המערכת (לא הופיעו בקובץ התיוג שלך).")

                # --- טופ 10 ---
                st.markdown("<br>", unsafe_allow_html=True)
                top_10 = exp_m.groupby('Desc')['Expense'].sum().reset_index().sort_values('Expense', ascending=False).head(10)
                fig_top10 = px.bar(top_10, x='Desc', y='Expense', title='10 בתי העסק היקרים ביותר בחודש זה', text_auto='.0f')
                fig_top10.update_traces(marker_color='indianred', textposition='outside')
                fig_top10.update_layout(xaxis_title="", yaxis_title="סכום (₪)")
                st.plotly_chart(fig_top10, use_container_width=True)
                
                # --- הוצאות קבועות מול משתנות (בלוקים) ---
                st.markdown("<br><hr>", unsafe_allow_html=True)
                st.markdown("#### 🔒 ניהול תקציב: קבועות מול משתנות")
                col_f, col_v = st.columns(2)
                
                with col_f:
                    st.markdown("##### הוצאות קבועות (קשיחות)")
                    fixed_df = exp_m[exp_m['Type'] == 'קבועות'].copy()
                    if not fixed_df.empty:
                        f_display = fixed_df[['Date', 'Desc', 'Category', 'Expense']].sort_values('Expense', ascending=False).copy()
                        f_display['Date'] = f_display['Date'].dt.strftime('%d/%m/%Y')
                        f_display.columns = ['תאריך', 'בית עסק', 'קטגוריה', 'סכום (₪)']
                        st.dataframe(f_display.style.format({'סכום (₪)': "{:,.2f}"}), hide_index=True, use_container_width=True, height=250)
                        st.markdown(f"<div class='summary-box-fixed'>סה\"כ קבועות לחודש זה: {fixed_df['Expense'].sum():,.2f} ₪</div>", unsafe_allow_html=True)
                        
                with col_v:
                    st.markdown("##### הוצאות משתנות (בשליטתך)")
                    var_df = exp_m[exp_m['Type'] == 'משתנות'].copy()
                    if not var_df.empty:
                        v_display = var_df[['Date', 'Desc', 'Category', 'Expense']].sort_values('Expense', ascending=False).copy()
                        v_display['Date'] = v_display['Date'].dt.strftime('%d/%m/%Y')
                        v_display.columns = ['תאריך', 'בית עסק', 'קטגוריה', 'סכום (₪)']
                        st.dataframe(v_display.style.format({'סכום (₪)': "{:,.2f}"}), hide_index=True, use_container_width=True, height=250)
                        st.markdown(f"<div class='summary-box-var'>סה\"כ משתנות לחודש זה: {var_df['Expense'].sum():,.2f} ₪</div>", unsafe_allow_html=True)
            else:
                st.info("אין הוצאות לחודש זה.")
        else:
            st.info("קובץ הנתונים ריק או שלא זוהו תנועות.")

else:
    st.info("👈 כדי להתחיל, העלה קובץ מאסטר היסטורי או קבצי בנק חדשים בסרגל הצד.")
