# ==============================================================================
# modules/vendors.py - مستحقات المحلات (مشتقة تلقائياً من السندات المعتمدة)
# ==============================================================================

import pandas as pd
import streamlit as st

import db
import pdf_utils
import excel_utils
from ui_helpers import smart_search_filter, confirm_action, image_viewer
from permissions import can, require
from config import VOUCHER_STATUS_APPROVED


def render():
    require("vendors", "access")
    st.header("🏪 مستحقات المحلات")

    settings = db.fetch_settings() or {}
    vouchers = db.fetch_vouchers()
    if not vouchers:
        st.info("لا توجد بيانات فواتير بعد.")
        return

    df = pd.DataFrame(vouchers)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    summary = df.groupby("vendor").agg(
        عدد_السندات=("voucher_no", "count"),
        إجمالي_المستحقات=("amount", "sum"),
    ).reset_index().rename(columns={"vendor": "المحل"})

    query = st.text_input("🔍 بحث ذكي عن محل")
    filtered = smart_search_filter(summary, ["المحل"], query)
    st.dataframe(filtered, use_container_width=True, hide_index=True)

    if can("vendors", "export"):
        c1, c2 = st.columns(2)
        c1.download_button("📊 تصدير كل المحلات Excel", excel_utils.df_to_excel_bytes(summary, "مستحقات المحلات"), file_name="vendors.xlsx")

    st.markdown("---")
    st.subheader("🔎 تفاصيل محل معين")
    if filtered.empty:
        return
    vendor_name = st.selectbox("اختر المحل", filtered["المحل"].tolist())
    vendor_vouchers = df[df["vendor"] == vendor_name].to_dict("records")

    total_pending = sum(v["amount"] for v in vendor_vouchers if v["status"] != VOUCHER_STATUS_APPROVED)
    total_approved = sum(v["amount"] for v in vendor_vouchers if v["status"] == VOUCHER_STATUS_APPROVED)

    c1, c2, c3 = st.columns(3)
    c1.metric("عدد السندات", len(vendor_vouchers))
    c2.metric("مستحقات معتمدة", f"{total_approved:,.0f}")
    c3.metric("قيد الإجراء", f"{total_pending:,.0f}")

    st.markdown("#### 🧾 السندات المالية المرتبطة بهذا المحل")
    for v in sorted(vendor_vouchers, key=lambda x: str(x.get("created_at", "")), reverse=True):
        with st.expander(f"{v['voucher_no']} — {v.get('amount',0):,.0f} — {v.get('status','')} — {str(v.get('created_at',''))[:10]}"):
            st.write(f"الآلية: {v.get('machine_code','')}")
            st.write(f"ملاحظات: {v.get('notes','') or '-'}")
            image_viewer(v.get("image_url"), key_prefix=f"vendor_img_{v['voucher_no']}", caption="الصورة الأصلية")
            if can("vendors", "export"):
                pdf_bytes = pdf_utils.voucher_pdf(settings, v)
                st.download_button("📄 تصدير هذا السند PDF", pdf_bytes, file_name=f"{v['voucher_no']}.pdf", key=f"vpdf_{v['voucher_no']}")

    if can("vendors", "export"):
        st.markdown("---")
        full_pdf = pdf_utils.vendor_statement_pdf(settings, vendor_name, vendor_vouchers)
        st.download_button("📄 تصدير كشف حساب كامل للمحل PDF", full_pdf, file_name=f"{vendor_name}_statement.pdf")

    if can("vendors", "delete"):
        st.markdown("---")
        if confirm_action(f"حذف كل سجلات المحل ({vendor_name}) من الفواتير", key=f"delvendor_{vendor_name}", danger=True):
            for v in vendor_vouchers:
                db.delete_voucher(v["id"])
            db.log_action("حذف محل", f"تم حذف كل فواتير المحل {vendor_name}")
            st.success("🗑️ تم الحذف.")
            st.rerun()
