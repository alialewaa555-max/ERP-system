# ==============================================================================
# Project: Suleiman ERP
# File: pdf_utils.py
# Purpose: توليد ملفات PDF احترافية بترويسة موحدة لكل تبويبات النظام:
# شعار الشركة أعلى اليسار، اسم الشركة أعلى اليمين، عنوان التصدير بالنص
# العلوي، والتاريخ تحت العنوان. بدعم كامل للعربية (RTL).
#
# ⚠️ الخط العربي (Amiri-Regular.ttf / Amiri-Bold.ttf) يجب أن يكون داخل
# مجلد fonts/ بمستودع GitHub. بدونه، الدوال هنا ترفع ArabicFontMissingError
# بدل ما تُسقط كامل الصفحة - الموديولات تتعامل مع هذا الاستثناء بلطف.
# ==============================================================================

import io
import os
import datetime
import requests
import streamlit as st
from fpdf import FPDF

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONT_REGULAR = os.path.join(FONT_DIR, "Amiri-Regular.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "Amiri-Bold.ttf")


class ArabicFontMissingError(Exception):
    """يُستثنى عند غياب ملفات خط Amiri من مجلد fonts/."""
    pass


def ar(text):
    """تشكيل النص العربي وعكس اتجاهه ليظهر صحيحاً داخل PDF (RTL)."""
    if text is None:
        return ""
    text = str(text)
    if not ARABIC_SUPPORT:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def _fetch_image_bytes(url_or_bytes):
    """تنزيل صورة من رابط Supabase العام أو إرجاعها كما هي إن كانت bytes."""
    if url_or_bytes is None:
        return None
    if isinstance(url_or_bytes, (bytes, bytearray)):
        return io.BytesIO(url_or_bytes)
    try:
        resp = requests.get(url_or_bytes, timeout=8)
        if resp.status_code == 200:
            return io.BytesIO(resp.content)
    except Exception:
        return None
    return None


class BrandedPDF(FPDF):
    """قالب PDF موحد: شعار أعلى اليسار / اسم شركة أعلى اليمين / عنوان
    وتاريخ بالمنتصف العلوي."""

    def __init__(self, settings: dict, title: str):
        super().__init__()
        self.settings = settings or {}
        self.doc_title = title
        self._has_arabic_font = False

        # نتحقق من توفر الخط العربي قبل أي شيء - وإلا نوقف بوضوح
        if not os.path.exists(FONT_REGULAR):
            raise ArabicFontMissingError(
                "⚠️ ملف الخط العربي (Amiri-Regular.ttf) غير موجود في مجلد fonts/ "
                "بمستودعك على GitHub. حمّله وارفعه ثم أعد المحاولة."
            )

        self._register_fonts()
        self.add_page()
        self._draw_header()

    def _register_fonts(self):
        try:
            self.add_font("Amiri", "", FONT_REGULAR, uni=True)
            bold_path = FONT_BOLD if os.path.exists(FONT_BOLD) else FONT_REGULAR
            self.add_font("Amiri", "B", bold_path, uni=True)
            self._has_arabic_font = True
        except Exception as e:
            raise ArabicFontMissingError(f"⚠️ تعذر تحميل الخط العربي: {e}")

    def font(self, size=12, bold=False):
        self.set_font("Amiri", "B" if bold else "", size)

    def _draw_header(self):
        company_name = self.settings.get("company_name") or "الشركة"
        logo_url = self.settings.get("logo_url")
        today = datetime.date.today().strftime("%Y-%m-%d")

        # 1) الشعار أعلى اليسار (الجهة الفيزيائية اليسرى من الصفحة)
        if logo_url:
            img = _fetch_image_bytes(logo_url)
            if img:
                try:
                    self.image(img, x=12, y=8, w=28)
                except Exception:
                    pass

        # 2) اسم الشركة أعلى اليمين (الجهة الفيزيائية اليمنى من الصفحة)
        self.set_xy(130, 10)
        self.font(15, bold=True)
        self.cell(68, 8, ar(company_name), align="R")

        # 3) عنوان التصدير بالمنتصف العلوي
        self.set_xy(55, 20)
        self.font(13, bold=True)
        self.cell(100, 8, ar(self.doc_title), align="C")

        # 4) التاريخ تحت العنوان بالمنتصف
        self.set_xy(55, 29)
        self.font(9)
        self.set_text_color(90, 90, 90)
        self.cell(100, 6, ar("التاريخ: ") + today, align="C")
        self.set_text_color(0, 0, 0)

        self.set_draw_color(200, 160, 40)
        self.line(10, 40, 200, 40)
        self.set_xy(10, 45)

    def add_stamp(self):
        stamp_url = self.settings.get("stamp_url")
        if not stamp_url:
            return
        img = _fetch_image_bytes(stamp_url)
        if img:
            try:
                self.image(img, x=150, y=self.get_y() + 5, w=35)
            except Exception:
                pass

    def kv_row(self, label, value):
        self.font(11, bold=True)
        self.cell(40, 8, ar(str(value)), align="R")
        self.font(11)
        self.cell(0, 8, ar(str(label)) + " :", align="R", new_x="LMARGIN", new_y="NEXT")

    def paragraph(self, text, size=10):
        self.font(size)
        self.multi_cell(0, 7, ar(text), align="R")

    def footer(self):
        self.set_y(-15)
        self.font(8)
        self.set_text_color(120, 120, 120)
        company_name = self.settings.get("company_name") or "النظام"
        self.cell(0, 10, ar(f"صفحة {self.page_no()} - {company_name}"), align="C")


def voucher_pdf(settings: dict, voucher: dict) -> bytes:
    """توليد PDF لسند مالي معتمد (فاتورة) مع الختم وإقرار الاستلام."""
    pdf = BrandedPDF(settings, f"سند مالي رقم {voucher.get('voucher_no', '')}")
    pdf.kv_row("رقم السند", voucher.get("voucher_no", ""))
    pdf.kv_row("التاريخ", str(voucher.get("created_at", ""))[:10])
    pdf.kv_row("اسم المحل / المورد", voucher.get("vendor", ""))
    pdf.kv_row("الآلية المرتبطة", voucher.get("machine_code", ""))
    pdf.kv_row("المبلغ", f"{voucher.get('amount', 0) or 0:,.0f}")
    pdf.kv_row("الحالة", voucher.get("status", ""))
    pdf.kv_row("أدخله موظف المشتريات", voucher.get("entered_by", ""))
    pdf.kv_row("دقّقه", voucher.get("reviewed_by", "") or "-")
    pdf.kv_row("اعتمده المدير", voucher.get("approved_by", "") or "-")
    pdf.ln(5)
    pdf.paragraph(voucher.get("notes", "") or "لا توجد ملاحظات إضافية.")

    pdf.ln(10)
    pdf.paragraph(
        "يقر صاحب المحل المذكور أعلاه باستلام كامل المبلغ الموضح في هذا السند، "
        "وتبرأ ذمة الشركة تجاهه بموجب هذا الإقرار، وقد تم توقيعه وختمه رقمياً "
        "من الجهة المخوّلة بالشركة."
    )

    pdf.ln(15)
    y = pdf.get_y()
    pdf.set_xy(120, y)
    pdf.font(10)
    pdf.cell(70, 8, ar("توقيع المُسلِّم: ..........................."), align="R")
    pdf.set_xy(20, y)
    pdf.cell(70, 8, ar("توقيع المُستلِم (بصمة): ..........................."), align="R")

    if voucher.get("status") == "معتمد ومختوم":
        pdf.add_stamp()

    return bytes(pdf.output())


def generic_table_pdf(settings: dict, title: str, rows: list, columns: list) -> bytes:
    """توليد PDF لجدول بيانات عام (آليات، موظفين، سجل تدقيق، مستحقات محل...)."""
    pdf = BrandedPDF(settings, title)
    pdf.font(9, bold=True)

    col_width = 190 / max(len(columns), 1)
    for col in columns:
        pdf.cell(col_width, 8, ar(col), border=1, align="C")
    pdf.ln()

    pdf.font(8)
    for row in rows:
        for col in columns:
            val = row.get(col, "")
            pdf.cell(col_width, 7, ar(str(val))[:40], border=1, align="C")
        pdf.ln()
        if pdf.get_y() > 270:
            pdf.add_page()
            pdf._draw_header()

    return bytes(pdf.output())


def vendor_statement_pdf(settings: dict, vendor_name: str, vouchers: list) -> bytes:
    """كشف حساب كامل لمحل معين مع كل السندات المرتبطة به."""
    total = sum(float(v.get("amount", 0) or 0) for v in vouchers)
    pdf = BrandedPDF(settings, f"كشف حساب: {vendor_name}")
    pdf.kv_row("اسم المحل", vendor_name)
    pdf.kv_row("عدد السندات", len(vouchers))
    pdf.kv_row("إجمالي المستحقات", f"{total:,.0f}")
    pdf.ln(5)

    pdf.font(9, bold=True)
    headers = ["الحالة", "المبلغ", "الآلية", "التاريخ", "رقم السند"]
    widths = [35, 30, 35, 35, 45]
    for h, w in zip(headers, widths):
        pdf.cell(w, 8, ar(h), border=1, align="C")
    pdf.ln()

    pdf.font(8)
    for v in vouchers:
        vals = [
            v.get("status", ""),
            f"{float(v.get('amount', 0) or 0):,.0f}",
            v.get("machine_code", ""),
            str(v.get("created_at", ""))[:10],
            v.get("voucher_no", ""),
        ]
        for val, w in zip(vals, widths):
            pdf.cell(w, 7, ar(str(val)), border=1, align="C")
        pdf.ln()

    return bytes(pdf.output())


def full_backup_pdf(settings: dict, summary: dict) -> bytes:
    """تقرير PDF موجز يرافق النسخة الاحتياطية الشاملة."""
    pdf = BrandedPDF(settings, "تقرير النسخة الاحتياطية الشاملة")
    for label, value in summary.items():
        pdf.kv_row(label, value)
    return bytes(pdf.output())
