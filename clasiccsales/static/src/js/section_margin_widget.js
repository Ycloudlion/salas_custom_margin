/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillUpdateProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { formatFloat } from "@web/fields/formatters";

export class SectionMarginWidget extends Component {
    setup() {
        this.state = useState({
            sections: [],
            totalMargin: 0,
            totalMarginPercent: 0,
        });
        
        try {
            this._updateData();
            
            onWillUpdateProps(() => {
                try {
                    this._updateData();
                } catch (error) {
                    console.error("Error updating section margins:", error);
                }
            });
        } catch (error) {
            console.error("Error setting up SectionMarginWidget:", error);
        }
    }
    
    _updateData() {
        try {
            if (!this.props || !this.props.record || !this.props.record.data) {
                return;
            }
            
            const jsonData = this.props.record.data[this.props.name];
            if (!jsonData) {
                this.state.sections = [];
                this.state.totalMargin = 0;
                this.state.totalMarginPercent = 0;
                return;
            }
            
            let data;
            if (typeof jsonData === 'string') {
                try {
                    data = JSON.parse(jsonData);
                } catch (parseError) {
                    console.error("Error parsing JSON string:", parseError);
                    this.state.sections = [];
                    this.state.totalMargin = 0;
                    this.state.totalMarginPercent = 0;
                    return;
                }
            } else if (typeof jsonData === 'object') {
                data = jsonData;
            } else {
                this.state.sections = [];
                this.state.totalMargin = 0;
                this.state.totalMarginPercent = 0;
                return;
            }
            
            this.state.sections = Array.isArray(data.sections) ? data.sections : [];
            this.state.totalMargin = Number(data.total_margin) || 0;
            this.state.totalMarginPercent = Number(data.total_margin_percent) || 0;
        } catch (error) {
            console.error("Error in _updateData:", error);
            this.state.sections = [];
            this.state.totalMargin = 0;
            this.state.totalMarginPercent = 0;
        }
    }
    
    formatCurrency(value) {
        try {
            if (value === null || value === undefined || isNaN(value)) {
                value = 0;
            }
            
            let symbol = '$';
            try {
                const currencyId = this.props?.record?.data?.currency_id;
                if (currencyId && Array.isArray(currencyId) && currencyId.length >= 2) {
                    const currencyName = currencyId[1] || '';
                    const symbolMatch = currencyName.match(/\(([^)]+)\)/);
                    if (symbolMatch) {
                        symbol = symbolMatch[1];
                    }
                }
            } catch (error) {
                // Usar símbolo por defecto si hay error
            }
            
            const formattedValue = formatFloat(Math.abs(value), { digits: [16, 2] });
            return `${symbol} ${formattedValue}`;
        } catch (error) {
            console.error("Error formatting currency:", error);
            return `$ ${Number(value || 0).toFixed(2)}`;
        }
    }
    
    formatPercent(value) {
        try {
            if (isNaN(value) || !isFinite(value) || value === null || value === undefined) {
                return "0.00%";
            }
            return `${Number(value).toFixed(2)}%`;
        } catch (error) {
            console.error("Error formatting percent:", error);
            return "0.00%";
        }
    }
}

SectionMarginWidget.template = "clasiccsales.SectionMarginWidget";
SectionMarginWidget.props = {
    ...standardFieldProps,
};

try {
    registry.category("fields").add("section_margin_widget", {
        component: SectionMarginWidget,
    });
} catch (error) {
    console.error("Error registering section_margin_widget:", error);
}

