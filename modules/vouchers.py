# ==============================================================================
# modules/vouchers.py - الاعتماد المزدوج للسندات
# المرحلة 1: موظف تدقيق الفواتير ينقل بيانات الصورة إلى السند المالي
# المرحلة 2: المدير يقارن السند بالصورة الأصلية ويوافق (ختم رقمي) أو يرفض
# ==============================================================================

import pandas as pd
import streamlit as st

import db
import pdf_utils
import excel_utils
from ui_helpers import smart_search_filter, split_screen_compare, image_viewer, safe_pdf_export_button
from permissions import can, require
from config import (
    VOUCHER_STATUS_NEW,
    VOUCHER_STATUS_REVIEWED,
    VOUCHER_STATUS_APPROVED,
    VOUCHER_STATUS_REJECTED,
)


def _status_badge(status):
    colors = {
        VOUCHER_STATUS_NEW: "🔴",
        VOUCHER_STATUS_REVIEWED: "🟠",
        VOUCHER_STATUS_APPROVED: "🟢",
        VOUCHER_STATUS_REJECTED: "⚫",
    }
    return f"{colors.get(status, '⚪')} {status}"


def render():
    require("vouchers", "access")
    st.header("🔐 الاعتماد المزدوج للسندات")

    settings = db.fetch_settings() or {}
    user = st.session_state.get("user", {})
    vouchers = db.fetch_vouchers()
    df = pd.DataFrame(vouchers) if vouchers else pd.DataFrame(
        columns=["id", "voucher_no", "vendor", "machine_code", "amount", "status", "created_at", "image_url"]
    )

    tab_pending, tab_approved, tab_search = st.tabs(["⏳ معلّقة", "✅ معتمدة", "🔎 بحث ذكي شامل"])

    # -------------------- المعلّقة --------------------
    with tab_pending:
        pending = df[df["status"].isin([VOUCHER_STATUS_NEW, VOUCHER_STATUS_REVIEWED])]
        if pending.empty:
            st.success("لا توجد سندات معلّقة حالياً ✅")
        for _, row in pending.iterrows():
            row = row.to_dict()
            with st.container(border=True):
                st.markdown(f"**{row['voucher_no']}** — {_status_badge(row['status'])} — 📅 {str(row.get('created_at',''))[:16]}")

                if row["status"] == VOUCHER_STATUS_NEW and can("purchases", "review_transcribe"):
                    _render_review_stage(row)
                elif row["status"] == VOUCHER_STATUS_REVIEWED and can("vouchers", "approve"):
                    _render_approval_stage(row, settings)
                else:
                    st.caption("بانتظار الجهة المختصة لمعالجة هذا السند.")

    # -------------------- المعتمدة --------------------
    with tab_approved:
        approved = df[df["status"] == VOUCHER_STATUS_APPROVED]
        if approved.empty:
            st.info("لا توجد سندات معتمدة بعد.")
        else:
            for _, row in approved.iterrows():
                row = row.to_dict()
                with st.expander(f"✅ {row['voucher_no']} — {row.get('vendor','')} — {row.get('amount',0):,.0f}"):
                    st.write(f"الآلية: {row.get('machine_code','')}")
                    st.write(f"دُقّق بواسطة: {row.get('reviewed_by','-')}")
                    st.write(f"اعتمده: {row.get('approved_by','-')}")
                    image_viewer(row.get("image_url"), key_prefix=f"appr_{row['voucher_no']}", caption="الصورة الأصلية")
                    if can("vouchers", "export"):
                        c1, c2 = st.columns(2)
                        with c1:
                            safe_pdf_export_button(
                                f"تصدير سند {row['voucher_no']} (مختوم)",
                                lambda row=row: pdf_utils.voucher_pdf(settings, row),
                                f"{row['voucher_no']}.pdf", key=f"pdf_{row['voucher_no']}",
                            )
                        with c2:
                            c2.download_button(
                                "📊 تصدير Excel", excel_utils.df_to_excel_bytes(pd.DataFrame([row]), "سند"),
                                file_name=f"{row['voucher_no']}.xlsx", key=f"xls_{row['voucher_no']}",
                            )

    # -------------------- بحث ذكي شامل --------------------
    with tab_search:
        query = st.text_input("🔍 اكتب أي جزء من رقم السند / المحل / الآلية / الحالة")
        filtered = smart_search_filter(df, ["voucher_no", "vendor", "machine_code", "status"], query)
        st.dataframe(
            filtered[["voucher_no", "vendor", "machine_code", "amount", "status", "created_at"]],
            use_container_width=True, hide_index=True,
        )
        if not filtered.empty:
            pick = st.selectbox("عرض سند بالتفصيل", filtered["voucher_no"].tolist())
            rec = filtered[filtered["voucher_no"] == pick].iloc[0].to_dict()
            image_viewer(rec.get("image_url"), key_prefix=f"srch_{pick}", caption="الصورة الأصلية")
            if can("vouchers", "export"):
                c1, c2 = st.columns(2)
                with c1:
                    safe_pdf_export_button(
                        f"تصدير سند {pick} PDF",
                        lambda rec=rec: pdf_utils.voucher_pdf(settings, rec),
                        f"{pick}.pdf", key=f"srch_pdf_{pick}",
                    )
                with c2:
                    c2.download_button(
                        "📊 تصدير Excel", excel_utils.df_to_excel_bytes(pd.DataFrame([rec]), "سند"),
                        file_name=f"{pick}.xlsx", key=f"srch_xls_{pick}",
                    )


