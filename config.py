# ==============================================================================
# Project: Suleiman ERP - Enterprise Fleet & Financial Management System
# File: config.py
# Purpose: كل الثوابت، الترجمات، أنواع الآليات، وهيكلية الصلاحيات الافتراضية
# ==============================================================================

APP_VERSION = "2.0.0"

# ------------------------------------------------------------------------------
# اللغات المدعومة
# ------------------------------------------------------------------------------
LANGUAGES = ["AR", "KU", "EN"]

TRANSLATIONS = {
    "AR": {
        "dashboard": "📊 لوحة القيادة",
        "purchases": "📸 المشتريات وتصوير الفواتير",
        "vouchers": "🔐 الاعتماد المزدوج للسندات",
        "vendors": "🏪 مستحقات المحلات",
        "fleet": "🚜 إدارة كلف الآليات",
        "expenses": "🧾 سجل النفقات العامة",
        "movement": "⛽ الحركة والعدادات",
        "staff": "👷 إدارة الموظفين والورشات",
        "audit": "📜 سجل التدقيق الأمني",
        "rbac": "🛡️ إدارة المستخدمين والصلاحيات",
        "tracking": "🗺️ التتبع الجغرافي للمستخدمين",
        "settings": "⚙️ إعدادات النظام وتصدير البيانات",
        "logout": "🚪 تسجيل الخروج",
        "welcome": "مرحباً",
        "role": "الرتبة / الصلاحية",
        "language": "🌐 لغة الواجهة",
        "main_menu": "القائمة الرئيسية",
        "search_placeholder": "🔍 ابحث هنا...",
        "confirm": "تأكيد",
        "cancel": "إلغاء",
        "save": "حفظ 💾",
        "edit": "تعديل ✏️",
        "delete": "حذف 🗑️",
        "add": "إضافة ➕",
        "export_pdf": "تصدير PDF 📄",
        "export_excel": "تصدير Excel 📊",
        "view_original": "🖼️ عرض الصورة الأصلية",
        "zoom_in": "🔍 تكبير",
        "zoom_out": "🔎 تصغير",
        "fullscreen": "⛶ ملء الشاشة",
        "back": "↩️ عودة",
        "approve": "✅ موافقة واعتماد",
        "reject": "❌ رفض",
        "select_all": "تحديد الكل",
    },
    "KU": {
        "dashboard": "📊 داشبۆرد",
        "purchases": "📸 کڕین و وێنەگرتنی پسوولە",
        "vouchers": "🔐 پەسەندکردنی دووانی سەند",
        "vendors": "🏪 شایستەی دوکانەکان",
        "fleet": "🚜 بەڕێوەبردنی ئامێرەکان",
        "expenses": "🧾 تۆماری خەرجی گشتی",
        "movement": "⛽ جووڵە و مەتەر",
        "staff": "👷 بەڕێوەبردنی کارمەندەکان",
        "audit": "📜 تۆماری پشکنینی ئاسایش",
        "rbac": "🛡️ بەڕێوەبردنی بەکارهێنەران و دەسەڵاتەکان",
        "tracking": "🗺️ شوێنپێی جوگرافی بەکارهێنەران",
        "settings": "⚙️ ڕێکخستنی سیستەم",
        "logout": "🚪 چوونەدەرەوە",
        "welcome": "بەخێربێیت",
        "role": "پلە / دەسەڵات",
        "language": "🌐 زمانی ڕووکار",
        "main_menu": "پێڕستی سەرەکی",
        "search_placeholder": "🔍 لێرە بگەڕێ...",
        "confirm": "دڵنیابوونەوە",
        "cancel": "هەڵوەشاندنەوە",
        "save": "پاشەکەوتکردن 💾",
        "edit": "دەستکاریکردن ✏️",
        "delete": "سڕینەوە 🗑️",
        "add": "زیادکردن ➕",
        "export_pdf": "دەرکردن PDF 📄",
        "export_excel": "دەرکردن Excel 📊",
        "view_original": "🖼️ بینینی وێنەی ڕەسەن",
        "zoom_in": "🔍 گەورەکردن",
        "zoom_out": "🔎 بچووککردنەوە",
        "fullscreen": "⛶ پڕی شاشە",
        "back": "↩️ گەڕانەوە",
        "approve": "✅ پەسەندکردن",
        "reject": "❌ ڕەتکردنەوە",
        "select_all": "هەموو هەڵبژێرە",
    },
    "EN": {
        "dashboard": "📊 Dashboard",
        "purchases": "📸 Procurement & Receipts",
        "vouchers": "🔐 Dual Verification",
        "vendors": "🏪 Vendors Ledger",
        "fleet": "🚜 Fleet Cost Management",
        "expenses": "🧾 General Expenses",
        "movement": "⛽ Odometer & Movement",
        "staff": "👷 Staff & Crew Management",
        "audit": "📜 Security Audit Log",
        "rbac": "🛡️ Users & Permissions",
        "tracking": "🗺️ User Geo-Tracking",
        "settings": "⚙️ System Settings & Backup",
        "logout": "🚪 Logout",
        "welcome": "Welcome",
        "role": "Role",
        "language": "🌐 Interface Language",
        "main_menu": "Main Menu",
        "search_placeholder": "🔍 Search here...",
        "confirm": "Confirm",
        "cancel": "Cancel",
        "save": "Save 💾",
        "edit": "Edit ✏️",
        "delete": "Delete 🗑️",
        "add": "Add ➕",
        "export_pdf": "Export PDF 📄",
        "export_excel": "Export Excel 📊",
        "view_original": "🖼️ View Original Image",
        "zoom_in": "🔍 Zoom In",
        "zoom_out": "🔎 Zoom Out",
        "fullscreen": "⛶ Fullscreen",
        "back": "↩️ Back",
        "approve": "✅ Approve & Stamp",
        "reject": "❌ Reject",
        "select_all": "Select All",
    },
}

