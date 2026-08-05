# ==============================================================================
# modules/purchases.py - المشتريات وتصوير الفواتير (مندوب المشتريات)
# تدفق العمل: مندوب المشتريات يختار الآلية ← يصور/يستورد الفاتورة ← يرفع
# ← تنبيه صوتي فوري لموظف تدقيق الفواتير ← يظهر في شاشة الاعتماد المزدوج
# ==============================================================================

import pandas as pd
import streamlit as st

import db
import pdf_utils
import excel_utils
from camera_utils import capture_or_upload
from ui_helpers import smart_search_filter, confirm_action, image_viewer
from permissions import can, require
from config import VOUCHER_STATUS_NEW, STORAGE_BUCKET


def _machine_picker(fleet_df: pd.DataFrame, key: str):
    """بحث ذكي تصاعدي عن آلية بالاسم/الكود/اسم السائق قبل اختيارها."""
    query = st.text_input("🔍 ابحث عن آلية بالكود أو اسم السائق أو النوع", key=f"{key}_q")
    filtered = smart_search_filter(fleet_df, ["code", "driver", "type"], query)
    if filtered.empty:
        st.warning("لا توجد نتائج مطابقة.")
        return None
    options = [f"{r['code']} - {r.get('type','')} - سائق: {r.get('driver','')}" for _, r in filtered.iterrows()]
    codes = filtered["code"].tolist()
    choice = st.selectbox("اختر الآلية", options, key=f"{key}_sel")
    if choice is None:
        return None
    idx = options.index(choice)
    return codes[idx]


