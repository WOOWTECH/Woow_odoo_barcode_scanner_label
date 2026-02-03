# PRD: 修復標籤列印空白問題

## 問題描述

使用者從產品列表選擇產品並點擊「列印標籤」後，產生的 PDF 是空白的，沒有任何標籤內容。

## 根本原因分析

### 問題流程追蹤

```
1. 使用者選擇產品 → 點擊「列印標籤」
2. action_print_label() 開啟精靈視窗，context 包含 active_ids
3. default_get() 被呼叫，設定 product_ids = [(6, 0, active_ids)]
4. ❌ _onchange_products() 沒有被觸發（onchange 只在前端 UI 變更時觸發）
5. ❌ line_ids 保持為空
6. 使用者點擊「列印」
7. action_print_labels() 迭代 self.line_ids → 空列表
8. 報表範本迭代 docs.line_ids → 空列表
9. ❌ PDF 輸出空白
```

### 核心問題

**檔案**: `wizard/product_label_wizard.py`

**問題 1**: `default_get()` 方法（第 47-76 行）只設定 `product_ids`，但沒有同時初始化 `line_ids`。

```python
# 目前的程式碼
if active_model == 'product.product':
    res['product_ids'] = [(6, 0, active_ids)]  # ✅ 設定 product_ids
    # ❌ 沒有設定 line_ids
```

**問題 2**: `@api.onchange('product_ids', 'quantity_per_product')` 裝飾器定義的 `_onchange_products()` 方法只在前端 UI 互動時觸發，後端 API 呼叫時不會自動執行。

**問題 3**: 即使使用者在精靈介面中手動變更產品或數量，觸發 onchange，產生的 `line_ids` 也需要在前端被正確保存才會傳遞到後端。

## 解決方案

### 方案 A：在 `default_get()` 中直接初始化 `line_ids`（推薦）

在 `default_get()` 方法中，設定 `product_ids` 的同時，也建立對應的 `line_ids`。

**優點**：
- 一次性解決問題
- 不依賴前端 onchange 觸發
- 使用者開啟精靈時立即看到標籤行

**修改位置**: `wizard/product_label_wizard.py:default_get()`

```python
@api.model
def default_get(self, fields_list):
    """Set default products from context."""
    res = super().default_get(fields_list)
    active_ids = self.env.context.get('active_ids', [])
    active_model = self.env.context.get('active_model')

    products = self.env['product.product']

    if active_model == 'product.product':
        products = self.env['product.product'].browse(active_ids)
    elif active_model == 'product.template':
        templates = self.env['product.template'].browse(active_ids)
        products = templates.mapped('product_variant_ids')
    elif active_model == 'sale.order':
        orders = self.env['sale.order'].browse(active_ids)
        products = orders.mapped('order_line.product_id')
    elif active_model == 'purchase.order':
        orders = self.env['purchase.order'].browse(active_ids)
        products = orders.mapped('order_line.product_id')
    elif active_model == 'stock.picking':
        pickings = self.env['stock.picking'].browse(active_ids)
        products = pickings.mapped('move_ids.product_id')
    elif active_model == 'account.move':
        moves = self.env['account.move'].browse(active_ids)
        products = moves.mapped('invoice_line_ids.product_id')

    if products:
        res['product_ids'] = [(6, 0, products.ids)]
        # 同時初始化 line_ids
        quantity = res.get('quantity_per_product', 1) or 1
        lines = []
        for product in products:
            lines.append((0, 0, {
                'product_id': product.id,
                'quantity': quantity,
            }))
        res['line_ids'] = lines

    return res
```

### 方案 B：使用 `@api.model_create_multi` 或 `create()` 覆寫

在 wizard 建立時自動填充 line_ids。

**缺點**：較複雜，需要處理更多邊界情況。

### 方案 C：改用 `@api.depends` 而非 `@api.onchange`

將 `_onchange_products` 改為 computed field 邏輯。

**缺點**：改動較大，可能影響 UI 互動體驗。

## 建議採用方案

**採用方案 A**：在 `default_get()` 中直接初始化 `line_ids`

這是最簡單、最直接的解決方案，且符合 Odoo 的最佳實踐。

## 實作步驟

1. [ ] 修改 `wizard/product_label_wizard.py` 的 `default_get()` 方法
2. [ ] 測試從不同來源列印標籤：
   - [ ] product.product（產品變體）
   - [ ] product.template（產品範本）
   - [ ] sale.order（銷售訂單）
   - [ ] purchase.order（採購訂單）
   - [ ] stock.picking（調撥單）
   - [ ] account.move（發票）
3. [ ] 確認 PDF 正確顯示標籤內容
4. [ ] 確認 onchange 在 UI 中仍正常運作（使用者手動增減產品時）

## 預期結果

修復後，使用者從任何來源點擊「列印標籤」：
1. 精靈視窗開啟時，`line_ids` 已預先填充
2. 使用者可以調整數量或移除特定產品
3. 點擊「列印」後，PDF 正確顯示所有標籤

## 附註

### 相關檔案

| 檔案 | 說明 |
|------|------|
| `wizard/product_label_wizard.py` | 需修改 - 精靈邏輯 |
| `wizard/product_label_wizard_views.xml` | 參考 - 精靈視圖 |
| `report/product_label_templates.xml` | 參考 - 報表範本 |
| `models/product_label.py` | 參考 - 標籤範本模型 |

### 測試重點

- 無產品條碼時的處理
- 多產品批次列印
- 不同標籤範本的相容性
