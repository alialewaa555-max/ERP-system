# ==============================================================================
# modules/users_rbac.py - إدارة المستخدمين والصلاحيات
# لا قوالب جاهزة: المالك يكتب اسم الصلاحية بنفسه ويحدد كل صلاحية فرعية
# دقيقة يدوياً (مثال حقيقي من طلب المالك: موظف الحركة يُمنح فقط: اختيار
# الآلية + التصوير + رفع الصورة ضمن قسم الحركة، دون بقية صلاحيات القسم
# أو الوصول لأي قسم آخر).
# ==============================================================================

import json
import pandas as pd
import streamlit as st

import db
import excel_utils
from auth import hash_password
from ui_helpers import smart_search_filter, confirm_action
from permissions import can, require
from config import PERMISSION_TREE, OWNER_ROLE_NAME, default_permissions_all_false


def _permission_editor(existing: dict, key_prefix: str) -> dict:
    """يرسم شجرة صلاحيات تفاعلية (checkboxes) ويرجع القاموس النهائي المحدد."""
    result = {}
    for module, meta in PERMISSION_TREE.items():
        with st.expander(f"📁 {meta['label']}"):
            module_perms = {}
            current_module = existing.get(module, {}) if existing else {}
            select_all = st.checkbox("تحديد كل صلاحيات هذا القسم", key=f"{key_prefix}_{module}_all")
            for child, label in meta["children"].items():
                default_val = True if select_all else bool(current_module.get(child, False))
                module_perms[child] = st.checkbox(
                    label, value=default_val, key=f"{key_prefix}_{module}_{child}"
                )
            result[module] = module_perms
    return result


