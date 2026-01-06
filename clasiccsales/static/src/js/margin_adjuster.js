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
    // Use event delegation to handle dynamically loaded content
    document.body.addEventListener('click', async function(e) {
        // Check if clicked element or its parent is the apply button
        const btn = e.target.closest('.apply_margin_btn');
        if (!btn) return;

        e.preventDefault();
        e.stopPropagation();

        const orderId = btn.getAttribute('data-order-id');
        const sectionName = btn.getAttribute('data-section-name');
        const inputContainer = btn.closest('td') || btn.closest('div');
        const input = inputContainer.querySelector('.section_margin_input');
        const targetMargin = parseFloat(input.value);

        // Check if order is saved
        if (!orderId || orderId.toString().startsWith('NewId_')) {
            showNotification('⚠️ Please save the sales order first', 'error');
            return;
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
            const result = await odooRPC('/sale_order/adjust_section_margin', {
                order_id: parseInt(orderId),
                section_name: sectionName,
                target_margin_percent: targetMargin
            });

            if (result.success) {
                // Show success notification
                showNotification(`Margin adjusted to ${result.new_margin_percent.toFixed(2)}%`, 'success');

                // Reload the page after a brief moment to show the notification
                setTimeout(() => {
                    window.location.reload();
                }, 800);
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
