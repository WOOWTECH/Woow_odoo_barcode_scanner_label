# -*- coding: utf-8 -*-
{
    'name': 'Barcode Scanner - Label Printing',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Barcode',
    'summary': 'Generate and print barcode/QR code labels for products',
    'description': """
Barcode Scanner - Label Printing
================================

This module provides barcode and QR code label generation and printing:

* Generate barcode labels (EAN-13, EAN-8, UPC-A, Code128)
* Generate QR code labels
* Customizable label templates
* Dynamic fields: product name, price, company logo, lot/serial, expiry
* Print from: products, sales orders, purchase orders, pickings, invoices
* Page orientation control (portrait/landscape)
* Multiple label sizes support

Uses python-barcode and qrcode libraries for generation.

Requires the Barcode Scanner Base module.
    """,
    'author': 'Woow Tech',
    'website': 'https://github.com/woowtech',
    'license': 'LGPL-3',
    'depends': [
        'barcode_scanner_base',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/paperformat_data.xml',
        'views/product_label_views.xml',
        'wizard/product_label_wizard_views.xml',
        'report/product_label_report.xml',
        'report/product_label_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'barcode_scanner_label/static/src/css/label_preview.css',
        ],
    },
    'external_dependencies': {
        'python': ['barcode', 'qrcode', 'PIL'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
