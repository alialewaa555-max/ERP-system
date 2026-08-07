# ==============================================================================
# modules/dashboard.py - لوحة القيادة: ملخص شامل وتنبيهات فورية
# ==============================================================================

import pandas as pd
import streamlit as st

import db
from config import VOUCHER_STATUS_NEW, VOUCHER_STATUS_REVIEWED, VOUCHER_STATUS_APPROVED
from ui_helpers import check_and_notify
from permissions import can


def render():
    st.header("📊 لوحة القيادة")

    fleet = db.fetch_fleet()
    staff = db.fetch_staff()
    vouchers = db.fetch_vouchers()

    pending_review = [v for v in vouchers if v.get("status") == VOUCHER_STATUS_NEW]
    pending_approval = [v for v in vouchers if v.get("status") == VOUCHER_STATUS_REVIEWED]
    approved = [v for v in vouchers if v.get("status") == VOUCHER_STATUS_APPROVED]

    # تنبيهات فورية حسب دور المستخدم الحالي
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    if can("purchases", "review_transcribe"):
        check_and_notify("seen_pending_review", len(pending_review), "🔔 لديك {n} فاتورة جديدة بانتظار التدقيق")
    if can("vouchers", "approve"):
        check_and_notify("seen_pending_approval", len(pending_approval), "🔔 لديك {n} سند بانتظار اعتمادك النهائي")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🚜 إجمالي الآليات", len(fleet))
    c2.metric("👷 إجمالي الموظفين", len(staff))
    c3.metric("🧾 سندات معلّقة", len(pending_review) + len(pending_approval))
    c4.metric("✅ سندات معتمدة", len(approved))

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚠️ آليات بحاجة صيانة")
        maint = [m for m in fleet if m.get("status") == "في الصيانة"]
        if maint:
            st.dataframe(pd.DataFrame(maint)[["code", "type", "driver"]], use_container_width=True, hide_index=True)
        else:
            st.success("لا توجد آليات في الصيانة حالياً ✅")

    with col2:
        st.subheader("🧾 آخر السندات المالية")
        if vouchers:
            recent = pd.DataFrame(vouchers[:8])
            cols = [c for c in ["voucher_no", "vendor", "amount", "status"] if c in recent.columns]
            st.dataframe(recent[cols], use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد سندات بعد.")

    st.markdown("---")
    st.subheader("💰 إجمالي المصروفات المعتمدة حسب الآلية")
    if approved:
        df = pd.DataFrame(approved)
        if "machine_code" in df.columns and "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
            grouped = df.groupby("machine_code")["amount"].sum().sort_values(ascending=False)
            st.bar_chart(grouped)
    else:
        st.info("لا توجد بيانات مصروفات معتمدة بعد لعرضها في الرسم البياني.")