def render():
    require("rbac", "access")
    st.header("🛡️ إدارة المستخدمين والصلاحيات")

    settings = db.fetch_settings() or {}
    users = db.fetch_users()
    udf = pd.DataFrame(users) if users else pd.DataFrame(columns=["username", "full_name", "role", "status"])

    tab_list, tab_add = st.tabs(["📋 قائمة المستخدمين", "➕ إضافة مستخدم / تخصيص صلاحية"])

    with tab_list:
        query = st.text_input("🔍 بحث ذكي عن مستخدم بالاسم أو الرتبة")
        display_cols = [c for c in ["username", "full_name", "role", "status"] if c in udf.columns]
        filtered = smart_search_filter(udf, display_cols, query)
        st.dataframe(filtered[display_cols] if not filtered.empty else filtered, use_container_width=True, hide_index=True)

        if can("rbac", "export") and not filtered.empty:
            st.download_button(
                "📊 تصدير المستخدمين Excel",
                excel_utils.df_to_excel_bytes(filtered[display_cols], "المستخدمون"),
                file_name="users.xlsx",
            )

        if filtered.empty:
            return

        st.markdown("#### 🔎 تعديل / حذف مستخدم")
        pick = st.selectbox("اختر مستخدماً", filtered["username"].tolist())
        rec_row = filtered[filtered["username"] == pick]
        if rec_row.empty:
            return
        rec = rec_row.iloc[0].to_dict()

        if rec.get("role") == OWNER_ROLE_NAME:
            st.info("👑 هذا حساب المالك ويملك كل الصلاحيات دائماً ولا يمكن تعديل صلاحياته أو حذفه.")
            return

        if can("rbac", "edit"):
            with st.expander("✏️ تعديل بيانات المستخدم واسمه ورتبته"):
                new_full_name = st.text_input("الاسم الكامل", value=rec.get("full_name", ""), key=f"un_{pick}")
                new_role = st.text_input("اسم الصلاحية / الرتبة (اكتبها بنفسك)", value=rec.get("role", ""), key=f"ur_{pick}")
                if st.button("💾 حفظ الاسم والرتبة", key=f"usave_{pick}"):
                    db.update_user(pick, {"full_name": new_full_name, "role": new_role})
                    db.log_action("تعديل مستخدم", f"تعديل بيانات {pick}")
                    st.success("✅ تم الحفظ.")
                    st.rerun()

            with st.expander("🔑 تغيير كلمة المرور"):
                new_pw = st.text_input("كلمة مرور جديدة", type="password", key=f"upw_{pick}")
                if st.button("💾 تحديث كلمة المرور", key=f"upwsave_{pick}"):
                    if len(new_pw) < 4:
                        st.error("⚠️ كلمة المرور قصيرة جداً.")
                    else:
                        db.update_user(pick, {"password_hash": hash_password(new_pw)})
                        db.log_action("تغيير كلمة مرور مستخدم", f"تغيير كلمة مرور {pick}")
                        st.success("✅ تم التحديث.")

            with st.expander("🛡️ تخصيص شجرة الصلاحيات الدقيقة لهذا المستخدم", expanded=True):
                existing_perms = rec.get("permissions") or {}
                if isinstance(existing_perms, str):
                    try:
                        existing_perms = json.loads(existing_perms)
                    except Exception:
                        existing_perms = {}
                new_perms = _permission_editor(existing_perms, key_prefix=f"perm_{pick}")
                if st.button("💾 حفظ الصلاحيات", key=f"psave_{pick}", type="primary"):
                    db.update_user(pick, {"permissions": new_perms})
                    db.log_action("تعديل صلاحيات", f"تعديل صلاحيات المستخدم {pick}")
                    st.success("✅ تم حفظ الصلاحيات المخصصة.")
                    st.rerun()

        if can("rbac", "delete"):
            if confirm_action(f"حذف المستخدم {pick} نهائياً", key=f"udel_{pick}", danger=True):
                db.delete_user(pick)
                db.log_action("حذف مستخدم", f"حذف المستخدم {pick}")
                st.success("🗑️ تم الحذف.")
                st.rerun()

    with tab_add:
        if not can("rbac", "add"):
            st.error("لا تملك صلاحية إضافة مستخدم.")
            return

        st.markdown("##### 👤 بيانات الحساب")
        username = st.text_input("اسم المستخدم (فريد) *")
        full_name = st.text_input("الاسم الكامل الثلاثي *")
        role_name = st.text_input(
            "اسم الصلاحية / الرتبة *",
            help="اكتب اسماً وصفياً حراً مثل: مندوب مشتريات - موظف تدقيق فواتير - موظف حركة. "
                 "لا توجد قوالب جاهزة، الصلاحيات الفعلية تُحدَّد أدناه بدقة.",
        )
        password = st.text_input("كلمة المرور *", type="password")

        st.markdown("##### 🛡️ شجرة الصلاحيات الدقيقة")
        st.caption(
            "حدد بدقة ما يمكن لهذا المستخدم فعله. مثال: لإنشاء 'موظف حركة' محصور فقط "
            "بقسم الحركة والعدادات، فعّل داخل قسم (الحركة والعدادات) فقط: الدخول + اختيار "
            "الآلية + التصوير + الرفع، واترك بقية الأقسام كلها معطّلة."
        )
        new_perms = _permission_editor(default_permissions_all_false(), key_prefix="newuser")

        if st.button("➕ إنشاء الحساب", type="primary"):
            if not username or not full_name or not role_name or not password:
                st.error("⚠️ جميع الحقول المميزة بـ * إلزامية.")
            elif db.find_user_by_username(username.strip()):
                st.error("❌ اسم المستخدم موجود مسبقاً، اختر اسماً آخر.")
            else:
                ok, err = db.insert_user({
                    "username": username.strip(),
                    "full_name": full_name.strip(),
                    "role": role_name.strip(),
                    "password_hash": hash_password(password),
                    "permissions": new_perms,
                    "status": "نشط",
                })
                if ok:
                    db.log_action("إضافة مستخدم", f"إنشاء حساب جديد {username} بصلاحية {role_name}")
                    st.success(f"✅ تم إنشاء حساب '{username}' بنجاح.")
                    st.rerun()
                else:
                    st.error(f"❌ فشلت العملية: {err}")

        st.markdown("---")
        st.caption(
            "⚠️ ملاحظة أمان: أسماء المستخدمين وكلمات المرور فريدة إلزامياً على مستوى النظام "
            "(يمنعه Supabase تلقائياً عبر قيد UNIQUE على عمود username في الجدول)."
        )
