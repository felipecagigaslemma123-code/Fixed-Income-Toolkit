# Armado y seguimiento de carteras de clientes

**Estado** — Propuesta diferida. Módulo independiente del Fixed Income Toolkit. Se retomará después de cerrar el modelo actual.

## Objetivo

Traducir las necesidades de un cliente en un calendario de cobros de renta fija. El módulo permitiría armar y comparar propuestas, verificar cuánto capital estará disponible por fecha y moneda, y mostrar qué compromisos dependen de vender una posición antes de su vencimiento.

## Primera entrega al retomar el módulo

- Cargar un mandato con monto, moneda, compromisos por fecha, reserva de liquidez, instrumentos permitidos y límites de concentración.
- Armar dos propuestas manuales con LECAP y BONCAP soportadas, precios fechados, costos ingresados y montos por posición.
- Comparar el desembolso inicial, el saldo disponible y los cobros contractuales antes de cada compromiso. Arrastrar el saldo después de cada pago para evitar contar los mismos fondos dos veces.
- Señalar faltantes por fecha y moneda. Mostrar por separado la caja disponible, los cobros previstos y los fondos que dependerían de ventas anticipadas.

**Caso de referencia ficticio.** Una PyME tiene $100 millones de excedente transitorio. Necesita $30 millones al día 30 para sueldos e impuestos, $40 millones al día 90 para proveedores y puede mantener el resto hasta el día 180. Comparar una propuesta con vencimientos escalonados contra otra con más caja disponible. Si al día 90 quedan $35 millones disponibles para proveedores, mostrar un faltante de $5 millones. Registrar por separado cualquier obligación en dólares.

## Evolución

| Etapa | Alcance |
| --- | --- |
| Riesgo y escenarios | Concentración por emisor, grupo, moneda, indexación y vencimiento. Sensibilidad a tasas, escenarios de salida anticipada y de reinversión. |
| Cartera real y seguimiento | Operaciones liquidadas, cupones, amortizaciones, aportes y retiros. Conciliación con el extracto del agente y alertas de vencimiento o desvío. |
| Ampliación del universo | Incorporar BONCER, dólar linked, deuda en moneda dura y obligaciones negociables cuando sus metodologías estén aprobadas. |
| Propuestas asistidas | Generar carteras candidatas bajo restricciones de caja, elegibilidad y concentración. Mostrar qué compromiso cubre cada posición y qué supuestos condicionan la asignación. |
| Reportes | Presentar objetivo, composición, próximos cobros, supuestos, fecha de las cotizaciones y principales riesgos. Conservar el historial de propuestas y decisiones. |

## Criterios de diseño y validación

- Distinguir propuesta, operación liquidada y posición. Conservar la diferencia entre precio de referencia y precio ejecutado, incluidos costos.
- Registrar procedencia y fecha de los datos de mercado, condiciones contractuales, parámetros del cliente y resultados calculados. Consumir los cálculos aprobados del motor financiero y mantener separada la adquisición de datos.
- Distinguir el rendimiento proyectado de una propuesta, el desempeño de la gestión y el retorno que obtuvo el cliente con sus aportes y retiros. Documentar y validar la metodología correspondiente a cada medición.
- La duración aprobada para el pago único de LECAP y BONCAP tiene su propio alcance. Duración de cartera, sensibilidad de bonos con cupón, desempeño y optimización requieren investigación, validación y aprobación antes de su implementación en producción.
- En una etapa posterior, el DCF puede aportar proyecciones de repago para analizar el crédito de emisores de ON. La evaluación de cada posición también debe considerar las condiciones de la emisión, la liquidez y la concentración.

Referencias internas: [Roadmap](../docs/roadmap.md) y [alcance financiero](../docs/financial_scope.md).