def _render_review_stage(row):
    """مرحلة موظف التدقيق: شاشة مقسومة (الصورة | نموذج نقل البيانات)."""
    user = st.session_state.get("user", {})

    def left():
        image_viewer(row.get("image_url"), key_prefix=f"rev_img_{row['voucher_no']}", caption="الفاتورة الأصلية")

    def right():
        with st.form(key=f"review_form_{row['voucher_no']}"):
            vendor = st.text_input("اسم المحل", value=row.get("vendor", ""))
            amount = st.number_input("المبلغ", value=float(row.get("amount", 0) or 0))
            notes = st.text_area("ملاحظات التدقيق", value=row.get("notes", "") or "")
            submitted = st.form_submit_button("✅ إرسال للمدير للاعتماد")
            if submitted:
                db.update_voucher(row["id"], {
                    "vendor": vendor,
                    "amount": amount,
                    "notes": notes,
                    "status": VOUCHER_STATUS_REVIEWED,
                    "reviewed_by": user.get("name", user.get("username", "")),
                    "reviewed_at": db.now_str(),
                })
                db.log_action("تدقيق سند", f"تم تدقيق ورفع السند {row['voucher_no']} للمدير")
                st.success("✅ تم إرسال السند للمدير، سيصله تنبيه فوري.")
                st.rerun()

    split_screen_compare(left, right, "الصورة الأصلية", "نموذج السند", key_prefix=f"review_{row['voucher_no']}")


def _render_approval_stage(row, settings):
    """مرحلة اعتماد المدير: مقارنة سريعة ثم موافقة (ختم رقمي) أو رفض."""
    user = st.session_state.get("user", {})

    def left():
        image_viewer(row.get("image_url"), key_prefix=f"apr_img_{row['voucher_no']}", caption="الصورة الأصلية")

    def right():
        st.write(f"**المحل:** {row.get('vendor','')}")
        st.write(f"**المبلغ:** {row.get('amount',0):,.0f}")
        st.write(f"**الآلية:** {row.get('machine_code','')}")
        st.write(f"**دقّقه:** {row.get('reviewed_by','')}")
        st.write(f"**ملاحظات:** {row.get('notes','') or '-'}")

        c1, c2 = st.columns(2)
        if c1.button("✅ موافقة واعتماد + ختم رقمي", key=f"ok_{row['voucher_no']}", type="primary"):
            db.update_voucher(row["id"], {
                "status": VOUCHER_STATUS_APPROVED,
                "approved_by": user.get("name", user.get("username", "")),
                "approved_at": db.now_str(),
            })
            db.log_action("اعتماد سند", f"اعتمد المدير السند {row['voucher_no']} وختمه رقمياً")
            st.success("✅ تم الاعتماد والختم الرقمي بنجاح.")
            st.rerun()
        if c2.button("❌ رفض وإعادة للتدقيق", key=f"rj_{row['voucher_no']}"):
            db.update_voucher(row["id"], {
                "status": VOUCHER_STATUS_NEW,
                "notes": (row.get("notes") or "") + " | ⚠️ مرفوض من المدير - يتطلب مراجعة",
            })
            db.log_action("رفض سند", f"رفض المدير السند {row['voucher_no']} وأعاده للتدقيق")
            st.warning("↩️ تم إرجاع السند لموظف التدقيق.")
            st.rerun()

    split_screen_compare(left, right, "الصورة الأصلية", "بيانات السند", key_prefix=f"approve_{row['voucher_no']}")
