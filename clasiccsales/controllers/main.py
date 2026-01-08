# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json


class SectionMarginController(http.Controller):

    @http.route('/sale_order/adjust_section_margin', type='jsonrpc', auth='user', methods=['POST'])
    def adjust_section_margin(self, order_id, section_name, target_margin_percent):
        """
        Adjust the prices in a section to achieve the target margin percentage.

        :param order_id: ID of the sale order
        :param section_name: Name of the section to adjust
        :param target_margin_percent: Desired target margin percentage for the section
        :return: dict with result status and message
        """
        try:
            # Validate order ID
            if not order_id or str(order_id).startswith('NewId_'):
                return {
                    'success': False,
                    'message': 'Please save the sales order before adjusting the margins.'
                }

            # Ensure IDs are integers
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

            # Perform section margin adjustment
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
        Adjust the price of a single product to achieve the target margin percentage.

        :param order_id: ID of the sale order
        :param line_id: ID of the sale order line (product)
        :param target_margin_percent: Desired target margin percentage for the product
        :return: dict with result status and message
        """
        try:
            # Validate order ID
            if not order_id or str(order_id).startswith('NewId_'):
                return {
                    'success': False,
                    'message': 'Please save the sales order before adjusting the margins.'
                }

            # Ensure IDs are integers
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

            # Perform product margin adjustment
            result = order.adjust_product_margin(line_id_int, float(target_margin_percent))
            return result

        except Exception as e:
            import traceback
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'traceback': traceback.format_exc()
            }

    @http.route('/sale_order/rollback_margin', type='jsonrpc', auth='user', methods=['POST'])
    def rollback_margin(self, order_id, history_id):
        """
        Restore a margin value from the margin adjustment history.

        :param order_id: ID of the sale order
        :param history_id: ID of the margin history record to restore
        :return: dict with result status and message
        """
        try:
            # Validate order ID
            if not order_id or str(order_id).startswith('NewId_'):
                return {
                    'success': False,
                    'message': 'Please save the sales order first.'
                }

            # Ensure IDs are integers
            try:
                order_id_int = int(order_id)
                history_id_int = int(history_id)
            except (ValueError, TypeError):
                return {
                    'success': False,
                    'message': 'Invalid order ID or history ID. Please save the order first.'
                }

            order = request.env['sale.order'].browse(order_id_int)

            if not order.exists():
                return {
                    'success': False,
                    'message': 'Sales order not found.'
                }

            # Perform rollback from history
            result = order.rollback_margin(history_id_int)
            return result

        except Exception as e:
            import traceback
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'traceback': traceback.format_exc()
            }
