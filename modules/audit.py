# ==============================================================================
# modules/audit.py - سجل التدقيق الأمني (من دخل، متى، وماذا فعل)
# ==============================================================================

import pandas as pd
import streamlit as st

import db
import pdf_utils
import excel_utils
from ui_helpers import smart_search_filter, confirm_action, safe_pdf_export_button
from permissions import can, require


def render():
    require("audit", "access")
    st.header("📜 سجل التدقيق الأمني")

    settings = db.fetch_settings() or {}
    logs = db.fetch_audit_logs()
    if not logs:
        st.info("لا توجد سجلات بعد.")
        return

    df = pd.DataFrame(logs)
    query = st.text_input("🔍 بحث ذكي: اسم المستخدم / الإجراء / التفاصيل")
    filtered = smart_search_filter(df, ["username", "full_name", "action", "details"], query)

    select_col = "✅ تحديد"
    display_df = filtered.copy()
    display_df.insert(0, select_col, False)

    edited = st.data_editor(
        display_df, use_container_width=True, hide_index=True,
        disabled=[c for c in display_df.columns if c != select_col],
        key="audit_editor",
    )
    selected_ids = edited[edited[select_col]]["id"].tolist() if "id" in edited.columns else []

    c1, c2, c3 = st.columns(3)
    if c1.button(f"{'✅' if not selected_ids else '☑️'} تحديد الكل"):
        st.session_state["audit_select_all"] = True

    if can("audit", "export"):
        target_df = filtered[filtered["id"].isin(selected_ids)] if selected_ids else filtered
        c2.download_button("📊 تصدير Excel (المحدد أو الكل)", excel_utils.df_to_excel_bytes(target_df, "سجل التدقيق"), file_name="audit_log.xlsx")
        with c3:
            safe_pdf_export_button(
                "تصدير PDF (المحدد أو الكل)",
                lambda: pdf_utils.generic_table_pdf(
                    settings, "سجل التدقيق الأمني", target_df.to_dict("records"),
                    ["timestamp", "username", "full_name", "action", "details"],
                ),
                "audit_log.pdf", key="audit_pdf",
            )

    if can("audit", "delete") and selected_ids:
        if confirm_action(f"حذف {len(selected_ids)} سجل محدد من سجل التدقيق", key="audit_bulk_delete", danger=True):
            db.delete_audit_logs(selected_ids)
            st.success("🗑️ تم الحذف.")
            st.rerun()
