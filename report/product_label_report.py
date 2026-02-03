# -*- coding: utf-8 -*-
from odoo import api, models


class ProductLabelReport(models.AbstractModel):
    _name = 'report.barcode_scanner_label.report_product_label'
    _description = 'Product Label Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepare data for the product label report."""
        docs = self.env['product.label.wizard'].browse(docids)

        # Get template from data or from wizard
        template_id = data.get('template_id') if data else False
        if template_id:
            template = self.env['product.label.template'].browse(template_id)
        else:
            template = docs.template_id if docs else False

        # Get lines data from data parameter or from wizard
        lines_data = data.get('lines_data', []) if data else []

        # If no lines_data provided, build from wizard line_ids
        if not lines_data and docs:
            for wizard in docs:
                pricelist = wizard.pricelist_id
                for line in wizard.line_ids:
                    if line.quantity > 0:
                        product = line.product_id

                        # Get price
                        price = product.list_price
                        if pricelist:
                            price = pricelist._get_product_price(product, 1.0)

                        # Generate barcode image
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

        return {
            'doc_ids': docids,
            'doc_model': 'product.label.wizard',
            'docs': docs,
            'template': template,
            'lines_data': lines_data,
            'data': data,
        }
