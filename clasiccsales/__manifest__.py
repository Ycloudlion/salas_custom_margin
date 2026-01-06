# -*- coding: utf-8 -*-
{
    'name': 'Custom Sales Margin',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Display margins grouped by section and subsection in quotations',
    'description': """
        This module adds a new tab in quotations/sales orders
        that displays margin and margin percentage grouped by section and subsection,
        with totals separated by each section.
    """,
    'author': 'Clasicc',
    'depends': ['sale', 'sale_margin'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'clasiccsales/static/src/js/section_margin_widget.js',
            'clasiccsales/static/src/xml/section_margin_widget.xml',
            'clasiccsales/static/src/css/section_margin_widget.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

