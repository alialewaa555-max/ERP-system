# ==============================================================================
# Project: Suleiman ERP - Enterprise Fleet & Financial Management System
# File: app.py  (نقطة الدخول الرئيسية)
#
# البيئة: Streamlit Community Cloud (أو أي استضافة Streamlit سحابية) +
# Supabase (قاعدة بيانات PostgreSQL + Storage للصور) - لا يوجد أي تخزين
# محلي دائم؛ كل البيانات والصور والجلسات تُدار عبر Supabase، وكل ملفات
# PDF/Excel تُبنى في الذاكرة وتُسلَّم مباشرة للمستخدم دون الكتابة على القرص،
# لأن نظام ملفات Streamlit Cloud مؤقت (Ephemeral) ويُصفَّر عند كل إعادة نشر.
# ==============================================================================

import streamlit as st

import auth
import db
from config import TRANSLATIONS, LANGUAGES, THEMES, DEFAULT_SETTINGS
from permissions import visible_menu_keys, can_access_module
from modules import expenses, movement, purchases, staff, vendors, vouchers
st.set_page_config(
    page_title="Suleiman ERP",
    page_icon="🚜",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------------------
# تهيئة الجلسة
# ------------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state["user"] = None
if "lang" not in st.session_state:
    st.session_state["lang"] = "AR"
if "active_module" not in st.session_state:
    st.session_state["active_module"] = "dashboard"

# محاولة استعادة الجلسة من كوكي المتصفح الدائم (يبقى المستخدم مسجلاً حتى يخرج يدوياً)
auth.try_restore_session()


# ------------------------------------------------------------------------------
# تطبيق الثيم (ليلي / نهاري) على كامل الواجهة عبر CSS
# ------------------------------------------------------------------------------
def apply_theme():
    settings = db.fetch_settings() or DEFAULT_SETTINGS
    theme_name = settings.get("theme", "ليلي")
    theme = THEMES.get(theme_name, THEMES["ليلي"])
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {theme['bg']};
            color: {theme['text']};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {theme['sidebar_bg']};
            min-width: 230px !important;
            max-width: 340px !important;
        }}
        h1, h2, h3 {{
            color: {theme['heading']};
        }}
        div[data-testid="stMetric"], div[data-testid="stExpander"], .stDataFrame {{
            background-color: {theme['card_bg']};
            border: 1px solid {theme['card_border']};
            border-radius: 10px;
        }}
        .stButton>button {{
            border-radius: 8px;
        }}
        html, body, [class*="css"] {{
            direction: rtl;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    return settings


settings = apply_theme()
T = TRANSLATIONS[st.session_state["lang"]]


# ------------------------------------------------------------------------------
# شاشة تسجيل الدخول
# ------------------------------------------------------------------------------
def render_login():
    st.markdown(
        f"<h1 style='text-align:center'>🚜 {settings.get('company_name', 'Suleiman ERP')}</h1>",
        unsafe_allow_html=True,
    )
    if settings.get("manager_name"):
        st.markdown(
            f"<p style='text-align:center;opacity:.7'>نظام إدارة الأسطول والمالية — بإدارة {settings.get('manager_name')}</p>",
            unsafe_allow_html=True,
        )

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.form("login_form"):
            st.subheader("🔐 تسجيل الدخول")
            username = st.text_input("اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password")
            submitted = st.form_submit_button("دخول 🚀", use_container_width=True, type="primary")

        if submitted:
            ok, err = auth.login(username, password)
            if ok:
                st.success("✅ تم تسجيل الدخول بنجاح.")
                st.rerun()
            else:
                st.error(err)

        if not db.get_client():
            st.warning(
                "⚠️ لم يتم العثور على مفاتيح الاتصال بـ Supabase. أضف "
                "`SUPABASE_URL` و `SUPABASE_KEY` ضمن Secrets في إعدادات "
                "تطبيق Streamlit Cloud الخاص بك."
            )


# ------------------------------------------------------------------------------
# القائمة الجانبية + التوجيه بين الموديولات
# ------------------------------------------------------------------------------
MODULE_RENDERERS = {
    "dashboard": dashboard.render,
    "purchases": purchases.render,
    "vouchers": vouchers.render,
    "vendors": vendors.render,
    "fleet": fleet.render,
    "expenses": expenses.render,
    "movement": movement.render,
    "staff": staff.render,
    "audit": audit.render,
    "rbac": users_rbac.render,
    "tracking": tracking.render,
    "settings": settings_module.render,
}


def render_sidebar():
    user = st.session_state["user"]
    with st.sidebar:
        if settings.get("logo_url"):
            st.image(settings["logo_url"], use_container_width=True)
        st.markdown(f"### 👋 {T['welcome']}, {user['name']}")
        st.caption(f"{T['role']}: {user['role']}")

        st.session_state["lang"] = st.selectbox(
            T["language"], LANGUAGES, index=LANGUAGES.index(st.session_state["lang"])
        )

        st.markdown("---")
        st.markdown(f"#### {T['main_menu']}")

        menu_keys = visible_menu_keys()
        for key in menu_keys:
            label = T.get(key, key)
            btn_type = "primary" if st.session_state["active_module"] == key else "secondary"
            if st.button(label, key=f"nav_{key}", use_container_width=True, type=btn_type):
                st.session_state["active_module"] = key
                st.rerun()

        st.markdown("---")
        st.markdown("---")
        with st.expander("🔧 معلومات تشخيصية (اضغط لعرضها)"):
            st.write(f"**اسم المستخدم (username):** `{user.get('username')}`")
            st.write(f"**الدور المكتوب بالنص (role):** `{user.get('role')}`")
            st.write(f"**علم المالك المطلق (is_owner):** `{user.get('is_owner')}`")
            st.write("**صلاحيات هذا الحساب كما قرأها السيرفر الآن من قاعدة البيانات:**")
            st.json(user.get("permissions") or {})
            st.caption(
                "إذا is_owner طالعة False وانت متأكد إنك عدّلتها true بقاعدة البيانات، "
                "فمعناها التحديث البرمجي (الكود) اللي ينفّذ هلق مو آخر نسخة رفعتها. "
                "إذا is_owner طالعة True والصلاحيات لسا فاضية {} - هذا طبيعي وصحيح، "
                "لأن is_owner لحاله كافي لتفعيل كل شي بغض النظر عن هاد الجدول."
            )

        if st.button(T["logout"], use_container_width=True):
            auth.logout()
            st.rerun()


# ------------------------------------------------------------------------------
# نقطة التشغيل الرئيسية
# ------------------------------------------------------------------------------
def main():
    if not st.session_state["user"]:
        render_login()
        return

    # بث موقع المستخدم الحالي بصمت (لخدمة التتبع الجغرافي) إن كان النظام مفعّلاً
    try:
        tracking.broadcast_current_user_location()
    except Exception:
        pass

    render_sidebar()

    with st.sidebar:
        with st.expander("🔧 معلومات تشخيصية (مؤقت)"):
            st.caption("VERSION-MARKER: DEBUG-BUILD-1")
            st.json(st.session_state.get("user"))
            st.write("can(fleet, add):", can_access_module("fleet"))
            from permissions import can as _can
            st.write("fleet.add:", _can("fleet", "add"))
            st.write("staff.add:", _can("staff", "add"))
            st.write("purchases.select_machine:", _can("purchases", "select_machine"))

    active = st.session_state["active_module"]
    if not can_access_module(active):
        visible = visible_menu_keys()
        active = visible[0] if visible else None
        st.session_state["active_module"] = active

    if active and active in MODULE_RENDERERS:
        MODULE_RENDERERS[active]()
    else:
        st.warning("🚫 لا تملك صلاحية الوصول لأي قسم في النظام حالياً. راجع المالك لتخصيص صلاحياتك.")


if __name__ == "__main__":
    main()
