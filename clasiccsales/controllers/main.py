# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json


class SectionMarginController(http.Controller):
    
    @http.route('/sale_order/adjust_section_margin', type='jsonrpc', auth='user', methods=['POST'])
    def adjust_section_margin(self, order_id, section_name, target_margin_percent):
        """
        Adjust prices in a section to achieve the target margin percentage

        :param order_id: ID of the sale order
        :param section_name: Name of the section to adjust
        :param target_margin_percent: Target margin percentage
        :return: dict with results
        """
        try:
            # Check if order_id is valid
            if not order_id or str(order_id).startswith('NewId_'):
                return {
                    'success': False,
                    'message': 'Please save the sales order before adjusting the margins.'
                }
            
            # Convert to int
            try:
                order_id_int = int(order_id)
            except (ValueError, TypeError):
                return {
                    'success': False,
                    'message': 'Invalid order ID. Please save the order first.'
                }
            
            order = request.env['sale.order'].browse(order_id_int)
            
            if not order.exists():
                return {
                    'success': False,
                    'message': 'Sales order not found.'
                }
            
            # Call the adjustment method
            result = order.adjust_section_margin(section_name, float(target_margin_percent))
            
            return result
            
        except Exception as e:
            import traceback
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'traceback': traceback.format_exc()
            }
    
    @http.route('/sale_order/adjust_product_margin', type='jsonrpc', auth='user', methods=['POST'])
    def adjust_product_margin(self, order_id, line_id, target_margin_percent):
        """
        Adjust price of a single product to achieve the target margin percentage

        :param order_id: ID of the sale order
        :param line_id: ID of the sale order line (product)
        :param target_margin_percent: Target margin percentage
        :return: dict with results
        """
        try:
            # Check if order_id is valid
            if not order_id or str(order_id).startswith('NewId_'):
                return {
                    'success': False,
                    'message': 'Please save the sales order before adjusting the margins.'
                }
            
            # Convert to int
            try:
                order_id_int = int(order_id)
                line_id_int = int(line_id)
            except (ValueError, TypeError):
                return {
                    'success': False,
                    'message': 'Invalid order ID or line ID. Please save the order first.'
                }
            
            order = request.env['sale.order'].browse(order_id_int)
            
            if not order.exists():
                return {
                    'success': False,
                    'message': 'Sales order not found.'
                }
            
            # Call the adjustment method
            result = order.adjust_product_margin(line_id_int, float(target_margin_percent))
            
            return result
            
        except Exception as e:
            import traceback
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'traceback': traceback.format_exc()
            }
