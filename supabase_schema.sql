-- ==============================================================================
-- Suleiman ERP - Supabase Schema
-- نفّذ هذا الملف كاملاً من: Supabase Dashboard → SQL Editor → New query → Run
-- ==============================================================================

-- جدول المستخدمين
create table if not exists users (
    id text primary key,
    username text unique not null,
    full_name text not null,
    role text not null,
    password_hash text not null,
    permissions jsonb default '{}'::jsonb,
    status text default 'نشط',
    created_at timestamp default now()
);

-- جلسات الدخول الدائمة (لبقاء المستخدم مسجلاً حتى الخروج اليدوي)
create table if not exists sessions (
    token text primary key,
    username text not null references users(username) on delete cascade,
    created_at timestamp default now()
);

-- الآليات
create table if not exists fleet (
    id text primary key,
    code text unique not null,
    type text,
    driver text,
    status text default 'شغالة',
    chassis_no text,
    engine_no text,
    maintenance_interval_days int default 90,
    next_maintenance_date date,
    odometer numeric default 0,
    odometer_image_url text,
    odometer_updated_at timestamp,
    notes text,
    created_at timestamp default now()
);

-- النفقات العامة (غير مرتبطة بآلية محددة)
create table if not exists expenses (
    id text primary key,
    title text not null,
    amount numeric default 0,
    category text,
    notes text,
    expense_date date,
    created_at timestamp default now()
);

-- الموظفين
create table if not exists staff (
    id text primary key,
    emp_id text unique not null,
    name text not null,
    job text,
    salary numeric default 0,
    phone text,
    status text default 'نشط',
    notes text,
    created_at timestamp default now()
);

-- السندات المالية / الفواتير
create table if not exists vouchers (
    id text primary key,
    voucher_no text unique not null,
    machine_code text,
    vendor text not null,
    amount numeric default 0,
    notes text,
    image_url text,
    status text default 'بانتظار التدقيق',
    entered_by text,
    reviewed_by text,
    reviewed_at timestamp,
    approved_by text,
    approved_at timestamp,
    created_at timestamp default now()
);

-- سجل التدقيق الأمني
create table if not exists audit_logs (
    id text primary key,
    username text,
    full_name text,
    action text,
    details text,
    timestamp timestamp default now()
);

-- إعدادات النظام (صف واحد فقط id = 1)
create table if not exists settings (
    id int primary key default 1,
    company_name text default 'شركة سليمان للمقاولات',
    manager_name text default 'م. سليمان نبهان',
    logo_url text,
    stamp_url text,
    theme text default 'ليلي'
);
insert into settings (id) values (1) on conflict (id) do nothing;

-- مواقع المستخدمين (التتبع الجغرافي)
create table if not exists locations (
    username text primary key references users(username) on delete cascade,
    lat double precision,
    lon double precision,
    status text default 'ثابت',
    updated_at timestamp default now()
);

-- ==============================================================================
-- ملاحظة أمان: التطبيق يتصل بـ Supabase عبر مفتاح service_role من جهة
-- الخادم (Streamlit) فقط، لذا يمكن ترك RLS معطلة على هذه الجداول أو
-- تفعيلها وإضافة سياسات تسمح فقط لـ service_role. لا تستخدم مفتاح
-- service_role أبداً داخل كود يعمل في متصفح المستخدم مباشرة.
-- ==============================================================================

-- إنشاء أول حساب مالك يدوياً (غيّر القيم قبل التنفيذ) - كلمة المرور هنا نصية
-- مؤقتاً، سيقوم النظام بترحيلها لصيغة SHA-256 المشفّرة عند أول تسجيل دخول
-- أو تغيير كلمة مرور من شاشة الإعدادات. يُفضّل إدخالها مباشرة كـ SHA-256.
-- مثال (استبدل my_username / My Full Name / hashed_password_here):
--
-- insert into users (id, username, full_name, role, password_hash, permissions, status)
-- values ('USR-OWNER01', 'admin', 'اسم المالك', 'المالك', 'ضع_هنا_قيمة_sha256', '{}'::jsonb, 'نشط');
--
-- لحساب SHA-256 لكلمة المرور محلياً على جهازك (بدون إنترنت):
--   python3 -c "import hashlib; print(hashlib.sha256('كلمة_المرور_هنا'.encode()).hexdigest())"

-- ==============================================================================
-- Supabase Storage: أنشئ من تبويب Storage في لوحة Supabase البكتات التالية
-- (اجعلها Public لتظهر الصور مباشرة داخل تقارير PDF):
--   1) invoices   → صور فواتير المشتريات
--   2) odometers  → صور قراءات العدادات
--   3) branding   → شعار الشركة + صورة الختم الرقمي
-- ==============================================================================
