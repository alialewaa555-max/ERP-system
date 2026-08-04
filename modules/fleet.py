# ==============================================================================
# modules/fleet.py - إدارة كلف الآليات (CRUD كامل + بحث ذكي + تصدير)
# ==============================================================================

import pandas as pd
import streamlit as st

import db
import pdf_utils
import excel_utils
from ui_helpers import smart_search_filter, confirm_action
from permissions import can, require
from config import MACHINE_TYPES, MACHINE_STATUSES


def render():
    require("fleet", "access")
    st.header("🚜 إدارة كلف الآليات")

    settings = db.fetch_settings() or {}
    fleet = db.fetch_fleet()
    vouchers = db.fetch_vouchers()
    fdf = pd.DataFrame(fleet) if fleet else pd.DataFrame(columns=["code", "type", "driver", "status", "notes"])
    vdf = pd.DataFrame(vouchers) if vouchers else pd.DataFrame(columns=["machine_code", "amount"])

    tab_list, tab_add = st.tabs(["📋 قائمة الآليات", "➕ إضافة آلية"])

    with tab_list:
        query = st.text_input("🔍 بحث ذكي عن آلية أو اسم سائق (يعرض أيضاً الفواتير المرتبطة)")
        filtered = smart_search_filter(fdf, ["code", "type", "driver", "status", "notes"], query)

        if not vdf.empty:
            vdf["amount"] = pd.to_numeric(vdf["amount"], errors="coerce").fillna(0)
            costs = vdf.groupby("machine_code")["amount"].sum().to_dict()
        else:
            costs = {}
        filtered = filtered.copy()
        filtered["إجمالي التكاليف"] = filtered["code"].map(costs).fillna(0)

        st.dataframe(filtered, use_container_width=True, hide_index=True)

        if can("fleet", "export"):
            c1, c2 = st.columns(2)
            c1.download_button("📊 تصدير Excel", excel_utils.df_to_excel_bytes(filtered, "الآليات"), file_name="fleet.xlsx")
            pdf_bytes = pdf_utils.generic_table_pdf(
                settings, "تقرير الآليات",
                filtered.to_dict("records"),
                ["code", "type", "driver", "status", "إجمالي التكاليف"],
            )
            c2.download_button("📄 تصدير PDF", pdf_bytes, file_name="fleet.pdf")

        if filtered.empty:
            return

        st.markdown("#### 🔎 تفاصيل / تعديل / حذف آلية")
        pick = st.selectbox("اختر آلية", filtered["code"].tolist())
        rec = filtered[filtered["code"] == pick].iloc[0].to_dict()

        related_vouchers = vdf[vdf["machine_code"] == pick] if not vdf.empty else pd.DataFrame()
        with st.expander(f"📄 مواصفات الآلية {pick}", expanded=True):
            st.write(f"**النوع:** {rec.get('type','')}")
            st.write(f"**السائق:** {rec.get('driver','')}")
            st.write(f"**الحالة:** {rec.get('status','')}")
            st.write(f"**إجمالي التكاليف:** {rec.get('إجمالي التكاليف',0):,.0f}")
            st.write(f"**ملاحظات:** {rec.get('notes','') or '-'}")
            if not related_vouchers.empty:
                st.dataframe(related_vouchers[["voucher_no", "vendor", "amount", "status"]], use_container_width=True, hide_index=True)

        if can("fleet", "edit"):
            with st.expander("✏️ تعديل بيانات الآلية"):
                new_type = st.selectbox("النوع", MACHINE_TYPES, index=_safe_index(MACHINE_TYPES, rec.get("type")), key=f"ftype_{pick}")
                new_driver = st.text_input("اسم السائق", value=rec.get("driver", ""), key=f"fdrv_{pick}")
                new_status = st.selectbox("الحالة", MACHINE_STATUSES, index=_safe_index(MACHINE_STATUSES, rec.get("status")), key=f"fst_{pick}")
                new_notes = st.text_area("ملاحظات", value=rec.get("notes", "") or "", key=f"fnt_{pick}")
                if st.button("💾 حفظ", key=f"fsave_{pick}"):
                    db.update_machine(pick, {"type": new_type, "driver": new_driver, "status": new_status, "notes": new_notes})
                    db.log_action("تعديل آلية", f"تعديل بيانات الآلية {pick}")
                    st.success("✅ تم الحفظ.")
                    st.rerun()

        if can("fleet", "delete"):
            if confirm_action(f"حذف الآلية {pick} نهائياً", key=f"fdel_{pick}", danger=True):
                db.delete_machine(pick)
                db.log_action("حذف آلية", f"حذف الآلية {pick}")
                st.success("🗑️ تم الحذف.")
                st.rerun()

    with tab_add:
        if not can("fleet", "add"):
            st.error("لا تملك صلاحية إضافة آلية.")
            return
        code = st.text_input("كود / رقم الآلية")
        mtype = st.selectbox("النوع", MACHINE_TYPES)
        driver = st.text_input("اسم السائق")
        status = st.selectbox("الحالة", MACHINE_STATUSES)
        notes = st.text_area("ملاحظات")
        if st.button("➕ إضافة الآلية", type="primary"):
            if not code:
                st.error("⚠️ أدخل كود الآلية.")
            else:
                ok = db.insert_machine({"code": code.strip(), "type": mtype, "driver": driver, "status": status, "notes": notes})
                if ok:
                    db.log_action("إضافة آلية", f"إضافة آلية جديدة {code}")
                    st.success("✅ تمت الإضافة.")
                    st.rerun()
                else:
                    st.error("❌ فشلت العملية، ربما الكود مستخدم مسبقاً.")


def _safe_index(options, value):
    try:
        return options.index(value)
    except (ValueError, TypeError):
        return 0
