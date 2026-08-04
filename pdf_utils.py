# ==============================================================================
# Project: Suleiman ERP
# File: pdf_utils.py
# Purpose: توليد ملفات PDF احترافية (سندات، تقارير آليات، موظفين، سجل تدقيق...)
# بدعم كامل للغة العربية (RTL) عبر arabic_reshaper + python-bidi + fpdf2.
# ==============================================================================

import io
import os
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
    """قالب PDF أساسي بترويسة موحّدة: الشعار واسم الشركة يمين، العنوان يسار."""

    def __init__(self, settings: dict, title: str):
        super().__init__()
        self.settings = settings or {}
        self.doc_title = title
        self._has_arabic_font = False
        
        # 1. تسجيل الخطوط أولاً لضمان عمل الحروف العربية
        self._register_fonts()
        
        # 2. إنشاء الصفحة ورسم الترويسة
        self.add_page()
        self._draw_header()

    def _register_fonts(self):
        try:
            if os.path.exists(FONT_REGULAR):
                self.add_font("Amiri", "", FONT_REGULAR, uni=True)
                bold_path = FONT_BOLD if os.path.exists(FONT_BOLD) else FONT_REGULAR
                self.add_font("Amiri", "B", bold_path, uni=True)
                self._has_arabic_font = True
        except Exception:
            self._has_arabic_font = False

    def font(self, size=12, bold=False):
        if self._has_arabic_font:
            self.set_font("Amiri", "B" if bold else "", size)
        else:
            self.set_font("Helvetica", "B" if bold else "", size)

    def _draw_header(self):
        company_name = self.settings.get("company_name", "الشركة")
        logo_url = self.settings.get("logo_url")

        # الشعار واسم الشركة على اليمين
        if logo_url:
            img = _fetch_image_bytes(logo_url)
            if img:
                try:
                    self.image(img, x=170, y=8, w=25)
                except Exception:
                    pass

        self.set_xy(10, 10)
        self.font(16, bold=True)
        self.cell(150, 10, ar(company_name), align="R")

        # عنوان المستند على اليسار
        self.set_xy(10, 22)
        self.font(12)
        self.cell(150, 8, ar(self.doc_title), align="R")

        self.set_draw_color(200, 160, 40)
        self.line(10, 33, 200, 33)
        self.set_xy(10, 38)

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
        self.cell(0, 10, ar(f"صفحة {self.page_no()} - نظام سليمان ERP"), align="C")


def voucher_pdf(settings: dict, voucher: dict) -> bytes:
    """توليد PDF لسند مالي معتمد (فاتورة) مع الختم وإقرار الاستلام."""
    pdf = BrandedPDF(settings, f"سند مالي رقم {voucher.get('voucher_no', '')}")
    pdf.kv_row("رقم السند", voucher.get("voucher_no", ""))
    pdf.kv_row("التاريخ", voucher.get("created_at", "")[:10])
    pdf.kv_row("اسم المحل / المورد", voucher.get("vendor", ""))
    pdf.kv_row("الآلية المرتبطة", voucher.get("machine_code", ""))
    pdf.kv_row("المبلغ", f"{voucher.get('amount', 0):,.0f}")
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
    return bytes(pdf.output())        return text


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
    """قالب PDF أساسي بترويسة موحّدة: الشعار واسم الشركة يمين، العنوان يسار."""

    def __init__(self, settings: dict, title: str):
        super().__init__()
        self.settings = settings or {}
        self.doc_title = title
        self._has_arabic_font = False
        
        # 1. تسجيل الخطوط أولاً قبل إنشاء أي صفحة لضمان عمل الحروف العربية
        self._register_fonts()
        
        # 2. إنشاء الصفحة ورسم الترويسة بعد تفعيل الخط
        self.add_page()
        self._draw_header()

    def _register_fonts(self):
        try:
            if os.path.exists(FONT_REGULAR):
                self.add_font("Amiri", "", FONT_REGULAR, uni=True)
                bold_path = FONT_BOLD if os.path.exists(FONT_BOLD) else FONT_REGULAR
                self.add_font("Amiri", "B", bold_path, uni=True)
                self._has_arabic_font = True
        except Exception:
            self._has_arabic_font = False

    def font(self, size=12, bold=False):
        if self._has_arabic_font:
            self.set_font("Amiri", "B" if bold else "", size)
        else:
            self.set_font("Helvetica", "B" if bold else "", size)

    def _draw_header(self):
        company_name = self.settings.get("company_name", "الشركة")
        logo_url = self.settings.get("logo_url")

        # الشعار واسم الشركة على اليمين
        if logo_url:
            img = _fetch_image_bytes(logo_url)
            if img:
                try:
                    self.image(img, x=170, y=8, w=25)
                except Exception:
                    pass

        self.set_xy(10, 10)
        self.font(16, bold=True)
        self.cell(150, 10, ar(company_name), align="R")

        # عنوان المستند على اليسار
        self.set_xy(10, 22)
        self.font(12)
        self.cell(150, 8, ar(self.doc_title), align="R")

        self.set_draw_color(200, 160, 40)
        self.line(10, 33, 200, 33)
        self.set_xy(10, 38)

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
        self.cell(0, 10, ar(f"صفحة {self.page_no()} - نظام سليمان ERP"), align="C")


