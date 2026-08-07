# ==============================================================================
# modules/movement.py - الحركة والعدادات (موظف الحركة يصوّر قراءة العداد فقط)
# صلاحيات دقيقة جداً حسب طلب المالك: يمكن حصر موظف الحركة على اختيار
# الآلية + التصوير + الرفع فقط، دون بقية أقسام النظام.
# ==============================================================================

import pandas as pd
import streamlit as st

import db
import pdf_utils
import excel_utils
from camera_utils import capture_or_upload
from ui_helpers import smart_search_filter, confirm_action, safe_pdf_export_button
from permissions import can, require
from config import STORAGE_BUCKET


def render():
    require("movement", "access")
    st.header("⛽ الحركة والعدادات")

    settings = db.fetch_settings() or {}
    tab_new, tab_log = st.tabs(["📸 تسجيل قراءة جديدة", "📋 سجل آخر القراءات"])

    with tab_new:
        _render_new_reading()

    with tab_log:
        _render_log(settings)


def _render_new_reading():

    fleet = db.fetch_fleet()
    fleet_df = pd.DataFrame(fleet) if fleet else pd.DataFrame(columns=["code", "type", "driver"])
    user = st.session_state.get("user", {})

machine_code = None
    if can("movement", "select_machine"):
        query = st.text_input("🔍 ابحث عن الآلية")
        filtered = smart_search_filter(fleet_df, ["code", "driver", "type"], query)
        if filtered.empty:
            st.warning("⚠️ لا توجد آليات مسجلة أو نتائج مطابقة حالياً.")
        else:
            options = [f"{r['code']} - {r.get('type','')} - سائق: {r.get('driver','')}" for _, r in filtered.iterrows()]
            codes = filtered["code"].tolist()
            choice = st.selectbox("اختر الآلية", options)
            if choice:
                machine_code = codes[options.index(choice)]
    else:
        st.error("لا تملك صلاحية اختيار الآلية.")

    odometer_value = st.number_input("🔢 قراءة العداد الحالية (اختياري - يمكن الاكتفاء بالصورة)", min_value=0.0, step=1.0)

    photo_bytes, content_type, filename = None, None, None
    if can("movement", "capture_photo") or can("movement", "upload_photo"):
        photo_bytes, content_type, filename = capture_or_upload(
            "movement",
            allow_camera=can("movement", "capture_photo"),
            allow_gallery=can("movement", "upload_photo"),
        )
        if photo_bytes:
            st.image(photo_bytes, caption="معاينة صورة العداد", width=300)

    c1, c2 = st.columns(2)
    if c1.button("⬆️ رفع قراءة العداد", type="primary"):
        if not machine_code:
            st.error("⚠️ اختر الآلية أولاً.")
        elif not photo_bytes and odometer_value == 0:
            st.error("⚠️ صوّر العداد أو أدخل القراءة يدوياً.")
        else:
            image_url = None
            if photo_bytes:
                image_url = db.upload_image(STORAGE_BUCKET, photo_bytes, filename or "odometer.jpg", content_type or "image/jpeg", subfolder="odometers")
            db.update_machine(machine_code, {"odometer": odometer_value, "odometer_image_url": image_url, "odometer_updated_at": db.now_str()})
            db.log_action("تحديث عداد", f"تحديث عداد الآلية {machine_code} إلى {odometer_value}")
            st.success("✅ تم رفع قراءة العداد بنجاح.")
            st.rerun()

    if c2.button("↩️ تراجع"):
        st.rerun()


def _render_log(settings):
    fleet = db.fetch_fleet()
    if not fleet:
        st.info("لا توجد آليات مسجّلة بعد.")
        return
    df = pd.DataFrame(fleet)
    cols = [c for c in ["code", "type", "driver", "odometer", "odometer_updated_at"] if c in df.columns]
    query = st.text_input("🔍 بحث ذكي عن آلية أو سائق بسجل العدادات")
    filtered = smart_search_filter(df, ["code", "driver", "type"], query)
    st.dataframe(filtered[cols], use_container_width=True, hide_index=True)

    if can("movement", "access") and not filtered.empty:
        c1, c2 = st.columns(2)
        c1.download_button(
            "📊 تصدير Excel", excel_utils.df_to_excel_bytes(filtered[cols], "سجل العدادات"),
            file_name="odometer_log.xlsx",
        )
        with c2:
            safe_pdf_export_button(
                "تصدير PDF",
                lambda: pdf_utils.generic_table_pdf(
                    settings, "سجل قراءات العدادات", filtered[cols].to_dict("records"), cols,
                ),
                "odometer_log.pdf", key="movement_pdf",
            )
