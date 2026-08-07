# ==============================================================================
# Project: Suleiman ERP
# File: db.py
# Purpose: طبقة الوصول لقاعدة بيانات Supabase (اتصال + عمليات CRUD لكل جدول)
# كل الجداول موصوفة في supabase_schema.sql
# ==============================================================================

import datetime
import uuid
import streamlit as st

try:
    from supabase import create_client
except ImportError:
    create_client = None


# ------------------------------------------------------------------------------
# الاتصال بـ Supabase
# ------------------------------------------------------------------------------
@st.cache_resource
def init_supabase():
    """الاتصال الآمن بقاعدة بيانات Supabase باستخدام مفاتيح Secrets."""
    if create_client is None:
        return None
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        try:
            return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        except Exception:
            return None
    return None


def get_client():
    return init_supabase()


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_id(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:10].upper()}"


# ------------------------------------------------------------------------------
# تخزين الصور (Supabase Storage)
# البكتات المطلوبة: invoices (صور الفواتير), branding (شعار/ختم الشركة)
# ------------------------------------------------------------------------------
def upload_image(bucket: str, file_bytes: bytes, filename: str, content_type: str = "image/jpeg", subfolder: str = ""):
    """رفع صورة إلى Supabase Storage وإرجاع الرابط العام.
    subfolder: مجلد فرعي اختياري داخل نفس الـ bucket (مثلاً 'odometers')
    يُستخدم لتوفير عدد الـ buckets المحدود على الخطط المجانية بدل إنشاء
    bucket منفصل لكل نوع صور."""
    client = get_client()
    if not client:
        st.error("❌ لا يوجد اتصال بقاعدة البيانات (تحقق من SUPABASE_URL/SUPABASE_KEY).")
        return None
    try:
        prefix = f"{subfolder}/" if subfolder else ""
        path = f"{prefix}{datetime.date.today()}/{new_id()}_{filename}"
        client.storage.from_(bucket).upload(
            path, file_bytes, {"content-type": content_type}
        )
        return client.storage.from_(bucket).get_public_url(path)
    except Exception as e:
        st.error(f"❌ فشل رفع الصورة إلى باكت '{bucket}': {type(e).__name__}: {e}")
        return None


# ------------------------------------------------------------------------------
# جدول المستخدمين (users)
# ------------------------------------------------------------------------------
def fetch_users():
    client = get_client()
    if not client:
        return []
    try:
        res = client.table("users").select("*").order("created_at").execute()
        return res.data or []
    except Exception:
        return []


def find_user_by_username(username: str):
    client = get_client()
    if not client:
        return None
    try:
        res = client.table("users").select("*").eq("username", username).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def insert_user(record: dict):
    client = get_client()
    if not client:
        return False, "لا يوجد اتصال بقاعدة البيانات"
    try:
        record.setdefault("id", new_id("USR-"))
        record.setdefault("created_at", now_str())
        client.table("users").insert(record).execute()
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def update_user(username: str, fields: dict):
    client = get_client()
    if not client:
        return False
    try:
        client.table("users").update(fields).eq("username", username).execute()
        return True
    except Exception:
        return False


def delete_user(username: str):
    client = get_client()
    if not client:
        return False
    try:
        client.table("users").delete().eq("username", username).execute()
        return True
    except Exception:
        return False


# ------------------------------------------------------------------------------
# جلسات الدخول الدائمة (sessions) - لبقاء المستخدم مسجلاً حتى يخرج يدوياً
# ------------------------------------------------------------------------------
def create_session_token(username: str) -> str:
    client = get_client()
    token = uuid.uuid4().hex
    if client:
        try:
            client.table("sessions").insert({
                "token": token,
                "username": username,
                "created_at": now_str(),
            }).execute()
        except Exception:
            pass
    return token


