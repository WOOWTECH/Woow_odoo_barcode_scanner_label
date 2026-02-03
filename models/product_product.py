# -*- coding: utf-8 -*-
import base64
import io
from odoo import api, fields, models, _

try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


class ProductProduct(models.Model):
    _inherit = 'product.product'

    barcode_image = fields.Binary(
        string='Barcode Image',
        compute='_compute_barcode_image',
        store=False,
    )
    qr_code_image = fields.Binary(
        string='QR Code Image',
        compute='_compute_qr_code_image',
        store=False,
    )

    @api.depends('barcode')
    def _compute_barcode_image(self):
        """Generate barcode image from product barcode."""
        for product in self:
            if product.barcode and BARCODE_AVAILABLE:
                product.barcode_image = self._generate_barcode_image(product.barcode)
            else:
                product.barcode_image = False

    @api.depends('barcode', 'default_code')
    def _compute_qr_code_image(self):
        """Generate QR code image from product barcode or reference."""
        for product in self:
            value = product.barcode or product.default_code
            if value and QRCODE_AVAILABLE:
                product.qr_code_image = self._generate_qr_code_image(value)
            else:
                product.qr_code_image = False

    @staticmethod
    def _generate_barcode_image(barcode_value, barcode_type='code128'):
        """Generate a barcode image.

        Args:
            barcode_value: The value to encode
            barcode_type: The barcode format (default: code128)

        Returns:
            base64 encoded PNG image
        """
        if not BARCODE_AVAILABLE or not barcode_value:
            return False

        try:
            # Determine barcode type based on value
            if barcode_value.isdigit():
                if len(barcode_value) == 13:
                    barcode_type = 'ean13'
                elif len(barcode_value) == 8:
                    barcode_type = 'ean8'
                elif len(barcode_value) == 12:
                    barcode_type = 'upca'

            BarcodeClass = barcode.get_barcode_class(barcode_type)
            bc = BarcodeClass(str(barcode_value), writer=ImageWriter())

            buffer = io.BytesIO()
            bc.write(buffer, options={
                'module_width': 0.25,
                'module_height': 12.0,
                'quiet_zone': 3.0,
                'font_size': 10,
                'text_distance': 3.0,
            })

            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode('utf-8')

        except Exception:
            # Fallback to code128
            try:
                BarcodeClass = barcode.get_barcode_class('code128')
                bc = BarcodeClass(str(barcode_value), writer=ImageWriter())
                buffer = io.BytesIO()
                bc.write(buffer)
                buffer.seek(0)
                return base64.b64encode(buffer.read()).decode('utf-8')
            except Exception:
                return False

    @staticmethod
    def _generate_qr_code_image(value):
        """Generate a QR code image.

        Args:
            value: The value to encode

        Returns:
            base64 encoded PNG image
        """
        if not QRCODE_AVAILABLE or not value:
            return False

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(str(value))
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            return base64.b64encode(buffer.read()).decode('utf-8')

        except Exception:
            return False

    def action_print_label(self):
        """Open the label printing wizard for selected products."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Labels'),
            'res_model': 'product.label.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_ids': [(6, 0, self.ids)],
                'active_model': 'product.product',
                'active_ids': self.ids,
            },
        }


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_print_label(self):
        """Open the label printing wizard for selected products."""
        products = self.mapped('product_variant_ids')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Labels'),
            'res_model': 'product.label.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_ids': [(6, 0, products.ids)],
                'active_model': 'product.product',
                'active_ids': products.ids,
            },
        }
