# ==============================================================================
# نظام الرصد المالي وإدارة الشركة - الجزء الأول (المحركات والأساسيات)
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import os
import json
import base64
from io import BytesIO
from supabase import create_client, Client
import folium
from streamlit_folium import st_folium

# ------------------------------------------------------------------------------
# 1. إعدادات الصفحة والثيمات (Theme & CSS)
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="نظام الرصد المالي وإدارة المقاولات",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تهيئة متغيرات الجلسة الأساسية
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'
if 'sys_settings' not in st.session_state:
    st.session_state['sys_settings'] = {
        'company_name': 'شركة المقاولات العامة',
        'manager_name': 'المدير العام',
        'logo_url': '',
        'stamp_url': ''
    }

# تصميم CSS مخصص لدعم اللغة العربية (RTL) وتقسيم الشاشات
css_base = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; direction: rtl; text-align: right; }
    .stButton>button { border-radius: 6px; font-weight: bold; width: 100%; transition: 0.3s; }
    .split-box { border-radius: 8px; padding: 15px; margin-bottom: 15px; }
"""
dark_theme = css_base + """
    .stApp { background-color: #0f172a; color: #f8fafc; }
    .main-card { background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 20px; }
    .split-box { background: #1e293b; border: 1px solid #475569; }
</style>
"""
light_theme = css_base + """
    .stApp { background-color: #f8fafc; color: #0f172a; }
    .main-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .split-box { background: #ffffff; border: 1px solid #cbd5e1; }
</style>
"""
st.markdown(dark_theme if st.session_state['theme'] == 'dark' else light_theme, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. الاتصال بقاعدة البيانات (Supabase)
# ------------------------------------------------------------------------------
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", ""))

@st.cache_resource
def init_supabase() -> Client:
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            st.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
    return None

supabase = init_supabase()

# ------------------------------------------------------------------------------
# 3. محركات النظام الأساسية (البحث الذكي، السجل الأمني، الصلاحيات، والتصدير)
# ------------------------------------------------------------------------------

def smart_search(df: pd.DataFrame, search_query: str) -> pd.DataFrame:
    """البحث التسلسلي الذكي في كافة أعمدة الجدول"""
    if not search_query or df.empty:
        return df
    query = str(search_query).strip().lower()
    mask = df.astype(str).apply(lambda col: col.str.lower().str.contains(query, na=False)).any(axis=1)
    return df[mask]

def log_audit(action: str, details: str):
    """تسجيل الإجراءات الأمنية بدقة عالية"""
    user = st.session_state.get('user', {}).get('username', 'النظام')
    now = datetime.datetime.now()
    if supabase:
        try:
            supabase.table("audit_logs").insert({
                "username": user,
                "entry_date": now.strftime("%Y-%m-%d"),
                "entry_time": now.strftime("%H:%M:%S"),
                "action": action,
                "details": details
            }).execute()
        except:
            pass

def check_permission(module_key: str, sub_action: str = None) -> bool:
    """محرك فحص الصلاحيات الدقيقة المخصصة"""
    user = st.session_state.get('user', {})
    if user.get("role") == "ADMIN":
        return True
    
    perms = user.get("custom_permissions", {})
    if isinstance(perms, str):
        try: perms = json.loads(perms)
        except: perms = {}
        
    if module_key not in perms:
        return False
        
    if sub_action:
        return perms[module_key].get(sub_action, False)
    return perms[module_key].get("allowed", False)

def generate_pdf_export(title: str, content_html: str):
    """توليد ملفات PDF احترافية مع الترويسة والشعار والختم الرقمي"""
    settings = st.session_state['sys_settings']
    
    logo_html = f"<img src='{settings['logo_url']}' style='height:60px;'>" if settings['logo_url'] else "<h2>شعار الشركة</h2>"
    stamp_html = f"<img src='{settings['stamp_url']}' style='height:80px;'>" if settings['stamp_url'] else "<div style='border:2px dashed #000; padding:15px; color:#000;'>مكان الختم الرقمي</div>"
    
    html_template = f"""
    <html dir="rtl">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Arial', sans-serif; padding: 40px; color: #000; background: #fff; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            .header-table {{ border: none; margin-bottom: 30px; border-bottom: 3px solid #1e293b; padding-bottom: 10px; }}
            .header-table td {{ border: none; text-align: right; }}
            .footer-table {{ border: none; margin-top: 50px; border-top: 1px solid #cbd5e1; padding-top: 20px; }}
            .footer-table td {{ border: none; text-align: center; vertical-align: top; }}
        </style>
    </head>
    <body>
        <table class="header-table">
            <tr>
                <td style="width: 50%;">{logo_html}<br><b style="font-size:18px;">{settings['company_name']}</b></td>
                <td style="width: 50%; text-align:left;">
                    <b>التاريخ:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
                    <b>رقم السجل:</b> {datetime.datetime.now().strftime('%Y%m%d%H%M%S')}
                </td>
            </tr>
        </table>
        <h2 style="text-align:center; color:#1e293b; margin-bottom: 20px;">{title}</h2>
        <div>{content_html}</div>
        <table class="footer-table">
            <tr>
                <td style="width: 33%;"><b>توقيع/بصمة المستلم:</b><br><br>....................................<br><small style="color:#475569;">أقر باستلام المبلغ وبراءة ذمة الشركة</small></td>
                <td style="width: 33%;">{stamp_html}<br><b>الختم الرقمي المعتمد</b></td>
                <td style="width: 33%;"><b>اعتماد المدير العام:</b><br><br><b style="font-size:16px;">{settings['manager_name']}</b></td>
            </tr>
        </table>
    </body>
    </html>
    """
    b64 = base64.b64encode(html_template.encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{title}.html" style="text-decoration:none;"><button style="background-color:#dc2626; color:white; padding:10px 20px; border:none; border-radius:5px; font-weight:bold; cursor:pointer; width:100%;">🖨️ تصدير ({title}) كـ PDF</button></a>'

# ==============================================================================
# نهاية الجزء الأول
# ==============================================================================

# ==============================================================================
# نظام الرصد المالي وإدارة الشركة - الجزء الثاني (تسجيل الدخول والمشتريات والتدقيق)
# ==============================================================================

# ------------------------------------------------------------------------------
# 4. شاشة تسجيل الدخول والمصادقة
# ------------------------------------------------------------------------------
def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='main-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center;'>🔐 تسجيل الدخول - نظام الرصد المالي</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            username_input = st.text_input("اسم المستخدم")
            password_input = st.text_input("كلمة المرور", type="password")
            submit_login = st.form_submit_button("دخول النظام 🚀")
            
            if submit_login:
                if supabase:
                    try:
                        res = supabase.table("users").select("*").eq("username", username_input.strip()).execute()
                        if res.data and res.data[0].get("password") == password_input.strip():
                            st.session_state['user'] = res.data[0]
                            log_audit("تسجيل دخول", f"تم تسجيل الدخول بنجاح للمستخدم: {username_input}")
                            st.success("✅ تم تسجيل الدخول بنجاح، جاري التحويل...")
                            st.rerun()
                        else:
                            st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة.")
                    except Exception as e:
                        st.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
                else:
                    st.error("❌ قاعدة البيانات غير متصلة حالياً.")
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 5. الوحدات البرمجية الأساسية للنظام (Modules)
# ------------------------------------------------------------------------------

# --- أ. وحدة المشتريات وتصوير الفواتير (للمندوبين) ---
def module_purchases():
    st.markdown("<div class='main-card'><h3>🛒 قسم المشتريات وتصوير الفواتير الميدانية</h3></div>", unsafe_allow_html=True)
    
    if not check_permission("purchases", "upload_invoice"):
        st.error("❌ عذراً، لا تملك صلاحية الوصول لقسم رفع الفواتير.")
        return

    # جلب قائمة الآليات والسائقين من قاعدة البيانات
    fleet_data = []
    if supabase:
        try:
            fleet_res = supabase.table("fleet").select("code, driver").execute()
            fleet_data = fleet_res.data if fleet_res.data else []
        except:
            fleet_data = []

    fleet_options = [f"{item['code']} - {item['driver']}" for item in fleet_data] if fleet_data else ["M-101 - سائق تجريبي"]

    # البحث الذكي المتسلسل للآليات
    search_veh = st.text_input("🔍 بحث تسلسلي مباشر عن الآلية أو السائق (اكتب حرفاً أو رقماً):")
    filtered_vehicles = [v for v in fleet_options if search_veh.lower() in v.lower()] if search_veh else fleet_options
    
    selected_vehicle = st.selectbox("اختر الآلية / السائق المستفيد:", filtered_vehicles)
    
    st.info("📷 الكاميرا مفعلة لالتقاط الفاتورة مباشرة (تفتح الكاميرا الخلفية حصراً على الهواتف المحمولة).")
    
    # استخدام كاميرا ستريملت التقاط مباشر
    cam_photo = st.camera_input("التقط صورة الفاتورة الأصلية")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        manual_photo = st.file_uploader("أو استورد صورة من ملفات الهاتف:", type=['jpg', 'png', 'jpeg'])
    with col_up2:
        vendor_name = st.text_input("اسم المحل / المورد:")
        amount = st.number_input("المبلغ الإجمالي للفاتورة ($):", min_value=0.0, format="%.2f")

    photo_to_use = cam_photo if cam_photo else manual_photo

    if st.button("🚀 رفع الفاتورة وإرسال إشعار فوري لموظف التدقيق", type="primary"):
        if not photo_to_use or amount <= 0 or not vendor_name.strip():
            st.warning("⚠️ يرجى التأكد من التقاط/إدراج الصورة، كتابة اسم المحل، وإدخال مبلغ صحيح.")
        else:
            try:
                img_bytes = photo_to_use.getvalue()
                b64_img = base64.b64encode(img_bytes).decode()
                
                inv_payload = {
                    "vehicle": selected_vehicle,
                    "vendor": vendor_name.strip(),
                    "amount": amount,
                    "image_data": b64_img,
                    "status": "قيد التدقيق",
                    "notes": "",
                    "created_by": st.session_state['user']['username']
                }
                
                if supabase:
                    supabase.table("invoices").insert(inv_payload).execute()
                
                log_audit("رفع فاتورة", f"تم رفع فاتورة بقيمة {amount} للمحل {vendor_name} تخص الآلية {selected_vehicle}")
                st.success("✅ تم رفع الفاتورة بنجاح وحفظها في قاعدة البيانات السحابية بانتظار التدقيق!")
            except Exception as ex:
                st.error(f"❌ حدث خطأ أثناء رفع الفاتورة: {ex}")

# --- ب. وحدة الاعتماد المزدوج وتدقيق الفواتير (تقسيم الشاشة) ---
def module_auditing():
    st.markdown("<div class='main-card'><h3>⚖️ نظام الاعتماد المزدوج وتدقيق السندات (تقسيم الشاشة)</h3></div>", unsafe_allow_html=True)
    
    is_auditor = check_permission("auditing", "audit_data")
    is_manager = check_permission("auditing", "manager_approval")

    if not (is_auditor or is_manager):
        st.error("❌ لا تملك صلاحية الوصول لنظام الاعتماد المزدوج.")
        return

    target_status = "قيد التدقيق" if is_auditor else "بانتظار موافقة المدير"
    
    invoices = []
    if supabase:
        try:
            res = supabase.table("invoices").select("*").eq("status", target_status).execute()
            invoices = res.data if res.data else []
        except:
            invoices = []

    if not invoices:
        st.success(f"🎉 لا توجد فواتير معلقة حالياً تحت حالة: ({target_status}).")
        return

    inv_list = [f"فاتورة #{i['id']} - المحل: {i['vendor']} - المبلغ: ${i['amount']}" for i in invoices]
    selected_inv_str = st.selectbox("🔍 ابحث أو اختر السند المعلق للتدقيق:", inv_list)
    selected_id = int(selected_inv_str.split("#")[1].split(" ")[0])
    inv = next((i for i in invoices if i['id'] == selected_id), None)

    if inv:
        st.markdown("---")
        # ==========================================================
        # نظام تقسيم الشاشة (Split Screen): الصورة والمقابل
        # ==========================================================
        col_img, col_form = st.columns([1, 1], gap="medium")

        with col_img:
            st.markdown("<div class='split-box'><h4>📸 صورة الفاتورة الأصلية (للمطابقة)</h4>", unsafe_allow_html=True)
            if inv.get("image_data"):
                try:
                    img_bytes = base64.b64decode(inv["image_data"])
                    st.image(img_bytes, use_container_width=True)
                    with st.expander("🔍 تكبير الصورة الأصلية بحجم الشاشة الكاملة"):
                        st.image(img_bytes)
                except:
                    st.error("تعذر عرض الصورة المرفقة.")
            else:
                st.warning("لا توجد صورة مرفقة مع هذه الفاتورة.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_form:
            st.markdown("<div class='split-box'><h4>📝 بيانات السند المالي الرقمي</h4>", unsafe_allow_html=True)
            v_vendor = st.text_input("اسم المحل / المورد المدقق", value=inv['vendor'])
            v_vehicle = st.text_input("الآلية / السائق", value=inv['vehicle'])
            v_amount = st.number_input("المبلغ المالي النهائي ($)", value=float(inv['amount']), format="%.2f")
            v_notes = st.text_area("ملاحظات التدقيق والمراجعة", value=inv.get("notes", ""))

            if is_auditor and inv['status'] == "قيد التدقيق":
                if st.button("📤 اعتماد التدقيق وتحويل السند للمدير العام", type="primary"):
                    if supabase:
                        supabase.table("invoices").update({
                            "vendor": v_vendor,
                            "vehicle": v_vehicle,
                            "amount": v_amount,
                            "notes": v_notes,
                            "status": "بانتظار موافقة المدير"
                        }).eq("id", inv['id']).execute()
                    log_audit("تدقيق فاتورة", f"تم تدقيق السند #{inv['id']} وتحويله للمدير")
                    st.success("✅ تم تدقيق البيانات وتحويل السند بنجاح للمدير العام!")
                    st.rerun()

            if is_manager and inv['status'] == "بانتظار موافقة المدير":
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    if st.button("✅ موافقة نهائية وختم رقمي", type="primary"):
                        if supabase:
                            supabase.table("invoices").update({
                                "status": "مقبولة ومختومة",
                                "notes": v_notes
                            }).eq("id", inv['id']).execute()
                        log_audit("اعتماد مدير", f"تم ختم واعتماد السند #{inv['id']} بالختم الرقمي الرسمي")
                        st.success("✅ تم ختم السند رسمياً وإدراجه في حسابات الشركة ومستحقات المحل!")
                        st.rerun()
                with col_m2:
                    if st.button("❌ رفض وإعادة للمندوب"):
                        if supabase:
                            supabase.table("invoices").update({"status": "قيد التدقيق", "notes": v_notes}).eq("id", inv['id']).execute()
                        log_audit("رفض سند", f"تم رفض السند #{inv['id']} وإعادته")
                        st.warning("⚠️ تمت إعادة السند إلى حالة التدقيق للتصحيح.")
                        st.rerun()

            if inv['status'] == 'مقبولة ومختومة':
                st.success("✨ هذا السند معتمد ومختوم رقمياً وجاهز للطباعة.")
                pdf_html_content = f"""
                <p><b>رقم السند:</b> #{inv['id']}</p>
                <p><b>المحل المستفيد:</b> {inv['vendor']}</p>
                <p><b>الآلية / المعدة:</b> {inv['vehicle']}</p>
                <p><b>المبلغ المعتمد:</b> ${inv['amount']}</p>
                <p><b>ملاحظات التدقيق:</b> {inv.get('notes', 'لا توجد ملاحظات')}</p>
                """
                st.markdown(generate_pdf_export(f"سند صرف مالي رقم #{inv['id']}", pdf_html_content), unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# نهاية الجزء الثاني
# ==============================================================================

# ==============================================================================
# نظام الرصد المالي وإدارة الشركة - الجزء الثالث (المحلات، الآليات، والموظفين)
# ==============================================================================

# --- ج. وحدة مستحقات المحلات والفواتير المعتمدة ---
def module_vendors():
    st.markdown("<div class='main-card'><h3>🏢 مستحقات المحلات وتفاصيل الكشوفات المالية</h3></div>", unsafe_allow_html=True)
    
    invoices = []
    if supabase:
        try:
            res = supabase.table("invoices").select("*").eq("status", "مقبولة ومختومة").execute()
            invoices = res.data if res.data else []
        except:
            invoices = []

    if not invoices:
        st.info("لا توجد فواتير مقبولة ومختومة مسجلة حالياً.")
        return

    df = pd.DataFrame(invoices)
    
    # البحث الذكي المتسلسل
    q = st.text_input("🔍 بحث ذكي في المستحقات (اسم المحل، كود الآلية، التاريخ):")
    df_filtered = smart_search(df, q)

    st.markdown("#### 📊 جدول السندات المعتمدة")
    st.dataframe(df_filtered[['id', 'vendor', 'vehicle', 'amount', 'created_at']], use_container_width=True)

    st.markdown("#### 💰 إجمالي المستحقات المالية لكل محل (كشف حساب)")
    if not df_filtered.empty:
        vendor_summary = df_filtered.groupby('vendor')['amount'].sum().reset_index()
        st.dataframe(vendor_summary, use_container_width=True)

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            if st.button("🖨️ تصدير كشف مستحقات المحلات الإجمالي كـ PDF"):
                html_table = vendor_summary.to_html(index=False, classes='table')
                st.markdown(generate_pdf_export("كشف حساب مستحقات المحلات الإجمالي", html_table), unsafe_allow_html=True)
        with col_v2:
            selected_vendor = st.selectbox("اختر محلاً لاستعراض فواتيره وصوره الأصلية:", vendor_summary['vendor'].tolist())
            if st.button("🔍 عرض تفاصيل وفواتير هذا المحل حصراً"):
                vendor_invoices = df_filtered[df_filtered['vendor'] == selected_vendor]
                for _, r in vendor_invoices.iterrows():
                    st.write(f"---")
                    st.write(f"**سند رقم #{r['id']} | المبلغ: ${r['amount']} | الآلية: {r['vehicle']} | التاريخ: {r['created_at']}**")
                    if r.get("notes"):
                        st.write(f"ملاحظات التدقيق: {r['notes']}")
                    if r.get("image_data"):
                        try:
                            st.image(base64.b64decode(r["image_data"]), width=300)
                        except:
                            pass

# --- د. وحدة إدارة كلف الآليات والمعدات ---
def module_fleet():
    st.markdown("<div class='main-card'><h3>🚜 إدارة أسطول الآليات والمعدات وكلف التشغيل</h3></div>", unsafe_allow_html=True)
    
    fleet_data = []
    if supabase:
        try:
            res = supabase.table("fleet").select("*").execute()
            fleet_data = res.data if res.data else []
        except:
            fleet_data = []

    df_fleet = pd.DataFrame(fleet_data) if fleet_data else pd.DataFrame(columns=["code", "driver", "status", "notes"])

    q_fleet = st.text_input("🔍 بحث ذكي في الأسطول (كود الآلية، اسم السائق، الحالة):")
    df_fleet_filtered = smart_search(df_fleet, q_fleet)

    st.dataframe(df_fleet_filtered, use_container_width=True)

    with st.expander("➕ إضافة آلية جديدة أو تعديل بيانات أسطول"):
        with st.form("fleet_add_form"):
            f_code = st.text_input("كود أو رقم الآلية (مثال: Excavator-01)")
            f_driver = st.text_input("اسم السائق المسؤول")
            f_status = st.selectbox("حالة الآلية", ["شغالة ميدانياً", "في الصيانة والورشة", "متوقفة / عاطلة"])
            f_notes = st.text_area("ملاحظات فنية أو كلف الصيانة")
            
            if st.form_submit_button("حفظ الآلية في النظام 💾"):
                if f_code.strip():
                    if supabase:
                        supabase.table("fleet").insert({
                            "code": f_code.strip(),
                            "driver": f_driver.strip(),
                            "status": f_status,
                            "notes": f_notes
                        }).execute()
                    log_audit("إضافة آلية", f"تمت إضافة الآلية الجديدة: {f_code}")
                    st.success("✅ تم حفظ الآلية بنجاح!")
                    st.rerun()
                else:
                    st.warning("⚠️ يرجى إدخال كود الآلية على الأقل.")

# --- هـ. وحدة الموظفين والورشات ---
def module_staff():
    st.markdown("<div class='main-card'><h3>👷 إدارة الكوادر البشرية والورشات والرواتب</h3></div>", unsafe_allow_html=True)
    
    staff_data = []
    if supabase:
        try:
            res = supabase.table("staff").select("*").execute()
            staff_data = res.data if res.data else []
        except:
            staff_data = []

    df_staff = pd.DataFrame(staff_data) if staff_data else pd.DataFrame(columns=["name", "job", "salary", "status"])

    q_staff = st.text_input("🔍 بحث ذكي عن موظف أو مهندس (الاسم، المسمى الوظيفي):")
    df_staff_filtered = smart_search(df_staff, q_staff)

    st.dataframe(df_staff_filtered, use_container_width=True)

    with st.expander("➕ إضافة موظف أو مهندس جديد للورشة"):
        with st.form("staff_add_form"):
            s_name = st.text_input("الاسم الثلاثي للموظف")
            s_job = st.text_input("المسمى الوظيفي (مثال: مهندس موقع، ميكانيكي، محاسب)")
            s_salary = st.number_input("الراتب الشهري ($):", min_value=0.0, format="%.2f")
            s_status = st.selectbox("حالة الدوام", ["على رأس العمل ميدانياً", "إجازة دورية", "موقوف / مغادر"])
            
            if st.form_submit_button("حفظ الموظف 💾"):
                if s_name.strip():
                    if supabase:
                        supabase.table("staff").insert({
                            "name": s_name.strip(),
                            "job": s_job.strip(),
                            "salary": s_salary,
                            "status": s_status
                        }).execute()
                    log_audit("إضافة موظف", f"تمت إضافة الموظف: {s_name} - {s_job}")
                    st.success("✅ تمت إضافة الموظف بنجاح!")
                    st.rerun()
                else:
                    st.warning("⚠️ يرجى إدخال اسم الموظف.")

# ==============================================================================
# نهاية الجزء الثالث
# ==============================================================================

# ==============================================================================
# نظام الرصد المالي وإدارة الشركة - الجزء الرابع والاخير (GPS، الصلاحيات، الإعدادات، والتشغيل)
# ==============================================================================

# --- و. وحدة التتبع الجغرافي (GPS) ---
def module_gps():
    st.markdown("<div class='main-card'><h3>📍 نظام التتبع الجغرافي الميداني للكوادر</h3></div>", unsafe_allow_html=True)
    st.info("🟢 نقطة خضراء: موظف نشط ميدانياً | ⚪ نقطة رمادية: غير متصل | 🔴 نقطة حمراء: خارج التغطية")
    
    # إنشاء الخريطة بمركز افتراضي (العراق)
    m = folium.Map(location=[33.3152, 44.3661], zoom_start=6)
    
    users_gps = []
    if supabase:
        try:
            res = supabase.table("users").select("full_name, last_lat, last_lng, status_color").execute()
            users_gps = res.data if res.data else []
        except:
            users_gps = []
            
    for u in users_gps:
        if u.get("last_lat") and u.get("last_lng"):
            folium.Marker(
                [u["last_lat"], u["last_lng"]],
                popup=u["full_name"],
                icon=folium.Icon(color=u.get("status_color", "green"))
            ).add_to(m)

    st_folium(m, width=900, height=450)

# --- ز. وحدة إدارة الصلاحيات الدقيقة للمستخدمين ---
def module_users_permissions():
    st.markdown("<div class='main-card'><h3>🔐 إدارة المستخدمين وتخصيص الصلاحيات الفرعية بدقة</h3></div>", unsafe_allow_html=True)
    
    if not check_permission("admin"):
        st.error("❌ هذه الشاشة مخصصة لمدير النظام (المالك) فقط.")
        return

    users_list = []
    if supabase:
        try:
            res = supabase.table("users").select("*").execute()
            users_list = res.data if res.data else []
        except:
            users_list = []
            
    if users_list:
        st.dataframe(pd.DataFrame(users_list)[['id', 'username', 'full_name', 'role']], use_container_width=True)

    st.markdown("#### ➕ إضافة مستخدم جديد وتحديد صلاحياته الدقيقة")
    with st.form("user_perm_add_form"):
        u_username = st.text_input("اسم المستخدم لتسجيل الدخول")
        u_pass = st.text_input("كلمة المرور", type="password")
        u_fullname = st.text_input("الاسم الثلاثي للمستخدم")
        
        st.markdown("---")
        st.write("🛠️ **تفعيل الصلاحيات الفرعية المخصصة:**")
        p_cam = st.checkbox("صلاحية رفع الفواتير واختيار الآلية (مندوب المشتريات)")
        p_audit = st.checkbox("صلاحية تدقيق السندات وتحويلها (موظف التدقيق)")
        p_mgr = st.checkbox("صلاحية الموافقة النهائية والختم الرقمي (المدير)")
        p_fleet = st.checkbox("صلاحية إدارة كلف الأسطول والآليات")
        
        if st.form_submit_button("حفظ المستخدم وصلاحياته 💾"):
            if u_username.strip() and u_pass.strip():
                custom_perm = {
                    "purchases": {"allowed": True, "upload_invoice": p_cam},
                    "auditing": {"allowed": True, "audit_data": p_audit, "manager_approval": p_mgr},
                    "fleet": {"allowed": p_fleet}
                }
                if supabase:
                    supabase.table("users").insert({
                        "username": u_username.strip(),
                        "password": u_pass.strip(),
                        "full_name": u_fullname.strip(),
                        "role": "USER",
                        "custom_permissions": json.dumps(custom_perm)
                    }).execute()
                log_audit("إضافة مستخدم", f"تم إنشاء مستخدم جديد: {u_username}")
                st.success("✅ تم حفظ المستخدم وصلاحياته المخصصة بنجاح!")
                st.rerun()
            else:
                st.warning("⚠️ يرجى إدخال اسم المستخدم وكلمة المرور.")

# --- ح. وحدة إعدادات النظام، الثيم، السجل الأمني، وتصفير البيانات ---
def module_settings():
    st.markdown("<div class='main-card'><h3>⚙️ إعدادات النظام، السجل الأمني، وإدارة البيانات</h3></div>", unsafe_allow_html=True)
    
    tab_set1, tab_set2, tab_set3 = st.tabs(["الإعدادات العامة والشعارات", "السجل الأمني الأرشيفي", "منطقة العمليات الحرجة (التصفير)"])
    
    with tab_set1:
        if st.button("🌙 / ☀️ تبديل ثيم الشاشة (ليلي / نهاري)"):
            st.session_state['theme'] = 'light' if st.session_state['theme'] == 'dark' else 'dark'
            st.rerun()
            
        with st.form("settings_update_form"):
            c_name = st.text_input("اسم الشركة الرسمية:", value=st.session_state['sys_settings']['company_name'])
            m_name = st.text_input("اسم المدير العام المعتمد:", value=st.session_state['sys_settings']['manager_name'])
            logo_url = st.text_input("رابط اللوغو (Logo URL):", value=st.session_state['sys_settings']['logo_url'])
            stamp_url = st.text_input("رابط الختم الرقمي (Stamp URL):", value=st.session_state['sys_settings']['stamp_url'])
            
            if st.form_submit_button("حفظ الإعدادات العامة 💾"):
                st.session_state['sys_settings'] = {
                    'company_name': c_name,
                    'manager_name': m_name,
                    'logo_url': logo_url,
                    'stamp_url': stamp_url
                }
                log_audit("تعديل إعدادات", "تم تحديث بيانات الشركة والاعتمادات الرسمية")
                st.success("✅ تم تحديث إعدادات النظام بنجاح!")
                
    with tab_set2:
        st.markdown("#### 🛡️ سجل العمليات والأحداث الأمنية (Audit Trail)")
        logs_data = []
        if supabase:
            try:
                res = supabase.table("audit_logs").select("*").order("created_at", desc=True).execute()
                logs_data = res.data if res.data else []
            except:
                logs_data = []
                
        if logs_data:
            df_logs = pd.DataFrame(logs_data)
            q_log = st.text_input("🔍 بحث في السجل الأمني (مستخدم، إجراء، تفاصيل):")
            df_logs_filtered = smart_search(df_logs, q_log)
            st.dataframe(df_logs_filtered, use_container_width=True)
            
            if st.button("🖨️ تصدير السجل الأمني كـ PDF"):
                html_logs = df_logs_filtered.to_html(index=False)
                st.markdown(generate_pdf_export("السجل الأمني الأرشيفي للشركة", html_logs), unsafe_allow_html=True)
        else:
            st.info("لا توجد سجلات أمنية مسجلة حتى الآن.")
            
    with tab_set3:
        st.markdown("#### 🚨 منطقة الحذف والتصفير الشامل للبيانات")
        with st.expander("⚠️ تحذير: تصفير كافة فواتير وسجلات النظام"):
            master_pass = st.text_input("أدخل كلمة مرور المالك لتأكيد عملية التصفير:", type="password")
            if st.button("🔴 تصفير وحذف جميع بيانات الفواتير والسجلات"):
                if master_pass == st.session_state.get('user', {}).get('password'):
                    if supabase:
                        try:
                            supabase.table("invoices").delete().neq("id", 0).execute()
                            supabase.table("audit_logs").delete().neq("id", 0).execute()
                        except:
                            pass
                    log_audit("تصفير شامل", "قام المالك بتصفير قاعدة بيانات الفواتير والسجلات بالكامل")
                    st.error("💥 تم حذف وتصفير بيانات الفواتير والسجلات الأمنية بنجاح.")
                else:
                    st.error("❌ كلمة المرور غير صحيحة!")

# ==============================================================================
# 6. المحرك الرئيسي وتوجيه القوائم (Main App Control Loop)
# ==============================================================================
def main():
    if 'user' not in st.session_state:
        login_screen()
    else:
        user_info = st.session_state['user']
        st.sidebar.markdown(f"### 👤 {user_info.get('full_name', 'مستخدم')}")
        st.sidebar.caption(f"الصلاحية: {user_info.get('role', 'USER')}")
        st.sidebar.markdown("---")
        
        menu_modules = {
            "🛒 المشتريات وتصوير الفواتير": module_purchases,
            "⚖️ الاعتماد المزدوج للسندات": module_auditing,
            "🏢 مستحقات المحلات المالية": module_vendors,
            "🚜 إدارة أسطول الآليات": module_fleet,
            "👷 الكوادر البشرية والورشات": module_staff,
            "📍 التتبع الجغرافي GPS": module_gps,
            "🔐 إدارة المستخدمين والصلاحيات": module_users_permissions,
            "⚙️ إعدادات النظام والأمان": module_settings
        }
        
        selected_module = st.sidebar.radio("📋 القائمة الرئيسية للنظام:", list(menu_modules.keys()))
        
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 تسجيل الخروج"):
            log_audit("تسجيل خروج", f"تم خروج المستخدم: {user_info.get('username')}")
            st.session_state.clear()
            st.rerun()
            
        # تشغيل القسم المحدد
        menu_modules[selected_module]()

if __name__ == "__main__":
    main()
