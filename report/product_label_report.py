# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class ProductLabelReport(models.AbstractModel):
    _name = 'report.barcode_scanner_label.report_product_label'
    _description = 'Product Label Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepare data for the product label report."""
        _logger.info("=== ProductLabelReport._get_report_values ===")
        _logger.info("docids: %s", docids)
        _logger.info("data keys: %s", data.keys() if data else None)

        docs = self.env['product.label.wizard'].browse(docids)
        _logger.info("docs: %s (exists: %s)", docs, docs.exists())

        # Get template from data or from wizard
        template_id = data.get('template_id') if data else False
        _logger.info("template_id from data: %s", template_id)

        if template_id:
            template = self.env['product.label.template'].browse(template_id)
        else:
            template = docs.template_id if docs else False
        _logger.info("template: %s", template)

        # Get lines_data from data - but product objects won't survive serialization
        # So we need to rebuild from product IDs
        lines_data = []

        # Check if data contains lines_data with product info
        raw_lines_data = data.get('lines_data', []) if data else []
        _logger.info("raw_lines_data count: %s", len(raw_lines_data))

        if raw_lines_data:
            # lines_data was passed but product objects may be lost
            # Check if products are still valid
            for idx, line in enumerate(raw_lines_data):
                product = line.get('product')
                _logger.info("Line %s: product=%s (type=%s)", idx, product, type(product))
                if product and hasattr(product, 'id'):
                    # Product object is still valid
                    lines_data.append(line)
                else:
                    _logger.warning("Line %s: product object is invalid or missing", idx)

        # If lines_data is empty, try to rebuild from wizard
        if not lines_data and docs:
            _logger.info("Rebuilding lines_data from wizard")
            for wizard in docs:
                _logger.info("Wizard %s: product_ids=%s, line_ids=%s",
                           wizard.id, wizard.product_ids.ids, len(wizard.line_ids))

                pricelist = wizard.pricelist_id

                # Try line_ids first
                if wizard.line_ids:
                    for line in wizard.line_ids:
                        if line.quantity > 0:
                            product = line.product_id
                            price = product.list_price
                            if pricelist:
                                price = pricelist._get_product_price(product, 1.0)

                            barcode_image = False
                            if product.barcode and template:
                                barcode_image = template.generate_barcode_image(
                                    product.barcode
                                )

                            for _ in range(line.quantity):
                                lines_data.append({
                                    'product': product,
                                    'barcode': product.barcode or product.default_code or '',
                                    'barcode_image': barcode_image,
                                    'price': price,
                                    'lot': line.lot_id.name if line.lot_id else '',
                                })
                # Fallback to product_ids
                elif wizard.product_ids:
                    _logger.info("Using product_ids fallback")
                    quantity = wizard.quantity_per_product or 1
                    for product in wizard.product_ids:
                        price = product.list_price
                        if pricelist:
                            price = pricelist._get_product_price(product, 1.0)

                        barcode_image = False
                        if product.barcode and template:
                            barcode_image = template.generate_barcode_image(
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

        _logger.info("Final lines_data count: %s", len(lines_data))

        return {
            'doc_ids': docids,
            'doc_model': 'product.label.wizard',
            'docs': docs,
            'template': template,
            'lines_data': lines_data,
            'data': data,
        }
