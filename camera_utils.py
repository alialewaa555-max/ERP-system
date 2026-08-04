# ==============================================================================
# Project: Suleiman ERP
# File: camera_utils.py
# Purpose: التقاط صورة (فاتورة / عداد) عبر الكاميرا الخلفية حصراً، أو استيراد
# صورة من معرض الهاتف - وإلغاء أي وضع "كاميرا أمامية/مباشرة".
#
# ⚠️ ملاحظة تقنية مهمة بخصوص المتصفح (Streamlit Cloud تعمل داخل متصفح الجوال):
# مكوّن Streamlit الأساسي `st.camera_input` لا يوفّر معامل برمجي لإجبار
# "الكاميرا الخلفية" (facingMode=environment) لأنه يعتمد كلياً على واجهة
# المتصفح، لكن الغالبية الساحقة من متصفحات الجوال (Chrome/Safari) تفتح
# الكاميرا الخلفية تلقائياً كافتراضي عند طلب إذن الكاميرا من صفحة ويب،
# وتتيح للمستخدم زر "تبديل الكاميرا" داخل واجهة الالتقاط نفسها لإلغاء ذلك
# يدوياً إن أراد. لضمان أقصى تحكم ممكن دون تثبيت مكوّن JS مخصص إضافي،
# نعرض أيضاً خيار "استيراد من المعرض" كبديل دائم متاح كما طلب المالك.
# ==============================================================================

import streamlit as st


def capture_or_upload(key_prefix: str, allow_gallery: bool = True, allow_camera: bool = True):
    """
    يعرض واجهة موحّدة لالتقاط صورة فاتورة/عداد.
    يرجع tuple: (bytes | None, content_type | None, filename | None)
    """
    mode_options = []
    if allow_camera:
        mode_options.append("📷 تصوير بالكاميرا الخلفية")
    if allow_gallery:
        mode_options.append("🖼️ استيراد من المعرض")

    if not mode_options:
        return None, None, None

    mode = st.radio("طريقة إرفاق الصورة", mode_options, key=f"{key_prefix}_mode", horizontal=True)

    if mode.startswith("📷"):
        st.caption(
            "💡 عند فتح الكاميرا: تُفتح الكاميرا الخلفية افتراضياً على أغلب أجهزة الجوال. "
            "إن ظهرت الكاميرا الأمامية استخدم زر تبديل الكاميرا (🔄) داخل نافذة الالتقاط."
        )
        img = st.camera_input("التقط صورة الفاتورة الآن", key=f"{key_prefix}_camera")
        if img is not None:
            return img.getvalue(), "image/jpeg", f"{key_prefix}_capture.jpg"
        return None, None, None

    uploaded = st.file_uploader(
        "اختر صورة من المعرض", type=["jpg", "jpeg", "png"], key=f"{key_prefix}_upload"
    )
    if uploaded is not None:
        return uploaded.getvalue(), uploaded.type or "image/jpeg", uploaded.name
    return None, None, None
