# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProductLabelWizard(models.TransientModel):
    _name = 'product.label.wizard'
    _description = 'Product Label Printing Wizard'

    template_id = fields.Many2one(
        comodel_name='product.label.template',
        string='Label Template',
        required=True,
        default=lambda self: self.env['product.label.template'].search([], limit=1),
    )
    product_ids = fields.Many2many(
        comodel_name='product.product',
        string='Products',
    )
    line_ids = fields.One2many(
        comodel_name='product.label.line',
        inverse_name='wizard_id',
        string='Label Lines',
    )
    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string='Pricelist',
        help="Pricelist to use for pricing on labels",
    )
    quantity_per_product = fields.Integer(
        string='Quantity per Product',
        default=1,
        help="Number of labels to print per product",
    )

    @api.onchange('product_ids', 'quantity_per_product')
    def _onchange_products(self):
        """Populate lines when products change."""
        lines = [(5, 0, 0)]  # Clear existing lines
        for product in self.product_ids:
            lines.append((0, 0, {
                'product_id': product.id,
                'quantity': self.quantity_per_product,
            }))
        self.line_ids = lines

    @api.model
    def default_get(self, fields_list):
        """Set default products from context."""
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model')

        if active_model == 'product.product':
            res['product_ids'] = [(6, 0, active_ids)]
        elif active_model == 'product.template':
            templates = self.env['product.template'].browse(active_ids)
            product_ids = templates.mapped('product_variant_ids').ids
            res['product_ids'] = [(6, 0, product_ids)]
        elif active_model == 'sale.order':
            orders = self.env['sale.order'].browse(active_ids)
            product_ids = orders.mapped('order_line.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]
        elif active_model == 'purchase.order':
            orders = self.env['purchase.order'].browse(active_ids)
            product_ids = orders.mapped('order_line.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]
        elif active_model == 'stock.picking':
            pickings = self.env['stock.picking'].browse(active_ids)
            product_ids = pickings.mapped('move_ids.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]
        elif active_model == 'account.move':
            moves = self.env['account.move'].browse(active_ids)
            product_ids = moves.mapped('invoice_line_ids.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]

        return res

    def action_print_labels(self):
        """Generate and print labels."""
        self.ensure_one()

        # Prepare data for the report
        lines_data = []
        for line in self.line_ids:
            if line.quantity > 0:
                product = line.product_id

                # Get price
                price = product.list_price
                if self.pricelist_id:
                    price = self.pricelist_id._get_product_price(
                        product, 1.0
                    )

                # Generate barcode image
                barcode_image = False
                if product.barcode:
                    barcode_image = self.template_id.generate_barcode_image(
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

        # Return report action
        return self.env.ref(
            'barcode_scanner_label.action_report_product_label'
        ).report_action(self, data={
            'template_id': self.template_id.id,
            'lines_data': lines_data,
            'pricelist_id': self.pricelist_id.id if self.pricelist_id else False,
        })

    def action_preview(self):
        """Preview labels (same as print but opens in new tab)."""
        return self.action_print_labels()
