# PRD: 修復標籤中文顯示亂碼問題

## 問題描述

列印標籤時，產品名稱顯示為亂碼而不是正確的中文字元。

## 根本原因分析

### 資料庫中的產品名稱格式

產品名稱在資料庫中以 **JSON 多語言格式** 儲存：

```json
{"en_US": "Four Person Desk", "zh_CN": "四人桌子", "zh_TW": "四人辦公桌"}
```

### 問題流程

```
1. 報表處理器取得 product.name
2. Odoo 應該根據當前語言上下文返回對應翻譯
3. 但在報表渲染過程中，語言上下文可能丟失或不正確
4. 導致返回原始 JSON 字串或錯誤編碼
5. wkhtmltopdf 嘗試渲染時顯示亂碼
```

### 驗證

資料庫查詢結果：
```sql
SELECT name FROM product_template LIMIT 1;
-- 結果: {"en_US": "Four Person Desk", "zh_CN": "四人桌子", "zh_TW": "四人辦公桌"}
```

這證明問題不是字體問題，而是 **Odoo 翻譯機制** 在報表上下文中沒有正確運作。

## 可能的原因

### 原因 1: 報表 Context 缺少語言設定

報表處理器 (`_get_report_values`) 可能沒有繼承正確的語言上下文。

### 原因 2: 產品物件在錯誤的語言環境中讀取

當我們用 `self.env['product.product'].browse(product_ids)` 取得產品時，env 可能沒有正確的語言設定。

### 原因 3: wkhtmltopdf 渲染時的編碼問題

HTML 可能沒有正確宣告 UTF-8 編碼。

## 解決方案

### 方案 A: 確保報表上下文包含正確語言（推薦）

在報表處理器中，確保使用正確的語言上下文來讀取產品：

```python
@api.model
def _get_report_values(self, docids, data=None):
    # 取得當前使用者語言或從 context 取得
    lang = self.env.context.get('lang') or self.env.user.lang or 'en_US'

    # 使用正確語言上下文來讀取產品
    Product = self.env['product.product'].with_context(lang=lang)
    products_by_id = {p.id: p for p in Product.browse(product_ids)}
```

### 方案 B: 直接從翻譯欄位取得名稱

如果產品名稱是 JSON 格式，直接解析並取得對應語言的名稱：

```python
import json

def get_translated_name(name, lang):
    if isinstance(name, str) and name.startswith('{'):
        try:
            translations = json.loads(name)
            return translations.get(lang) or translations.get('en_US') or name
        except:
            return name
    return name
```

### 方案 C: 確保 HTML 正確宣告編碼

在報表模板中加入正確的 meta 標籤：

```xml
<head>
    <meta charset="UTF-8"/>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
</head>
```

## 建議採用方案

**優先嘗試方案 A**，因為這是 Odoo 標準的多語言處理方式。

如果方案 A 無效，則嘗試方案 C 確保編碼正確。

方案 B 作為最後手段，因為它繞過了 Odoo 的翻譯機制。

## 實作步驟

1. [ ] 修改 `report/product_label_report.py`，確保使用正確語言上下文
2. [ ] 修改報表模板，加入 UTF-8 編碼聲明
3. [ ] 測試中文標籤列印
4. [ ] 確認不同語言環境下都能正確顯示

## 測試重點

- 使用繁體中文 (zh_TW) 使用者測試
- 使用簡體中文 (zh_CN) 使用者測試
- 使用英文 (en_US) 使用者測試
- 確認產品名稱在各語言下都正確顯示
