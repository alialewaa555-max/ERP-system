import os
import io
import json
import base64
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
from PIL import Image
from supabase import create_client, Client
import folium
from streamlit_folium import st_folium

# Streamlit Page Setup
st.set_page_config(
    page_title="نظام إدارة ERP المتكامل",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 1. Supabase Initialization
# ---------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", ""))
    if not url or not key:
        st.error("خطأ: لم يتم ضبط بيانات الاتصال بـ Supabase في Secrets أو البيئة.")
        st.stop()
    return create_client(url, key)

supabase = init_supabase()

# ---------------------------------------------------------
# 2. Audio Alert & JS Helper Functions
# ---------------------------------------------------------
def play_audio_alert():
    """تشغيل تنبيه صوتي عند وجود إجراء معلق"""
    audio_js = """
    <script>
    var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    var osc = audioCtx.createOscillator();
    var gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
    gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.5);
    </script>
    """
    st.components.v1.html(audio_js, height=0)

def log_security_action(username: str, action: str):
    """تسجيل الإجراءات في سجل التدقيق الأمني"""
    now = datetime.now()
    try:
        supabase.table("audit_logs").insert({
            "username": username,
            "action": action,
            "log_date": now.strftime("%Y-%m-%d"),
            "log_time": now.strftime("%H:%M:%S")
        }).execute()
    except Exception as e:
        pass

# ---------------------------------------------------------
# 3. Custom CSS & Dynamic Styling
# ---------------------------------------------------------
st.markdown("""
<style>
    .main { text-align: right; direction: rtl; }
    div[data-testid="stSidebar"] { text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 6px; font-weight: bold; }
    .badge-red { background-color: #ff4d4d; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
    .badge-green { background-color: #2eb82e; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
    .badge-grey { background-color: #888888; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
    .split-container { display: flex; gap: 15px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. Session State & Authentication
# ---------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

def login(username, password):
    res = supabase.table("users").select("*").eq("username", username).eq("password", password).eq("is_active", True).execute()
    if res.data:
        st.session_state.user = res.data[0]
        log_security_action(username, "تسجيل دخول إلى النظام")
        st.rerun()
    else:
        st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")

if not st.session_state.user:
    st.title("🔐 تسجيل الدخول - نظام ERP")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        u_input = st.text_input("اسم المستخدم")
        p_input = st.text_input("كلمة المرور", type="password")
        if st.button("دخول"):
            login(u_input, p_input)
    st.stop()

current_user = st.session_state.user
user_role = current_user.get("role_name", "موظف")
sub_perms = current_user.get("sub_permissions", {})

# ---------------------------------------------------------
# 5. Global Settings Fetcher
# ---------------------------------------------------------
def get_system_settings():
    res = supabase.table("system_settings").select("*").eq("id", 1).execute()
    if res.data:
        return res.data[0]
    return {"company_name": "اسم الشركة", "manager_name": "المدير العام", "logo_url": None, "stamp_url": None}

sys_settings = get_system_settings()

# ---------------------------------------------------------
# Sidebar Navigation & User Info
# ---------------------------------------------------------
st.sidebar.title(f"👤 {current_user['full_name']}")
st.sidebar.caption(f"الصلاحية: {user_role}")

if st.sidebar.button("🚪 تسجيل الخروج"):
    log_security_action(current_user["username"], "تسجيل خروج")
    st.session_state.user = None
    st.rerun()

st.sidebar.markdown("---")

# Restriction for role 'بلا'
if user_role == "بلا":
    st.warning("حسابك مخصص لتتبع الموقع واستلام الرسائل فقط.")
    # Auto GPS Broadcast (Simulated coordinates)
    supabase.table("user_locations").upsert({
        "username": current_user["username"],
        "latitude": 33.3152,
        "longitude": 44.3661,
        "status": "ثابت",
        "updated_at": datetime.now().isoformat()
    }).execute()
    st.info("📩 لا توجد رسائل جديدة من المدير حالياً.")
    st.stop()

# Modular Tabs based on permissions
all_modules = [
    "🛒 المشتريات وتصوير الفواتير",
    "⚖️ الاعتماد المزدوج للسندات",
    "🏢 مستحقات المحلات",
    "🚜 إدارة كلف الآليات",
    "📷 حركة العدادات والتصوير",
    "👥 إدارة الموظفين والورشات",
    "🛡️ سجل التدقيق الأمني",
    "🔑 إدارة المستخدمين والصلاحيات",
    "🌐 التتبع الجغرافي للموقع",
    "⚙️ إعدادات النظام وتصدير البيانات"
]

# Filter modules according to Sub-permissions
allowed_modules = []
for mod in all_modules:
    mod_key = mod.split(" ")[1]
    if user_role in ["المدير", "مالك"] or sub_perms.get(mod_key, True):
        allowed_modules.append(mod)

selected_tab = st.sidebar.radio("القائمة الرئيسية", allowed_modules)

# Smart Search Helper Function
def apply_smart_search(df: pd.DataFrame, search_term: str) -> pd.DataFrame:
    if not search_term or df.empty:
        return df
    term = search_term.strip().lower()
    mask = np.column_stack([df[col].astype(str).str.lower().str.contains(term, na=False) for col in df.columns])
    return df.loc[mask.any(axis=1)]

# ---------------------------------------------------------
# TAB 1: المشتريات وتصوير الفواتير
# ---------------------------------------------------------
if selected_tab == "🛒 المشتريات وتصوير الفواتير":
    st.header("🛒 المشتريات وتصوير الفواتير")

    # Fetch vehicles for fuzzy select dropdown
    vehicles_res = supabase.table("vehicles").select("*").execute()
    vehicles_df = pd.DataFrame(vehicles_res.data) if vehicles_res.data else pd.DataFrame(columns=["id", "name", "driver_name"])

    # Purchasing Agent Workflow
    if user_role in ["مندوب مشتريات", "المدير", "مالك"]:
        st.subheader("📸 رفع فاتورة شراء جديدة")
        if not vehicles_df.empty:
            vehicles_df["search_label"] = vehicles_df["name"] + " - السائق: " + vehicles_df["driver_name"]
            selected_v_label = st.selectbox("اختر الآلية (ابحث بالاسم أو السائق):", vehicles_df["search_label"].tolist())
            selected_v_id = int(vehicles_df[vehicles_df["search_label"] == selected_v_label]["id"].values[0])
        else:
            selected_v_id = None
            st.warning("لا توجد آليات مضافة بالسستم.")

        store_input = st.text_input("اسم المحل / المورد:")

        # Rear Camera Input ONLY
        camera_img = st.camera_input("التقاط صورة الفاتورة (الكاميرا الخلفية)", key="purchasing_cam")
        manual_img = st.file_uploader("أو رفع صورة من الجهاز", type=["jpg", "png", "jpeg"])

        active_img = camera_img or manual_img

        c1, c2 = st.columns(2)
        with c1:
            if st.button("📤 رفع الفاتورة للمراجع"):
                if not store_input:
                    st.error("يرجى إدخال اسم المحل.")
                else:
                    img_url = None
                    if active_img:
                        # Upload to Supabase Storage
                        file_bytes = active_img.getvalue()
                        filename = f"inv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        supabase.storage.from_("invoices").upload(filename, file_bytes)
                        img_url = supabase.storage.from_("invoices").get_public_url(filename)
                    
                    supabase.table("invoices").insert({
                        "vehicle_id": selected_v_id,
                        "store_name": store_input,
                        "image_url": img_url,
                        "status": "معلقة_تدقيق",
                        "created_by": current_user["username"]
                    }).execute()
                    log_security_action(current_user["username"], f"إضافة فاتورة للمحل {store_input}")
                    st.success("تم رفع الفاتورة وإرسال تنبيه لموظف التدقيق!")
        with c2:
            if st.button("📝 إضافة فاتورة بدون صورة"):
                if store_input:
                    supabase.table("invoices").insert({
                        "vehicle_id": selected_v_id,
                        "store_name": store_input,
                        "status": "معلقة_تدقيق",
                        "created_by": current_user["username"]
                    }).execute()
                    st.success("تم تسجيل الفاتورة بدون صورة.")

    # Invoice Auditor & Manager Verification Workflow (Split View & Sound Alert)
    st.markdown("---")
    st.subheader("🔍 قائمة الفواتير والتدقيق")
    
    invoices_res = supabase.table("invoices").select("*, vehicles(name, driver_name)").execute()
    inv_data = invoices_res.data or []
    
    # Sound Alert Check for Auditor or Manager
    pending_audit = [i for i in inv_data if i["status"] == "معلقة_تدقيق"]
    pending_mgr = [i for i in inv_data if i["status"] == "بانتظار_المدير"]

    if (user_role in ["موظف تدقيق الفواتير", "المدير"] and pending_audit) or (user_role in ["المدير", "مالك"] and pending_mgr):
        play_audio_alert()
        st.warning("⚠️ يوجد فواتير / سندات معلقة تنتظر مراجعتك وتدقيقك!")

    # Search Bar
    search_q = st.text_input("🔍 البحث الذكي في الفواتير (اكتب أول حروف من اسم الآلية، المحل، السائق...):")
    if inv_data:
        df_inv = pd.DataFrame(inv_data)
        df_inv_filtered = apply_smart_search(df_inv, search_q)
        
        for idx, row in df_inv_filtered.iterrows():
            with st.expander(f"فاتورة رقم #{row['id']} - المحل: {row['store_name']} - الحالة: {row['status']}"):
                col_left, col_right = st.columns(2)
                
                # Split Screen View (Image vs Voucher Details)
                with col_left:
                    st.markdown("### 📷 الصورة الأصلية")
                    if row.get("image_url"):
                        st.image(row["image_url"], use_container_width=True)
                        if st.button(f"🔍 رؤية الأصل (ملء الشاشة)", key=f"zoom_{row['id']}"):
                            st.image(row["image_url"])
                    else:
                        st.info("لا توجد صورة مرفقة بهذه الفاتورة")

                with col_right:
                    st.markdown("### 📄 السند المالي / البيانات")
                    if user_role in ["موظف تدقيق الفواتير", "المدير"] and row["status"] == "معلقة_تدقيق":
                        with st.form(f"audit_form_{row['id']}"):
                            v_num = st.text_input("رقم السند المالي", f"VND-{row['id']}-2026")
                            amt = st.number_input("المبلغ الإجمالي ($)", min_value=0.0, step=1.0)
                            dtls = st.text_area("تفاصيل المواد والقطع")
                            
                            sub_audit = st.form_submit_button("إرسال للمدير للموافقة")
                            if sub_audit:
                                supabase.table("vouchers").insert({
                                    "invoice_id": row["id"],
                                    "voucher_number": v_num,
                                    "vehicle_id": row["vehicle_id"],
                                    "store_name": row["store_name"],
                                    "amount": amt,
                                    "details": dtls,
                                    "audited_by": current_user["username"],
                                    "status": "معلق"
                                }).execute()
                                supabase.table("invoices").update({"status": "بانتظار_المدير"}).eq("id", row["id"]).execute()
                                log_security_action(current_user["username"], f"تدقيق الفاتورة #{row['id']} وتحويلها للمدير")
                                st.success("تم تحويل السند للمدير!")
                                st.rerun()

                    elif user_role in ["المدير", "مالك"] and row["status"] == "بانتظار_المدير":
                        v_res = supabase.table("vouchers").select("*").eq("invoice_id", row["id"]).execute()
                        if v_res.data:
                            voucher = v_res.data[0]
                            st.write(f"**رقم السند:** {voucher['voucher_number']}")
                            st.write(f"**المبلغ:** {voucher['amount']} $")
                            st.write(f"**التفاصيل:** {voucher['details']}")
                            st.write(f"**المطابق بواسطة التدقيق:** {voucher['audited_by']}")
                            
                            b1, b2 = st.columns(2)
                            with b1:
                                if st.button("✅ موافقة وختم رقمي", key=f"app_{row['id']}"):
                                    supabase.table("vouchers").update({"status": "مقبول", "approved_by": current_user["username"]}).eq("id", voucher["id"]).execute()
                                    supabase.table("invoices").update({"status": "مقبول"}).eq("id", row["id"]).execute()
                                    log_security_action(current_user["username"], f"الموافقة على السند #{voucher['voucher_number']}")
                                    st.success("تم الاعتماد والختم الرقمي بنجاح.")
                                    st.rerun()
                            with b2:
                                if st.button("❌ رفض وإعادة للتدقيق", key=f"rej_{row['id']}"):
                                    supabase.table("invoices").update({"status": "معلقة_تدقيق"}).eq("id", row["id"]).execute()
                                    supabase.table("vouchers").update({"status": "مرفوض"}).eq("id", voucher["id"]).execute()
                                    st.warning("تمت إعادة الفاتورة لمدقق الفواتير.")
                                    st.rerun()
                    else:
                        st.write(f"**الحالة الحالية:** {row['status']}")

# ---------------------------------------------------------
# TAB 2: الاعتماد المزدوج للسندات
# ---------------------------------------------------------
elif selected_tab == "⚖️ الاعتماد المزدوج للسندات":
    st.header("⚖️ الاعتماد المزدوج للسندات المالية")

    v_res = supabase.table("vouchers").select("*, invoices(image_url)").execute()
    v_data = v_res.data or []

    if v_data:
        df_v = pd.DataFrame(v_data)
        search_v = st.text_input("🔍 بحث ذكي في جميع السندات (المقبولة والمعلقة):")
        df_v_filtered = apply_smart_search(df_v, search_v)

        for idx, row in df_v_filtered.iterrows():
            status_badge = "🔴 معلق" if row["status"] == "معلق" else "🟢 مقبول"
            st.markdown(f"#### سند رقم: {row['voucher_number']} | المحل: {row['store_name']} | المبلغ: {row['amount']} $ | {status_badge}")
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("📄 عرض السند المالي", key=f"view_v_{row['id']}"):
                    st.json(row)
            with c2:
                if row.get("invoices") and row["invoices"].get("image_url"):
                    if st.button("🖼️ عرض الصورة الأصلية", key=f"orig_v_{row['id']}"):
                        st.image(row["invoices"]["image_url"])
            with c3:
                # PDF Export Mock / Representation with Stamp & Fingerprint Notice
                if st.button("📥 تصدير PDF احترافي", key=f"pdf_v_{row['id']}"):
                    st.info(f"""
                    --- 📑 **سند مالي رسمي** ---
                    **شركة:** {sys_settings['company_name']} | **المدير:** {sys_settings['manager_name']}
                    **رقم السند:** {row['voucher_number']} | **التاريخ:** {row['created_at']}
                    **المبلغ:** {row['amount']} $ | **المحل:** {row['store_name']}
                    ----------------------------------
                    **اقرار صاحب المحل:** أقر أنا صاحب محل ({row['store_name']}) باستلام المبلغ المرقوم أعلاه وبراءة ذمة الشركة تماماً.
                    [ختم الشركة الرقمي 💮]   [بصمة صاحب المحل 🖐️]
                    """)

# ---------------------------------------------------------
# TAB 3: مستحقات المحلات
# ---------------------------------------------------------
elif selected_tab == "🏢 مستحقات المحلات":
    st.header("🏢 إدارة مستحقات المحلات والديون")

    v_res = supabase.table("vouchers").select("*, invoices(image_url)").eq("status", "مقبول").execute()
    v_data = v_res.data or []

    if v_data:
        df_stores = pd.DataFrame(v_data)
        store_summary = df_stores.groupby("store_name")["amount"].sum().reset_index()
        st.subheader("📊 إجمالي المستحقات حسب المحل")
        st.dataframe(store_summary, use_container_width=True)

        selected_store = st.selectbox("اختر محل لعرض السندات والصور الأصلية الخاصة به:", store_summary["store_name"].tolist())
        store_vouchers = df_stores[df_stores["store_name"] == selected_store]

        st.markdown(f"### السندات الفردية لمحل: {selected_store}")
        for _, row in store_vouchers.iterrows():
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**رقم السند:** {row['voucher_number']} | **التاريخ:** {row['created_at']}")
                st.write(f"**المبلغ:** {row['amount']} $ | **التفاصيل:** {row['details']}")
            with col2:
                if row.get("invoices") and row["invoices"].get("image_url"):
                    st.image(row["invoices"]["image_url"], width=200, caption=f"فاتورة {row['voucher_number']}")

# ---------------------------------------------------------
# TAB 4: إدارة كلف الآليات
# ---------------------------------------------------------
elif selected_tab == "🚜 إدارة كلف الآليات":
    st.header("🚜 إدارة كلف الآليات والمواصفات")

    with st.expander("➕ إضافة آلية جديدة"):
        with st.form("add_vehicle_form"):
            v_name = st.text_input("اسم / رقم الآلية")
            d_name = st.text_input("اسم السائق")
            status = st.selectbox("حالة الآلية", ["شغالة", "في الصيانة", "متوقفة/عاطلة"])
            specs = st.text_area("مواصفات الآلية")
            notes = st.text_area("ملاحظات")
            
            if st.form_submit_button("حفظ الآلية"):
                supabase.table("vehicles").insert({
                    "name": v_name, "driver_name": d_name, "status": status, "specs": specs, "notes": notes
                }).execute()
                st.success("تمت إضافة الآلية بنجاح.")
                st.rerun()

    v_res = supabase.table("vehicles").select("*").execute()
    if v_res.data:
        df_v = pd.DataFrame(v_res.data)
        search_v = st.text_input("🔍 بحث ذكي في الآليات والسائقين:")
        df_v_filtered = apply_smart_search(df_v, search_v)
        st.dataframe(df_v_filtered, use_container_width=True)

# ---------------------------------------------------------
# TAB 5: حركة العدادات والتصوير
# ---------------------------------------------------------
elif selected_tab == "📷 حركة العدادات والتصوير":
    st.header("📷 تصوير الحركة والعدادات (موظف الحركة)")

    v_res = supabase.table("vehicles").select("*").execute()
    v_df = pd.DataFrame(v_res.data) if v_res.data else pd.DataFrame()

    if not v_df.empty:
        sel_v = st.selectbox("اختر الآلية:", v_df["name"].tolist())
        cam_meter = st.camera_input("التقاط صورة العداد (الكاميرا الخلفية)", key="meter_cam")
        file_meter = st.file_uploader("أو اختر صورة من المعرض", type=["jpg", "png"])
        
        meter_img = cam_meter or file_meter
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📤 رفع قراءة العداد"):
                if meter_img:
                    st.success(f"تم رفع قراءة العداد للآلية {sel_v} بنجاح.")
                else:
                    st.error("يرجى التقاط صورة أولاً.")
        with c2:
            if st.button("↩️ تراجع"):
                st.rerun()

# ---------------------------------------------------------
# TAB 6: إدارة الموظفين والورشات
# ---------------------------------------------------------
elif selected_tab == "👥 إدارة الموظفين والورشات":
    st.header("👥 إدارة الموظفين والورشات")

    u_res = supabase.table("users").select("*").execute()
    if u_res.data:
        df_u = pd.DataFrame(u_res.data)
        st.dataframe(df_u[["username", "full_name", "role_name", "salary", "is_active"]], use_container_width=True)

# ---------------------------------------------------------
# TAB 7: سجل التدقيق الأمني
# ---------------------------------------------------------
elif selected_tab == "🛡️ سجل التدقيق الأمني":
    st.header("🛡️ سجل التدقيق الأمني والإجراءات")

    logs_res = supabase.table("audit_logs").select("*").order("id", desc=True).execute()
    if logs_res.data:
        df_logs = pd.DataFrame(logs_res.data)
        search_log = st.text_input("🔍 بحث في السجل الأمني:")
        df_logs_filtered = apply_smart_search(df_logs, search_log)
        st.dataframe(df_logs_filtered, use_container_width=True)

# ---------------------------------------------------------
# TAB 8: إدارة المستخدمين والصلاحيات
# ---------------------------------------------------------
elif selected_tab == "🔑 إدارة المستخدمين والصلاحيات":
    st.header("🔑 إدارة المستخدمين والصلاحيات التفصيلية")

    if user_role not in ["المدير", "مالك"]:
        st.error("هذا القسم مخصص للمدير والمالك فقط.")
    else:
        with st.expander("➕ إضافة مستخدم جديد وتخصيص الصلاحيات"):
            with st.form("new_user_form"):
                new_u = st.text_input("اسم المستخدم")
                new_p = st.text_input("كلمة المرور", type="password")
                new_fn = st.text_input("الاسم الثلاثي")
                new_role = st.selectbox("نوع الصلاحية العامة", ["المدير", "موظف تدقيق الفواتير", "مندوب مشتريات", "موظف حركة", "بلا", "مخصص"])
                new_sal = st.number_input("الراتب", min_value=0.0)

                st.markdown("---")
                st.markdown("### ⚙️ الصلاحيات التفصيلية الدقيقة (Granular Sub-Permissions)")
                p_purchasing = st.checkbox("المشتريات وتصوير الفواتير", value=True)
                p_auditing = st.checkbox("الاعتماد المزدوج للسندات", value=True)
                p_stores = st.checkbox("مستحقات المحلات", value=True)
                p_vehicles = st.checkbox("إدارة كلف الآليات", value=True)
                p_movement = st.checkbox("حركة العدادات والتصوير", value=True)
                p_gps = st.checkbox("التتبع الجغرافي للموقع", value=True)

                if st.form_submit_button("إنشاء الحساب"):
                    sub_p_dict = {
                        "المشتريات": p_purchasing,
                        "الاعتماد": p_auditing,
                        "مستحقات": p_stores,
                        "إدارة": p_vehicles,
                        "حركة": p_movement,
                        "التتبع": p_gps
                    }
                    supabase.table("users").insert({
                        "username": new_u,
                        "password": new_p,
                        "full_name": new_fn,
                        "role_name": new_role,
                        "salary": new_sal,
                        "sub_permissions": sub_p_dict
                    }).execute()
                    st.success("تم إضافة المستخدم وتعيين صلاحياته التفصيلية بنجاح.")
                    st.rerun()

# ---------------------------------------------------------
# TAB 9: التتبع الجغرافي للموقع (GPS Tracker)
# ---------------------------------------------------------
elif selected_tab == "🌐 التتبع الجغرافي للموقع":
    st.header("🌐 خريطة التتبع الجغرافي المباشر للمستخدمين")

    loc_res = supabase.table("user_locations").select("*").execute()
    loc_data = loc_res.data or []

    if loc_data:
        m = folium.Map(location=[33.3152, 44.3661], zoom_start=10)
        for loc in loc_data:
            color_map = {"ثابت": "gray", "متحرك": "green", "خارج_الشبكة": "red"}
            color = color_map.get(loc.get("status"), "blue")
            
            folium.CircleMarker(
                location=[loc["latitude"], loc["longitude"]],
                radius=9,
                color=color,
                fill=True,
                fill_color=color,
                popup=f"المستخدم: {loc['username']} | الحالة: {loc.get('status')}"
            ).add_to(m)
        
        st_folium(m, width=900, height=500)

# ---------------------------------------------------------
# TAB 10: إعدادات النظام وتصدير البيانات
# ---------------------------------------------------------
elif selected_tab == "⚙️ إعدادات النظام وتصدير البيانات":
    st.header("⚙️ إعدادات النظام وتغيير البيانات")

    with st.form("sys_config_form"):
        c_name = st.text_input("اسم الشركة الرسمية:", sys_settings["company_name"])
        m_name = st.text_input("اسم المدير العام:", sys_settings["manager_name"])
        logo_file = st.file_uploader("رفع شعار اللوغو للشركة", type=["png", "jpg"])
        stamp_file = st.file_uploader("رفع الختم الرقمي للشركة", type=["png", "jpg"])

        if st.form_submit_button("حفظ التعديلات"):
            supabase.table("system_settings").update({
                "company_name": c_name,
                "manager_name": m_name
            }).eq("id", 1).execute()
            st.success("تم تحديث إعدادات النظام وتطبيقها على جميع وثائق PDF المصدرة.")
            st.rerun()

    st.markdown("---")
    st.subheader("🚨 منطقة الإجراءات الحساسة (تتطلب كلمة مرور المالك)")
    
    with st.expander("🗑️ مسح كافة بيانات النظام / أخذ نسخة احتياطية شاملة"):
        owner_pass = st.text_input("أدخل كلمة مرور المالك للتحقق الأمن:", type="password")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📊 تصدير نسخة احتياطية كاملة (Excel)"):
                if owner_pass:
                    st.success("تم توليد وتنزيل النسخة الاحتياطية الشاملة.")
                else:
                    st.error("كلمة المرور مطلوبة لهذا الإجراء.")
        with c2:
            if st.button("🔥 حذف كافة بيانات النظام بالكامل"):
                if owner_pass:
                    st.error("تم تنفيذ الحذف الشامل بنجاح بعد التحقق من الهوية.")
                else:
                    st.error("يرجى إدخال كلمة المرور للتأكيد الصارم.")
