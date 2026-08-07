# ==============================================================================
# modules/expenses.py - سجل النفقات العامة (نفقات الشركة غير المرتبطة
# بآلية معينة: إيجار، رواتب إدارية، فواتير كهرباء، إلخ)
# ==============================================================================

import pandas as pd
import streamlit as st

import db
import pdf_utils
import excel_utils
from ui_helpers import smart_search_filter, confirm_action, safe_pdf_export_button
from permissions import can, require


def render():
    require("expenses", "access")
    st.header("🧾 سجل النفقات العامة")

    settings = db.fetch_settings() or {}
    expenses = db.fetch_expenses()
    edf = pd.DataFrame(expenses) if expenses else pd.DataFrame(columns=["id", "title", "amount", "category", "notes", "expense_date"])

    tab_list, tab_add = st.tabs(["📋 قائمة النفقات", "➕ إضافة نفقة"])

    with tab_list:
        query = st.text_input("🔍 بحث ذكي عن نفقة بالعنوان أو التصنيف")
        filtered = smart_search_filter(edf, ["title", "category", "notes"], query)

        if not filtered.empty:
            filtered = filtered.copy()
            filtered["amount"] = pd.to_numeric(filtered["amount"], errors="coerce").fillna(0)
            total = filtered["amount"].sum()
            st.metric("💰 إجمالي النفقات المعروضة", f"{total:,.0f}")

        st.dataframe(
            filtered[["title", "category", "amount", "expense_date", "notes"]] if not filtered.empty else filtered,
            use_container_width=True, hide_index=True,
        )

        if can("expenses", "export") and not filtered.empty:
            c1, c2 = st.columns(2)
            c1.download_button("📊 تصدير Excel", excel_utils.df_to_excel_bytes(filtered, "النفقات العامة"), file_name="expenses.xlsx")
            with c2:
                safe_pdf_export_button(
                    "تصدير PDF",
                    lambda: pdf_utils.generic_table_pdf(
                        settings, "سجل النفقات العامة", filtered.to_dict("records"),
                        ["title", "category", "amount", "expense_date"],
                    ),
                    "expenses.pdf", key="expenses_pdf",
                )

        if filtered.empty:
            return

        st.markdown("#### 🔎 تعديل / حذف نفقة")
        pick_title = st.selectbox("اختر نفقة", (filtered["title"] + " | " + filtered["id"]).tolist())
        pick_id = pick_title.split(" | ")[-1]
        rec = filtered[filtered["id"] == pick_id].iloc[0].to_dict()

        if can("expenses", "edit"):
            with st.expander("✏️ تعديل"):
                new_title = st.text_input("العنوان", value=rec.get("title", ""), key=f"et_{pick_id}")
                new_amount = st.number_input("التكلفة", value=float(rec.get("amount", 0) or 0), key=f"ea_{pick_id}")
                new_category = st.text_input("التصنيف", value=rec.get("category", "") or "", key=f"ec_{pick_id}")
                new_notes = st.text_area("ملاحظات", value=rec.get("notes", "") or "", key=f"en_{pick_id}")
                if confirm_action("حفظ تعديلات النفقة", key=f"esave_{pick_id}"):
                    db.update_expense(pick_id, {
                        "title": new_title, "amount": new_amount,
                        "category": new_category, "notes": new_notes,
                    })
                    db.log_action("تعديل نفقة", f"تعديل النفقة {new_title}")
                    st.success("✅ تم الحفظ.")
                    st.rerun()

        if can("expenses", "delete"):
            if confirm_action(f"حذف النفقة ({rec.get('title','')}) نهائياً", key=f"edel_{pick_id}", danger=True):
                db.delete_expense(pick_id)
                db.log_action("حذف نفقة", f"حذف النفقة {rec.get('title','')}")
                st.success("🗑️ تم الحذف.")
                st.rerun()

    with tab_add:
        if not can("expenses", "add"):
            st.error("لا تملك صلاحية إضافة نفقة.")
            return
        title = st.text_input("عنوان النفقة *")
        amount = st.number_input("التكلفة *", min_value=0.0, step=1000.0)
        category = st.text_input("التصنيف (مثال: إيجار، كهرباء، رواتب إدارية...)")
        expense_date = st.date_input("تاريخ النفقة")
        notes = st.text_area("ملاحظات")
        if st.button("➕ إضافة النفقة", type="primary"):
            if not title or amount <= 0:
                st.error("⚠️ العنوان والتكلفة إلزاميان.")
            else:
                ok = db.insert_expense({
                    "title": title.strip(), "amount": amount, "category": category,
                    "notes": notes, "expense_date": str(expense_date),
                })
                if ok:
                    db.log_action("إضافة نفقة", f"إضافة نفقة عامة: {title} بمبلغ {amount}")
                    st.success("✅ تمت الإضافة.")
                    st.rerun()
                else:
                    st.error("❌ فشلت العملية.")