def voucher_pdf(settings: dict, voucher: dict) -> bytes:
    """توليد PDF لسند مالي معتمد (فاتورة) مع الختم وإقرار الاستلام."""
    pdf = BrandedPDF(settings, f"سند مالي رقم {voucher.get('voucher_no', '')}")
    pdf.kv_row("رقم السند", voucher.get("voucher_no", ""))
    pdf.kv_row("التاريخ", voucher.get("created_at", "")[:10])
    pdf.kv_row("اسم المحل / المورد", voucher.get("vendor", ""))
    pdf.kv_row("الآلية المرتبطة", voucher.get("machine_code", ""))
    pdf.kv_row("المبلغ", f"{voucher.get('amount', 0):,.0f}")
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
    return bytes(pdf.output())        return text


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
    """قالب PDF أساسي بترويسة موحّدة: الشعار واسم الشركة يمين، العنوان يسار."""

    def __init__(self, settings: dict, title: str):
        super().__init__()
        self.settings = settings or {}
        self.doc_title = title
        self._has_arabic_font = False
        
        # 1. تسجيل الخطوط أولاً قبل إنشاء أي صفحة لضمان عمل الحروف العربية
        self._register_fonts()
        
        # 2. إنشاء الصفحة ورسم الترويسة بعد تفعيل الخط
        self.add_page()
        self._draw_header()

    def _register_fonts(self):
        try:
            if os.path.exists(FONT_REGULAR):
                self.add_font("Amiri", "", FONT_REGULAR, uni=True)
                bold_path = FONT_BOLD if os.path.exists(FONT_BOLD) else FONT_REGULAR
                self.add_font("Amiri", "B", bold_path, uni=True)
                self._has_arabic_font = True
        except Exception:
            self._has_arabic_font = False

    def font(self, size=12, bold=False):
        if self._has_arabic_font:
            self.set_font("Amiri", "B" if bold else "", size)
        else:
            self.set_font("Helvetica", "B" if bold else "", size)

    def _draw_header(self):
        company_name = self.settings.get("company_name", "الشركة")
        logo_url = self.settings.get("logo_url")

        # الشعار واسم الشركة على اليمين
        if logo_url:
            img = _fetch_image_bytes(logo_url)
            if img:
                try:
                    self.image(img, x=170, y=8, w=25)
                except Exception:
                    pass

        self.set_xy(10, 10)
        self.font(16, bold=True)
        self.cell(150, 10, ar(company_name), align="R")

        # عنوان المستند على اليسار
        self.set_xy(10, 22)
        self.font(12)
        self.cell(150, 8, ar(self.doc_title), align="R")

        self.set_draw_color(200, 160, 40)
        self.line(10, 33, 200, 33)
        self.set_xy(10, 38)

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
        self.cell(0, 10, ar(f"صفحة {self.page_no()} - نظام سليمان ERP"), align="C")


def voucher_pdf(settings: dict, voucher: dict) -> bytes:
    """توليد PDF لسند مالي معتمد (فاتورة) مع الختم وإقرار الاستلام."""
    pdf = BrandedPDF(settings, f"سند مالي رقم {voucher.get('voucher_no', '')}")
    pdf.kv_row("رقم السند", voucher.get("voucher_no", ""))
    pdf.kv_row("التاريخ", voucher.get("created_at", "")[:10])
    pdf.kv_row("اسم المحل / المورد", voucher.get("vendor", ""))
    pdf.kv_row("الآلية المرتبطة", voucher.get("machine_code", ""))
    pdf.kv_row("المبلغ", f"{voucher.get('amount', 0):,.0f}")
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
