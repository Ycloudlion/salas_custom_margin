# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    section_margins_json = fields.Text(
        string='Margins by Section (JSON)',
        compute='_compute_section_margins_json',
        store=False,
    )
    
    section_margins_html = fields.Html(
        string='Margins by Section',
        compute='_compute_section_margins_html',
        store=False,
        sanitize=False,
    )

    @api.depends('order_line', 'order_line.margin', 'order_line.margin_percent',
                 'order_line.display_type', 'order_line.price_subtotal',
                 'order_line.product_uom_qty', 'order_line.name',
                 'order_line.product_id', 'order_line.purchase_price')
    def _compute_section_margins_json(self):
        """Calculate margins grouped by section and subsection"""
        for order in self:
            order.section_margins_json = json.dumps(order._get_section_margins())
    
    @api.depends('order_line', 'order_line.margin', 'order_line.margin_percent',
                 'order_line.display_type', 'order_line.price_subtotal',
                 'order_line.product_uom_qty', 'order_line.name',
                 'order_line.product_id', 'order_line.purchase_price',
                 'currency_id')
    def _compute_section_margins_html(self):
        """Generate HTML to display margins"""
        for order in self:
            try:
                order.section_margins_html = order._generate_margins_html()
            except Exception as e:
                # In case of error, show error message
                order.section_margins_html = f"""
                    <div class="alert alert-danger">
                        <p>Error generating margins: {str(e)}</p>
                    </div>
                """

    def _get_section_margins(self):
        self.ensure_one()
        
        sections_data = []
        current_section = None
        current_subsection = None
        total_margin = 0.0
        total_price_subtotal = 0.0
        
        for line in self.order_line:
            # Identify section
            if line.display_type == 'line_section':
                # Save previous section if exists
                if current_section:
                    # First, save any active subsection belonging to the previous section
                    if current_subsection:
                        subsection_price = current_subsection.get('price_subtotal', 0.0)
                        subsection_margin = current_subsection.get('margin', 0.0)
                        if subsection_price > 0 and subsection_margin != 0:
                            current_subsection['margin_percent'] = (
                                subsection_margin / subsection_price
                            ) * 100
                        else:
                            current_subsection['margin_percent'] = 0.0
                        current_section['subsections'].append(current_subsection)
                        current_subsection = None

                    # Then, calculate final percentage of the section
                    section_price = current_section.get('price_subtotal', 0.0)
                    section_margin = current_section.get('margin', 0.0)
                    if section_price > 0 and section_margin != 0:
                        current_section['margin_percent'] = (
                            section_margin / section_price
                        ) * 100
                    else:
                        current_section['margin_percent'] = 0.0
                    sections_data.append(current_section)
                
                # Create new section
                current_section = {
                    'name': line.name or 'Unnamed',
                    'margin': 0.0,
                    'margin_percent': 0.0,
                    'price_subtotal': 0.0,
                    'subsections': [],
                    'products': [],  # Products directly under section
                }
                current_subsection = None
            
            # Identify subsection
            elif line.display_type == 'line_subsection':
                # Save previous subsection if exists
                if current_subsection and current_section:
                    # Calculate final percentage of the subsection
                    subsection_price = current_subsection.get('price_subtotal', 0.0)
                    if subsection_price > 0:
                        current_subsection['margin_percent'] = (
                            current_subsection['margin'] / subsection_price
                        ) * 100
                    current_section['subsections'].append(current_subsection)
                
                # Create new subsection
                current_subsection = {
                    'name': line.name or 'Unnamed',
                    'margin': 0.0,
                    'margin_percent': 0.0,
                    'price_subtotal': 0.0,
                    'products': [],  # Products in this subsection
                }
            
            # Normal product line
            elif line.display_type == False and line.product_id:
                # Get line price
                line_price_subtotal = line.price_subtotal if line.price_subtotal else 0.0
                
                # Get line margin (use margin field if available)
                line_margin = 0.0
                line_margin_percent = 0.0
                try:
                    # Try to get margin from margin field (if sale_margin is installed)
                    if hasattr(line, 'margin') and line.margin is not None:
                        line_margin = float(line.margin)
                    elif line_price_subtotal > 0:
                        # If no margin calculated, calculate it manually
                        cost = 0.0
                        # Try to get purchase_price from line
                        if hasattr(line, 'purchase_price') and line.purchase_price:
                            cost = float(line.purchase_price) * float(line.product_uom_qty)
                        # Otherwise, use product standard cost
                        elif hasattr(line.product_id, 'standard_price') and line.product_id.standard_price:
                            cost = float(line.product_id.standard_price) * float(line.product_uom_qty)
                        
                        line_margin = float(line_price_subtotal) - cost
                    
                    # Calculate margin percent for this line
                    if line_price_subtotal > 0:
                        line_margin_percent = (line_margin / line_price_subtotal) * 100
                        
                except (ValueError, TypeError, AttributeError):
                    # If error, margin will be 0
                    line_margin = 0.0
                    line_margin_percent = 0.0
                
                # Only process if there is a price
                if line_price_subtotal > 0:
                    # Create product data
                    product_data = {
                        'line_id': line.id,
                        'name': line.name or (line.product_id.name if line.product_id else 'Unnamed'),
                        'margin': line_margin,
                        'margin_percent': line_margin_percent,
                    }
                    
                    # Add to subsection if exists
                    if current_subsection and current_section:
                        current_subsection['margin'] += line_margin
                        current_subsection['price_subtotal'] += line_price_subtotal
                        current_subsection['products'].append(product_data)
                    # Add to section's direct products if no subsection
                    elif current_section:
                        current_section['products'].append(product_data)
                    
                    # Add to section if exists
                    if current_section:
                        current_section['margin'] += line_margin
                        current_section['price_subtotal'] += line_price_subtotal
                    
                    # Add to general totals
                    total_margin += line_margin
                    total_price_subtotal += line_price_subtotal
        
        # Save last subsection if exists
        if current_subsection and current_section:
            # Calculate final percentage of the subsection
            subsection_price = current_subsection.get('price_subtotal', 0.0)
            subsection_margin = current_subsection.get('margin', 0.0)
            if subsection_price > 0 and subsection_margin != 0:
                current_subsection['margin_percent'] = (
                    subsection_margin / subsection_price
                ) * 100
            else:
                current_subsection['margin_percent'] = 0.0
            current_section['subsections'].append(current_subsection)
        
        # Save last section if exists
        if current_section:
            # Calculate final percentage of the section
            section_price = current_section.get('price_subtotal', 0.0)
            section_margin = current_section.get('margin', 0.0)
            if section_price > 0 and section_margin != 0:
                current_section['margin_percent'] = (
                    section_margin / section_price
                ) * 100
            else:
                current_section['margin_percent'] = 0.0
            sections_data.append(current_section)
        
        # Calculate total margin percentage
        total_margin_percent = 0.0
        if total_price_subtotal > 0 and total_margin != 0:
            total_margin_percent = (total_margin / total_price_subtotal) * 100
        
        return {
            'sections': sections_data,
            'total_margin': total_margin,
            'total_margin_percent': total_margin_percent,
        }
    
    def _generate_margins_html(self):
        """Generate HTML to display margins in a table"""
        self.ensure_one()
        margins_data = self._get_section_margins()
        sections = margins_data.get('sections', [])
        total_margin = margins_data.get('total_margin', 0.0)
        total_margin_percent = margins_data.get('total_margin_percent', 0.0)
        
        # Get currency symbol
        currency_symbol = self.currency_id.symbol if self.currency_id else '$'
        
        if not sections:
            return """
                <div class="alert alert-info text-center" style="padding: 40px 20px; margin: 20px 0; border: 2px dashed #dee2e6; border-radius: 8px; background-color: #f8f9fa;">
                    <i class="fa fa-info-circle fa-2x" style="color: #6c757d; margin-bottom: 10px;"></i>
                    <p style="font-size: 1.1em; color: #495057; margin-bottom: 8px;">No sections defined in this order.</p>
                    <small style="font-size: 0.9em; color: #6c757d;">Add sections in order lines to see grouped margins.</small>
                </div>
            """
        
        html = f"""
        <div class="section_margin_widget_container" style="width: 100%; padding: 0 20px; margin: 0; background-color: #ffffff; box-sizing: border-box;">
            <div class="table-responsive" style="width: 100%; overflow-x: auto;">
                <table class="table table-hover" style="width: 100%; margin-bottom: 0; background-color: #fff; border-collapse: separate; border-spacing: 0;">
                    <thead style="background: linear-gradient(135deg, #4a4a4a 0%, #2c2c2c 100%); color: #fff;">
                        <tr>
                            <th style="padding: 16px 12px; font-weight: 600; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; border: none; color: #fff; text-align: left;">Section</th>
                            <th style="padding: 16px 12px; font-weight: 600; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; border: none; color: #fff; text-align: left;">       </th>
                            <th style="padding: 16px 12px; font-weight: 600; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; border: none; color: #fff; text-align: right;">Margin</th>
                            <th style="padding: 16px 12px; font-weight: 600; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; border: none; color: #fff; text-align: right; width: 280px;">Margin (%)</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for idx, section in enumerate(sections):
            section_name = section.get('name', 'Unnamed')
            section_margin = section.get('margin', 0.0)
            section_margin_percent = section.get('margin_percent', 0.0)
            subsections = section.get('subsections', [])
            section_products = section.get('products', [])
            
            # Section header row
            html += f"""
                        <tr style="background: linear-gradient(90deg, #e0e0e0 0%, #bdbdbd 100%); border-top: 2px solid #9e9e9e; border-bottom: 1px solid #9e9e9e;">
                            <td style="padding: 16px 12px; font-weight: 600; text-align: left; padding-left: 10px;" colspan="2">
                                <span style="display: inline-flex; align-items: center; padding: 6px 12px; background-color: #e0e0e0; color: #424242; border-radius: 6px; font-size: 0.95em;">
                                    <i class="fa fa-folder-open" style="margin-right: 8px;"></i>
                                    <strong>{section_name}</strong>
                                </span>
                            </td>
                            <td style="padding: 16px 12px; font-weight: 600; text-align: right; font-family: 'Courier New', monospace; color: #424242;">
                                <strong>{abs(section_margin):,.2f}</strong>
                            </td>
                            <td style="padding: 16px 12px; font-weight: 600; text-align: right;">
                                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px;">
                                    <input type="number" 
                                           class="section_margin_input" 
                                           data-order-id="{self.id}"
                                           data-section-name="{section_name}"
                                           data-current-margin="{section_margin_percent:.2f}"
                                           value="{section_margin_percent:.2f}" 
                                           step="0.01" 
                                           min="0" 
                                           max="100"
                                           style="width: 80px; padding: 6px 8px; border: 1px solid #9e9e9e; border-radius: 4px; font-size: 0.9em; font-weight: 600; text-align: right;" />
                                    <span style="font-weight: 600; color: #424242;">%</span>
                                    <button type="button"
                                            class="btn btn-sm btn-primary apply_margin_btn" 
                                            data-order-id="{self.id}"
                                            data-section-name="{section_name}"
                                            style="padding: 6px 12px; background-color: #616161; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em; white-space: nowrap; display: none;">
                                        <i class="fa fa-check" style="margin-right: 4px;"></i>Apply
                                    </button>
                                </div>
                            </td>
                        </tr>
            """
            
            # Show subsections (if any) - ONLY display, no editing
            for subsection in subsections:
                sub_name = subsection.get('name', 'Unnamed')
                sub_margin = subsection.get('margin', 0.0)
                sub_margin_percent = subsection.get('margin_percent', 0.0)
                sub_products = subsection.get('products', [])
                
                html += f"""
                        <tr style="background-color: #f5f5f5; border-bottom: 1px solid #e0e0e0;">
                            <td style="padding: 12px; vertical-align: middle; text-align: left; padding-left: 30px;" colspan="2">
                                <span style="display: inline-flex; align-items: center; padding: 4px 10px; background-color: #e8e8e8; color: #616161; border-radius: 4px; font-size: 0.9em;">
                                    <i class="fa fa-folder" style="margin-right: 6px;"></i>
                                    <strong>{sub_name}</strong>
                                </span>
                            </td>
                            <td style="padding: 12px; vertical-align: middle; text-align: right; font-family: 'Courier New', monospace; font-weight: 600; color: #424242;">
                                {abs(sub_margin):,.2f}
                            </td>
                            <td style="padding: 12px; vertical-align: middle; text-align: right;">
                                <span style="display: inline-block; padding: 6px 10px; background-color: #757575; color: #fff; border-radius: 0.25rem; font-size: 0.9em; font-weight: 600;">
                                    {sub_margin_percent:.2f}%
                                </span>
                            </td>
                        </tr>
                """
                
                # Show products within subsection
                for product in sub_products:
                    prod_name = product.get('name', 'Unnamed')
                    prod_margin = product.get('margin', 0.0)
                    prod_margin_percent = product.get('margin_percent', 0.0)
                    prod_line_id = product.get('line_id', 0)
                    
                    html += f"""
                        <tr style="background-color: #fafafa; border-bottom: 1px solid #eeeeee;">
                            <td style="padding: 10px; vertical-align: middle; text-align: left; padding-left: 60px;" colspan="2">
                                <span style="color: #666; font-size: 0.85em;">
                                    <i class="fa fa-cube" style="margin-right: 4px; color: #999;"></i>
                                    {prod_name}
                                </span>
                            </td>
                            <td style="padding: 10px; vertical-align: middle; text-align: right; font-family: 'Courier New', monospace; color: #666; font-size: 0.85em;">
                                {abs(prod_margin):,.2f}
                            </td>
                            <td style="padding: 10px; vertical-align: middle; text-align: right;">
                                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 6px;">
                                    <input type="number" 
                                           class="product_margin_input" 
                                           data-order-id="{self.id}"
                                           data-line-id="{prod_line_id}"
                                           data-current-margin="{prod_margin_percent:.2f}"
                                           value="{prod_margin_percent:.2f}" 
                                           step="0.01" 
                                           min="0" 
                                           max="100"
                                           style="width: 80px; padding: 4px 6px; border: 1px solid #ccc; border-radius: 3px; font-size: 0.85em; text-align: right;" />
                                    <span style="font-size: 0.85em; color: #666;">%</span>
                                    <button type="button"
                                            class="btn btn-sm btn-primary apply_product_margin_btn" 
                                            data-order-id="{self.id}"
                                            data-line-id="{prod_line_id}"
                                            style="padding: 4px 10px; background-color: #9e9e9e; color: #fff; border: none; border-radius: 3px; cursor: pointer; font-size: 0.8em; white-space: nowrap; display: none;">
                                        <i class="fa fa-check" style="margin-right: 2px;"></i>Apply
                                    </button>
                                </div>
                            </td>
                        </tr>
                    """
            
            # Show products directly under section (no subsection)
            for product in section_products:
                prod_name = product.get('name', 'Unnamed')
                prod_margin = product.get('margin', 0.0)
                prod_margin_percent = product.get('margin_percent', 0.0)
                prod_line_id = product.get('line_id', 0)
                
                html += f"""
                        <tr style="background-color: #fafafa; border-bottom: 1px solid #eeeeee;">
                            <td style="padding: 10px; vertical-align: middle; text-align: left; padding-left: 40px;" colspan="2">
                                <span style="color: #666; font-size: 0.85em;">
                                    <i class="fa fa-cube" style="margin-right: 4px; color: #999;"></i>
                                    {prod_name}
                                </span>
                            </td>
                            <td style="padding: 10px; vertical-align: middle; text-align: right; font-family: 'Courier New', monospace; color: #666; font-size: 0.85em;">
                                {abs(prod_margin):,.2f}
                            </td>
                            <td style="padding: 10px; vertical-align: middle; text-align: right;">
                                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 6px;">
                                    <input type="number" 
                                           class="product_margin_input" 
                                           data-order-id="{self.id}"
                                           data-line-id="{prod_line_id}"
                                           data-current-margin="{prod_margin_percent:.2f}"
                                           value="{prod_margin_percent:.2f}" 
                                           step="0.01" 
                                           min="0" 
                                           max="100"
                                           style="width: 80px; padding: 4px 6px; border: 1px solid #ccc; border-radius: 3px; font-size: 0.85em; text-align: right;" />
                                    <span style="font-size: 0.85em; color: #666;">%</span>
                                    <button type="button"
                                            class="btn btn-sm btn-primary apply_product_margin_btn" 
                                            data-order-id="{self.id}"
                                            data-line-id="{prod_line_id}"
                                            style="padding: 4px 10px; background-color: #9e9e9e; color: #fff; border: none; border-radius: 3px; cursor: pointer; font-size: 0.8em; white-space: nowrap; display: none;">
                                        <i class="fa fa-check" style="margin-right: 2px;"></i>Apply
                                    </button>
                                </div>
                            </td>
                        </tr>
                """
            
            # Spacer between sections
            if idx < len(sections) - 1:
                html += """
                        <tr style="height: 12px;">
                            <td colspan="4" style="border: none; padding: 0; background: linear-gradient(90deg, transparent 0%, #dee2e6 50%, transparent 100%); height: 1px;"></td>
                        </tr>
                """
        
        # Grand total
        html += f"""
                    </tbody>
                    <tfoot>
                        <tr style="background: linear-gradient(135deg, #4a4a4a 0%, #2c2c2c 100%); color: #fff; border-top: 3px solid #616161;">
                            <td style="padding: 18px 12px; font-weight: 700; font-size: 1.1em; color: #fff; text-align: left;" colspan="2">
                                <strong style="color: #fff; font-size: 1.15em;">
                                    <i class="fa fa-chart-bar" style="color: #fff; margin-right: 6px;"></i>
                                    GRAND TOTAL
                                </strong>
                            </td>
                            <td style="padding: 18px 12px; font-weight: 700; font-size: 1.1em; color: #fff; text-align: right;">
                                <strong style="color: #fff; font-size: 1.2em;">{abs(total_margin):,.2f}</strong>
                            </td>
                            <td style="padding: 18px 12px; font-weight: 700; font-size: 1.1em; color: #fff; text-align: right;">
                                <strong style="display: inline-block; padding: 8px 12px; background-color: #616161; color: #fff; border-radius: 0.25rem; font-size: 1.1em;">
                                    {total_margin_percent:.2f}%
                                </strong>
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>
        """
        
        return html

    def adjust_section_margin(self, section_name, target_margin_percent):
        """
        Adjust prices of products in a section to achieve target margin percentage.
        Distribution: Equitably (same percentage increase for all products).
        
        :param section_name: Name of the section to adjust
        :param target_margin_percent: Target margin percentage to achieve
        :return: dict with results
        """
        self.ensure_one()
        
        # Find all lines belonging to this section (including subsections)
        section_lines = []
        current_section = None
        in_target_section = False
        
        for line in self.order_line:
            # Identify section
            if line.display_type == 'line_section':
                # Check if this is our target section
                if line.name == section_name:
                    current_section = line.name
                    in_target_section = True
                else:
                    # Found a different section, stop collecting
                    in_target_section = False
                    current_section = None
            # Subsections belong to the current section
            elif line.display_type == 'line_subsection':
                # Subsections don't change the in_target_section flag
                pass
            # Collect product lines from target section (including those in subsections)
            elif in_target_section and line.display_type == False and line.product_id:
                section_lines.append(line)
        
        if not section_lines:
            return {
                'success': False,
                'message': f'No products found in section "{section_name}"'
            }
        
        # Calculate current totals
        total_cost = 0.0
        total_price = 0.0
        
        for line in section_lines:
            qty = float(line.product_uom_qty) if line.product_uom_qty else 0.0
            price_subtotal = float(line.price_subtotal) if line.price_subtotal else 0.0
            
            # Get cost and round to 2 decimals for precision
            cost = 0.0
            if hasattr(line, 'purchase_price') and line.purchase_price:
                cost = round(float(line.purchase_price) * qty, 2)
            elif hasattr(line.product_id, 'standard_price') and line.product_id.standard_price:
                cost = round(float(line.product_id.standard_price) * qty, 2)
            
            total_cost += cost
            total_price += price_subtotal
        
        if total_cost == 0:
            return {
                'success': False,
                'message': 'Cannot adjust: total cost is 0'
            }
        
        # Calculate target price needed to achieve target margin
        # margin_percent = ((price - cost) / price) * 100
        # target_margin_percent = ((target_price - cost) / target_price) * 100
        # Solving for target_price:
        # target_price = cost / (1 - target_margin_percent/100)
        
        target_margin_decimal = target_margin_percent / 100.0
        if target_margin_decimal >= 1.0:
            return {
                'success': False,
                'message': 'Margin cannot be 100% or greater'
            }
        
        target_total_price = total_cost / (1 - target_margin_decimal)
        
        # Calculate adjustment factor (same percentage for all products)
        adjustment_factor = target_total_price / total_price if total_price > 0 else 1.0
        
        # Apply adjustment to all lines with proper rounding
        updated_lines = []
        for line in section_lines:
            old_price = line.price_unit
            # Calculate new price and round to currency precision (2 decimals)
            new_price = round(old_price * adjustment_factor, 2)
            
            # Update price_unit - this will trigger recalculation of subtotals and margins
            line.price_unit = new_price
            
            updated_lines.append({
                'name': line.name or line.product_id.name,
                'old_price': old_price,
                'new_price': new_price
            })
        
        # Force recalculation of order totals
        self._compute_section_margins_json()
        self._compute_section_margins_html()
        
        # Recalculate to verify
        new_total_price = sum(float(line.price_subtotal) for line in section_lines)
        new_margin = new_total_price - total_cost
        new_margin_percent = (new_margin / new_total_price * 100) if new_total_price > 0 else 0
        
        return {
            'success': True,
            'message': f'Successfully adjusted {len(section_lines)} products',
            'section_name': section_name,
            'old_margin_percent': (total_price - total_cost) / total_price * 100 if total_price > 0 else 0,
            'new_margin_percent': new_margin_percent,
            'adjustment_factor': adjustment_factor,
            'updated_lines': updated_lines
        }

    def adjust_product_margin(self, line_id, target_margin_percent):
        """
        Adjust price of a single product line to achieve target margin percentage.
        
        :param line_id: ID of the sale order line
        :param target_margin_percent: Target margin percentage to achieve
        :return: dict with results
        """
        self.ensure_one()
        
        # Find the specific line
        line = self.order_line.filtered(lambda l: l.id == line_id)
        
        if not line:
            return {
                'success': False,
                'message': f'Product line not found'
            }
        
        line = line[0]
        
        if line.display_type or not line.product_id:
            return {
                'success': False,
                'message': 'Cannot adjust margin for non-product lines'
            }
        
        # Get current values
        qty = float(line.product_uom_qty) if line.product_uom_qty else 0.0
        old_price_unit = float(line.price_unit) if line.price_unit else 0.0
        
        # Get cost and round to 2 decimals for precision
        cost_per_unit = 0.0
        if hasattr(line, 'purchase_price') and line.purchase_price:
            cost_per_unit = round(float(line.purchase_price), 2)
        elif hasattr(line.product_id, 'standard_price') and line.product_id.standard_price:
            cost_per_unit = round(float(line.product_id.standard_price), 2)
        
        if cost_per_unit == 0:
            return {
                'success': False,
                'message': 'Cannot adjust: product cost is 0'
            }
        
        # Calculate target price
        # margin_percent = ((price - cost) / price) * 100
        # Solving for price: price = cost / (1 - margin_percent/100)
        target_margin_decimal = target_margin_percent / 100.0
        if target_margin_decimal >= 1.0:
            return {
                'success': False,
                'message': 'Margin cannot be 100% or greater'
            }
        
        # Calculate new price and round to currency precision (2 decimals)
        new_price_unit = round(cost_per_unit / (1 - target_margin_decimal), 2)
        
        # Calculate old margin
        old_subtotal = old_price_unit * qty
        old_cost_total = cost_per_unit * qty
        old_margin = old_subtotal - old_cost_total
        old_margin_percent = (old_margin / old_subtotal * 100) if old_subtotal > 0 else 0
        
        # Update price with rounded value
        line.price_unit = new_price_unit
        
        # Force recalculation
        self._compute_section_margins_json()
        self._compute_section_margins_html()
        
        # Calculate new margin
        new_subtotal = new_price_unit * qty
        new_cost_total = cost_per_unit * qty
        new_margin = new_subtotal - new_cost_total
        new_margin_percent = (new_margin / new_subtotal * 100) if new_subtotal > 0 else 0
        
        return {
            'success': True,
            'message': f'Successfully adjusted product price',
            'product_name': line.name or line.product_id.name,
            'old_price_unit': old_price_unit,
            'new_price_unit': new_price_unit,
            'old_margin_percent': old_margin_percent,
            'new_margin_percent': new_margin_percent,
        }
