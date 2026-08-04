import os
import base64
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
from supabase import create_client, Client
import folium
from streamlit_folium import st_folium
import io

# ---------------------------------------------------------
# 1. إعدادات الصفحة الأساسية والثيمات
# ---------------------------------------------------------
st.set_page_config(page_title="نظام ERP المتكامل - إدارة الشركة", layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------
# 2. الاتصال بقاعدة البيانات (Supabase)
# ---------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    # يجب وضع SUPمعك حق تماماً، وأعتذر عن الاختصار غير المقصود في الكود السابق وتخطي بعض التفاصيل. في نظام الرصد المالي، الدقة والشمولية هما الأساس، وكل تفصيل يصنع فرقاً في مراقبة الحسابات. 

لقد قمت الآن بإعادة صياغة الكود ليكون **كاملاً ومفصلاً** دون أي اقتطاع، وأضفت **قسم التقارير** الذي يتضمن ملخصاً للحسابات وجدولاً لعرض السجلات.

### التفاصيل التي تم دمجها في هذا الكود:
1. **واجهة إدخال شاملة:** لتسجيل الواردات والمصروفات بدقة (المبلغ، النوع، البيان، التاريخ).
2. **قسم التقارير المالية:**
   * بطاقات تلخص (إجمالي الواردات، إجمالي المصروفات، الرصيد الحالي الصافي).
   * جدول عرض تفصيلي للسجلات يتحدث برمجياً فور إضافة أي حركة جديدة.
3. **تجهيز نقاط الربط (Hooks):** الكود مهيأ لربطه لاحقاً بقاعدة البيانات الخاصة بك (مثل Supabase) لاسترجاع وحفظ البيانات السحابية.

---

### الكود الشامل (واجهة المستخدم والمنطق البرمجي)

**طريقة الاستبدال:** قم بنسخ هذا الكود بالكامل واستبدله بمحتوى ملف الواجهة (HTML) الحالي لديك من السطر الأول `<!DOCTYPE html>` وحتى السطر الأخير `</html>`.

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>برنامج الرصد المالي - لوحة التحكم والتقارير</title>
    <style>
        /* التنسيقات الشاملة للنظام */
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #34495e;
            --accent-color: #3498db;
            --success-color: #27ae60;
            --danger-color: #e74c3c;
            --bg-color: #ecf0f1;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            margin: 0;
            padding: 20px;
            color: #333;
        }

        .dashboard-container {
            max-width: 1200px;
            margin: 0 auto;
            background: #fff;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        h1, h2 { color: var(--primary-color); border-bottom: 2px solid var(--bg-color); padding-bottom: 10px; }
        
        /* تنسيق نموذج الإدخال */
        .entry-form {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }

        .form-group { display: flex; flex-direction: column; }
        .form-group label { margin-bottom: 8px; font-weight: bold; font-size: 14px; }
        .form-group input, .form-group select {
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 15px;
        }

        .btn-submit {
            grid-column: 1 / -1;
            padding: 12px;
            background-color: var(--accent-color);
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s ease;
        }
        .btn-submit:hover { background-color: #2980b9; }

        /* تنسيقات قسم التقارير */
        .reports-section { margin-top: 40px; }
        
        .summary-cards {
            display: flex;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            flex: 1;
            padding: 20px;
            border-radius: 8px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .card-income { background-color: var(--success-color); }
        .card-expense { background-color: var(--danger-color); }
        .card-balance { background-color: var(--primary-color); }
        
        .card h3 { margin: 0 0 10px 0; font-size: 18px; border: none; padding: 0;}
        .card p { margin: 0; font-size: 24px; font-weight: bold; }

        /* تنسيق جدول السجلات */
        .table-responsive { overflow-x: auto; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: #fff;
        }
        th, td {
            padding: 15px;
            text-align: right;
            border-bottom: 1px solid #ddd;
        }
        th { background-color: var(--secondary-color); color: white; }
        tr:hover { background-color: #f5f5f5; }
        
        .type-income { color: var(--success-color); font-weight: bold; }
        .type-expense { color: var(--danger-color); font-weight: bold; }
    </style>
</head>
<body>

    <div class="dashboard-container">
        <h1>برنامج الرصد المالي</h1>

        <!-- قسم الإدخال -->
        <h2>تسجيل حركة مالية جديدة</h2>
        <div class="entry-form">
            <div class="form-group">
                <label>نوع الحركة:</label>
                <select id="trans-type">
                    <option value="income">وارد (+)</option>
                    <option value="expense">صادر (-)</option>
                </select>
            </div>
            <div class="form-group">
                <label>المبلغ:</label>
                <input type="number" id="trans-amount" placeholder="أدخل المبلغ بدقة..." step="0.01">
            </div>
            <div class="form-group">
                <label>تاريخ الحركة:</label>
                <input type="date" id="trans-date">
            </div>
            <div class="form-group" style="grid-column: 1 / -1;">
                <label>البيان / تفاصيل الحركة:</label>
                <input type="text" id="trans-desc" placeholder="اكتب تفاصيل ومبررات هذه الحركة المباشرة...">
            </div>
            <button class="btn-submit" onclick="saveTransaction()">حفظ السجل المالي</button>
        </div>

        <!-- قسم التقارير الشاملة -->
        <div class="reports-section" id="reports-area">
            <h2>التقارير والإحصائيات</h2>
            
            <div class="summary-cards">
                <div class="card card-income">
                    <h3>إجمالي الواردات</h3>
                    <p id="report-total-income">0.00</p>
                </div>
                <div class="card card-expense">
                    <h3>إجمالي المصروفات</h3>
                    <p id="report-total-expense">0.00</p>
                </div>
                <div class="card card-balance">
                    <h3>الرصيد الصافي</h3>
                    <p id="report-net-balance" dir="ltr">0.00</p>
                </div>
            </div>

            <h2>سجل الحركات المفصل</h2>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>التاريخ</th>
                            <th>النوع</th>
                            <th>المبلغ</th>
                            <th>البيان التفصيلي</th>
                        </tr>
                    </thead>
                    <tbody id="reports-table-body">
                        <!-- سيتم توليد الصفوف هنا بواسطة جافاسكريبت -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // مصفوفة محلية لتخزين البيانات (يتم استبدالها لاحقاً بطلب جلب البيانات من القاعدة السحابية)
        let financialRecords = [];

        // تعيين التاريخ الحالي كافتراضي عند فتح الصفحة
        document.getElementById('trans-date').valueAsDate = new Date();

        // دالة حفظ البيانات الجديدة
        function saveTransaction() {
            const type = document.getElementById('trans-type').value;
            const amountInput = document.getElementById('trans-amount').value;
            const date = document.getElementById('trans-date').value;
            const desc = document.getElementById('trans-desc').value;

            const amount = parseFloat(amountInput);

            // التحقق من صحة البيانات لضمان عدم وجود مدخلات فارغة
            if (isNaN(amount) || amount <= 0 || !date || desc.trim() === '') {
                alert('يرجى التأكد من إدخال المبلغ بشكل صحيح وتعبئة كافة الحقول (البيان والتاريخ).');
                return;
            }

            // تجهيز كائن السجل المالي
            const newRecord = {
                id: Date.now(), // معرف فريد
                type: type,
                amount: amount,
                date: date,
                description: desc
            };

            // إضافة السجل للمصفوفة
            financialRecords.push(newRecord);

            // تفريغ الحقول بعد الحفظ الناجح (ما عدا التاريخ)
            document.getElementById('trans-amount').value = '';
            document.getElementById('trans-desc').value = '';

            // تحديث قسم التقارير فوراً
            generateReports();
            
            // هنا يمكنك لاحقاً وضع كود الإرسال إلى Supabase
            // await supabase.from('transactions').insert([newRecord]);
        }

        // دالة توليد التقارير وتحديث الواجهة
        function generateReports() {
            let totalIncome = 0;
            let totalExpense = 0;
            
            const tableBody = document.getElementById('reports-table-body');
            tableBody.innerHTML = ''; // مسح الجدول القديم

            // ترتيب السجلات من الأحدث للأقدم
            const sortedRecords = [...financialRecords].sort((a, b) => new Date(b.date) - new Date(a.date));

            sortedRecords.forEach(record => {
                // تجميع الأرصدة
                if (record.type === 'income') {
                    totalIncome += record.amount;
                } else if (record.type === 'expense') {
                    totalExpense += record.amount;
                }

                // بناء صف الجدول
                const row = document.createElement('tr');
                
                const typeLabel = record.type === 'income' ? 'وارد' : 'صادر';
                const typeClass = record.type === 'income' ? 'type-income' : 'type-expense';
                
                row.innerHTML = `
                    <td>${record.date}</td>
                    <td class="${typeClass}">${typeLabel}</td>
                    <td dir="ltr" style="text-align: right;">${record.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td>${record.description}</td>
                `;
                
                tableBody.appendChild(row);
            });

            const netBalance = totalIncome - totalExpense;

            // تحديث الأرقام في بطاقات التقارير
            document.getElementById('report-total-income').textContent = totalIncome.toLocaleString(undefined, {minimumFractionDigits: 2});
            document.getElementById('report-total-expense').textContent = totalExpense.toLocaleString(undefined, {minimumFractionDigits: 2});
            document.getElementById('report-net-balance').textContent = netBalance.toLocaleString(undefined, {minimumFractionDigits: 2});
        }
    </script>
</body>
</html>
