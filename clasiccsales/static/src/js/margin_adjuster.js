/** @odoo-module **/

// Simple RPC function using fetch, returns a Promise
async function odooRPC(route, params) {
    const response = await fetch(route, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: 'call',
            params: params,
            id: new Date().getTime(),
        }),
    });

    const data = await response.json();

    if (data.error) {
        throw new Error(data.error.data?.message || data.error.message || 'RPC Error');
    }

    return data.result;
}


// Show a temporary notification
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        background-color: ${type === 'success' ? '#28a745' : '#dc3545'};
        color: white;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        z-index: 10000;
        font-size: 14px;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
    notification.innerHTML = `<i class="fa fa-${type === 'success' ? 'check' : 'exclamation'}-circle"></i> ${message}`;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    initMarginAdjuster();
});

function initMarginAdjuster() {
    // Listen for input changes to show/hide apply button
    document.body.addEventListener('input', function(e) {
        // Handle section inputs
        let input = e.target.closest('.section_margin_input');
        let btnClass = '.apply_margin_btn';
        
        // Handle product inputs
        if (!input) {
            input = e.target.closest('.product_margin_input');
            btnClass = '.apply_product_margin_btn';
        }
        
        if (!input) return;
        
        const currentValue = parseFloat(input.value);
        const originalValue = parseFloat(input.getAttribute('data-current-margin'));
        const container = input.closest('div');
        const applyBtn = container.querySelector(btnClass);
        
        if (applyBtn) {
            // Show button only if value has changed
            if (!isNaN(currentValue) && currentValue !== originalValue) {
                applyBtn.style.display = 'inline-block';
            } else {
                applyBtn.style.display = 'none';
            }
        }
    });
    
    // Use event delegation to handle dynamically loaded content
    document.body.addEventListener('click', async function(e) {
        // Check if clicked element or its parent is one of the apply buttons
        let btn = e.target.closest('.apply_margin_btn');
        let adjustType = 'section';
        
        if (!btn) {
            btn = e.target.closest('.apply_product_margin_btn');
            adjustType = 'product';
        }
        
        if (!btn) return;

        e.preventDefault();
        e.stopPropagation();

        const orderId = btn.getAttribute('data-order-id');
        const inputContainer = btn.closest('td') || btn.closest('div');
        let input, targetMargin, route, params;

        // Check if order is saved
        if (!orderId || orderId.toString().startsWith('NewId_')) {
            showNotification('⚠️ Please save the sales order first', 'error');
            return;
        }

        // Prepare parameters based on adjustment type
        if (adjustType === 'section') {
            const sectionName = btn.getAttribute('data-section-name');
            input = inputContainer.querySelector('.section_margin_input');
            targetMargin = parseFloat(input.value);
            route = '/sale_order/adjust_section_margin';
            params = {
                order_id: parseInt(orderId),
                section_name: sectionName,
                target_margin_percent: targetMargin
            };
        } else if (adjustType === 'product') {
            const lineId = btn.getAttribute('data-line-id');
            input = inputContainer.querySelector('.product_margin_input');
            targetMargin = parseFloat(input.value);
            route = '/sale_order/adjust_product_margin';
            params = {
                order_id: parseInt(orderId),
                line_id: parseInt(lineId),
                target_margin_percent: targetMargin
            };
        }

        if (isNaN(targetMargin) || targetMargin < 0 || targetMargin > 100) {
            showNotification('Please enter a valid margin between 0 and 100%', 'error');
            return;
        }

        // Disable button and show loading
        btn.disabled = true;
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i>';

        try {
            const result = await odooRPC(route, params);

            if (result.success) {
                // Show success notification
                const itemType = adjustType === 'section' ? 'Section' : 'Product';
                showNotification(`${itemType} margin adjusted to ${result.new_margin_percent.toFixed(2)}%`, 'success');
                
                // Reload the page to show all updated values
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification(result.message || 'Error adjusting margin', 'error');
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        } catch (error) {
            showNotification('Error communicating with server', 'error');
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    });
}

// Try to initialize immediately in case DOM is already ready
if (document.readyState !== 'loading') {
    initMarginAdjuster();
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
    }
`;
document.head.appendChild(style);
