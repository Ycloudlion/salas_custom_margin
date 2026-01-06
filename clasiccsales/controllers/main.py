# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json


class SectionMarginController(http.Controller):
    
    @http.route('/sale_order/adjust_section_margin', type='json', auth='user', methods=['POST'])
    def adjust_section_margin(self, order_id, section_name, target_margin_percent):
        """
        Adjust prices in a section to achieve target margin percentage
        
        :param order_id: ID of the sale order
        :param section_name: Name of the section to adjust
        :param target_margin_percent: Target margin percentage
        :return: dict with results
        """
        try:
            order = request.env['sale.order'].browse(int(order_id))
            
            if not order.exists():
                return {
                    'success': False,
                    'message': 'Orden de venta no encontrada'
                }
            
            # Call the adjustment method
            result = order.adjust_section_margin(section_name, float(target_margin_percent))
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
