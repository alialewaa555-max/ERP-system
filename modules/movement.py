# ==============================================================================
# modules/movement.py - الحركة والعدادات (موظف الحركة يصوّر قراءة العداد فقط)
# صلاحيات دقيقة جداً حسب طلب المالك: يمكن حصر موظف الحركة على اختيار
# الآلية + التصوير + الرفع فقط، دون بقية أقسام النظام.
# ==============================================================================

import pandas as pd
import streamlit as st

import db
from camera_utils import capture_or_upload
from ui_helpers import smart_search_filter, confirm_action
from permissions import can, require


def render():
    require("movement", "access")
    st.header("⛽ الحركة والعدادات")

    fleet = db.fetch_fleet()
    fleet_df = pd.DataFrame(fleet) if fleet else pd.DataFrame(columns=["code", "type", "driver"])
    user = st.session_state.get("user", {})

    if can("movement", "select_machine"):
        query = st.text_input("🔍 ابحث عن الآلية")
        filtered = smart_search_filter(fleet_df, ["code", "driver", "type"], query)
        if filtered.empty:
            st.warning("لا توجد نتائج.")
            return
        options = [f"{r['code']} - {r.get('type','')} - سائق: {r.get('driver','')}" for _, r in filtered.iterrows()]
        codes = filtered["code"].tolist()
        choice = st.selectbox("اختر الآلية", options)
        machine_code = codes[options.index(choice)] if choice else None
    else:
        st.error("لا تملك صلاحية اختيار الآلية.")
        return

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
                image_url = db.upload_image("odometers", photo_bytes, filename or "odometer.jpg", content_type or "image/jpeg")
            db.update_machine(machine_code, {"odometer": odometer_value, "odometer_image_url": image_url, "odometer_updated_at": db.now_str()})
            db.log_action("تحديث عداد", f"تحديث عداد الآلية {machine_code} إلى {odometer_value}")
            st.success("✅ تم رفع قراءة العداد بنجاح.")
            st.rerun()

    if c2.button("↩️ تراجع"):
        st.rerun()
