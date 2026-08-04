# ==============================================================================
# Project: Suleiman ERP
# File: auth.py
# Purpose: تسجيل الدخول / الخروج + إبقاء الجلسة محفوظة عبر الأجهزة
# باستخدام كوكيز المتصفح (extra_streamlit_components) حتى يقوم المستخدم
# بتسجيل الخروج يدوياً - لا تنتهي الجلسة بإغلاق المتصفح أو تحديث الصفحة.
# ==============================================================================

import hashlib
import streamlit as st

import db

COOKIE_NAME = "suleiman_erp_session"

try:
    import extra_streamlit_components as stx

    @st.cache_resource
    def _get_cookie_manager():
        return stx.CookieManager(key="suleiman_erp_cookie_manager")

    COOKIES_AVAILABLE = True
except ImportError:
    COOKIES_AVAILABLE = False

    def _get_cookie_manager():
        return None


def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_password(raw: str, stored: str) -> bool:
    """
    يدعم كلمتي المرور: المشفرة (sha256) والقديمة النصية الصريحة توافقاً مع
    قواعد البيانات المُنشأة سابقاً. يُنصح بترحيل كل الكلمات إلى SHA-256.
    """
    if stored is None:
        return False
    stored = str(stored).strip()
    raw = str(raw).strip()
    if stored == hash_password(raw):
        return True
    # توافق رجعي مع كلمات مرور نصية غير مشفرة
    return stored == raw


def _cookie_get():
    if not COOKIES_AVAILABLE:
        return None
    cm = _get_cookie_manager()
    try:
        return cm.get(COOKIE_NAME)
    except Exception:
        return None


def _cookie_set(token: str):
    if not COOKIES_AVAILABLE:
        return
    cm = _get_cookie_manager()
    import datetime
    try:
        cm.set(
            COOKIE_NAME,
            token,
            expires_at=datetime.datetime.now() + datetime.timedelta(days=365),
            key="set_session_cookie",
        )
    except Exception:
        pass


def _cookie_delete():
    if not COOKIES_AVAILABLE:
        return
    cm = _get_cookie_manager()
    try:
        cm.delete(COOKIE_NAME, key="delete_session_cookie")
    except Exception:
        pass


def try_restore_session():
    """يحاول استعادة جلسة المستخدم من الكوكيز عند فتح التطبيق من جديد."""
    if st.session_state.get("user"):
        return
    token = _cookie_get()
    if not token:
        return
    username = db.get_session_username(token)
    if not username:
        return
    user_row = db.find_user_by_username(username)
    if not user_row:
        return
    if user_row.get("status") == "محظور":
        return
    st.session_state["user"] = {
        "name": user_row.get("full_name", user_row.get("username")),
        "username": user_row.get("username"),
        "role": user_row.get("role", ""),
        "permissions": user_row.get("permissions", {}),
    }
    st.session_state["session_token"] = token


def login(username: str, password: str):
    """
    محاولة تسجيل دخول. يرجع (نجاح: bool, رسالة الخطأ أو None).
    عند النجاح: يحفظ المستخدم في session_state + كوكي دائم.
    """
    username = (username or "").strip()
    password = (password or "").strip()

    if not username or not password:
        return False, "⚠️ يرجى إدخال اسم المستخدم وكلمة المرور."

    client = db.get_client()
    if not client:
        return False, "❌ لم يتم العثور على SUPABASE_URL أو SUPABASE_KEY في إعدادات Secrets."

    try:
        user_row = db.find_user_by_username(username)
    except Exception as e:
        return False, f"❌ خطأ من Supabase: {e}"

    if not user_row:
        return False, f"❌ لم يتم العثور على اسم المستخدم '{username}'."

    stored_pw = user_row.get("password_hash") or user_row.get("password")
    if not verify_password(password, stored_pw):
        return False, "❌ كلمة المرور غير صحيحة."

    if user_row.get("status") == "محظور":
        return False, "❌ هذا الحساب محظور. راجع الإدارة."

    st.session_state["user"] = {
        "name": user_row.get("full_name", user_row.get("username")),
        "username": user_row.get("username"),
        "role": user_row.get("role", ""),
        "permissions": user_row.get("permissions", {}),
    }

    token = db.create_session_token(username)
    st.session_state["session_token"] = token
    _cookie_set(token)

    db.log_action("تسجيل دخول", f"تم دخول المستخدم {username}")
    return True, None


def logout():
    user = st.session_state.get("user")
    token = st.session_state.get("session_token")
    if user:
        db.log_action("تسجيل خروج", f"خرج المستخدم {user['username']}")
    if token:
        db.delete_session_token(token)
    _cookie_delete()
    st.session_state["user"] = None
    st.session_state["session_token"] = None
