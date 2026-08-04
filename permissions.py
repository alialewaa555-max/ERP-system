# ==============================================================================
# Project: Suleiman ERP
# File: permissions.py
# Purpose: فحص الصلاحيات الدقيقة (Granular) لكل مستخدم - لا قوالب جاهزة،
# كل مستخدم/دور له شجرة صلاحيات مخصصة يبنيها المالك بنفسه من شاشة RBAC
# ==============================================================================

import json
import streamlit as st
from config import PERMISSION_TREE, OWNER_ROLE_NAME, default_permissions_all_true


def get_current_permissions() -> dict:
    """إرجاع شجرة صلاحيات المستخدم الحالي المسجل دخوله."""
    user = st.session_state.get("user")
    if not user:
        return {}
    if user.get("role") == OWNER_ROLE_NAME:
        return default_permissions_all_true()
    raw = user.get("permissions")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    if isinstance(raw, dict):
        return raw
    return {}


def can(module: str, child: str = "access") -> bool:
    """
    فحص دقيق: هل يملك المستخدم الحالي صلاحية <child> ضمن الموديول <module>؟
    مثال: can("movement", "capture_photo")
    """
    user = st.session_state.get("user")
    if not user:
        return False
    if user.get("role") == OWNER_ROLE_NAME:
        return True
    perms = get_current_permissions()
    module_perms = perms.get(module, {})
    return bool(module_perms.get(child, False))


def can_access_module(module: str) -> bool:
    return can(module, "access")


def visible_menu_keys() -> list:
    """قائمة الموديولات التي يحق للمستخدم الحالي رؤيتها في القائمة الجانبية."""
    keys = []
    for module in PERMISSION_TREE.keys():
        if can_access_module(module):
            keys.append(module)
    return keys


def require(module: str, child: str = "access"):
    """يوقف تنفيذ الصفحة ويعرض رسالة رفض إن لم تتوفر الصلاحية."""
    if not can(module, child):
        st.error("🚫 لا تملك الصلاحية الكافية للقيام بهذا الإجراء.")
        st.stop()
