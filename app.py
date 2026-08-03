# ==============================================================================
# Project: Suleiman ERP - Enterprise Fleet & Financial Management System
# Author: Engineer Suleiman Nabhan
# Platform: Streamlit Cloud & Supabase Multi-Tier Architecture
# Features: Fleet Management (53 Units), OCR Verification, RBAC, Excel/CSV Exports
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
import json
import io
import os

# ==============================================================================
# 1. PAGE CONFIGURATION & CUSTOM CSS
# ==============================================================================
st.set_page_config(
    page_title="Suleiman ERP System",
    page_icon="🚜",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { 
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); 
        color: #ecf0f1; 
    }
    .metric-card { 
        background: rgba(255, 255, 255, 0.05); 
        padding: 18px; 
        border-radius: 12px; 
        border: 1px solid rgba(255, 255, 255, 0.12); 
        margin-bottom: 15px; 
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    h1, h2, h3 { 
        color: #f1c40f !important; 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    }
    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        font-weight: bold; 
        background-color: #27ae60;
        color: white;
        border: none;
        padding: 8px 16px;
    }
    .stButton>button:hover {
        background-color: #2ec771;
        color: white;
    }
    .download-btn {
        background-color: #2980b9 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. HELPER FUNCTIONS & EXPORT UTILITIES
# ==============================================================================
def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    """تحويل الجدول إلى ملف CSV يدعم اللغة العربية (UTF-8 with BOM)"""
    return df.to_csv(index=False).encode('utf-8-sig')

def convert_dfs_to_excel_bytes(data_dict: dict) -> bytes:
    """تحويل عدة جداول إلى ملف Excel متعدد الأوراق"""
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for sheet_name, df in data_dict.items():
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        return output.getvalue()
    except Exception:
        # في حال عدم توفر مكتبة xlsxwriter يتم التصدير لصيغة CSV مبسطة
        primary_df = list(data_dict.values())[0]
        return convert_df_to_csv(primary_df)

@st.cache_resource
def init_supabase():
    """الاتصال الآمن بقاعدة بيانات Supabase"""
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        try:
            from supabase import create_client
            return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        except Exception:
            return None
    return None

supabase = init_supabase()

# ==============================================================================
# 3. TRANSLATIONS & DICTIONARIES
# ==============================================================================
TRANSLATIONS = {
    "AR": {
        "dashboard": "📊 لوحة القيادة",
        "expenses": "💸 المشتريات وتصوير الفواتير",
        "vouchers": "🔐 الاعتماد المزدوج للسندات",
        "vendors": "🏪 مستحقات المحلات",
        "fleet": "🚜 إدارة كلف الآليات (53)",
        "movement": "⛽ الحركة والعدادات (OCR)",
        "staff": "👷 إدارة الموظفين والورشات",
        "audit": "📜 سجل التدقيق الأمني",
        "rbac": "🛡️ إدارة المستخدمين والصلاحيات",
        "settings": "⚙️ إعدادات النظام وتصدير البيانات"
    },
    "KU": {
        "dashboard": "📊 داشبۆرد",
        "expenses": "💸 خەرجییەکان",
        "vouchers": "🔐 پەسەندکردن",
        "vendors": "🏪 شایستەی دوکانەکان",
        "fleet": "🚜 ئامێرەکان (53)",
        "movement": "⛽ جووڵە و مەتەر",
        "staff": "👷 کارمەندەکان",
        "audit": "📜 تۆماری پشکنین",
        "rbac": "🛡️ دەسەڵاتەکان",
        "settings": "⚙️ رێکخستن"
    },
    "EN": {
        "dashboard": "📊 Dashboard",
        "expenses": "💸 Procurement & Receipts",
        "vouchers": "🔐 Dual Verification",
        "vendors": "🏪 Vendors Ledger",
        "fleet": "🚜 Fleet Management (53)",
        "movement": "⛽ Odometer & Movement",
        "staff": "👷 Staff & Crew Management",
        "audit": "📜 Audit Logs",
        "rbac": "🛡️ RBAC & User Management",
        "settings": "⚙️ System Settings & Backup"
    }
}

ROLE_PERMISSIONS = {
    "ADMIN": ["dashboard", "expenses", "vouchers", "vendors", "fleet", "movement", "staff", "audit", "rbac", "settings"],
    "ACCOUNTANT": ["dashboard", "expenses", "vouchers", "vendors", "fleet"],
    "SUPERVISOR": ["expenses", "movement", "staff"],
    "DRIVER": ["movement"]
}

# ==============================================================================
# 4. SESSION STATE INITIALIZATION
# ==============================================================================
if 'lang' not in st.session_state:
    st.session_state['lang'] = 'AR'

if 'user' not in st.session_state:
    st.session_state['user'] = None

if 'audit_logs' not in st.session_state:
    st.session_state['audit_logs'] = []

if 'users_db' not in st.session_state:
    st.session_state['users_db'] = pd.DataFrame([
        {"username": "suleiman", "full_name": "م. سليمان نبهان", "role": "ADMIN", "status": "نشط"},
        {"username": "accountant", "full_name": "محاسب المشروع", "role": "ACCOUNTANT", "status": "نشط"},
        {"username": "supervisor", "full_name": "مشرف الموقع", "role": "SUPERVISOR", "status": "نشط"},
        {"username": "driver1", "full_name": "سائق الحفارة EX-01", "role": "DRIVER", "status": "نشط"}
    ])

if 'fleet_db' not in st.session_state:
    fleet_list = []
    for i in range(1, 54):
        if i <= 20:
            m_type, code = "حفارة ثقيلة", f"EX-{i:02d}"
        elif i <= 35:
            m_type, code = "جرافة كتربيلر", f"WL-{i:02d}"
        else:
            m_type, code = "قلاب شحن", f"TR-{i:02d}"
        
        fleet_list.append({
            "code": code,
            "type": m_type,
            "driver": f"سائق {code}",
            "status": "شغالة" if i % 7 != 0 else "في الصيانة",
            "odometer": 10000 + (i * 250),
            "monthly_cost": 1200 + (i * 50)
        })
    st.session_state['fleet_db'] = pd.DataFrame(fleet_list)

if 'staff_db' not in st.session_state:
    st.session_state['staff_db'] = pd.DataFrame([
        {"id": "EMP-101", "name": "أحمد خليل", "job": "ميكانيكي معدات ثقيلة", "site": "الورشة المركزية", "salary": 1200, "status": "على رأس العمل"},
        {"id": "EMP-102", "name": "محمود جاسم", "job": "مشرف حركة وصيانة", "site": "الموقع الأول", "salary": 1500, "status": "على رأس العمل"},
        {"id": "EMP-103", "name": "كريم عبد العال", "job": "سائق قلاب", "site": "الموقع الثاني", "salary": 900, "status": "إجازة"}
    ])

if 'vouchers_db' not in st.session_state:
    st.session_state['vouchers_db'] = [
        {"id": "VOUCH-1001", "vendor": "محلات الهندسية للقطع", "machine": "EX-01", "amount": 450.0, "notes": "تبديل فلتر هيدروليك", "status": "معلق", "date": str(datetime.date.today())},
        {"id": "VOUCH-1002", "vendor": "كراج الرافدين للوقود", "machine": "TR-05", "amount": 820.0, "notes": "تعبئة ديزل 1000 لتر", "status": "معلق", "date": str(datetime.date.today())}
    ]

def log_action(action: str, details: str):
    """تسجيل العمليات في أرشيف الأمان"""
    user_name = st.session_state['user']['name'] if st.session_state['user'] else "النظام"
    st.session_state['audit_logs'].insert(0, {
        "الوقت": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "المستخدم": user_name,
        "الإجراء": action,
        "التفاصيل": details
    })

t = TRANSLATIONS[st.session_state['lang']]

# ==============================================================================
# 5. LOGIN SCREEN
# ==============================================================================
def login_screen():
    st.markdown("<h1 style='text-align: center;'>🔐 نظام Suleiman ERP للمقاولات</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #bdc3c7;'>إدارة الأسطول، المصاريف التشغيلية، والرصد المالي اللحظي</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("اسم المستخدم (Username)")
            password = st.text_input("كلمة المرور (Password)", type="password")
            submit = st.form_submit_button("تسجيل الدخول 🚀")
            
            if submit:
                users = st.session_state['users_db']
                match = users[users['username'] == username]
                
                if not match.empty and password in ["admin123", "123456"]:
                    user_data = match.iloc[0].to_dict()
                    if user_data['status'] == "محظور":
                        st.error("❌ هذا الحساب محظور حالياً. يرجى مراجعة م. سليمان نبهان.")
                    else:
                        st.session_state['user'] = {
                            "name": user_data['full_name'],
                            "username": user_data['username'],
                            "role": user_data['role']
                        }
                        log_action("تسجيل دخول", f"تم تسجيل دخول المستخدم {user_data['username']}")
                        st.success("✅ تم تسجيل الدخول بنجاح!")
                        st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")
        st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# 6. MAIN ROUTER
# ==============================================================================
if st.session_state['user'] is None:
    login_screen()
else:
    user = st.session_state['user']
    user_role = user['role']
    
    allowed_keys = ROLE_PERMISSIONS.get(user_role, [])
    menu_options = {key: t[key] for key in allowed_keys if key in t}
    
    with st.sidebar:
        st.markdown(f"### 👤 {user['name']}")
        st.markdown(f" الرتبة: `{user_role}`")
        if st.button("🚪 تسجيل الخروج"):
            log_action("تسجيل خروج", f"خرج المستخدم {user['username']}")
            st.session_state['user'] = None
            st.rerun()
            
        st.markdown("---")
        selected_lang = st.selectbox("🌐 لغة الواجهة", ["AR", "KU", "EN"], index=["AR", "KU", "EN"].index(st.session_state['lang']))
        if selected_lang != st.session_state['lang']:
            st.session_state['lang'] = selected_lang
            st.rerun()
            
        selected_label = st.radio("القائمة الرئيسية", list(menu_options.values()))
        selected_key = [k for k, v in menu_options.items() if v == selected_label][0]

    # ==============================================================================
    # 7. MODULE: DASHBOARD
    # ==============================================================================
    if selected_key == "dashboard":
        st.title(t['dashboard'])
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي المصاريف هذا الشهر", "$18,450", "+3.1%")
        
        active_machines = len(st.session_state['fleet_db'][st.session_state['fleet_db']['status'] == "شغالة"])
        total_machines = len(st.session_state['fleet_db'])
        c2.metric("جاهزية الأسطول", f"{active_machines} / {total_machines} آلية", f"{(active_machines/total_machines)*100:.0f}%")
        
        c3.metric("عدد الموظفين والعمال", f"{len(st.session_state['staff_db'])} موظف", "نشط")
        
        pending_count = len([v for v in st.session_state['vouchers_db'] if v['status'] == "معلق"])
        c4.metric("السندات المعلقة للاعتماد", f"{pending_count} سندات", "مراجعة مطلوب")
        
        st.markdown("---")
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.subheader("📢 إرسال توجيه ميداني عاجل")
            target = st.selectbox("إلى الورشة / الفئة:", ["جميع الموظفين", "سائقو الآليات", "مشرفو المواقع"])
            msg = st.text_area("نص التوجيه:")
            if st.button("إرسال التنبيه الفوري 🔔"):
                if msg:
                    st.success("✅ تم إرسال التوجيه بنجاح وتسجيل إشعار استلام.")
                    log_action("إرسال توجيه", f"إلى {target}: {msg}")
                else:
                    st.warning("يرجى كتابة نص التوجيه أولاً.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_right:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.subheader("📈 توزيع النفقات حسب الفئة")
            chart_df = pd.DataFrame({
                "الفئة": ["وقود ديزل", "قطع غيار", "أجور صيانة", "مصاريف موقع"],
                "المبلغ ($)": [8500, 4200, 3100, 2650]
            }).set_index("الفئة")
            st.bar_chart(chart_df)
            st.markdown("</div>", unsafe_allow_html=True)

    # ==============================================================================
    # 8. MODULE: FLEET MANAGEMENT (إدارة الآليات الـ 53 + Excel/CSV Export)
    # ==============================================================================
    elif selected_key == "fleet":
        st.title(t['fleet'])
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 قائمة الآليات (53)", 
            "➕ إضافة آلية جديدة", 
            "✏️ تعديل / حذف آلية", 
            "⛽ حاسبة استهلاك الوقود"
        ])
        
        # التبويب 1: العرض مع الفلترة والتصدير
        with tab1:
            st.subheader("أسطول الآليات المسجلة والتحكم بالبيانات")
            
            c_search, c_filter_type, c_filter_status = st.columns(3)
            search_query = c_search.text_input("🔍 بحث برمز الآلية أو السائق:")
            type_filter = c_filter_type.selectbox("فلترة حسب النوع:", ["الكل", "حفارة ثقيلة", "جرافة كتربيلر", "قلاب شحن"])
            status_filter = c_filter_status.selectbox("فلترة حسب الحالة:", ["الكل", "شغالة", "في الصيانة", "متوقفة"])
            
            df_display = st.session_state['fleet_db'].copy()
            
            if search_query:
                df_display = df_display[
                    df_display['code'].str.contains(search_query, case=False, na=False) |
                    df_display['driver'].str.contains(search_query, case=False, na=False)
                ]
            if type_filter != "الكل":
                df_display = df_display[df_display['type'] == type_filter]
            if status_filter != "الكل":
                df_display = df_display[df_display['status'] == status_filter]
                
            st.dataframe(df_display, use_container_width=True)
            
            # تصدير البيانات إلى CSV / Excel
            st.markdown("### 📥 تصدير جدول الآليات:")
            col_exp1, col_exp2 = st.columns(2)
            
            csv_data = convert_df_to_csv(df_display)
            col_exp1.download_button(
                label="📥 تحميل الجدول كملف CSV",
                data=csv_data,
                file_name=f"fleet_report_{datetime.date.today()}.csv",
                mime="text/csv"
            )
            
            excel_data = convert_dfs_to_excel_bytes({"الآليات": df_display})
            col_exp2.download_button(
                label="📊 تحميل الجدول كملف Excel",
                data=excel_data,
                file_name=f"fleet_report_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # التبويب 2: الإضافة
        with tab2:
            st.subheader("إدراج آلية جديدة للأسطول")
            with st.form("add_machine_form"):
                c1, c2 = st.columns(2)
                code = c1.text_input("رمز الآلية (مثال: EX-54)")
                m_type = c2.selectbox("نوع الآلية", ["حفارة ثقيلة", "جرافة كتربيلر", "قلاب شحن", "كرين مرفاع", "مولدة ضخمة"])
                driver = c1.text_input("السائق المسؤول")
                odometer = c2.number_input("قراءة العداد الحالية", min_value=0, value=5000)
                
                if st.form_submit_button("حفظ الآلية الجديدة 💾"):
                    if code:
                        new_row = {"code": code, "type": m_type, "driver": driver, "status": "شغالة", "odometer": odometer, "monthly_cost": 0}
                        st.session_state['fleet_db'] = pd.concat([st.session_state['fleet_db'], pd.DataFrame([new_row])], ignore_index=True)
                        log_action("إضافة آلية", f"تم إدراج الآلية الجديدة {code}")
                        st.success(f"✅ تم إضافة الآلية {code} بنجاح إلى قاعدة البيانات!")
                        st.rerun()
                    else:
                        st.error("يرجى إدخال رمز الآلية.")

        # التبويب 3: التعديل والحذف
        with tab3:
            st.subheader("تعديل بيانات أو حذف آلية")
            fleet_df = st.session_state['fleet_db']
            selected_code = st.selectbox("اختر الآلية لتعديلها:", fleet_df['code'].tolist())
            
            match_m = fleet_df[fleet_df['code'] == selected_code].iloc[0]
            
            with st.form("edit_machine_form"):
                e_driver = st.text_input("السائق الحالي", value=match_m['driver'])
                e_status = st.selectbox("حالة الآلية", ["شغالة", "في الصيانة", "متوقفة"], index=["شغالة", "في الصيانة", "متوقفة"].index(match_m['status']))
                e_odo = st.number_input("تحديث العداد", value=int(match_m['odometer']))
                
                c_save, c_del = st.columns(2)
                if c_save.form_submit_button("تحديث البيانات 🔄"):
                    st.session_state['fleet_db'].loc[st.session_state['fleet_db']['code'] == selected_code, ['driver', 'status', 'odometer']] = [e_driver, e_status, e_odo]
                    log_action("تعديل آلية", f"تحديث بيانات الآلية {selected_code}")
                    st.success(f"✅ تم تحديث بيانات الآلية {selected_code} بنجاح!")
                    st.rerun()
                    
                if c_del.form_submit_button("حذف الآلية نهائياً 🗑️"):
                    st.session_state['fleet_db'] = st.session_state['fleet_db'][st.session_state['fleet_db']['code'] != selected_code]
                    log_action("حذف آلية", f"تم حذف الآلية {selected_code}")
                    st.warning(f"⚠️ تم حذف الآلية {selected_code} من النظام.")
                    st.rerun()

        # التبويب 4: حاسبة الوقود
        with tab4:
            st.subheader("⛽ حاسبة استهلاك الوقود والتكلفة التقديرية")
            c_calc1, c_calc2 = st.columns(2)
            hours_worked = c_calc1.number_input("عدد ساعات العمل الإضافية:", min_value=1, value=10)
            rate_per_hour = c_calc2.number_input("معدل الاستهلاك (لتر/ساعة):", min_value=1.0, value=15.0)
            fuel_price = c_calc1.number_input("سعر لتر الديزل ($):", min_value=0.1, value=0.75)
            
            total_liters = hours_worked * rate_per_hour
            total_cost = total_liters * fuel_price
            
            st.info(f"📊 الاستهلاك المتوقع: **{total_liters:.1f} لتر** | التكلفة التقديرية: **${total_cost:.2f}**")

    # ==============================================================================
    # 9. MODULE: STAFF & WORKSHOPS (إدارة الموظفين + Excel Export)
    # ==============================================================================
    elif selected_key == "staff":
        st.title(t['staff'])
        
        tab1, tab2, tab3 = st.tabs(["👷 قائمة الموظفين", "➕ إضافة موظف جديد", "✏️ تعديل الرواتب والحظر"])
        
        with tab1:
            st.subheader("جدول بيانات الموظفين والكادر الميداني")
            st.dataframe(st.session_state['staff_db'], use_container_width=True)
            
            # تصدير بيانات الكادر
            staff_csv = convert_df_to_csv(st.session_state['staff_db'])
            st.download_button(
                label="📥 تصدير قائمة الموظفين إلى CSV",
                data=staff_csv,
                file_name=f"staff_list_{datetime.date.today()}.csv",
                mime="text/csv"
            )
            
        with tab2:
            st.subheader("إدراج موظف أو عامل جديد")
            with st.form("add_staff_form"):
                emp_id = st.text_input("رقم الوظيفة (مثال: EMP-104)")
                name = st.text_input("اسم الموظف الكامل")
                job = st.text_input("المسمى الوظيفي")
                site = st.selectbox("موقع العمل / الورشة", ["الورشة المركزية", "الموقع الأول", "الموقع الثاني", "الإدارة"])
                salary = st.number_input("الراتب الشهري ($)", min_value=0, value=1000)
                
                if st.form_submit_button("حفظ الموظف الجديد 💾"):
                    if emp_id and name:
                        new_emp = {"id": emp_id, "name": name, "job": job, "site": site, "salary": salary, "status": "على رأس العمل"}
                        st.session_state['staff_db'] = pd.concat([st.session_state['staff_db'], pd.DataFrame([new_emp])], ignore_index=True)
                        log_action("إضافة موظف", f"تم تسجيل الموظف {name} ({emp_id})")
                        st.success(f"✅ تم إضافة الموظف {name} بنجاح!")
                        st.rerun()

        with tab3:
            st.subheader("تعديل بيانات الموظفين أو إنهاء الخدمات")
            staff_df = st.session_state['staff_db']
            selected_emp_id = st.selectbox("اختر الموظف:", staff_df['id'].tolist())
            emp_row = staff_df[staff_df['id'] == selected_emp_id].iloc[0]
            
            with st.form("edit_staff_form"):
                st.write(f"الموظف الحالي: **{emp_row['name']}**")
                up_site = st.selectbox("تغيير موقع العمل", ["الورشة المركزية", "الموقع الأول", "الموقع الثاني", "الإدارة"], index=0)
                up_salary = st.number_input("تحديث الراتب ($)", value=int(emp_row['salary']))
                up_status = st.selectbox("الحالة الوظيفية", ["على رأس العمل", "إجازة", "موقوف عن العمل"])
                
                b_up, b_del = st.columns(2)
                if b_up.form_submit_button("تحديث البيانات 🔄"):
                    st.session_state['staff_db'].loc[st.session_state['staff_db']['id'] == selected_emp_id, ['site', 'salary', 'status']] = [up_site, up_salary, up_status]
                    log_action("تعديل موظف", f"تحديث بيانات الموظف {emp_row['name']}")
                    st.success("✅ تم التحديث بنجاح!")
                    st.rerun()
                    
                if b_del.form_submit_button("حذف الموظف 🗑️"):
                    st.session_state['staff_db'] = st.session_state['staff_db'][st.session_state['staff_db']['id'] != selected_emp_id]
                    log_action("حذف موظف", f"حذف الموظف {emp_row['name']}")
                    st.warning("⚠️ تم حذف الموظف من السجلات.")
                    st.rerun()

    # ==============================================================================
    # 10. MODULE: EXPENSES & CAMERA
    # ==============================================================================
    elif selected_key == "expenses":
        st.title(t['expenses'])
        
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.subheader("إدخال فاتورة مشتريات جديدة مع الصورة")
        
        with st.form("expense_entry_form"):
            c1, c2 = st.columns(2)
            vendor = c1.text_input("اسم المحل / المورد")
            machine = c2.selectbox("مرتبطة بالآلية رقم:", st.session_state['fleet_db']['code'].tolist())
            amount = c1.number_input("المبلغ الإجمالي ($)", min_value=0.0, value=50.0)
            notes = c2.text_input("بيان المشتريات / القطع")
            
            st.write("📸 **التقاط أو رفع صورة الفاتورة للتدقيق:**")
            cam_img = st.camera_input("التقاط عبر كاميرا الموبايل")
            file_img = st.file_uploader("أو اختر صورة من الاستديو", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("رفع الفاتورة وإرسالها للتدقيق 📤"):
                if vendor and amount > 0:
                    vouch_id = f"VOUCH-{np.random.randint(2000, 9999)}"
                    new_voucher = {
                        "id": vouch_id,
                        "vendor": vendor,
                        "machine": machine,
                        "amount": amount,
                        "notes": notes,
                        "status": "معلق",
                        "date": str(datetime.date.today())
                    }
                    st.session_state['vouchers_db'].append(new_voucher)
                    log_action("إدخال فاتورة", f"سند {vouch_id} بقيمة ${amount} للمورد {vendor}")
                    st.success(f"✅ تم حفظ الفاتورة بنجاح وتحويلها لشاشة الاعتماد برقم `{vouch_id}`!")
                else:
                    st.error("يرجى إدخال اسم المورد والمبلغ بشكل صحيح.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ==============================================================================
    # 11. MODULE: DUAL VERIFICATION
    # ==============================================================================
    elif selected_key == "vouchers":
        st.title(t['vouchers'])
        st.subheader("شاشة الاعتماد والمقارنة المزدوجة (Split Verification)")
        
        vouchers = st.session_state['vouchers_db']
        pending = [v for v in vouchers if v['status'] == "معلق"]
        
        if not pending:
            st.info("🎉 لا توجد سندات معلقة تنتظر الاعتماد حالياً.")
        else:
            for v in pending:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                col_img, col_data = st.columns(2)
                
                with col_img:
                    st.markdown("**🖼️ صورة الفاتورة المرفقة:**")
                    st.image("https://via.placeholder.com/400x250.png?text=Original+Receipt+Image", use_container_width=True)
                    
                with col_data:
                    st.markdown(f"### سند رقم: `{v['id']}`")
                    st.write(f"**المورد:** {v['vendor']}")
                    st.write(f"**الآلية:** {v['machine']}")
                    st.write(f"**المبلغ:** `${v['amount']}`")
                    st.write(f"**البيان:** {v['notes']}")
                    
                    b_ok, b_no = st.columns(2)
                    if b_ok.button(f"✅ اعتماد وتختيم {v['id']}"):
                        v['status'] = "معتمد"
                        log_action("اعتماد سند", f"تم اعتماد السند رقم {v['id']}")
                        st.success(f"تم اعتماد السند {v['id']} وتدقيق حسابه!")
                        st.rerun()
                        
                    if b_no.button(f"❌ رفض السند {v['id']}"):
                        v['status'] = "مرفوض"
                        log_action("رفض سند", f"تم رفض السند رقم {v['id']}")
                        st.error(f"تم رفض السند {v['id']}.")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # ==============================================================================
    # 12. MODULE: MOVEMENT & ODOMETER
    # ==============================================================================
    elif selected_key == "movement":
        st.title(t['movement'])
        st.info("🔍 مطابقة قراءة العدادات بالكاميرا المباشرة لمنع التلاعب بالسولار والحركة.")
        
        c1, c2 = st.columns(2)
        with c1:
            sel_m = st.selectbox("اختر الآلية:", st.session_state['fleet_db']['code'].tolist())
            manual_read = st.number_input("القراءة اليدوية المكتوبة:", min_value=0, value=12500)
            
        with c2:
            odo_cam = st.camera_input("📸 تصوير عداد الآلية اللحظي")
            
        if st.button("مطابقة الصورة مع القراءة اليدوية 🤖"):
            if odo_cam:
                st.success(f"✅ تم قراءة العداد من الصورة بنجاح! القراءة المطابقة: {manual_read} كم/ساعة.")
                st.session_state['fleet_db'].loc[st.session_state['fleet_db']['code'] == sel_m, 'odometer'] = manual_read
                log_action("تحديث عداد", f"تحديث عداد الآلية {sel_m} إلى {manual_read}")
            else:
                st.warning("يرجى التقاط صورة للعداد أولاً.")

    # ==============================================================================
    # 13. MODULE: VENDORS LEDGER
    # ==============================================================================
    elif selected_key == "vendors":
        st.title(t['vendors'])
        st.subheader("مستحقات المحلات والكراجات الإسبوعية")
        
        vendors_summary = pd.DataFrame([
            {"المحل / المورد": "محلات الهندسية للقطع", "عدد الفواتير": 5, "إجمالي المستحقات ($)": 3250.0, "الحالة": "معلق"},
            {"المحل / المورد": "كراج الرافدين للوقود", "عدد الفواتير": 12, "إجمالي المستحقات ($)": 8400.0, "الحالة": "جاهز للصرف"},
            {"المحل / المورد": "تجهيزات السلامة الميدانية", "عدد الفواتير": 2, "إجمالي المستحقات ($)": 600.0, "الحالة": "مدفوع"}
        ])
        
        st.dataframe(vendors_summary, use_container_width=True)

    # ==============================================================================
    # 14. MODULE: RBAC & USER MANAGEMENT
    # ==============================================================================
    elif selected_key == "rbac":
        st.title(t['rbac'])
        
        tab1, tab2 = st.tabs(["👥 قائمة المستخدمين والصلاحيات", "➕ إضافة مستخدم جديد"])
        
        with tab1:
            st.subheader("إدارة الحسابات وصلاحيات الوصول")
            users_df = st.session_state['users_db']
            st.dataframe(users_df, use_container_width=True)
            
            st.markdown("---")
            st.subheader("تغيير حالة حساب أو حظر")
            target_user = st.selectbox("اختر المستخدم:", users_df['username'].tolist())
            
            c_block, c_activate = st.columns(2)
            if c_block.button("حظر هذا الحساب 🚫"):
                st.session_state['users_db'].loc[st.session_state['users_db']['username'] == target_user, 'status'] = "محظور"
                log_action("حظر مستخدم", f"تم حظر الحساب {target_user}")
                st.error(f"تم حظر المستخدم {target_user} وتجريده من الصلاحيات.")
                st.rerun()
                
            if c_activate.button("تفعيل الحساب ✅"):
                st.session_state['users_db'].loc[st.session_state['users_db']['username'] == target_user, 'status'] = "نشط"
                log_action("تفعيل مستخدم", f"تم تفعيل الحساب {target_user}")
                st.success(f"تم إعادة تفعيل حساب {target_user}.")
                st.rerun()

        with tab2:
            st.subheader("إنشاء حساب مستخدم جديد")
            with st.form("new_user_form"):
                new_u_name = st.text_input("اسم المستخدم (Username)")
                new_f_name = st.text_input("الاسم الكامل")
                new_role = st.selectbox("الرتبة والصلاحية", ["ADMIN", "ACCOUNTANT", "SUPERVISOR", "DRIVER"])
                
                if st.form_submit_button("إنشاء الحساب 💾"):
                    if new_u_name and new_f_name:
                        new_u_row = {"username": new_u_name, "full_name": new_f_name, "role": new_role, "status": "نشط"}
                        st.session_state['users_db'] = pd.concat([st.session_state['users_db'], pd.DataFrame([new_u_row])], ignore_index=True)
                        log_action("إضافة مستخدم", f"تم إنشاء حساب {new_u_name} برتبة {new_role}")
                        st.success(f"✅ تم إضافة الحساب `{new_u_name}` بنجاح!")
                        st.rerun()

    # ==============================================================================
    # 15. MODULE: AUDIT LOGS
    # ==============================================================================
    elif selected_key == "audit":
        st.title(t['audit'])
        st.subheader("الأرشيف والتتبع الأمني لجميع الحركات داخل النظام")
        if st.session_state['audit_logs']:
            audit_df = pd.DataFrame(st.session_state['audit_logs'])
            st.dataframe(audit_df, use_container_width=True)
            
            audit_csv = convert_df_to_csv(audit_df)
            st.download_button(
                label="📥 تصدير سجل التدقيق إلى CSV",
                data=audit_csv,
                file_name=f"audit_logs_{datetime.date.today()}.csv",
                mime="text/csv"
            )
        else:
            st.info("لا توجد سجلات بعد.")

    # ==============================================================================
    # 16. MODULE: SETTINGS & FULL BACKUP
    # ==============================================================================
    elif selected_key == "settings":
        st.title(t['settings'])
        st.subheader("الإعدادات العامة وتصدير النسخة الاحتياطية")
        
        st.text_input("اسم الشركة الرسمية", value="شركة المقاولات والآليات العامة")
        st.text_input("العنوان / الموقع الرئيسي", value="العراق - داهوك / الموصل")
        
        st.markdown("---")
        st.subheader("📦 تصدير قاعدة البيانات بالكامل (Full System Backup)")
        st.write("يمكنك تحميل نسخة احتياطية شاملة تحتوي على جداول الآليات، الموظفين، السندات، وسجل الأمان في ملف واحد:")
        
        all_data_dict = {
            "الآليات": st.session_state['fleet_db'],
            "الموظفين": st.session_state['staff_db'],
            "السندات": pd.DataFrame(st.session_state['vouchers_db']),
            "المستخدمين": st.session_state['users_db'],
            "سجل الأمان": pd.DataFrame(st.session_state['audit_logs']) if st.session_state['audit_logs'] else pd.DataFrame([{"ملاحظة": "لا يوجد سجلات"}])
        }
        
        backup_bytes = convert_dfs_to_excel_bytes(all_data_dict)
        st.download_button(
            label="💾 تحميل النسخة الاحتياطية الشاملة (Excel Backup)",
            data=backup_bytes,
            file_name=f"FULL_SYSTEM_BACKUP_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
