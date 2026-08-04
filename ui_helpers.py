# ==============================================================================
# Project: Suleiman ERP
# File: ui_helpers.py
# Purpose: مكونات واجهة مشتركة تُستخدم في كل الموديولات:
#   - البحث الذكي التصاعدي (يضيق النتائج مع كل حرف يُكتب)
#   - تنبيه صوتي + Toast عند وصول عنصر جديد يحتاج مراجعة/اعتماد
#   - عارض صور بقابلية التكبير/التصغير/ملء الشاشة/المقارنة الثنائية
#   - نافذة تأكيد إجراء موحّدة (حذف/إضافة/تعديل/تصدير...)
# ==============================================================================

import base64
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# نغمة تنبيه قصيرة جداً (beep) مُرمّزة base64 كي تعمل بدون اتصال إنترنت خارجي
_BEEP_B64 = (
    "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4LjI5LjEwMAAAAAAAAAAAAAAA//tQxAADwAABp"
    "AAAACAAADSAAAAETEFNRTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
    "VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
)


def smart_search_filter(df: pd.DataFrame, columns: list, query: str) -> pd.DataFrame:
    """
    بحث ذكي تصاعدي: كل حرف يضاف يُضيّق النتائج ضمن مجموعة الأعمدة المحددة،
    بدون حساسية لحالة الأحرف، ويعمل على أي عمود نصي أو رقمي.
    """
    if not query:
        return df
    query = str(query).strip()
    if not query:
        return df
    mask = None
    for col in columns:
        if col not in df.columns:
            continue
        col_mask = df[col].astype(str).str.contains(query, case=False, na=False, regex=False)
        mask = col_mask if mask is None else (mask | col_mask)
    if mask is None:
        return df
    return df[mask]


def play_notification_sound():
    """تشغيل تنبيه صوتي تلقائي (beep) داخل المتصفح."""
    components.html(
        f"""
        <audio autoplay style="display:none">
            <source src="data:audio/mp3;base64,{_BEEP_B64}" type="audio/mp3">
        </audio>
        """,
        height=0,
    )


def notify_new_item(message: str, play_sound: bool = True):
    """تنبيه بصري (toast) + صوتي عند وصول عنصر جديد يحتاج إجراء (سند، فاتورة...)."""
    st.toast(message, icon="🔔")
    if play_sound:
        play_notification_sound()


def check_and_notify(state_key: str, current_count: int, message_template: str):
    """
    يقارن العدد الحالي (مثلاً السندات المعلقة) بآخر عدد محفوظ في الجلسة.
    إن زاد العدد يعرض تنبيهاً صوتياً/بصرياً تلقائياً (محاكاة "وصول رسالة").
    """
    last_count = st.session_state.get(state_key, current_count)
    if current_count > last_count:
        notify_new_item(message_template.format(n=current_count - last_count))
    st.session_state[state_key] = current_count


def image_viewer(image_source, key_prefix: str, caption: str = ""):
    """
    عارض صورة موحّد بأزرار: تكبير / تصغير / ملء الشاشة / عودة.
    image_source: رابط URL أو bytes أو UploadedFile
    """
    zoom_key = f"{key_prefix}_zoom"
    full_key = f"{key_prefix}_fullscreen"
    if zoom_key not in st.session_state:
        st.session_state[zoom_key] = 1.0
    if full_key not in st.session_state:
        st.session_state[full_key] = False

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🔍 تكبير", key=f"{key_prefix}_in"):
        st.session_state[zoom_key] = min(st.session_state[zoom_key] + 0.25, 3.0)
    if c2.button("🔎 تصغير", key=f"{key_prefix}_out"):
        st.session_state[zoom_key] = max(st.session_state[zoom_key] - 0.25, 0.5)
    if c3.button("⛶ ملء الشاشة", key=f"{key_prefix}_full"):
        st.session_state[full_key] = not st.session_state[full_key]
    if c4.button("↩️ إعادة ضبط", key=f"{key_prefix}_reset"):
        st.session_state[zoom_key] = 1.0
        st.session_state[full_key] = False

    if image_source is None:
        st.info("لا توجد صورة مرفقة لهذا العنصر.")
        return

    width = None
    use_container = True
    if st.session_state[zoom_key] != 1.0:
        use_container = False
        width = int(400 * st.session_state[zoom_key])

    if st.session_state[full_key]:
        st.image(image_source, caption=caption, use_container_width=True)
    else:
        if use_container:
            st.image(image_source, caption=caption, use_container_width=True)
        else:
            st.image(image_source, caption=caption, width=width)


