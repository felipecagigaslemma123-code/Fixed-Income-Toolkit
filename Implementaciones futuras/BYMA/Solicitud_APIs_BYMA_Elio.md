# APIs de BYMA para el Fixed Income Toolkit

**Fecha:** 19 de noviembre de 2026  
**Propósito:** preparar la consulta a Elio y darle a Claude contexto para evaluar la cobertura, el valor y el esfuerzo de integrar cada API.  
**Estado al preparar este documento:** consulta por confirmar con Elio. La conversación del proyecto no registra un envío, una respuesta, credenciales habilitadas ni una prueba autenticada exitosa.

## Qué queremos resolver

El Toolkit ya usa A3 para precios. La evaluación de BYMA tiene dos objetivos inmediatos. El primero es obtener **precios de cierre de renta fija** para contrastar observaciones y alimentar el tablero cuando se valide la correspondencia de los datos. El segundo es hacer **seguimiento de emisiones y licitaciones** para contar con un historial de colocaciones y acceder a su documentación. Las otras APIs se evalúan según el uso concreto y el costo de acceso.

## Solicitudes para evaluar

| API de BYMA | Prioridad | Motivo del pedido | Qué debe verificar Claude |
|---|---|---|---|
| **End of Day (EOD)** | Piloto | Incorporar cierres de letras, bonos y ON y contrastarlos con otras fuentes. | Cobertura por grupo de renta fija, segmento, moneda y plazo. Distinguir precio de cierre de último operado. Verificar fecha, base del precio, registros sin operaciones y disponibilidad histórica real. |
| **BYMA Primarias Placements** | Piloto | Seguir próximas licitaciones y conservar un historial de colocaciones con datos de la emisión y enlaces a documentos. | Filtros por fecha, emisor y colocador, paginación, estados y acceso a adjuntos. Confirmar si informa resultados de adjudicación, monto y tasa de corte, o si esos campos requieren leer documentos. |
| **Delay20** | Segunda etapa | Agregar cotizaciones de BYMA durante la rueda con 20 minutos de demora. | Hora de la cotización, último operado, puntas y volumen. Verificar cobertura, cuota de consultas y valor incremental si EOD cubre el uso diario. |
| **Índices** | Segunda etapa | Sumar referencias de mercado para el tablero, comenzando por el índice de caución. | Listado de series realmente disponibles, profundidad histórica, frecuencia, unidades, metodología e identificadores. Verificar posible solapamiento con Índice Dólar BYMA. |
| **Índice Dólar BYMA** | Segunda etapa | Incorporar las referencias de dólar BYMA y CCL con la identificación publicada por el proveedor. | Series que devuelve, fecha y hora, formato y cobertura de cierre e intradiaria. Cotejar una observación con la publicación oficial de BYMA. |
| **Market Data Instruments** | Segunda etapa | Completar el maestro de renta fija y vincular instrumentos con sus cotizaciones. | Campos e identificadores disponibles, cobertura PPT y SENEBI y tratamiento de un mismo título por moneda, plazo y ámbito de negociación. Verificar cuáles datos contractuales requieren otra fuente. |
| **Market Data News** | Complementaria | Seguir hechos relevantes, avisos, balances y prospectos de emisores. | Métodos y filtros por tipo, fecha y emisor. Verificar si devuelve enlaces o documentos, cómo detectar rectificaciones y si se puede vincular el emisor al maestro. |
| **Economic Indicators** | Complementaria | Evaluar si agrega valor para los resúmenes macro. | Comparar el catálogo, el historial, las unidades y la actualización con la API directa del BCRA. Limitar la evaluación a series económicas, sin consultas crediticias por CUIT/CUIL ni por cheque. |

**Alcance del pedido.** Para Primarias, pedir el producto **Placements**, que es el de consulta de colocaciones. La gestión de ofertas vía **BYMA Primarias Agentes**, Clearing Risk y Market Fees queda fuera de esta evaluación.

## Homologación y habilitación

En el catálogo oficial, las ocho fichas muestran **«No requiere homologación»**. Esto permite plantear una integración sin el proceso formal de certificación técnica previa de BYMA. La prueba interna del Toolkit sigue siendo necesaria para validar que los datos recibidos sirven para el uso previsto.

