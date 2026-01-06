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
        """
        Returns a data structure with margins grouped by section and subsection.
        
        Return structure:
        {
            'sections': [
                {
                    'name': 'Section Name',
                    'margin': 100.0,
                    'margin_percent': 25.5,
                    'subsections': [
                        {
                            'name': 'Subsection Name',
                            'margin': 50.0,
                            'margin_percent': 30.0,
                        }
                    ]
                }
            ],
            'total_margin': 200.0,
            'total_margin_percent': 20.0
        }
        """
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
                }
            
            # Normal product line
            elif line.display_type == False and line.product_id:
                # Get line price
                line_price_subtotal = line.price_subtotal if line.price_subtotal else 0.0
                
                # Get line margin (use margin field if available)
                line_margin = 0.0
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
                except (ValueError, TypeError, AttributeError):
                    # If error, margin will be 0
                    line_margin = 0.0
                
                # Only process if there is a price
                if line_price_subtotal > 0:
                    # Add to subsection if exists
                    if current_subsection and current_section:
                        current_subsection['margin'] += line_margin
                        current_subsection['price_subtotal'] += line_price_subtotal
                    
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
        <div class="section_margin_widget_container" style="padding: 20px; background-color: #ffffff;">
            <div class="o_section_margin_header" style="margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #e9ecef;">
            </div>
            <div class="table-responsive">
                <table class="table table-hover" style="width: 100%; margin-bottom: 0; background-color: #fff; border-collapse: separate; border-spacing: 0;">
                    <thead style="background: linear-gradient(135deg, #4a4a4a 0%, #2c2c2c 100%); color: #fff;">
                        <tr>
                            <th style="padding: 16px 12px; font-weight: 600; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; border: none; color: #fff; text-align: left;">Section</th>
                            <th style="padding: 16px 12px; font-weight: 600; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; border: none; color: #fff; text-align: left;">Subsection</th>
                            <th style="padding: 16px 12px; font-weight: 600; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; border: none; color: #fff; text-align: right;">Margin</th>
                            <th style="padding: 16px 12px; font-weight: 600; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; border: none; color: #fff; text-align: right;">Margin (%)</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for idx, section in enumerate(sections):
            section_name = section.get('name', 'Unnamed')
            section_margin = section.get('margin', 0.0)
            section_margin_percent = section.get('margin_percent', 0.0)
            subsections = section.get('subsections', [])
            
            if subsections:
                # Section with subsections - First show section row with totals
                html += f"""
                        <tr style="background: linear-gradient(90deg, #e0e0e0 0%, #bdbdbd 100%); border-top: 2px solid #9e9e9e; border-bottom: 2px solid #9e9e9e;">
                            <td style="padding: 16px 12px; font-weight: 600; text-align: left; padding-left: 20px;" colspan="2">
                                <span style="display: inline-flex; align-items: center; padding: 6px 12px; background-color: #e0e0e0; color: #424242; border-radius: 6px; font-size: 0.95em;">
                                    <i class="fa fa-folder-open" style="margin-right: 6px;"></i>
                                    <strong>{section_name}</strong>
                                </span>
                            </td>
                            <td style="padding: 16px 12px; font-weight: 600; text-align: right; font-family: 'Courier New', monospace; color: #424242;">
                                <strong>{currency_symbol} {abs(section_margin):,.2f}</strong>
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
                                            onclick="console.log('Botón clickeado directamente'); return false;"
                                            style="padding: 6px 12px; background-color: #616161; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em; white-space: nowrap; z-index: 1000; position: relative;">
                                        <i class="fa fa-check" style="margin-right: 4px;"></i>Aplicar
                                    </button>
                                </div>
                            </td>
                        </tr>
                """
                
                # Then show all subsections below
                for subsection in subsections:
                    sub_name = subsection.get('name', 'Unnamed')
                    sub_margin = subsection.get('margin', 0.0)
                    sub_margin_percent = subsection.get('margin_percent', 0.0)
                    
                    html += f"""
                        <tr style="background-color: #fafafa;">
                            <td style="padding: 14px 12px; vertical-align: middle; border-bottom: 1px solid #e9ecef; text-align: left; padding-left: 40px;">
                            </td>
                            <td style="padding: 14px 12px; vertical-align: middle; border-bottom: 1px solid #e9ecef; text-align: left;">
                                <span style="display: inline-flex; align-items: center; padding: 4px 10px; background-color: #f5f5f5; color: #616161; border-radius: 4px; font-size: 0.9em;">
                                    <i class="fa fa-folder" style="margin-right: 6px;"></i>
                                    {sub_name}
                                </span>
                            </td>
                            <td style="padding: 14px 12px; vertical-align: middle; border-bottom: 1px solid #e9ecef; text-align: right; font-family: 'Courier New', monospace; font-weight: 600; color: #424242;">
                                {currency_symbol} {abs(sub_margin):,.2f}
                            </td>
                            <td style="padding: 14px 12px; vertical-align: middle; border-bottom: 1px solid #e9ecef; text-align: right;">
                                <span style="display: inline-block; padding: 6px 10px; background-color: #757575; color: #fff; border-radius: 0.25rem; font-size: 0.9em; font-weight: 600;">
                                    {sub_margin_percent:.2f}%
                                </span>
                            </td>
                        </tr>
                    """
            else:
                # Section without subsections
                html += f"""
                        <tr style="background: linear-gradient(90deg, #eeeeee 0%, #e0e0e0 100%); border-top: 2px solid #bdbdbd; border-bottom: 2px solid #bdbdbd;">
                            <td style="padding: 16px 12px; font-weight: 600; text-align: left; padding-left: 20px;" colspan="2">
                                <span style="display: inline-flex; align-items: center; padding: 6px 12px; background-color: #e0e0e0; color: #424242; border-radius: 6px; font-size: 0.95em;">
                                    <i class="fa fa-folder-open" style="margin-right: 6px;"></i>
                                    <strong>{section_name}</strong>
                                </span>
                            </td>
                            <td style="padding: 16px 12px; font-weight: 600; text-align: right; font-family: 'Courier New', monospace; color: #424242;">
                                <strong>{currency_symbol} {abs(section_margin):,.2f}</strong>
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
                                            onclick="console.log('Botón clickeado directamente'); return false;"
                                            style="padding: 6px 12px; background-color: #616161; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em; white-space: nowrap; z-index: 1000; position: relative;">
                                        <i class="fa fa-check" style="margin-right: 4px;"></i>Aplicar
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
                                <strong style="color: #fff; font-size: 1.2em;">{currency_symbol} {abs(total_margin):,.2f}</strong>
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
                'message': f'No se encontraron productos en la sección "{section_name}"'
            }
        
        # Calculate current totals
        total_cost = 0.0
        total_price = 0.0
        
        for line in section_lines:
            qty = float(line.product_uom_qty) if line.product_uom_qty else 0.0
            price_subtotal = float(line.price_subtotal) if line.price_subtotal else 0.0
            
            # Get cost
            cost = 0.0
            if hasattr(line, 'purchase_price') and line.purchase_price:
                cost = float(line.purchase_price) * qty
            elif hasattr(line.product_id, 'standard_price') and line.product_id.standard_price:
                cost = float(line.product_id.standard_price) * qty
            
            total_cost += cost
            total_price += price_subtotal
        
        if total_cost == 0:
            return {
                'success': False,
                'message': 'No se puede ajustar: el costo total es 0'
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
                'message': 'El margen no puede ser 100% o mayor'
            }
        
        target_total_price = total_cost / (1 - target_margin_decimal)
        
        # Calculate adjustment factor (same percentage for all products)
        adjustment_factor = target_total_price / total_price if total_price > 0 else 1.0
        
        # Apply adjustment to all lines
        updated_lines = []
        for line in section_lines:
            old_price = line.price_unit
            new_price = old_price * adjustment_factor
            
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
            'message': f'Ajuste aplicado exitosamente a {len(section_lines)} productos',
            'section_name': section_name,
            'old_margin_percent': (total_price - total_cost) / total_price * 100 if total_price > 0 else 0,
            'new_margin_percent': new_margin_percent,
            'adjustment_factor': adjustment_factor,
            'updated_lines': updated_lines
        }
