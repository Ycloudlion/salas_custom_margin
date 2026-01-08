# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json


class MarginHistory(models.Model):
    _name = 'sale.order.margin.history'
    _description = 'Margin Adjustment History'
    _order = 'create_date desc'

    order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade'
    )
    
    adjustment_type = fields.Selection([
        ('section', 'Section'),
        ('subsection', 'Subsection'),
        ('product', 'Product'),
    ], string='Adjustment Type', required=True)
    
    section_name = fields.Char(string='Section Name')
    subsection_name = fields.Char(string='Subsection Name')
    line_id = fields.Many2one('sale.order.line', string='Product Line')
    product_name = fields.Char(string='Product Name')
    
    old_margin_percent = fields.Float(string='Previous Margin (%)', digits=(16, 2))
    new_margin_percent = fields.Float(string='New Margin (%)', digits=(16, 2))
    
    old_price_unit = fields.Float(string='Previous Unit Price', digits=(16, 2))
    new_price_unit = fields.Float(string='New Unit Price', digits=(16, 2))
    
    # For sections: store all affected lines with their prices in JSON
    affected_lines = fields.Text(string='Affected Lines (JSON)')
    
    create_date = fields.Datetime(string='Date', readonly=True)
    create_uid = fields.Many2one('res.users', string='Modified By', readonly=True)
    
    @api.model
    def create_history(self, order_id, adjustment_type, old_data, new_data):
        """Create a new margin history record"""
        vals = {
            'order_id': order_id,
            'adjustment_type': adjustment_type,
            'old_margin_percent': old_data.get('margin_percent', 0),
            'new_margin_percent': new_data.get('margin_percent', 0),
        }
        
        if adjustment_type == 'section':
            vals['section_name'] = old_data.get('section_name', '')
            vals['affected_lines'] = json.dumps(new_data.get('updated_lines', []))
            vals['old_price_unit'] = 0
            vals['new_price_unit'] = 0
        elif adjustment_type == 'subsection':
            vals['section_name'] = old_data.get('section_name', '')
            vals['subsection_name'] = old_data.get('subsection_name', '')
            vals['affected_lines'] = json.dumps(new_data.get('updated_lines', []))
            vals['old_price_unit'] = 0
            vals['new_price_unit'] = 0
        else:
            vals['line_id'] = old_data.get('line_id')
            vals['product_name'] = old_data.get('product_name', '')
            vals['old_price_unit'] = old_data.get('price_unit', 0)
            vals['new_price_unit'] = new_data.get('price_unit', 0)
            vals['affected_lines'] = ''
        
        record = self.create(vals)
        # Invalidate computed fields to refresh the history HTML
        if record.order_id:
            # Invalidate section_margins_html since it includes history
            record.order_id.invalidate_recordset(['section_margins_html'])
        return record