El acceso se habilita por separado. BYMA indica que Market Data por API se ofrece a personas jurídicas y publica condiciones comerciales por producto. Para el piloto corresponde confirmar qué tiene habilitado la entidad, si puede autorizar una aplicación con permisos de solo lectura y qué condiciones aplican al uso, almacenamiento y eventual presentación de datos en informes a clientes. Para **Índices** y **Economic Indicators**, conviene preguntar por la disponibilidad para la entidad en particular, porque la ficha técnica muestra la etiqueta de agente miembro. [Catálogo técnico de BYMA](https://www.byma.com.ar/byma-apis) · [Planes y requisitos de Market Data](https://www.byma.com.ar/productos/productos-de-datos/market-data/apis)

## Consulta preparada para Elio

> Hola, Elio. ¿Cómo estás? Estoy evaluando qué datos de BYMA podemos conectar a una herramienta de renta fija. Para una primera prueba me interesan **End of Day**, para precios de cierre, y **BYMA Primarias Placements**, para seguimiento de emisiones y licitaciones.
>
> También quisiera saber si tienen habilitadas Delay20, Índices, Índice Dólar BYMA, Market Data Instruments, Market Data News y Economic Indicators, para evaluar cuáles sumaría después. En el catálogo de BYMA estas APIs figuran sin homologación.
>
> ¿Podés confirmar qué productos están disponibles y si se puede habilitar un acceso de solo lectura para probar las dos primeras? Si corresponde, también me serviría saber en qué entorno está permitido usarlas y si hay condiciones para guardar datos o incluirlos en informes. Si esto lo lleva otra persona, ¿me indicás con quién verlo? Gracias.

## Punto de partida técnico

- Existe un cliente con consultas iniciales de solo lectura y un comando para inspeccionar las respuestas de cada API. Las pruebas simuladas pasaron. El endpoint de EOD respondió **401** en una consulta sin token. La conectividad autenticada y el contenido de las respuestas reales siguen pendientes.
- El cliente devuelve las respuestas de BYMA en su formato de origen. La integración al tablero y a SQLite se evalúa después de revisar muestras reales. Para EOD y Delay20 todavía hay que confirmar los permisos específicos que indique el portal.
- Los nombres de operaciones, rutas y filtros implementados están en el contrato del proveedor. Si este archivo se abre fuera de la carpeta del proyecto, las rutas de abajo identifican los archivos que conviene darle a Claude junto con este documento.

| Ruta dentro del proyecto | Qué revisar |
|---|---|
| [`docs/providers/byma_provider_contract.md`](../../docs/providers/byma_provider_contract.md) | Manuales oficiales, comandos y alcance de las consultas implementadas. |
| [`src/market_data/providers/byma.py`](../../src/market_data/providers/byma.py) | Operaciones, autenticación, filtros y formato de respuesta. |
| [`tools/smoke_byma.py`](../../tools/smoke_byma.py) | Comando para probar cada consulta cuando haya acceso autorizado. |
| [`tests/test_byma_provider.py`](../../tests/test_byma_provider.py) | Casos y validaciones que ya se probaron con respuestas simuladas. |

## Revisión pedida a Claude

1. Cotejá la lista de solicitudes con el cliente y la documentación oficial. Para cada API indicá qué cubre el código actual, qué solo está documentado y qué depende de la respuesta de Elio o BYMA.
2. Devolvé una recomendación por API con su utilidad concreta, el dato o permiso decisivo que falta y la prueba mínima para resolverlo. Si un campo no aparece en una fuente verificable, dejalo como **N/D** con el motivo.
3. Definí el piloto mínimo. Para **EOD**, elegí una rueda y un instrumento identificados de manera inequívoca. Cotejá fecha, moneda, plazo, segmento y base de cotización antes de comparar precios. Para **Placements**, elegí una colocación conocida y verificá estado, fechas y enlaces contra la publicación oficial.
4. Si hay una propuesta de integración, indicá por dónde entra el dato, cómo se conserva su fuente y qué validaciones necesita antes de alimentar el tablero. Cualquier nuevo cálculo financiero requiere el proceso de validación del proyecto. El alcance de esta revisión es evaluar y proponer.

## Fuentes públicas

- [BYMA Primarias, listado público de colocaciones](https://www.byma.com.ar/productos/productos-financieros/primarias/colocaciones).
- [BYMA, publicación de índices de mercado](https://www.byma.com.ar/).
- [BCRA, catálogo de APIs](https://www.bcra.gob.ar/apis-banco-central/).
