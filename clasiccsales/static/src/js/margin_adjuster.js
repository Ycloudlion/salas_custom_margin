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

// Show Odoo-style confirmation dialog
function showConfirmDialog(title, message, confirmText = 'Confirm', cancelText = 'Cancel') {
    return new Promise((resolve) => {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'modal-backdrop fade show';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 9999;
            animation: fadeIn 0.15s ease-in;
        `;

        // Create dialog wrapper
        const dialog = document.createElement('div');
        dialog.className = 'modal fade show d-block';
        dialog.style.cssText = `
            position: fixed;
            top: 0%;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 10000;
            display: flex !important;
            align-items: center;
            padding-top: 14%;
            justify-content: center;
            animation: fadeIn 0.15s ease-in;
        `;

        dialog.innerHTML = `
            <div class="modal-dialog" style="max-width: 550px; width: 550px; margin: 0; animation: zoomIn 0.2s ease-out;">
                <div class="modal-content" style="border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); border: none;">
                    <div class="modal-header" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; padding: 12px 20px; border-radius: 8px 8px 0 0;">
                        <h5 class="modal-title" style="font-weight: 600; color: white; margin: 0; font-size: 16px;">
                            <i class="fa fa-question-circle" style="margin-right: 8px;"></i>
                            ${title}
                        </h5>
                    </div>
                    <div class="modal-body" style="padding: 20px; font-size: 13px; color: #212529; background-color: #fff;">
                        ${message}
                    </div>
                    <div class="modal-footer" style="background-color: #f8f9fa; border-top: 1px solid #e9ecef; padding: 12px 20px; border-radius: 0 0 8px 8px; display: flex; justify-content: flex-end; gap: 8px;">
                        <button type="button" class="btn btn-secondary cancel-btn" style="padding: 6px 20px; font-weight: 500; border-radius: 4px; font-size: 13px;">
                            <i class="fa fa-times" style="margin-right: 5px;"></i>${cancelText}
                        </button>
                        <button type="button" class="btn btn-primary confirm-btn" style="padding: 6px 20px; font-weight: 500; border-radius: 4px; font-size: 13px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none;">
                            <i class="fa fa-check" style="margin-right: 5px;"></i>${confirmText}
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Add to document
        document.body.appendChild(overlay);
        document.body.appendChild(dialog);

        // Close dialog function
        const closeDialog = (confirmed) => {
            const modalDialog = dialog.querySelector('.modal-dialog');
            
            // Smooth close animations
            modalDialog.style.animation = 'zoomOut 0.2s ease-in';
            overlay.style.opacity = '0';
            overlay.style.transition = 'opacity 0.2s ease-in';
            
            setTimeout(() => {
                dialog.remove();
                overlay.remove();
                resolve(confirmed);
            }, 200);
        };

        // Handle confirm
        const confirmBtn = dialog.querySelector('.confirm-btn');
        confirmBtn.addEventListener('click', () => {
            closeDialog(true);
        });

        // Handle cancel
        const cancelBtn = dialog.querySelector('.cancel-btn');
        cancelBtn.addEventListener('click', () => {
            closeDialog(false);
        });

        // Close on overlay click
        overlay.addEventListener('click', () => {
            closeDialog(false);
        });
    });
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
    
    // Handle rollback buttons
    document.body.addEventListener('click', async function(e) {
        const btn = e.target.closest('.rollback_margin_btn');
        if (!btn) return;

        e.preventDefault();
        e.stopPropagation();

        const orderId = btn.getAttribute('data-order-id');
        const historyId = btn.getAttribute('data-history-id');
        const itemName = btn.getAttribute('data-item-name');
        const oldMargin = btn.getAttribute('data-old-margin');
        const newMargin = btn.getAttribute('data-new-margin');

        // Check if order is saved
        if (!orderId || orderId.toString().startsWith('NewId_')) {
            showNotification('⚠️ Please save the sales order first', 'error');
            return;
        }

        // Confirm rollback with Odoo-style dialog
        const confirmed = await showConfirmDialog(
            'Restore Margin?',
            `<div style="display: flex; flex-direction: column; gap: 12px;">
                <div style="text-align: center; padding: 8px 12px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 5px;">
                    <span style="font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600;">Item: </span>
                    <span style="font-size: 13px; font-weight: 700; color: #2d3748;">${itemName}</span>
                </div>
                <div style="display: flex; gap: 10px; justify-content: space-between; align-items: center;">
                    <div style="flex: 1; text-align: center; padding: 12px 15px; background-color: #fff3cd; border: 2px solid #ffc107; border-radius: 5px;">
                        <div style="font-size: 10px; color: #856404; text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 4px; font-weight: 600;">Current</div>
                        <div style="font-size: 22px; font-weight: 700; color: #856404;">${newMargin}%</div>
                    </div>
                    <div style="color: #6c757d; font-size: 20px; flex-shrink: 0;">
                        <i class="fa fa-arrow-right"></i>
                    </div>
                    <div style="flex: 1; text-align: center; padding: 12px 15px; background-color: #d1ecf1; border: 2px solid #17a2b8; border-radius: 5px;">
                        <div style="font-size: 10px; color: #0c5460; text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 4px; font-weight: 600;">Restore To</div>
                        <div style="font-size: 22px; font-weight: 700; color: #0c5460;">${oldMargin}%</div>
                    </div>
                </div>
            </div>`,
            'Restore',
            'Cancel'
        );

        if (!confirmed) {
            return;
        }

        // Disable button and show loading
        btn.disabled = true;
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i>';

        try {
            const result = await odooRPC('/sale_order/rollback_margin', {
                order_id: parseInt(orderId),
                history_id: parseInt(historyId)
            });

            if (result.success) {
                showNotification(result.message || 'Margin restored successfully', 'success');
                
                // Reload the page to show updated values
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification(result.message || 'Error restoring margin', 'error');
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
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    @keyframes zoomIn {
        from { 
            transform: scale(0.7);
            opacity: 0;
        }
        to { 
            transform: scale(1);
            opacity: 1;
        }
    }
    @keyframes zoomOut {
        from { 
            transform: scale(1);
            opacity: 1;
        }
        to { 
            transform: scale(0.7);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
