# ==============================================================================
# modules/settings.py - إعدادات النظام: الهوية البصرية، الثيم، كلمة المرور،
# النسخ الاحتياطي الشامل، والحذف الشامل (كلاهما محمي بكلمة مرور المالك)
# ==============================================================================

import pandas as pd
import streamlit as st

import db
import pdf_utils
import excel_utils
from auth import hash_password, verify_password
from ui_helpers import confirm_action, safe_pdf_export_button
from permissions import can, require
from config import THEMES, OWNER_ROLE_NAME, STORAGE_BUCKET


def render():
    require("settings", "access")
    st.header("⚙️ إعدادات النظام وتصدير البيانات")

    settings = db.fetch_settings() or {}
    user = st.session_state.get("user", {})

    tabs = st.tabs(["🎨 الهوية البصرية والثيم", "🔑 حسابي", "💾 نسخة احتياطية شاملة", "🗑️ حذف شامل"])

    # -------------------- الهوية البصرية --------------------
    with tabs[0]:
        if not can("settings", "branding"):
            st.info("لا تملك صلاحية تعديل الهوية البصرية.")
        else:
            company_name = st.text_input("🏢 اسم الشركة", value=settings.get("company_name", ""))
            manager_name = st.text_input("👤 اسم المدير (يظهر بدل الاسم الافتراضي)", value=settings.get("manager_name", ""))

            logo_file = st.file_uploader("📌 شعار الشركة (Logo)", type=["png", "jpg", "jpeg"])
            stamp_file = st.file_uploader("🔏 صورة الختم الرقمي", type=["png", "jpg", "jpeg"])

            if settings.get("logo_url"):
                st.image(settings["logo_url"], caption="الشعار الحالي", width=150)
            if settings.get("stamp_url"):
                st.image(settings["stamp_url"], caption="الختم الحالي", width=150)

            if st.button("💾 حفظ الهوية البصرية", type="primary"):
                fields = {"company_name": company_name, "manager_name": manager_name}
                if logo_file:
                    url = db.upload_image(STORAGE_BUCKET, logo_file.getvalue(), "logo.png", logo_file.type, subfolder="branding")
                    if url:
                        fields["logo_url"] = url
                if stamp_file:
                    url = db.upload_image(STORAGE_BUCKET, stamp_file.getvalue(), "stamp.png", stamp_file.type, subfolder="branding")
                    if url:
                        fields["stamp_url"] = url
                ok = db.upsert_settings(fields)
                if ok:
                    db.log_action("تعديل إعدادات الهوية", "تحديث اسم الشركة / الشعار / الختم")
                    st.success("✅ تم الحفظ. ستظهر هذه العناصر تلقائياً في كل تقارير PDF.")
                    st.rerun()

        if can("settings", "theme"):
            st.markdown("---")
            current_theme = settings.get("theme", "ليلي")
            theme = st.radio("🌗 ثيم النظام", list(THEMES.keys()), index=list(THEMES.keys()).index(current_theme) if current_theme in THEMES else 0, horizontal=True)
            if st.button("💾 تطبيق الثيم"):
                db.upsert_settings({"theme": theme})
                db.log_action("تغيير الثيم", f"تغيير الثيم إلى {theme}")
                st.success("✅ تم التطبيق، أعد تحميل الصفحة لرؤية التغيير بالكامل.")
                st.rerun()

    # -------------------- حسابي --------------------
    with tabs[1]:
        if not can("settings", "change_credentials"):
            st.info("لا تملك صلاحية تغيير بيانات حسابك من هنا.")
        else:
            st.subheader("🔑 تغيير كلمة المرور / اسم المستخدم")
            current_pw = st.text_input("كلمة المرور الحالية", type="password")
            new_username = st.text_input("اسم مستخدم جديد (اختياري)")
            new_pw = st.text_input("كلمة مرور جديدة (اختياري)", type="password")
            if st.button("💾 حفظ التغييرات", type="primary"):
                user_row = db.find_user_by_username(user["username"])
                stored_pw = user_row.get("password_hash") or user_row.get("password")
                if not verify_password(current_pw, stored_pw):
                    st.error("❌ كلمة المرور الحالية غير صحيحة.")
                else:
                    fields = {}
                    if new_pw:
                        fields["password_hash"] = hash_password(new_pw)
                    if new_username and new_username.strip() != user["username"]:
                        if db.find_user_by_username(new_username.strip()):
                            st.error("❌ اسم المستخدم الجديد مستخدم مسبقاً.")
                            return
                        fields["username"] = new_username.strip()
                    if fields:
                        db.update_user(user["username"], fields)
                        db.log_action("تحديث بيانات حساب", "المستخدم غيّر بيانات حسابه الخاص")
                        st.success("✅ تم التحديث. سجّل الخروج والدخول من جديد إن غيّرت اسم المستخدم.")

    # -------------------- نسخة احتياطية شاملة --------------------
    with tabs[2]:
        if not can("settings", "full_export"):
            st.info("لا تملك صلاحية أخذ نسخة احتياطية شاملة.")
        else:
            st.warning("⚠️ يتطلب هذا الإجراء كلمة مرور المالك للتأكيد.")
            owner_pw = st.text_input("🔑 كلمة مرور المالك", type="password", key="backup_owner_pw")
            if st.button("💾 توليد نسخة احتياطية شاملة الآن", type="primary"):
                owner_row = _find_owner_row()
                stored_pw = owner_row.get("password_hash") if owner_row else None
                if not owner_row or not verify_password(owner_pw, stored_pw):
                    st.error("❌ كلمة مرور المالك غير صحيحة.")
                else:
                    sheets = {
                        "الآليات": pd.DataFrame(db.fetch_fleet()),
                        "الموظفين": pd.DataFrame(db.fetch_staff()),
                        "السندات": pd.DataFrame(db.fetch_vouchers()),
                        "المستخدمين": pd.DataFrame(db.fetch_users()),
                        "سجل التدقيق": pd.DataFrame(db.fetch_audit_logs()),
                    }
                    excel_bytes = excel_utils.multi_sheet_excel_bytes(sheets)
                    summary = {name: len(df) for name, df in sheets.items()}

                    db.log_action("نسخة احتياطية شاملة", "تم توليد نسخة احتياطية كاملة من كل بيانات النظام")

                    c1, c2 = st.columns(2)
                    c1.download_button("📊 تحميل النسخة الاحتياطية (Excel)", excel_bytes, file_name="full_backup.xlsx")
                    try:
                        pdf_bytes = pdf_utils.full_backup_pdf(settings, summary)
                        c2.download_button("📄 تحميل ملخص PDF", pdf_bytes, file_name="full_backup_summary.pdf")
                    except pdf_utils.ArabicFontMissingError as e:
                        c2.error(str(e))
                    st.success("✅ النسخة الاحتياطية جاهزة للتحميل أعلاه.")

    # -------------------- حذف شامل --------------------
    with tabs[3]:
        if not can("settings", "full_delete"):
            st.info("لا تملك صلاحية الحذف الشامل.")
        else:
            st.error("🚨 هذا الإجراء يحذف كل بيانات النظام (آليات، موظفين، سندات، مستخدمين عدا المالك) نهائياً ولا رجعة عنه.")
            owner_row = _find_owner_row()
            stored_pw = owner_row.get("password_hash") if owner_row else None
            if confirm_action("حذف شامل لكل بيانات النظام", key="full_delete_action", danger=True, require_password=None):
                owner_pw = st.text_input("🔑 كلمة مرور المالك للتأكيد النهائي", type="password", key="final_delete_pw")
                if st.button("🚨 تنفيذ الحذف الشامل نهائياً", key="final_delete_btn"):
                    if not owner_row or not verify_password(owner_pw, stored_pw):
                        st.error("❌ كلمة مرور المالك غير صحيحة، تم إلغاء العملية.")
                    else:
                        for m in db.fetch_fleet():
                            db.delete_machine(m["code"])
                        for s in db.fetch_staff():
                            db.delete_staff(s["emp_id"])
                        for v in db.fetch_vouchers():
                            db.delete_voucher(v["id"])
                        for u in db.fetch_users():
                            if not u.get("is_owner"):
                                db.delete_user(u["username"])
                        db.log_action("حذف شامل", "تم حذف كل بيانات النظام بأمر مباشر من المالك")
                        st.success("✅ تم تنفيذ الحذف الشامل.")
                        st.rerun()


def _find_owner_row():
    for u in db.fetch_users():
        if u.get("is_owner"):
            return u
    return None
