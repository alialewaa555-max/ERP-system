# ==============================================================================
# modules/staff.py - إدارة الموظفين والورشات
# ==============================================================================

import pandas as pd
import streamlit as st

import db
import pdf_utils
import excel_utils
from ui_helpers import smart_search_filter, confirm_action, safe_pdf_export_button
from permissions import can, require


def render():
    require("staff", "access")
    st.header("👷 إدارة الموظفين والورشات")

    settings = db.fetch_settings() or {}
    staff = db.fetch_staff()
    sdf = pd.DataFrame(staff) if staff else pd.DataFrame(columns=["emp_id", "name", "job", "salary", "status", "phone"])

    tab_list, tab_add = st.tabs(["📋 قائمة الموظفين", "➕ إضافة موظف"])

    # -------------------- تبويب: قائمة الموظفين --------------------
    with tab_list:
        query = st.text_input("🔍 بحث ذكي عن موظف بالاسم أو الوظيفة أو رقم الهاتف")
        filtered = smart_search_filter(sdf, ["emp_id", "name", "job", "phone", "status"], query)

        select_col = "✅ تحديد"
        display_df = filtered.copy()
        if can("staff", "bulk_actions") and not display_df.empty:
            display_df.insert(0, select_col, False)
            edited = st.data_editor(
                display_df, use_container_width=True, hide_index=True,
                disabled=[c for c in display_df.columns if c != select_col],
                key="staff_editor",
            )
            selected_ids = edited[edited[select_col]]["emp_id"].tolist()
        else:
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            selected_ids = []

        if selected_ids and can("staff", "bulk_actions"):
            st.info(f"تم تحديد {len(selected_ids)} موظف.")
            new_status = st.selectbox("إجراء جماعي: تغيير الحالة إلى", ["نشط", "محظور", "إجازة"], key="bulk_status")
            if st.button("⚡ تطبيق الإجراء الجماعي"):
                db.bulk_update_staff(selected_ids, {"status": new_status})
                db.log_action("إجراء جماعي على الموظفين", f"تغيير حالة {len(selected_ids)} موظف إلى {new_status}")
                st.success("✅ تم تطبيق الإجراء.")
                st.rerun()

        if filtered.empty:
            st.info("لا يوجد موظفون مسجّلون بعد. أضف أول موظف من تبويب ➕ إضافة موظف.")
        else:
            if can("staff", "export"):
                c1, c2 = st.columns(2)
                c1.download_button("📊 تصدير Excel", excel_utils.df_to_excel_bytes(filtered, "الموظفين"), file_name="staff.xlsx")
                with c2:
                    safe_pdf_export_button(
                        "تصدير PDF",
                        lambda: pdf_utils.generic_table_pdf(
                            settings, "تقرير الموظفين", filtered.to_dict("records"),
                            ["emp_id", "name", "job", "salary", "status"],
                        ),
                        "staff.pdf", key="staff_pdf",
                    )

            st.markdown("#### 🔎 تفاصيل / تعديل / حذف / حظر موظف")
            pick = st.selectbox("اختر موظفاً", filtered["emp_id"].tolist())
            rec = filtered[filtered["emp_id"] == pick].iloc[0].to_dict()

            with st.expander("📄 بيانات الموظف", expanded=True):
                for k, v in rec.items():
                    st.write(f"**{k}:** {v}")

            if can("staff", "edit"):
                with st.expander("✏️ تعديل"):
                    new_name = st.text_input("الاسم", value=rec.get("name", ""), key=f"sn_{pick}")
                    new_job = st.text_input("الوظيفة", value=rec.get("job", ""), key=f"sj_{pick}")
                    new_salary = st.number_input("الراتب", value=float(rec.get("salary", 0) or 0), key=f"ss_{pick}")
                    new_phone = st.text_input("الهاتف", value=rec.get("phone", "") or "", key=f"sp_{pick}")
                    if confirm_action("حفظ تعديلات الموظف", key=f"ssave_{pick}"):
                        db.update_staff(pick, {"name": new_name, "job": new_job, "salary": new_salary, "phone": new_phone})
                        db.log_action("تعديل موظف", f"تعديل بيانات الموظف {pick}")
                        st.success("✅ تم الحفظ.")
                        st.rerun()

            c1, c2 = st.columns(2)
            if can("staff", "ban"):
                with c1:
                    if rec.get("status") != "محظور":
                        if st.button("⛔ حظر هذا الموظف", key=f"ban_{pick}"):
                            db.update_staff(pick, {"status": "محظور"})
                            db.log_action("حظر موظف", f"تم حظر الموظف {pick}")
                            st.success("⛔ تم الحظر.")
                            st.rerun()
                    else:
                        if st.button("✅ رفع الحظر", key=f"unban_{pick}"):
                            db.update_staff(pick, {"status": "نشط"})
                            db.log_action("رفع حظر موظف", f"تم رفع الحظر عن {pick}")
                            st.rerun()

            if can("staff", "delete"):
                with c2:
                    if confirm_action(f"حذف الموظف {pick} نهائياً", key=f"sdel_{pick}", danger=True):
                        db.delete_staff(pick)
                        db.log_action("حذف موظف", f"حذف الموظف {pick}")
                        st.success("🗑️ تم الحذف.")
                        st.rerun()

    # -------------------- تبويب: إضافة موظف --------------------
    with tab_add:
        st.warning("✅ CHECKPOINT-STAFF-ADD-TAB-LOADED (إذا شفت هالسطر، التبويب نفسه شغّال)")
        if not can("staff", "add"):
            st.warning("🚫 لا تملك صلاحية إضافة موظف. راجع المالك لتفعيل هذه الصلاحية.")
        else:
            emp_id = st.text_input("الرقم الوظيفي", key="staff_add_id")
            name = st.text_input("الاسم الكامل", key="staff_add_name")
            job = st.text_input("الوظيفة / الورشة", key="staff_add_job")
            salary = st.number_input("الراتب", min_value=0.0, step=50000.0, key="staff_add_salary")
            phone = st.text_input("رقم الهاتف", key="staff_add_phone")
            notes = st.text_area("ملاحظات", key="staff_add_notes")
            if st.button("➕ إضافة الموظف", type="primary", key="staff_add_submit"):
                if not emp_id or not name:
                    st.error("⚠️ الرقم الوظيفي والاسم إلزاميان.")
                else:
                    ok = db.insert_staff({
                        "emp_id": emp_id.strip(), "name": name, "job": job,
                        "salary": salary, "phone": phone, "notes": notes, "status": "نشط",
                    })
                    if ok:
                        db.log_action("إضافة موظف", f"إضافة الموظف {name} ({emp_id})")
                        st.success("✅ تمت الإضافة.")
                        st.rerun()
                    else:
                        st.error("❌ فشلت العملية، ربما الرقم الوظيفي مستخدم مسبقاً.")