def get_session_username(token: str):
    client = get_client()
    if not client or not token:
        return None
    try:
        res = client.table("sessions").select("*").eq("token", token).execute()
        if res.data:
            return res.data[0]["username"]
        return None
    except Exception:
        return None


def delete_session_token(token: str):
    client = get_client()
    if not client or not token:
        return
    try:
        client.table("sessions").delete().eq("token", token).execute()
    except Exception:
        pass


# ------------------------------------------------------------------------------
# جدول الآليات (fleet)
# ------------------------------------------------------------------------------
def fetch_fleet():
    client = get_client()
    if not client:
        return []
    try:
        res = client.table("fleet").select("*").order("code").execute()
        return res.data or []
    except Exception:
        return []


def insert_machine(record: dict):
    client = get_client()
    if not client:
        st.error("❌ لا يوجد اتصال بقاعدة البيانات.")
        return False
    try:
        record.setdefault("id", new_id("MCH-"))
        record.setdefault("created_at", now_str())
        client.table("fleet").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"❌ فشل إضافة الآلية: {type(e).__name__}: {e}")
        return False


def update_machine(code: str, fields: dict):
    client = get_client()
    if not client:
        return False
    try:
        client.table("fleet").update(fields).eq("code", code).execute()
        return True
    except Exception:
        return False


def delete_machine(code: str):
    client = get_client()
    if not client:
        return False
    try:
        client.table("fleet").delete().eq("code", code).execute()
        return True
    except Exception:
        return False


# ------------------------------------------------------------------------------
# جدول الموظفين (staff)
# ------------------------------------------------------------------------------
def fetch_staff():
    client = get_client()
    if not client:
        return []
    try:
        res = client.table("staff").select("*").order("emp_id").execute()
        return res.data or []
    except Exception:
        return []


def insert_staff(record: dict):
    client = get_client()
    if not client:
        st.error("❌ لا يوجد اتصال بقاعدة البيانات.")
        return False
    try:
        record.setdefault("id", new_id("STF-"))
        record.setdefault("created_at", now_str())
        client.table("staff").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"❌ فشل إضافة الموظف: {type(e).__name__}: {e}")
        return False


def update_staff(emp_id: str, fields: dict):
    client = get_client()
    if not client:
        return False
    try:
        client.table("staff").update(fields).eq("emp_id", emp_id).execute()
        return True
    except Exception:
        return False


def delete_staff(emp_id: str):
    client = get_client()
    if not client:
        return False
    try:
        client.table("staff").delete().eq("emp_id", emp_id).execute()
        return True
    except Exception:
        return False


def bulk_update_staff(emp_ids: list, fields: dict):
    client = get_client()
    if not client:
        return False
    try:
        for emp_id in emp_ids:
            client.table("staff").update(fields).eq("emp_id", emp_id).execute()
        return True
    except Exception:
        return False


# ------------------------------------------------------------------------------
# جدول السندات المالية / الفواتير (vouchers)
# ------------------------------------------------------------------------------
def fetch_vouchers():
    client = get_client()
    if not client:
        return []
    try:
        res = client.table("vouchers").select("*").order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []


def insert_voucher(record: dict):
    client = get_client()
    if not client:
        return False, None
    try:
        vid = record.get("id") or new_id("VOUCH-")
        record["id"] = vid
        record.setdefault("created_at", now_str())
        client.table("vouchers").insert(record).execute()
        return True, vid
    except Exception as e:
        st.error(f"خطأ أثناء حفظ السند: {e}")
        return False, None


def update_voucher(voucher_id: str, fields: dict):
    client = get_client()
    if not client:
        return False
    try:
        client.table("vouchers").update(fields).eq("id", voucher_id).execute()
        return True
    except Exception:
        return False


def delete_voucher(voucher_id: str):
    client = get_client()
    if not client:
        return False
    try:
        client.table("vouchers").delete().eq("id", voucher_id).execute()
        return True
    except Exception:
        return False


