# PRD: 修復標籤列印空白問題 V2

## 問題描述

使用者從產品列表選擇產品並點擊「列印標籤」後，產生的 PDF 是空白的，沒有任何標籤內容。

## 深入根本原因分析

### Odoo Wizard 的運作機制

```
1. 使用者點擊「列印標籤」按鈕
2. action_print_label() 返回 act_window action
3. Odoo 前端開啟新視窗，呼叫 default_get() 取得預設值
4. default_get() 返回：
   {
     'product_ids': [(6, 0, [1, 2, 3])],
     'line_ids': [(0, 0, {'product_id': 1, 'quantity': 1}), ...]
   }
5. 前端在記憶體中創建虛擬記錄顯示在 UI 上
6. ⚠️ 此時 wizard 記錄尚未存在於資料庫中

7. 使用者點擊「Print Labels」按鈕
8. 前端呼叫 create() 建立 wizard 記錄
9. ⚠️ 關鍵問題：One2many 欄位的 Command tuples 需要從前端正確傳遞
10. Odoo 呼叫 action_print_labels()
11. self.line_ids 可能是空的（取決於前端傳遞的資料）
```

### 問題核心

**One2many 欄位 (`line_ids`) 在 TransientModel 中的行為**：

1. `default_get()` 返回的 `[(0, 0, {...})]` 格式會在前端被解析
2. 前端顯示這些虛擬記錄給使用者
3. 當使用者點擊按鈕時，Odoo 會 `create()` wizard 記錄
4. **問題**：前端需要正確地將 `line_ids` 的資料傳回後端

### 實際問題點

檢查 `action_print_labels()` 第 93 行：

```python
for line in self.line_ids:  # ← self.line_ids 可能是空的！
```

原因：
1. Wizard 是 TransientModel，每次請求可能是新的記錄
2. `line_ids` 是 One2many，依賴 `product.label.line` 記錄的 `wizard_id` 外鍵
3. 如果 `product.label.line` 記錄沒有被正確創建，`line_ids` 就是空的

### 驗證問題的方法

在 `action_print_labels()` 加入除錯：

```python
def action_print_labels(self):
    self.ensure_one()
    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("=== DEBUG ===")
    _logger.info("Wizard ID: %s", self.id)
    _logger.info("product_ids: %s", self.product_ids.ids)
    _logger.info("line_ids count: %s", len(self.line_ids))
    for line in self.line_ids:
        _logger.info("  Line: product=%s, qty=%s", line.product_id.name, line.quantity)
```

## 解決方案

### 方案 A：不依賴 `line_ids`，直接使用 `product_ids`（推薦）

在 `action_print_labels()` 中，如果 `line_ids` 為空，就從 `product_ids` 建立標籤資料。

**優點**：
- 最簡單直接
- 不需要改變 Odoo 的標準行為
- 兼容性最好

**修改位置**: `wizard/product_label_wizard.py:action_print_labels()`

```python
def action_print_labels(self):
    """Generate and print labels."""
    self.ensure_one()

    # Prepare data for the report
    lines_data = []

    # If line_ids exists, use it; otherwise fallback to product_ids
    if self.line_ids:
        for line in self.line_ids:
            if line.quantity > 0:
                product = line.product_id
                # ... 現有邏輯 ...
    else:
        # Fallback: use product_ids directly
        quantity = self.quantity_per_product or 1
        for product in self.product_ids:
            price = product.list_price
            if self.pricelist_id:
                price = self.pricelist_id._get_product_price(product, 1.0)

            barcode_image = False
            if product.barcode:
                barcode_image = self.template_id.generate_barcode_image(
                    product.barcode
                )

            for _ in range(quantity):
                lines_data.append({
                    'product': product,
                    'barcode': product.barcode or product.default_code or '',
                    'barcode_image': barcode_image,
                    'price': price,
                    'lot': '',
                })

    # Return report action
    return self.env.ref(
        'barcode_scanner_label.action_report_product_label'
    ).report_action(self, data={
        'template_id': self.template_id.id,
        'lines_data': lines_data,
        'pricelist_id': self.pricelist_id.id if self.pricelist_id else False,
    })
```

### 方案 B：使用 `@api.model_create_multi` 覆寫 `create()`

在 wizard 建立時，手動創建 `line_ids` 記錄。

**缺點**：較複雜，需要處理更多邊界情況。

### 方案 C：改用 stored=True 的 Many2many 關係

將 `line_ids` 的設計改為使用 Many2many + 額外欄位模型。

**缺點**：改動太大，不建議。

## 建議採用方案

**採用方案 A**：在 `action_print_labels()` 中加入 fallback 邏輯

這是最簡單、最可靠的解決方案。

## 實作步驟

1. [ ] 修改 `wizard/product_label_wizard.py` 的 `action_print_labels()` 方法
2. [ ] 加入 fallback 邏輯：若 `line_ids` 為空，使用 `product_ids`
3. [ ] 測試列印功能
4. [ ] 確認 PDF 正確顯示標籤內容

## 預期結果

修復後：
1. 無論 `line_ids` 是否有資料，都能正確列印
2. 如果有 `line_ids`，使用個別產品的數量設定
3. 如果沒有 `line_ids`，使用 `quantity_per_product` 作為預設數量

## 附註

### 額外發現

報表範本現在使用 `lines_data`（由 wizard 或報表處理器準備），所以關鍵是確保 `lines_data` 被正確填充。

### 測試重點

1. 從產品列表列印（`product.product`）
2. 從產品範本列印（`product.template`）
3. 確認數量設定正確運作
