# -*- coding: utf-8 -*-
import base64
import io
from odoo import api, fields, models, _
from odoo.exceptions import UserError

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


class ProductLabelTemplate(models.Model):
    _name = 'product.label.template'
    _description = 'Product Label Template'
    _order = 'sequence, name'

    name = fields.Char(
        string='Template Name',
        required=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    # Label dimensions
    label_width = fields.Float(
        string='Label Width (mm)',
        default=50.0,
        required=True,
    )
    label_height = fields.Float(
        string='Label Height (mm)',
        default=30.0,
        required=True,
    )
    labels_per_row = fields.Integer(
        string='Labels per Row',
        default=2,
        required=True,
    )
    labels_per_column = fields.Integer(
        string='Labels per Column',
        default=5,
        required=True,
    )

    # Barcode settings
    barcode_type = fields.Selection(
        selection=[
            ('ean13', 'EAN-13'),
            ('ean8', 'EAN-8'),
            ('upca', 'UPC-A'),
            ('code128', 'Code 128'),
            ('code39', 'Code 39'),
            ('qr', 'QR Code'),
        ],
        string='Barcode Type',
        default='ean13',
        required=True,
    )
    barcode_width = fields.Float(
        string='Barcode Width (mm)',
        default=40.0,
    )
    barcode_height = fields.Float(
        string='Barcode Height (mm)',
        default=15.0,
    )

    # Content options
    show_product_name = fields.Boolean(
        string='Show Product Name',
        default=True,
    )
    show_internal_ref = fields.Boolean(
        string='Show Internal Reference',
        default=True,
    )
    show_barcode_text = fields.Boolean(
        string='Show Barcode Text',
        default=True,
    )
    show_price = fields.Boolean(
        string='Show Price',
        default=True,
    )
    show_price_with_tax = fields.Boolean(
        string='Price Includes Tax',
        default=True,
    )
    show_company_logo = fields.Boolean(
        string='Show Company Logo',
        default=False,
    )
    show_lot_serial = fields.Boolean(
        string='Show Lot/Serial',
        default=False,
    )
    show_expiry_date = fields.Boolean(
        string='Show Expiry Date',
        default=False,
    )

    # Styling
    font_size = fields.Integer(
        string='Font Size (pt)',
        default=10,
    )
    price_font_size = fields.Integer(
        string='Price Font Size (pt)',
        default=14,
    )

    def generate_barcode_image(self, barcode_value, barcode_type=None):
        """Generate a barcode image.

        Args:
            barcode_value: The value to encode
            barcode_type: Override barcode type (optional)

        Returns:
            base64 encoded image string
        """
        if not barcode_value:
            return False

        barcode_type = barcode_type or self.barcode_type

        if barcode_type == 'qr':
            return self._generate_qr_code(barcode_value)
        else:
            return self._generate_barcode(barcode_value, barcode_type)

    def _generate_barcode(self, value, barcode_type):
        """Generate a 1D barcode image.

        Args:
            value: The value to encode
            barcode_type: The barcode format

        Returns:
            base64 encoded PNG image
        """
        if not BARCODE_AVAILABLE:
            raise UserError(_('python-barcode library is not installed. Please install it with: pip install python-barcode[images]'))

        # Map our barcode types to python-barcode types
        barcode_map = {
            'ean13': 'ean13',
            'ean8': 'ean8',
            'upca': 'upca',
            'code128': 'code128',
            'code39': 'code39',
        }

        bc_type = barcode_map.get(barcode_type, 'code128')

        try:
            # Get barcode class
            BarcodeClass = barcode.get_barcode_class(bc_type)

            # Generate barcode
            bc = BarcodeClass(str(value), writer=ImageWriter())

            # Write to buffer
            buffer = io.BytesIO()
            bc.write(buffer, options={
                'module_width': 0.2,
                'module_height': 10.0,
                'quiet_zone': 2.0,
                'font_size': 8 if self.show_barcode_text else 0,
                'text_distance': 3.0,
                'write_text': self.show_barcode_text,
            })

            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode('utf-8')

        except Exception as e:
            # Fallback to Code128 for invalid barcodes
            try:
                BarcodeClass = barcode.get_barcode_class('code128')
                bc = BarcodeClass(str(value), writer=ImageWriter())
                buffer = io.BytesIO()
                bc.write(buffer)
                buffer.seek(0)
                return base64.b64encode(buffer.read()).decode('utf-8')
            except Exception:
                return False

    def _generate_qr_code(self, value):
        """Generate a QR code image.

        Args:
            value: The value to encode

        Returns:
            base64 encoded PNG image
        """
        if not QRCODE_AVAILABLE:
            raise UserError(_('qrcode library is not installed. Please install it with: pip install qrcode[pil]'))

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


class ProductLabelLine(models.TransientModel):
    _name = 'product.label.line'
    _description = 'Product Label Line'

    wizard_id = fields.Many2one(
        comodel_name='product.label.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
    )
    quantity = fields.Integer(
        string='Quantity',
        default=1,
        required=True,
    )
    barcode = fields.Char(
        string='Barcode',
        related='product_id.barcode',
    )
    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string='Lot/Serial',
    )
