# 🚜 Suleiman ERP — نظام إدارة الأسطول والمالية

نظام Streamlit سحابي كامل (Frontend + Backend في نفس التطبيق) بتخزين بيانات
وصور عبر **Supabase** (PostgreSQL + Storage)، ونشر عبر **Streamlit Community
Cloud** مرتبط بمستودع **GitHub**.

## 📁 هيكلية المشروع

```
suleiman_erp/
├── app.py                  # نقطة الدخول الرئيسية (شغّل هذا الملف)
├── config.py                # الترجمات AR/KU/EN + شجرة الصلاحيات + الثيمات
├── db.py                    # كل عمليات Supabase (CRUD + Storage)
├── auth.py                  # تسجيل الدخول + الجلسة الدائمة عبر كوكيز
├── permissions.py           # فحص الصلاحيات الدقيقة
├── pdf_utils.py              # توليد PDF عربي (RTL) بترويسة وختم الشركة
├── excel_utils.py            # تصدير Excel/CSV (متعدد الأوراق للنسخة الشاملة)
├── camera_utils.py           # كاميرا خلفية + استيراد من المعرض
├── ui_helpers.py             # بحث ذكي، تنبيهات صوتية، عارض صور، تأكيد إجراء
├── modules/
│   ├── dashboard.py          # لوحة القيادة
│   ├── purchases.py          # المشتريات وتصوير الفواتير
│   ├── vouchers.py           # الاعتماد المزدوج للسندات
│   ├── vendors.py            # مستحقات المحلات
│   ├── fleet.py              # إدارة كلف الآليات
│   ├── movement.py           # الحركة والعدادات
│   ├── staff.py               # إدارة الموظفين والورشات
│   ├── audit.py               # سجل التدقيق الأمني
│   ├── users_rbac.py          # إدارة المستخدمين والصلاحيات المخصصة
│   ├── settings.py            # الإعدادات + النسخ الاحتياطي + الحذف الشامل
│   └── tracking.py            # التتبع الجغرافي للمستخدمين
├── fonts/                     # ضع هنا خط عربي (انظر القسم أدناه) - إلزامي لـ PDF
├── requirements.txt
├── supabase_schema.sql        # نفّذه في Supabase SQL Editor أول شيء
└── .streamlit/secrets.toml.example
```

## 🚀 خطوات النشر (بالترتيب)

