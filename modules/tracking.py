# ==============================================================================
# modules/tracking.py - التتبع الجغرافي لمواقع المستخدمين
#
# ⚠️ ملاحظة واقعية مهمة (لأن النظام تطبيق ويب يعمل داخل متصفح على
# Streamlit Cloud، وليس تطبيق جوال أصلي):
#   - الموقع الجغرافي يُقرأ من متصفح المستخدم عبر واجهة Geolocation API
#     القياسية، ويتطلب موافقة المستخدم صراحة في كل جهاز.
#   - "التتبع الحي المستمر" ممكن فقط أثناء بقاء تبويب المتصفح مفتوحاً ونشطاً
#     (لا يوجد تتبع في الخلفية بعد إغلاق المتصفح، وهذا قيد تقني في كل تطبيقات
#     الويب وليس خاصاً بهذا النظام - لتتبع خلفي حقيقي 24/7 يلزم تطبيق جوال
#     أصلي منفصل Android/iOS يستخدم نفس جداول Supabase).
#   - نحدّث الموقع تلقائياً كل بضع ثوانٍ طالما المستخدم على شاشة النظام عبر
#     مكتبة streamlit-js-eval + إعادة تحديث دورية (streamlit-autorefresh).
#   - نصنّف الحالة: 🟢 متحرك (تغيّر الموقع عن آخر قراءة) / ⚪ ثابت
#     (نفس الموقع تقريباً) / 🔴 خارج الشبكة (لم يُحدَّث موقعه منذ أكثر من
#     5 دقائق - أي أن التطبيق مغلق أو لا يوجد اتصال إنترنت لديه).
# ==============================================================================

import datetime
import math
import streamlit as st

import db
from ui_helpers import smart_search_filter
from permissions import can, require

try:
    from streamlit_js_eval import get_geolocation
    JS_EVAL_AVAILABLE = True
except ImportError:
    JS_EVAL_AVAILABLE = False

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

OFFLINE_THRESHOLD_MINUTES = 5


def _distance_meters(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def broadcast_current_user_location():
    """
    يُستدعى تلقائياً من app.py لكل مستخدم دخل النظام (باستثناء المالك إن
    أراد) لبث موقعه الحالي بصمت في الخلفية طالما الصفحة مفتوحة، تحقيقاً
    لطلب: "الحسابات التي لا تحدد لها صلاحيات (خيار بلا) يبث موقعها فقط".
    """
    if not JS_EVAL_AVAILABLE:
        return
    user = st.session_state.get("user")
    if not user:
        return
    try:
        loc = get_geolocation()
    except Exception:
        loc = None
    if not loc or "coords" not in loc:
        return

    lat = loc["coords"]["latitude"]
    lon = loc["coords"]["longitude"]

    last = st.session_state.get("last_location")
    status = "ثابت"
    if last:
        moved = _distance_meters(lat, lon, last[0], last[1])
        status = "متحرك" if moved > 15 else "ثابت"
    st.session_state["last_location"] = (lat, lon)

    db.upsert_location(user["username"], lat, lon, status)


def render():
    require("tracking", "access")
    st.header("🗺️ التتبع الجغرافي لمواقع المستخدمين")

    if not JS_EVAL_AVAILABLE or not AUTOREFRESH_AVAILABLE:
        st.warning(
            "⚠️ مكتبتا `streamlit-js-eval` و `streamlit-autorefresh` غير مثبّتتين. "
            "أضفهما إلى requirements.txt لتفعيل قراءة الموقع الحي والتحديث التلقائي."
        )

    if AUTOREFRESH_AVAILABLE:
        st_autorefresh(interval=15000, key="tracking_autorefresh")

    locations = db.fetch_locations()
    if not locations:
        st.info("لا توجد مواقع مسجّلة بعد. سيظهر المستخدمون هنا فور دخولهم للنظام وموافقتهم على مشاركة الموقع من المتصفح.")
        return

    now = datetime.datetime.now()
    rows = []
    for loc in locations:
        try:
            updated = datetime.datetime.strptime(loc["updated_at"], "%Y-%m-%d %H:%M:%S")
            minutes_ago = (now - updated).total_seconds() / 60
        except Exception:
            minutes_ago = 999

        if minutes_ago > OFFLINE_THRESHOLD_MINUTES:
            status, color = "خارج الشبكة", [230, 30, 30]
        elif loc.get("status") == "متحرك":
            status, color = "متحرك", [30, 180, 60]
        else:
            status, color = "ثابت", [140, 140, 140]

        rows.append({
            "المستخدم": loc["username"], "lat": loc["lat"], "lon": loc["lon"],
            "الحالة": status, "color": color, "آخر تحديث": loc["updated_at"],
        })

    query = st.text_input("🔍 بحث ذكي عن مستخدم بالاسم لتتبعه بشكل مستقل")
    import pandas as pd
    df = pd.DataFrame(rows)
    filtered = smart_search_filter(df, ["المستخدم"], query) if query else df

    st.dataframe(filtered[["المستخدم", "الحالة", "آخر تحديث"]], use_container_width=True, hide_index=True)

    try:
        import pydeck as pdk
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=filtered.to_dict("records"),
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius=120,
            pickable=True,
        )
        view_state = pdk.ViewState(
            latitude=filtered["lat"].mean() if not filtered.empty else 33.3,
            longitude=filtered["lon"].mean() if not filtered.empty else 44.4,
            zoom=10,
        )
        st.pydeck_chart(pdk.Deck(
            layers=[layer], initial_view_state=view_state,
            tooltip={"text": "{المستخدم}\n{الحالة}\n{آخر تحديث}"},
        ))
    except Exception:
        st.map(filtered.rename(columns={"lat": "latitude", "lon": "longitude"}))

    st.caption("🟢 متحرك  ⚪ ثابت  🔴 خارج الشبكة (لم يُحدَّث موقعه منذ أكثر من 5 دقائق)")