def split_screen_compare(left_render, right_render, left_title: str, right_title: str, key_prefix: str):
    """
    مقارنة شاشة مقسومة لعنصرين (مثلاً: صورة الفاتورة | نموذج السند).
    يدعم تكبير أي قسم إلى ملء الشاشة والعودة عبر نفس الأزرار.
    left_render / right_render: دوال (callbacks) بلا معاملات ترسم المحتوى.
    """
    mode_key = f"{key_prefix}_split_mode"
    if mode_key not in st.session_state:
        st.session_state[mode_key] = "split"  # split | left | right

    b1, b2, b3 = st.columns(3)
    if b1.button(f"⛶ تكبير: {left_title}", key=f"{key_prefix}_expand_left"):
        st.session_state[mode_key] = "left"
    if b2.button("⚌ عرض مقسوم", key=f"{key_prefix}_expand_split"):
        st.session_state[mode_key] = "split"
    if b3.button(f"⛶ تكبير: {right_title}", key=f"{key_prefix}_expand_right"):
        st.session_state[mode_key] = "right"

    mode = st.session_state[mode_key]
    if mode == "split":
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown(f"**{left_title}**")
            left_render()
        with col_r:
            st.markdown(f"**{right_title}**")
            right_render()
    elif mode == "left":
        st.markdown(f"**{left_title}**")
        left_render()
    else:
        st.markdown(f"**{right_title}**")
        right_render()


def confirm_action(action_label: str, key: str, danger: bool = False, require_password: str = None) -> bool:
    """
    نافذة تأكيد موحّدة لأي إجراء (حذف/تعديل/تصدير شامل...).
    ترجع True فقط عند نقر المستخدم على تأكيد فعلياً.
    require_password: إن مررت كلمة مرور المالك هنا، يُطلب إدخالها لإتمام
    الإجراء (تُستخدم لعمليات الحذف الشامل والنسخ الاحتياطي الشامل).
    """
    confirm_key = f"{key}_confirm_open"
    if confirm_key not in st.session_state:
        st.session_state[confirm_key] = False

    icon = "⚠️" if danger else "ℹ️"
    if st.button(f"{icon} {action_label}", key=f"{key}_trigger"):
        st.session_state[confirm_key] = True

    if not st.session_state[confirm_key]:
        return False

    with st.container(border=True):
        st.warning(f"{icon} هل أنت متأكد من: **{action_label}**؟ هذا الإجراء سيُسجَّل في سجل التدقيق.")
        pw_ok = True
        entered_pw = None
        if require_password is not None:
            entered_pw = st.text_input(
                "🔑 أدخل كلمة مرور المالك للمتابعة:", type="password", key=f"{key}_pw"
            )
            pw_ok = entered_pw == require_password

        c1, c2 = st.columns(2)
        confirmed = False
        if c1.button("✅ نعم، تأكيد", key=f"{key}_yes"):
            if require_password is not None and not pw_ok:
                st.error("❌ كلمة المرور غير صحيحة.")
            else:
                confirmed = True
                st.session_state[confirm_key] = False
        if c2.button("❌ إلغاء", key=f"{key}_no"):
            st.session_state[confirm_key] = False
            st.rerun()
        return confirmed