# ------------------------------------------------------------------------------
# أنواع الآليات الافتراضية (قابلة للتعديل من قاعدة البيانات لاحقاً)
# ------------------------------------------------------------------------------
MACHINE_TYPES = ["حفارة ثقيلة", "جرافة كتربيلر", "قلاب شحن", "كرين مرفاع", "مولدة ضخمة"]
MACHINE_STATUSES = ["شغالة", "في الصيانة", "متوقفة"]

# ------------------------------------------------------------------------------
# حالات السند المالي عبر مراحل الاعتماد المزدوج
# ------------------------------------------------------------------------------
VOUCHER_STATUS_NEW = "بانتظار التدقيق"          # وصلت من مندوب المشتريات
VOUCHER_STATUS_REVIEWED = "بانتظار اعتماد المدير"  # دققها موظف التدقيق
VOUCHER_STATUS_APPROVED = "معتمد ومختوم"          # وافق المدير وختمها
VOUCHER_STATUS_REJECTED = "مرفوض"

VOUCHER_ALL_STATUSES = [
    VOUCHER_STATUS_NEW,
    VOUCHER_STATUS_REVIEWED,
    VOUCHER_STATUS_APPROVED,
    VOUCHER_STATUS_REJECTED,
]

# ------------------------------------------------------------------------------
# هيكلية الصلاحيات الدقيقة (Granular Permission Tree)
# كل موديول له صلاحية وصول عامة (access) + صلاحيات فرعية دقيقة
# المالك يبني منها صلاحيات مخصصة باسم يختاره هو، وليست قوالب جاهزة
# ------------------------------------------------------------------------------
PERMISSION_TREE = {
    "dashboard": {
        "label": "لوحة القيادة",
        "children": {
            "access": "الدخول إلى لوحة القيادة",
        },
    },
    "purchases": {
        "label": "المشتريات وتصوير الفواتير",
        "children": {
            "access": "الدخول إلى قسم المشتريات",
            "select_machine": "اختيار الآلية عبر البحث الذكي",
            "capture_photo": "تصوير الفاتورة بالكاميرا الخلفية",
            "upload_photo": "استيراد صورة من المعرض",
            "add_no_photo": "إضافة فاتورة بدون صورة",
            "review_transcribe": "نقل بيانات الصورة إلى السند (تدقيق)",
            "edit": "تعديل فاتورة",
            "delete": "حذف فاتورة",
            "export": "تصدير PDF/CSV",
        },
    },
    "vouchers": {
        "label": "الاعتماد المزدوج للسندات",
        "children": {
            "access": "الدخول إلى شاشة الاعتماد",
            "create": "إنشاء سند مالي مباشر (آلية اختيارية، صورة اختيارية)",
            "approve": "اعتماد وختم السند رقمياً",
            "reject": "رفض السند وإعادته للتدقيق",
            "export": "تصدير PDF للسند",
        },
    },
    "vendors": {
        "label": "مستحقات المحلات",
        "children": {
            "access": "الدخول إلى مستحقات المحلات",
            "edit": "تعديل بيانات محل",
            "delete": "حذف محل",
            "export": "تصدير PDF/Excel",
        },
    },
    "fleet": {
        "label": "إدارة كلف الآليات",
        "children": {
            "access": "الدخول إلى إدارة الآليات",
            "add": "إضافة آلية جديدة",
            "edit": "تعديل بيانات آلية",
            "delete": "حذف آلية",
            "export": "تصدير PDF/Excel",
        },
    },
    "expenses": {
        "label": "سجل النفقات العامة",
        "children": {
            "access": "الدخول إلى سجل النفقات",
            "add": "إضافة نفقة جديدة",
            "edit": "تعديل نفقة",
            "delete": "حذف نفقة",
            "export": "تصدير PDF/Excel",
        },
    },
    "movement": {
        "label": "الحركة والعدادات",
        "children": {
            "access": "الدخول إلى قسم الحركة",
            "select_machine": "اختيار الآلية",
            "capture_photo": "تصوير العداد بالكاميرا الخلفية",
            "upload_photo": "استيراد صورة العداد من المعرض",
        },
    },
    "staff": {
        "label": "إدارة الموظفين والورشات",
        "children": {
            "access": "الدخول إلى إدارة الموظفين",
            "add": "إضافة موظف جديد",
            "edit": "تعديل بيانات موظف",
            "delete": "حذف موظف",
            "ban": "حظر موظف",
            "bulk_actions": "تحديد الكل وإجراء جماعي",
            "export": "تصدير PDF/Excel",
        },
    },
    "audit": {
        "label": "سجل التدقيق الأمني",
        "children": {
            "access": "الدخول إلى سجل التدقيق",
            "delete": "حذف سجلات",
            "export": "تصدير PDF/Excel",
        },
    },
    "rbac": {
        "label": "إدارة المستخدمين والصلاحيات",
        "children": {
            "access": "الدخول إلى إدارة المستخدمين",
            "add": "إضافة مستخدم",
            "edit": "تعديل مستخدم أو صلاحياته",
            "delete": "حذف مستخدم",
            "export": "تصدير PDF/Excel",
        },
    },
    "tracking": {
        "label": "التتبع الجغرافي",
        "children": {
            "access": "الدخول إلى خريطة التتبع",
        },
    },
    "settings": {
        "label": "إعدادات النظام",
        "children": {
            "access": "الدخول إلى الإعدادات",
            "branding": "تغيير الشعار / اسم الشركة / الختم",
            "theme": "تغيير الثيم",
            "change_credentials": "تغيير كلمة المرور واسم المستخدم",
            "full_export": "نسخة احتياطية كاملة (يتطلب كلمة مرور المالك)",
            "full_delete": "حذف شامل لبيانات النظام (يتطلب كلمة مرور المالك)",
        },
    },
}


