import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# 1. הגדרות בסיס ותצוגה מימין לשמאל (RTL)
st.set_page_config(page_title="הדאשבורד הפיננסי שלי", layout="wide", page_icon="💰")
st.markdown("""
    <style>
        .block-container { direction: rtl; text-align: right; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        p, div, h1, h2, h3, h4, h5, h6, table { text-align: right; }
        .stMetric { direction: rtl; }
        th { text-align: right !important; }
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

# פונקציית סיווג היברידית (מילון אישי + אוטומטי)
def get_category(desc, mapping_dict):
    desc_clean = str(desc).strip()
    
    # בדיקה 1: האם קיים בקובץ התיוג האישי של המשתמש?
    if desc_clean in mapping_dict:
        return mapping_dict[desc_clean], False # False = לא סווג אוטומטית
    
    # בדיקה 2: סיווג אוטומטי למקרה שלא נמצא
    desc_lower = desc_clean.lower()
    auto_cat = "כללי / אחר"
    if any(w in desc_lower for w in ["שופרסל", "פרשמרקט", "רמי לוי", "מגה", "יינות ביתן", "ויקטורי", "אושר עד", "מחסני השוק", "חצי חינם", "וולט", "wolt", "תן ביס", "משלוחה", "מכולת", "מסעד", "קפה", "אוכל"]):
        auto_cat = "מזון ומסעדות"
    elif any(w in desc_lower for w in ["דלק", "פז", "סונול", "דור אלון", "מיקה", "פנגו", "pango", "רב קו", "רכבת", "gett", "yango", "כביש 6", "חניה", "רכב", "תחבורה"]):
        auto_cat = "תחבורה ורכב"
    elif any(w in desc_lower for w in ["הראל", "מנורה", "כללית", "מכבי", "הפניקס", "מגדל", "מאוחדת", "ביטוח", "סופר פארם", "be", "פארם"]):
        auto_cat = "בריאות וביטוח"
    elif any(w in desc_lower for w in ["פרטנר", "סלקום", "הוט", "פלאפון", "יס", "partner", "cellcom", "netflix", "spotify", "תקשורת"]):
        auto_cat = "תקשורת ופנאי"
    elif any(w in desc_lower for w in ["חשמל", "מים", "ארנונה", "גז", "תאגיד", "ועד בית"]):
        auto_cat = "חשבונות בית"
    
    return auto_cat, True # True = סווג אוטומטית!

# 3. מנוע קריאת קבצי בנק
def process_osh(file):
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
    return parsed.dropna(subset=['Date'])

def process_ash(file):
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

# 4. ממשק המשתמש - העלאת קבצים
st.sidebar.header("העלאת נתונים 📂")
st.sidebar.markdown("**חובה:**")
osh_file = st.sidebar.file_uploader("בחר קובץ תנועות עו\"ש", type=['csv', 'xlsx', 'xls'])
ash_files = st.sidebar.file_uploader("בחר קבצי כרטיס אשראי", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)

st.sidebar.markdown("**רשות (מומלץ):**")
tagging_file = st.sidebar.file_uploader("בחר קובץ תיוג הוצאות (אקסל)", type=['xlsx', 'xls', 'csv'])

if osh_file:
    with st.spinner('מעבד נתונים...'):
        
        # בניית מילון התיוגים מהקובץ האישי
        category_map = {}
        if tagging_file is not None:
            try:
                if tagging_file.name.endswith('.csv'):
                    tags_df = pd.read_csv(tagging_file)
                else:
                    tags_df = pd.read_excel(tagging_file)
                
                if "הוצאה" in tags_df.columns and "קטגוריה" in tags_df.columns:
                    tags_df = tags_df.dropna(subset=['הוצאה', 'קטגוריה'])
                    # יצירת המילון (ניקוי רווחים משמות העסקים ליתר ביטחון)
                    category_map = dict(zip(tags_df['הוצאה'].astype(str).str.strip(), tags_df['קטגוריה'].astype(str).str.strip()))
                    st.sidebar.success(f"נטענו {len(category_map)} תיוגים אישיים בהצלחה!")
                else:
                    st.sidebar.warning("קובץ התיוג חייב להכיל עמודות בשם 'הוצאה' ו-'קטגוריה'.")
            except Exception as e:
                st.sidebar.error(f"שגיאה בקריאת קובץ התיוג: {e}")

        # עיבוד בנק ואשראי
        osh_df = process_osh(osh_file)
        ash_dfs = [process_ash(f) for f in ash_files] if ash_files else []
        ash_df = pd.concat(ash_dfs, ignore_index=True) if ash_dfs else pd.DataFrame(columns=['Date', 'Desc', 'Expense'])
        
        # סינון כפילויות של אשראי בעו"ש
        cc_keywords = ["ישראכרט", "ויזה", "לאומי קארד", "מקס", "כאל", "מסטרקרד", "אמריקן אקספרס"]
        is_cc = osh_df['Desc'].str.contains('|'.join(cc_keywords), na=False)
        osh_filtered = osh_df[~is_cc]
        
        # איחוד כל ההוצאות
        all_expenses = pd.concat([
            osh_filtered[osh_filtered['Expense'] > 0][['Date', 'Desc', 'Expense']], 
            ash_df[ash_df['Expense'] > 0]
        ], ignore_index=True)
        
        # הפעלת פונקציית התיוג ההיברידית על כל הוצאה
        tagging_results = all_expenses['Desc'].apply(lambda x: get_category(x, category_map))
        all_expenses['Category'] = [res[0] for res in tagging_results]
        all_expenses['Auto_Classified'] = [res[1] for res in tagging_results]
        all_expenses['Month'] = all_expenses['Date'].dt.to_period('M').astype(str)
        
        all_incomes = osh_df[osh_df['Income'] > 0][['Date', 'Desc', 'Income']].copy()
        all_incomes['Month'] = all_incomes['Date'].dt.to_period('M').astype(str)
        
        # 5. דאשבורד לפי חודש (Monthly Focus & PIVOT)
        st.markdown("---")
        
        monthly_summary = pd.DataFrame({
            'Month': pd.concat([all_incomes['Month'], all_expenses['Month']]).unique()
        }).sort_values('Month')
        
        selected_month = st.selectbox("📅 בחר חודש לניתוח:", reversed(monthly_summary['Month'].tolist()))
        
        exp_m = all_expenses[all_expenses['Month'] == selected_month].copy()
        inc_m = all_incomes[all_incomes['Month'] == selected_month].copy()
        
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("סה\"כ הכנסות", f"{inc_m['Income'].sum():,.0f} ₪")
        m_col2.metric("סה\"כ הוצאות", f"{exp_m['Expense'].sum():,.0f} ₪")
        m_col3.metric("נטו (חיסכון)", f"{(inc_m['Income'].sum() - exp_m['Expense'].sum()):,.0f} ₪")
        
        st.markdown("### 🔍 פילוח הוצאות מפורט")
        
        row2_col1, row2_col2 = st.columns([1, 1.5])
        
        if not exp_m.empty:
            # 1. עוגת פילוחים של ההוצאות
            cat_sum_m = exp_m.groupby('Category')['Expense'].sum().reset_index()
            fig_pie_m = px.pie(cat_sum_m, values='Expense', names='Category', title='פילוח לפי קטגוריות', hole=0.3)
            fig_pie_m.update_traces(textposition='inside', textinfo='percent+label')
            row2_col1.plotly_chart(fig_pie_m, use_container_width=True)
            
            # 2. טבלת פיבוט הוצאות (הכי חשוב!)
            # הוספת התראת סיווג למי שסווג אוטומטית
            exp_m['Display_Desc'] = exp_m.apply(
                lambda row: f"{row['Desc']} ⚠️ (סיווג אוטומטי)" if row['Auto_Classified'] else row['Desc'], 
                axis=1
            )
            
            pivot_m = exp_m.groupby(['Category', 'Display_Desc'])['Expense'].sum().reset_index()
            pivot_m = pivot_m.sort_values(['Category', 'Expense'], ascending=[True, False])
            pivot_m.columns = ['קטגוריה', 'בית עסק', 'סה"כ (₪)']
            
            # עיצוב הטבלה
            row2_col2.markdown(f"**פירוט עסקאות חודשי - {selected_month}**")
            row2_col2.dataframe(
                pivot_m.style.format({'סה"כ (₪)': "{:,.2f}"}), 
                use_container_width=True, 
                height=400,
                hide_index=True
            )
            
            # הצגת הודעה במידה והיו סיווגים אוטומטיים
            if exp_m['Auto_Classified'].any():
                st.info("💡 **שים לב:** הוצאות המסומנות ב-⚠️ תויגו על ידי המערכת האוטומטית מכיוון שלא הופיעו בקובץ התיוג שלך. תוכל להוסיף אותן לקובץ האקסל שלך לפעם הבאה.")
                
        else:
            st.info("אין הוצאות לחודש זה.")

else:
    st.info("👈 כדי להתחיל, העלה את קבצי הבנק שלך בסרגל הצד (ולאחר מכן את קובץ התיוג האישי שלך).")
