# ==============================================================================
# Project: Suleiman ERP
# File: excel_utils.py
# Purpose: تصدير أي جدول بيانات إلى Excel (متعدد الأوراق) أو CSV، بالكامل في
# الذاكرة (BytesIO) دون الكتابة على القرص - متوافق مع بيئة Streamlit Cloud
# ذات نظام الملفات المؤقت.
# ==============================================================================

import io
import pandas as pd


def df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "البيانات") -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        _autofit(writer, df, sheet_name[:31])
    return buffer.getvalue()


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")  # utf-8-sig لدعم العربية في Excel


def multi_sheet_excel_bytes(sheets: dict) -> bytes:
    """
    sheets: dict {اسم_الورقة: DataFrame} - يُستخدم للنسخة الاحتياطية الشاملة
    التي تحتوي كل الجداول (آليات، موظفين، سندات، مستخدمين، سجل تدقيق...).
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            safe_name = str(name)[:31]
            if df is None or df.empty:
                df = pd.DataFrame({"ملاحظة": ["لا توجد بيانات"]})
            df.to_excel(writer, index=False, sheet_name=safe_name)
            _autofit(writer, df, safe_name)
    return buffer.getvalue()


def _autofit(writer, df: pd.DataFrame, sheet_name: str):
    try:
        worksheet = writer.sheets[sheet_name]
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max() if not df.empty else 10, len(str(col))) + 3
            worksheet.set_column(i, i, min(max_len, 45))
    except Exception:
        pass
