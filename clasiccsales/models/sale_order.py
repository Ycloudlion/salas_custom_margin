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
                margins_html = order._generate_margins_html()
                # Append history HTML if order is saved
                if order.id:
                    # Compute history HTML (without depends, calculated on demand)
                    history_html = order._generate_margin_history_html()
                    # Always append history section (even if empty message)
                    margins_html += history_html
                order.section_margins_html = margins_html
            except Exception as e:
                # In case of error, show error message
                import logging
                _logger = logging.getLogger(__name__)
                _logger.exception('Error in _compute_section_margins_html')
                order.section_margins_html = f"""
                    <div class="alert alert-danger">
                        <p>Error generating margins: {str(e)}</p>
                        <pre>{str(e)}</pre>
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
        <div class="section_margin_widget_container">
            <div class="table-responsive">
                <table class="table table-hover margins-table">
                    <thead>
                        <tr>
                            <th class="text-start">Section</th>
                            <th class="text-start"></th>
                            <th class="text-end">Margin</th>
                            <th class="text-end col-margin-input">Margin (%)</th>
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
                        <tr class="section-row">
                            <td class="text-start" colspan="2">
                                <span class="section-badge">
                                    <i class="fa fa-folder-open"></i>
                                    <strong>{section_name}</strong>
                                </span>
                            </td>
                            <td class="text-end margin-value">
                                <strong>{abs(section_margin):,.2f}</strong>
                            </td>
                            <td class="text-end">
                                <div class="margin-input-container">
                                    <input type="number" 
                                           class="section_margin_input" 
                                           data-order-id="{self.id}"
                                           data-section-name="{section_name}"
                                           data-current-margin="{section_margin_percent:.2f}"
                                           value="{section_margin_percent:.2f}" 
                                           step="0.01" 
                                           min="0" 
                                           max="99.99" />
                                    <span>%</span>
                                    <button type="button"
                                            class="btn btn-sm btn-primary apply_margin_btn" 
                                            data-order-id="{self.id}"
                                            data-section-name="{section_name}">
                                        <i class="fa fa-check"></i>Apply
                                    </button>
                                </div>
                            </td>
                        </tr>
            """
            
            # Show subsections (if any) - NOW EDITABLE
            for subsection in subsections:
                sub_name = subsection.get('name', 'Unnamed')
                sub_margin = subsection.get('margin', 0.0)
                sub_margin_percent = subsection.get('margin_percent', 0.0)
                sub_products = subsection.get('products', [])
                
                html += f"""
                        <tr class="subsection-row">
                            <td class="text-start" colspan="2" style="padding-left: 30px;">
                                <span class="subsection-label">
                                    <i class="fa fa-folder"></i>
                                    <strong>{sub_name}</strong>
                                </span>
                            </td>
                            <td class="text-end margin-value">
                                {abs(sub_margin):,.2f}
                            </td>
                            <td class="text-end">
                                <div class="margin-input-container">
                                    <input type="number" 
                                           class="subsection_margin_input" 
                                           data-order-id="{self.id}"
                                           data-section-name="{section_name}"
                                           data-subsection-name="{sub_name}"
                                           data-current-margin="{sub_margin_percent:.2f}"
                                           value="{sub_margin_percent:.2f}" 
                                           step="0.01" 
                                           min="0" 
                                           max="99.99" />
                                    <span>%</span>
                                    <button type="button"
                                            class="btn btn-sm btn-primary apply_subsection_margin_btn" 
                                            data-order-id="{self.id}"
                                            data-section-name="{section_name}"
                                            data-subsection-name="{sub_name}">
                                        <i class="fa fa-check"></i>Apply
                                    </button>
                                </div>
                            </td>
                        </tr>
                """
                
                # Show products within subsection - DISPLAY ONLY (edit functionality commented)
                for product in sub_products:
                    prod_name = product.get('name', 'Unnamed')
                    prod_margin = product.get('margin', 0.0)
                    prod_margin_percent = product.get('margin_percent', 0.0)
                    prod_line_id = product.get('line_id', 0)
                    
                    html += f"""
                        <tr class="product-row">
                            <td class="text-start" colspan="2" style="padding-left: 60px;">
                                <span class="product-name">
                                    <i class="fa fa-cube"></i>
                                    {prod_name}
                                </span>
                            </td>
                            <td class="text-end margin-value">
                                {abs(prod_margin):,.2f}
                            </td>
                            <td class="text-end">
                                <span class="margin-badge">
                                    {prod_margin_percent:.2f}%
                                </span>
                                <!--
                                PRODUCT MARGIN EDITING - COMMENTED FOR FUTURE USE
                                <div class="margin-input-container">
                                    <input type="number" 
                                           class="product_margin_input" 
                                           data-order-id="{self.id}"
                                           data-line-id="{prod_line_id}"
                                           data-current-margin="{prod_margin_percent:.2f}"
                                           value="{prod_margin_percent:.2f}" 
                                           step="0.01" 
                                           min="0" />
                                    <span>%</span>
                                    <button type="button"
                                            class="btn btn-sm btn-primary apply_product_margin_btn" 
                                            data-order-id="{self.id}"
                                            data-line-id="{prod_line_id}">
                                        <i class="fa fa-check"></i>Apply
                                    </button>
                                </div>
                                -->
                            </td>
                        </tr>
                    """
            
            # Show products directly under section (no subsection) - DISPLAY ONLY (edit functionality commented)
            for product in section_products:
                prod_name = product.get('name', 'Unnamed')
                prod_margin = product.get('margin', 0.0)
                prod_margin_percent = product.get('margin_percent', 0.0)
                prod_line_id = product.get('line_id', 0)
                
                html += f"""
                        <tr class="product-row">
                            <td class="text-start" colspan="2" style="padding-left: 40px;">
                                <span class="product-name">
                                    <i class="fa fa-cube"></i>
                                    {prod_name}
                                </span>
                            </td>
                            <td class="text-end margin-value">
                                {abs(prod_margin):,.2f}
                            </td>
                            <td class="text-end">
                                <span class="margin-badge">
                                    {prod_margin_percent:.2f}%
                                </span>
                                <!--
                                PRODUCT MARGIN EDITING - COMMENTED FOR FUTURE USE
                                <div class="margin-input-container">
                                    <input type="number" 
                                           class="product_margin_input" 
                                           data-order-id="{self.id}"
                                           data-line-id="{prod_line_id}"
                                           data-current-margin="{prod_margin_percent:.2f}"
                                           value="{prod_margin_percent:.2f}" 
                                           step="0.01" 
                                           min="0" />
                                    <span>%</span>
                                    <button type="button"
                                            class="btn btn-sm btn-primary apply_product_margin_btn" 
                                            data-order-id="{self.id}"
                                            data-line-id="{prod_line_id}">
                                        <i class="fa fa-check"></i>Apply
                                    </button>
                                </div>
                                -->
                            </td>
                        </tr>
                """
            
            # Spacer between sections
            if idx < len(sections) - 1:
                html += """
                        <tr class="section-spacer">
                            <td colspan="4"></td>
                        </tr>
                """
        
        # Grand total
        html += f"""
                    </tbody>
                    <tfoot>
                        <tr>
                            <td class="text-start" colspan="2">
                                <strong class="total-label">
                                    <i class="fa fa-chart-bar"></i>
                                    GRAND TOTAL
                                </strong>
                            </td>
                            <td class="text-end">
                                <strong class="total-value">{abs(total_margin):,.2f}</strong>
                            </td>
                            <td class="text-end">
                                <strong class="total-badge">
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
        
        # Get current margin BEFORE adjustment for history
        margins_data = self._get_section_margins()
        section_data = next((s for s in margins_data.get('sections', []) 
                            if s.get('name') == section_name), None)
        old_margin_percent = section_data.get('margin_percent', 0) if section_data else 0
        
        # Save old prices for history
        old_prices = {}
        for line in section_lines:
            old_prices[line.id] = {
                'line_id': line.id,
                'product_name': line.name or (line.product_id.name if line.product_id else 'Unnamed'),
                'old_price': float(line.price_unit),
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
        
        # Calculate target price using traditional margin formula
        # margin_percent = ((price - cost) / price) * 100
        # Solving for price: price = cost / (1 - margin_percent/100)
        
        target_margin_decimal = target_margin_percent / 100.0
        
        # Validate margin range (cannot be >= 100% with this formula)
        if target_margin_decimal >= 1.0:
            return {
                'success': False,
                'message': 'Margin cannot be 100% or greater (maximum is 99.99%)'
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
                'line_id': line.id,
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
        
        # Prepare data for history
        old_data = {
            'section_name': section_name,
            'margin_percent': old_margin_percent,
        }
        
        new_data = {
            'margin_percent': new_margin_percent,
            'updated_lines': updated_lines,
        }
        
        # Save to history
        try:
            self.env['sale.order.margin.history'].create_history(
                self.id, 'section', old_data, new_data
            )
        except Exception as e:
            # Don't fail if history fails, just log it
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f'Error saving margin history: {str(e)}')
        
        return {
            'success': True,
            'message': f'Successfully adjusted {len(section_lines)} products',
            'section_name': section_name,
            'old_margin_percent': old_margin_percent,
            'new_margin_percent': new_margin_percent,
            'adjustment_factor': adjustment_factor,
            'updated_lines': updated_lines
        }

    def adjust_subsection_margin(self, section_name, subsection_name, target_margin_percent):
        
        # Get all lines in this subsection
        subsection_lines = self.order_line.filtered(
            lambda l: (l.display_type == False and 
                      (l.name or '').startswith(subsection_name))
        )
        
        if not subsection_lines:
            return {
                'success': False,
                'message': 'No products found in subsection'
            }
        
        # Get current margin data
        sections = json.loads(self.section_margins_json) if self.section_margins_json else []
        section_data = next((s for s in sections if s.get('name') == section_name), None)
        subsection_data = None
        if section_data:
            subsection_data = next((sub for sub in section_data.get('subsections', []) 
                                   if sub.get('name') == subsection_name), None)
        
        old_margin_percent = subsection_data.get('margin_percent', 0) if subsection_data else 0
        
        # Save old prices for history
        old_prices = {}
        for line in subsection_lines:
            old_prices[line.id] = {
                'line_id': line.id,
                'product_name': line.name or (line.product_id.name if line.product_id else 'Unnamed'),
                'old_price': float(line.price_unit),
            }
        
        # Calculate current totals
        total_cost = 0.0
        total_price = 0.0
        
        for line in subsection_lines:
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
        
        # Calculate target price using traditional margin formula
        # margin_percent = ((price - cost) / price) * 100
        # Solving for price: price = cost / (1 - margin_percent/100)
        
        target_margin_decimal = target_margin_percent / 100.0
        
        # Validate margin range (cannot be >= 100% with this formula)
        if target_margin_decimal >= 1.0:
            return {
                'success': False,
                'message': 'Margin cannot be 100% or greater (maximum is 99.99%)'
            }
        
        target_total_price = total_cost / (1 - target_margin_decimal)
        
        # Calculate adjustment factor
        adjustment_factor = target_total_price / total_price if total_price > 0 else 1.0
        
        # Apply adjustment to all lines
        updated_lines = []
        for line in subsection_lines:
            old_price = line.price_unit
            new_price = round(old_price * adjustment_factor, 2)
            
            line.price_unit = new_price
            
            updated_lines.append({
                'line_id': line.id,
                'name': line.name or line.product_id.name,
                'old_price': old_price,
                'new_price': new_price
            })
        
        # Force recalculation
        self._compute_section_margins_json()
        self._compute_section_margins_html()
        
        # Recalculate to verify
        new_total_price = sum(float(line.price_subtotal) for line in subsection_lines)
        new_margin = new_total_price - total_cost
        new_margin_percent = (new_margin / new_total_price * 100) if new_total_price > 0 else 0
        
        # Prepare history data
        old_data = {
            'section_name': section_name,
            'subsection_name': subsection_name,
            'margin_percent': old_margin_percent,
        }
        
        new_data = {
            'section_name': section_name,
            'subsection_name': subsection_name,
            'margin_percent': new_margin_percent,
            'updated_lines': updated_lines,
        }
        
        # Save to history
        try:
            self.env['sale.order.margin.history'].create_history(
                self.id, 'subsection', old_data, new_data
            )
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f'Error saving margin history: {str(e)}')
        
        return {
            'success': True,
            'message': f'Successfully adjusted {len(subsection_lines)} products in subsection',
            'section_name': section_name,
            'subsection_name': subsection_name,
            'old_margin_percent': old_margin_percent,
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
        
        # Prepare data for history
        old_data = {
            'line_id': line_id,
            'product_name': line.name or line.product_id.name,
            'margin_percent': old_margin_percent,
            'price_unit': old_price_unit,
        }
        
        new_data = {
            'margin_percent': new_margin_percent,
            'price_unit': new_price_unit,
        }
        
        # Save to history
        try:
            self.env['sale.order.margin.history'].create_history(
                self.id, 'product', old_data, new_data
            )
        except Exception as e:
            # Don't fail if history fails, just log it
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f'Error saving margin history: {str(e)}')
        
        return {
            'success': True,
            'message': f'Successfully adjusted product price',
            'product_name': line.name or line.product_id.name,
            'old_price_unit': old_price_unit,
            'new_price_unit': new_price_unit,
            'old_margin_percent': old_margin_percent,
            'new_margin_percent': new_margin_percent,
        }

    def _generate_margin_history_html(self):
        """Generate HTML to display margin history - returns HTML string"""
        self.ensure_one()
        
        if not self.id:
            return ''
        
        # Get history records (last 20)
        try:
            history_records = self.env['sale.order.margin.history'].search([
                ('order_id', '=', self.id)
            ], order='create_date desc', limit=20)
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f'Error accessing margin history: {str(e)}')
            return f"""
                <div style="padding: 20px; text-align: center; color: #dc3545; margin-top: 30px; border-top: 2px solid #dee2e6; padding-top: 20px;">
                    <i class="fa fa-exclamation-triangle fa-2x" style="margin-bottom: 10px;"></i>
                    <p><strong>Error loading history:</strong> {str(e)}</p>
                </div>
            """
        
        if not history_records:
            return """
                <div class="history-container">
                    <h4 class="history-header">
                        <i class="fa fa-history"></i>
                        <span>Modification History</span>
                    </h4>
                    <div class="history-empty">
                        <i class="fa fa-info-circle"></i>
                        <p class="title">No history yet</p>
                        <p class="subtitle">Modify any margin (section or product) and you will see the change history here.</p>
                    </div>
                </div>
            """
        
        # Build HTML table (when there are records)
        html = """
        <div class="history-container">
            <h4 class="history-header">
                <i class="fa fa-history"></i>
                <span>Modification History</span>
                <span class="subtitle">(last 20)</span>
            </h4>
            <div class="table-responsive">
                <table class="table history-table">
                    <thead>
                        <tr>
                            <th class="text-start">Type</th>
                            <th class="text-start">Item</th>
                            <th class="text-end">Previous Margin</th>
                            <th class="text-end">New Margin</th>
                            <th class="text-center">Date</th>
                            <th class="text-start">User</th>
                            <th class="text-center">Action</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for idx, record in enumerate(history_records):
            # Format date
            date_str = ''
            if record.create_date:
                date_str = record.create_date.strftime('%d/%m/%Y %H:%M')
            
            # Get user name
            user_name = record.create_uid.name if record.create_uid else ''
            
            # Type badge class
            if record.adjustment_type == 'product':
                type_class = 'product'
                type_label = 'Product'
            elif record.adjustment_type == 'subsection':
                type_class = 'subsection'
                type_label = 'Subsection'
            else:
                type_class = 'section'
                type_label = 'Section'
            
            # Item name
            if record.adjustment_type == 'product':
                item_name = record.product_name
            elif record.adjustment_type == 'subsection':
                item_name = f"{record.section_name} / {record.subsection_name}" if record.subsection_name else record.section_name
            else:
                item_name = record.section_name
            
            html += f"""
                        <tr>
                            <td class="text-start">
                                <span class="history-type-badge {type_class}">{type_label}</span>
                            </td>
                            <td class="text-start history-item-name">
                                {item_name or '-'}
                            </td>
                            <td class="text-end history-margin-old">
                                {record.old_margin_percent:.2f}%
                            </td>
                            <td class="text-end history-margin-new">
                                <strong>{record.new_margin_percent:.2f}%</strong>
                            </td>
                            <td class="text-center history-date">
                                {date_str}
                            </td>
                            <td class="text-start history-user">
                                {user_name}
                            </td>
                            <td class="text-center">
                                <button type="button"
                                        class="btn btn-sm btn-secondary rollback_margin_btn" 
                                        data-order-id="{self.id}"
                                        data-history-id="{record.id}"
                                        data-item-name="{item_name or ''}"
                                        data-old-margin="{record.old_margin_percent:.2f}"
                                        data-new-margin="{record.new_margin_percent:.2f}">
                                    <i class="fa fa-undo"></i>Restore
                                </button>
                            </td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
            </div>
        </div>
        """
        
        return html

    def rollback_margin(self, history_id):
        """
        Restore a previous margin value from the history record

        :param history_id: ID of the history record to restore
        :return: dict with the result
        """
        self.ensure_one()
        
        history = self.env['sale.order.margin.history'].browse(history_id)
        
        if not history.exists():
            return {
                'success': False,
                'message': 'History record not found'
            }
        
        if history.order_id != self:
            return {
                'success': False,
                'message': 'History does not belong to this order'
            }
        
        try:
            if history.adjustment_type == 'product':
                # Restore individual product
                line = history.line_id
                if not line.exists():
                    return {
                        'success': False,
                        'message': 'Product line no longer exists'
                    }
                
                # Restore previous price
                line.price_unit = history.old_price_unit
                
                # Force recalculation
                self._compute_section_margins_json()
                self._compute_section_margins_html()
                
                return {
                    'success': True,
                    'message': f'Margin for "{history.product_name}" restored to {history.old_margin_percent:.2f}%'
                }
                
            elif history.adjustment_type == 'section':
                # Restore all products in the section
                if not history.affected_lines:
                    return {
                        'success': False,
                        'message': 'No affected lines information found'
                    }
                
                affected_lines_data = json.loads(history.affected_lines)
                restored_count = 0
                
                for line_data in affected_lines_data:
                    line_id = line_data.get('line_id')
                    if not line_id:
                        continue
                    
                    line = self.env['sale.order.line'].browse(line_id)
                    if line.exists() and line.order_id == self:
                        old_price = line_data.get('old_price')
                        if old_price:
                            line.price_unit = old_price
                            restored_count += 1
                
                if restored_count == 0:
                    return {
                        'success': False,
                        'message': 'Could not restore any lines'
                    }
                
                # Force recalculation
                self._compute_section_margins_json()
                self._compute_section_margins_html()
                
                return {
                    'success': True,
                    'message': f'Section "{history.section_name}" restored to {history.old_margin_percent:.2f}% ({restored_count} products)'
                }
            
            elif history.adjustment_type == 'subsection':
                # Restore all products in the subsection
                if not history.affected_lines:
                    return {
                        'success': False,
                        'message': 'No affected lines information found'
                    }
                
                affected_lines_data = json.loads(history.affected_lines)
                restored_count = 0
                
                for line_data in affected_lines_data:
                    line_id = line_data.get('line_id')
                    if not line_id:
                        continue
                    
                    line = self.env['sale.order.line'].browse(line_id)
                    if line.exists() and line.order_id == self:
                        old_price = line_data.get('old_price')
                        if old_price:
                            line.price_unit = old_price
                            restored_count += 1
                
                if restored_count == 0:
                    return {
                        'success': False,
                        'message': 'Could not restore any lines'
                    }
                
                # Force recalculation
                self._compute_section_margins_json()
                self._compute_section_margins_html()
                
                return {
                    'success': True,
                    'message': f'Subsection "{history.subsection_name}" restored to {history.old_margin_percent:.2f}% ({restored_count} products)'
                }
            
            else:
                return {
                    'success': False,
                    'message': 'Unknown adjustment type'
                }
                
        except Exception as e:
            import traceback
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f'Error restoring margin: {str(e)}\n{traceback.format_exc()}')
            return {
                'success': False,
                'message': f'Error restoring: {str(e)}'
            }