# ------------------------------------------------------------------------------
# جدول سجل التدقيق (audit_logs)
# ------------------------------------------------------------------------------
def log_action(action: str, details: str):
    """تسجيل أي عملية في سجل التدقيق الأمني."""
    client = get_client()
    user = st.session_state.get("user")
    user_name = user["name"] if user else "النظام"
    record = {
        "id": new_id("LOG-"),
        "username": user["username"] if user else "system",
        "full_name": user_name,
        "action": action,
        "details": details,
        "timestamp": now_str(),
    }
    if client:
        try:
            client.table("audit_logs").insert(record).execute()
        except Exception:
            pass
    # نحتفظ بنسخة محلية في الجلسة أيضاً كاحتياط سريع للعرض الفوري
    st.session_state.setdefault("local_audit_cache", [])
    st.session_state["local_audit_cache"].insert(0, record)


def fetch_audit_logs():
    client = get_client()
    if not client:
        return st.session_state.get("local_audit_cache", [])
    try:
        res = client.table("audit_logs").select("*").order("timestamp", desc=True).limit(2000).execute()
        return res.data or []
    except Exception:
        return st.session_state.get("local_audit_cache", [])


def delete_audit_logs(ids: list):
    client = get_client()
    if not client:
        return False
    try:
        for _id in ids:
            client.table("audit_logs").delete().eq("id", _id).execute()
        return True
    except Exception:
        return False


# ------------------------------------------------------------------------------
# جدول الإعدادات (settings) - صف واحد ثابت id=1
# ------------------------------------------------------------------------------
def fetch_settings():
    client = get_client()
    if not client:
        return None
    try:
        res = client.table("settings").select("*").eq("id", 1).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def upsert_settings(fields: dict):
    client = get_client()
    if not client:
        st.error("❌ لا يوجد اتصال بقاعدة البيانات (تحقق من SUPABASE_URL/SUPABASE_KEY).")
        return False
    try:
        fields["id"] = 1
        client.table("settings").upsert(fields).execute()
        return True
    except Exception as e:
        st.error(f"❌ فشل حفظ الإعدادات: {type(e).__name__}: {e}")
        return False


# ------------------------------------------------------------------------------
# جدول النفقات العامة (expenses)
# ------------------------------------------------------------------------------
def fetch_expenses():
    client = get_client()
    if not client:
        return []
    try:
        res = client.table("expenses").select("*").order("expense_date", desc=True).execute()
        return res.data or []
    except Exception:
        return []


def insert_expense(record: dict):
    client = get_client()
    if not client:
        st.error("❌ لا يوجد اتصال بقاعدة البيانات.")
        return False
    try:
        record.setdefault("id", new_id("EXP-"))
        record.setdefault("created_at", now_str())
        client.table("expenses").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"❌ فشل إضافة النفقة: {type(e).__name__}: {e}")
        return False


def update_expense(expense_id: str, fields: dict):
    client = get_client()
    if not client:
        return False
    try:
        client.table("expenses").update(fields).eq("id", expense_id).execute()
        return True
    except Exception:
        return False


def delete_expense(expense_id: str):
    client = get_client()
    if not client:
        return False
    try:
        client.table("expenses").delete().eq("id", expense_id).execute()
        return True
    except Exception:
        return False


# ------------------------------------------------------------------------------
# جدول مواقع المستخدمين (locations) - للتتبع الجغرافي
# ------------------------------------------------------------------------------
def upsert_location(username: str, lat: float, lon: float, status: str):
    client = get_client()
    if not client:
        return False
    try:
        client.table("locations").upsert({
            "username": username,
            "lat": lat,
            "lon": lon,
            "status": status,
            "updated_at": now_str(),
        }).execute()
        return True
    except Exception:
        return False


def fetch_locations():
    client = get_client()
    if not client:
        return []
    try:
        res = client.table("locations").select("*").execute()
        return res.data or []
    except Exception:
        return []