### 1) إعداد Supabase
1. أنشئ مشروعاً جديداً على [supabase.com](https://supabase.com).
2. افتح **SQL Editor** ونفّذ محتوى `supabase_schema.sql` كاملاً.
3. من تبويب **Storage** أنشئ 3 Buckets عامة (Public):
   `invoices` ، `odometers` ، `branding`.
4. من **Project Settings → API** انسخ:
   - `Project URL` → سيصبح `SUPABASE_URL`
   - `service_role key` (وليس anon key، لأن كل العمليات تُنفَّذ من الخادم) → `SUPABASE_KEY`
5. أنشئ أول حساب **مالك** يدوياً عبر SQL Editor (راجع التعليق أسفل
   `supabase_schema.sql`) — احسب كلمة مرور SHA-256 أولاً بهذا الأمر على أي
   جهاز فيه Python:
   ```
   python3 -c "import hashlib; print(hashlib.sha256('كلمة_المرور_هنا'.encode()).hexdigest())"
   ```

### 2) الخط العربي (إلزامي لملفات PDF)
نظام ملفات Streamlit Cloud **مؤقت** ولا يمكن تحميل ملفات وقت التشغيل
وتوقّع بقاءها، لذلك يجب تضمين خط عربي **داخل المستودع نفسه**:
1. نزّل خط Amiri (مجاني/مفتوح المصدر) بصيغة `.ttf`.
2. ضع `Amiri-Regular.ttf` و `Amiri-Bold.ttf` داخل مجلد `fonts/`.
3. ادفعهما (commit + push) إلى GitHub مع بقية الكود.
> بدون هذه الخطوة سيعمل النظام بالكامل، لكن نصوص PDF العربية قد تظهر
> بحروف لاتينية احتياطية بدل العربية.

### 3) رفع المشروع إلى GitHub
```bash
git init
git add .
git commit -m "Suleiman ERP - initial version"
git branch -M main
git remote add origin https://github.com/<اسمك>/<اسم-المستودع>.git
git push -u origin main
```
`secrets.toml` الحقيقي **لا يُرفع** أبداً (موجود في `.gitignore` مسبقاً).

### 4) النشر على Streamlit Community Cloud
1. ادخل [share.streamlit.io](https://share.streamlit.io) واربط حساب GitHub.
2. اختر المستودع → الفرع `main` → الملف الرئيسي `app.py`.
3. من **Advanced settings → Secrets** الصق:
   ```toml
   SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
   SUPABASE_KEY = "service_role_key_هنا"
   ```
4. اضغط **Deploy**. سيثبّت Streamlit كل مكتبات `requirements.txt` تلقائياً.
5. أي تعديل لاحق: عدّل الكود محلياً → `git push` → يُعاد النشر تلقائياً.

## 🔑 تسجيل الدخول والصلاحيات
- سجّل دخولك بحساب **المالك** أولاً (الذي أنشأته يدوياً في الخطوة 1-5).
- من **🛡️ إدارة المستخدمين والصلاحيات** أنشئ باقي الحسابات، واكتب اسم
  الصلاحية بنفسك (مثال: "مندوب مشتريات")، ثم فعّل يدوياً كل صلاحية فرعية
  دقيقة يحتاجها فقط (مثال: موظف الحركة يُفعَّل له فقط: الدخول لقسم الحركة +
  اختيار الآلية + التصوير + الرفع، دون أي شيء آخر).
- الحساب صاحب دور "المالك" يملك كل الصلاحيات تلقائياً ولا يمكن حذفه أو
  تقييده من داخل الواجهة.

## ⚠️ قيود تقنية واقعية يجب معرفتها
هذه ليست نواقص في الكود، بل حدود فعلية لأي تطبيق **ويب** (سواء بُني بـ
Streamlit أو غيره) يعمل داخل متصفح:

| الميزة المطلوبة | كيف تعمل فعلياً هنا |
|---|---|
| الكاميرا الخلفية حصراً | تُفتح تلقائياً كافتراضي على أغلب متصفحات الجوال؛ لا توجد واجهة برمجية في Streamlit لإجباره 100% دون مكوّن JS مخصص إضافي، لكن تم توفير بديل "استيراد من المعرض" دائماً كما طلبت. |
| التنبيه الصوتي الفوري | يعمل فعلياً (Toast + صوت) طالما المستخدم المستهدف فاتح تبويب النظام في متصفحه في تلك اللحظة. لإشعارات Push حقيقية تصل حتى لو أغلق المتصفح، يلزم تطبيق جوال منفصل (PWA أو Native) يتصل بنفس قاعدة Supabase. |
| التتبع الجغرافي الحي | يعمل عبر Geolocation API في المتصفح طالما الصفحة مفتوحة ونشطة، ويطلب إذن المستخدم. لا يوجد تتبع خلفي دائم 24/7 من متصفح ويب - هذا قيد على كل الويب وليس خاصاً بالنظام. |
| "تبقى الجلسة محفوظة حتى تسجّل الخروج" | مُنفَّذ فعلياً عبر كوكي دائم صالح لمدة سنة + جدول `sessions` في Supabase، ويُحذف فقط عند الضغط على "تسجيل الخروج". |

## 🧩 المكتبات الرئيسية المستخدمة
`streamlit` `supabase-py` `pandas` `fpdf2` `arabic-reshaper` `python-bidi`
`XlsxWriter` `extra-streamlit-components` `streamlit-js-eval`
`streamlit-autorefresh` `pydeck`

## 🛠️ التشغيل محلياً للاختبار (اختياري)
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# عدّل القيم داخل secrets.toml
streamlit run app.py
```