def render():
    require("purchases", "access")
    st.header("📸 المشتريات وتصوير الفواتير")

    fleet = db.fetch_fleet()
    fleet_df = pd.DataFrame(fleet) if fleet else pd.DataFrame(columns=["code", "type", "driver"])
    settings = db.fetch_settings() or {}
    user = st.session_state.get("user", {})

    tab_new, tab_list = st.tabs(["➕ فاتورة جديدة", "📋 كل الفواتير"])

    # -------------------- تبويب: فاتورة جديدة --------------------
    with tab_new:
        if can("purchases", "select_machine"):
            machine_code = _machine_picker(fleet_df, "new_voucher")
        else:
            st.error("لا تملك صلاحية اختيار الآلية.")
            machine_code = None

        vendor = st.text_input("🏪 اسم المحل / المورد")
        amount = st.number_input("💵 المبلغ", min_value=0.0, step=1000.0)
        notes = st.text_area("📝 ملاحظات (اختياري)")

        photo_bytes, content_type, filename = None, None, None
        no_photo = False
        if can("purchases", "add_no_photo"):
            no_photo = st.checkbox("➕ إضافة فاتورة بدون صورة")
        if not no_photo and (can("purchases", "capture_photo") or can("purchases", "upload_photo")):
            photo_bytes, content_type, filename = capture_or_upload(
                "new_voucher",
                allow_camera=can("purchases", "capture_photo"),
                allow_gallery=can("purchases", "upload_photo"),
            )
            if photo_bytes:
                st.image(photo_bytes, caption="معاينة الفاتورة الملتقطة", width=300)

        if st.button("⬆️ رفع الفاتورة", type="primary"):
            if not machine_code:
                st.error("⚠️ يرجى اختيار الآلية أولاً.")
            elif not vendor:
                st.error("⚠️ يرجى إدخال اسم المحل/المورد.")
            elif not no_photo and not photo_bytes:
                st.error("⚠️ يرجى تصوير الفاتورة أو استيراد صورة، أو تفعيل خيار (بدون صورة).")
            else:
                image_url = None
                if photo_bytes:
                    image_url = db.upload_image(STORAGE_BUCKET, photo_bytes, filename or "invoice.jpg", content_type or "image/jpeg", subfolder="invoices")

                voucher_no = db.new_id("V-")
                ok, vid = db.insert_voucher({
                    "voucher_no": voucher_no,
                    "machine_code": machine_code,
                    "vendor": vendor.strip(),
                    "amount": amount,
                    "notes": notes,
                    "image_url": image_url,
                    "status": VOUCHER_STATUS_NEW,
                    "entered_by": user.get("name", user.get("username", "")),
                })
                if ok:
                    db.log_action("رفع فاتورة جديدة", f"سند {voucher_no} للمحل {vendor} بمبلغ {amount}")
                    st.success(f"✅ تم رفع الفاتورة بنجاح برقم سند: {voucher_no}. سيصل تنبيه فوري لموظف التدقيق.")
                    st.balloons()
                else:
                    st.error("❌ فشل حفظ الفاتورة، تحقق من الاتصال بقاعدة البيانات.")

    # -------------------- تبويب: كل الفواتير --------------------
    with tab_list:
        vouchers = db.fetch_vouchers()
        if not vouchers:
            st.info("لا توجد فواتير مسجلة بعد.")
            return

        df = pd.DataFrame(vouchers)
        query = st.text_input("🔍 بحث ذكي: رقم السند / المحل / الآلية", key="purchases_list_q")
        filtered = smart_search_filter(df, ["voucher_no", "vendor", "machine_code", "status"], query)

        st.dataframe(
            filtered[["voucher_no", "vendor", "machine_code", "amount", "status", "created_at"]],
            use_container_width=True, hide_index=True,
        )

        st.markdown("#### 🔎 تفاصيل / تعديل / حذف فاتورة")
        if filtered.empty:
            return
        selected_no = st.selectbox("اختر رقم السند", filtered["voucher_no"].tolist(), key="purchases_pick")
        record = filtered[filtered["voucher_no"] == selected_no].iloc[0].to_dict()

        image_viewer(record.get("image_url"), key_prefix=f"purch_view_{selected_no}", caption=f"فاتورة {selected_no}")

        if can("purchases", "edit"):
            with st.expander("✏️ تعديل بيانات الفاتورة"):
                new_vendor = st.text_input("اسم المحل", value=record.get("vendor", ""), key=f"ev_{selected_no}")
                new_amount = st.number_input("المبلغ", value=float(record.get("amount", 0) or 0), key=f"ea_{selected_no}")
                new_notes = st.text_area("ملاحظات", value=record.get("notes", "") or "", key=f"en_{selected_no}")
                if st.button("💾 حفظ التعديلات", key=f"save_{selected_no}"):
                    db.update_voucher(record["id"], {"vendor": new_vendor, "amount": new_amount, "notes": new_notes})
                    db.log_action("تعديل فاتورة", f"تعديل سند {selected_no}")
                    st.success("✅ تم حفظ التعديلات.")
                    st.rerun()

        if can("purchases", "delete"):
            if confirm_action("حذف هذه الفاتورة نهائياً", key=f"del_{selected_no}", danger=True):
                db.delete_voucher(record["id"])
                db.log_action("حذف فاتورة", f"حذف سند {selected_no}")
                st.success("🗑️ تم الحذف.")
                st.rerun()

        if can("purchases", "export"):
            st.markdown("#### 📤 تصدير")
            c1, c2 = st.columns(2)
            pdf_bytes = pdf_utils.voucher_pdf(settings, record)
            c1.download_button("📄 تصدير هذه الفاتورة PDF", pdf_bytes, file_name=f"{selected_no}.pdf")
            csv_bytes = excel_utils.df_to_csv_bytes(filtered)
            c2.download_button("📊 تصدير كل الفواتير CSV", csv_bytes, file_name="purchases.csv")

        # تحليل التكاليف حسب الآلية والمحل
        st.markdown("---")
        st.subheader("📈 تحليل التكاليف")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.caption("إجمالي التكاليف حسب الآلية")
            by_machine = df.groupby("machine_code")["amount"].sum()
            st.bar_chart(by_machine)
        with cc2:
            st.caption("إجمالي التكاليف حسب المحل")
            by_vendor = df.groupby("vendor")["amount"].sum()
            st.bar_chart(by_vendor)
