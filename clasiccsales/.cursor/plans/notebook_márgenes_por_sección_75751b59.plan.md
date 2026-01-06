# Plan: Notebook de Márgenes por Sección y Subsección

## Objetivo

Agregar una nueva pestaña en la vista de cotización/pedido de venta de Odoo 19 que muestre:

- Margen y porcentaje de margen por sección y sus subsecciones
- Suma total de cada sección (separando las sumas de cada sección)
- Visualización clara y estructurada de la información

## Estructura del Módulo

### Archivos a Crear

1. **`__manifest__.py`** - Manifesto del módulo con dependencias y recursos
2. **`__init__.py`** - Inicialización del módulo
3. **`models/__init__.py`** - Inicialización de modelos
4. **`models/sale_order.py`** - Extensión del modelo sale.order con métodos para calcular márgenes por sección
5. **`views/sale_order_views.xml`** - Vista XML que agrega la nueva pestaña
6. **`static/src/js/section_margin_widget.js`** - Widget JavaScript para mostrar los márgenes agrupados
7. **`static/src/xml/section_margin_widget.xml`** - Template XML del widget
8. **`static/src/css/section_margin_widget.css`** - Estilos para el widget

## Implementación Detallada

### 1. Estructura del Módulo (`__manifest__.py`)

- Nombre: `clasiccsales`
- Versión: 19.0.1.0.0
- Dependencias: `sale`, `sale_margin` (si existe en Odoo 19)
- Categoría: Sales
- Datos: vistas XML
- Assets: JavaScript y CSS del widget

### 2. Extensión del Modelo (`models/sale_order.py`)

- Agregar método `_get_section_margins()` que:
- Recorra las líneas de pedido (`order_line`)
- Identifique secciones (`display_type == 'line_section'`)
- Agrupe subsecciones (`display_type == 'line_subsection'`) bajo su sección padre
- Calcule margen total y porcentaje por sección/subsección
- Retorne estructura de datos: `{section_name: {margin: X, margin_percent: Y, subsections: [...]}}`

### 3. Vista XML (`views/sale_order_views.xml`)

- Extender la vista de formulario `sale.order`
- Localizar el notebook existente (que contiene "Order Lines", "Other Info", "Customer Signature")
- Agregar nueva página `<page>` antes de "Customer Signature" con:
- Nombre: "Márgenes por Sección"
- Campo widget personalizado que muestre los datos agrupados

### 4. Widget JavaScript (`static/src/js/section_margin_widget.js`)

- Crear widget que extienda `AbstractField` o `FieldText`
- Implementar `_render()` para:
- Obtener datos del método `_get_section_margins()` del modelo
- Renderizar tabla HTML con:
- Encabezados: Sección, Subsección, Margen, Margen (%)
- Filas agrupadas por sección
- Fila de total por sección (en negrita)
- Total general al final
- Manejar actualización cuando cambien las líneas de pedido

### 5. Template XML del Widget (`static/src/xml/section_margin_widget.xml`)

- Definir estructura HTML base del widget
- Incluir placeholders para datos dinámicos

### 6. Estilos CSS (`static/src/css/section_margin_widget.css`)

- Estilos para tabla de márgenes
- Resaltar totales de sección
- Diseño responsive y consistente con Odoo

## Consideraciones Técnicas

- **Identificación de Secciones**: Usar `display_type == 'line_section'` y `display_type == 'line_subsection'` en `sale.order.line`
- **Cálculo de Margen**: Usar campos `margin` y `margin_percent` existentes en las líneas de pedido (si están disponibles) o calcular: `margin = price_subtotal - cost`, `margin_percent = (margin / price_subtotal) * 100`
- **Agrupación**: Las subsecciones pertenecen a la sección anterior más cercana en el orden de las líneas
- **Actualización**: El widget debe actualizarse cuando se modifiquen las líneas de pedido (onchange)

## Flujo de Datos

```javascript
sale.order (order_line)
→ _get_section_margins()
→ Estructura agrupada por sección/subsección
→ Wid



## Archivos Clave

- `models/sale_order.py` - Lógica de negocio y cálculo de márgenes




```