/** @odoo-module **/

console.log('Margin Adjuster JS cargado');

// Simple RPC function using fetch
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
        throw new Error(data.error.data?.message || data.error.message || 'Error en RPC');
    }
    
    return data.result;
}

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Ready - Inicializando manejadores de margen');
    initMarginAdjuster();
});

function initMarginAdjuster() {
    console.log('Inicializando MarginAdjuster');
    
    // Use event delegation to handle dynamically loaded content
    document.body.addEventListener('click', async function(e) {
        // Check if clicked element or its parent is the apply button
        const btn = e.target.closest('.apply_margin_btn');
        if (!btn) return;
        
        console.log('Botón de ajuste clickeado', btn);
        e.preventDefault();
        e.stopPropagation();
        
        const orderId = btn.getAttribute('data-order-id');
        const sectionName = btn.getAttribute('data-section-name');
        const inputContainer = btn.closest('td') || btn.closest('div');
        const input = inputContainer.querySelector('.section_margin_input');
        const targetMargin = parseFloat(input.value);
        
        console.log('Datos del ajuste:', {
            orderId: orderId,
            sectionName: sectionName,
            targetMargin: targetMargin
        });
        
        if (isNaN(targetMargin) || targetMargin < 0 || targetMargin > 100) {
            alert('Por favor ingrese un margen válido entre 0 y 100%');
            return;
        }
        
        // Confirm action
        if (!confirm(`¿Desea ajustar el margen de la sección "${sectionName}" a ${targetMargin}%?`)) {
            return;
        }
        
        // Disable button and show loading
        btn.disabled = true;
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Ajustando...';
        
        try {
            console.log('Llamando al servidor...');
            const result = await odooRPC('/sale_order/adjust_section_margin', {
                order_id: parseInt(orderId),
                section_name: sectionName,
                target_margin_percent: targetMargin
            });
            
            console.log('Resultado del servidor:', result);
            
            if (result.success) {
                const message = result.message + 
                    '\n\nMargen anterior: ' + result.old_margin_percent.toFixed(2) + '%' +
                    '\nNuevo margen: ' + result.new_margin_percent.toFixed(2) + '%' +
                    '\nFactor de ajuste: ' + result.adjustment_factor.toFixed(4);
                
                alert(message);
                
                // Reload the page to show updated values
                window.location.reload();
            } else {
                alert('Error: ' + (result.message || 'Error desconocido'));
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        } catch (error) {
            console.error('Error al ajustar margen:', error);
            alert('Error al comunicarse con el servidor: ' + (error.message || 'Error desconocido'));
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    });
    
    console.log('Event listener agregado al body para .apply_margin_btn');
}

// Try to initialize immediately in case DOM is already ready
if (document.readyState === 'loading') {
    console.log('DOM aún cargando, esperando...');
} else {
    console.log('DOM ya está listo, inicializando inmediatamente');
    initMarginAdjuster();
}
