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
from permissions import visible_menu_keys, can_access_module, can

# ------------------------------------------------------------------------------
# رقم إصدار الملف - راية غير قابلة للتفويت لتأكيد وصول أي تحديث فعلياً
# للسيرفر. غيّر هالرقم بكل مرة تستبدل فيها app.py حتى تتأكد بلمحة.
# ------------------------------------------------------------------------------
BUILD_VERSION = "CHECKPOINT-BUILD-99887766"
st.error(f"🔴🔴🔴 {BUILD_VERSION} 🔴🔴🔴")

from modules import (
    dashboard, purchases, vouchers, vendors, fleet, expenses,
    movement, staff, audit, users_rbac, settings as settings_module, tracking,
)

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
        st.caption(f"🔖 {BUILD_VERSION}")
        with st.expander("🔧 معلومات تشخيصية"):
            st.write(f"**اسم المستخدم:** `{user.get('username')}`")
            st.write(f"**الدور:** `{user.get('role')}`")
            st.write(f"**is_owner:** `{user.get('is_owner')}`")
            st.write(f"**fleet.add:** `{can('fleet', 'add')}`")
            st.write(f"**staff.add:** `{can('staff', 'add')}`")
            st.write(f"**purchases.select_machine:** `{can('purchases', 'select_machine')}`")
            st.write("**كامل الصلاحيات المخزّنة:**")
            st.json(user.get("permissions") or {})

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

    try:
        tracking.broadcast_current_user_location()
    except Exception:
        pass

    render_sidebar()

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