def default_permissions_all_true():
    """صلاحيات كاملة (تستخدم للمالك/المدير الأساسي فقط)."""
    perms = {}
    for module, meta in PERMISSION_TREE.items():
        perms[module] = {child: True for child in meta["children"]}
    return perms


def default_permissions_all_false():
    """صلاحيات فارغة كنقطة بداية عند إنشاء صلاحية مخصصة جديدة."""
    perms = {}
    for module, meta in PERMISSION_TREE.items():
        perms[module] = {child: False for child in meta["children"]}
    return perms


OWNER_ROLE_NAME = "المالك"  # الدور المحمي الذي يملك كل الصلاحيات دائماً

# اسم باكت التخزين الموحّد في Supabase Storage (باكت واحد فقط، وكل الصور
# تُقسَّم داخله عبر مجلدات فرعية: invoices / odometers / branding).
# إن كان اسم الباكت الذي أنشأته مختلفاً، غيّر القيمة هنا فقط.
STORAGE_BUCKET = "company_data"

THEMES = {
    "ليلي": {
        "bg": "linear-gradient(135deg, #0f2027, #203a43, #2c5364)",
        "text": "#ecf0f1",
        "card_bg": "rgba(255, 255, 255, 0.05)",
        "card_border": "rgba(255, 255, 255, 0.12)",
        "heading": "#f1c40f",
        "sidebar_bg": "#111820",
    },
    "نهاري": {
        "bg": "linear-gradient(135deg, #f5f7fa, #e4ecf1, #dfe9f3)",
        "text": "#1c2833",
        "card_bg": "rgba(0, 0, 0, 0.03)",
        "card_border": "rgba(0, 0, 0, 0.10)",
        "heading": "#1a5276",
        "sidebar_bg": "#ffffff",
    },
}

DEFAULT_SETTINGS = {
    "company_name": "اسم شركتك",
    "manager_name": "",
    "logo_url": None,
    "stamp_url": None,
    "theme": "ليلي",
}
