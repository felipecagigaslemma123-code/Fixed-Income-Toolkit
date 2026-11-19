# BYMA Market Data

**Versión 1.0 · 18 de noviembre de 2026**

El cliente de BYMA permite ejecutar consultas de solo lectura contra el gateway
de Market Data. Cada consulta solicita un token OAuth 2.0 `client_credentials`
con el permiso de ese método. Los resultados se conservan en el formato del
proveedor. El comando informa el estado y la hora de recepción en UTC. Con
`--raw` permite inspeccionar la respuesta original.

| Consulta | Datos que devuelve | Implementación |
| --- | --- | --- |
| `eod` | Cierre de renta fija, con filtros de grupo, mercado, forma operativa, moneda y plazo | JSON, `/eod/v1/fixed_income.raw/`, una página explícita |
| `delay20` | Estado intradiario de renta fija con 20 minutos de demora | JSON, `/delay20/v1/fixed_income` |
| `placements` | Colocaciones vigentes e históricas, con emisor, fechas, condiciones y documentos asociados | JSON, `/byma-primarias-placements/v1/historical-placements.json/`, una página explícita |
| `indices` | Historial del índice de caución de BYMA | CSV, `/byma-indices/v1/caucion/eod.csv/`, ejemplo productivo del manual. Requiere fechas `fromdate` y `todate` |
| `indices-intraday` | Valores intradiarios del índice de caución de BYMA | CSV, `/byma-indices/v1/caucion/intraday.csv/`, una página explícita |
| `dollar-eod` | Cierre del Índice Dólar BYMA y CCL | JSON, `/indice-dolar-byma/v1/eod.json/` |
| `dollar-intraday` | Valores intradiarios del Índice Dólar BYMA y CCL | JSON, `/indice-dolar-byma/v1/intraday.json/` |
| `instruments` | Maestro de instrumentos de renta fija, con identificadores y parámetros de negociación | JSON, `/market-data-instruments/v1/fixedincome.json/`. El producto también cubre acciones, CEDEARs, derivados, cauciones, préstamos y escalas de precios |
| `news` | Hechos relevantes de emisores | JSON, `/market-data-news/v1/relevant-events.json/`. El producto también publica balances, avisos y boletines/prospectos |
| `economic-indicators` | Catálogo de variables publicadas por el BCRA a través de BYMA | JSON, `/economic-indicators/v1/principales-variables/variables.json/` |
| `economic-series` | Serie BCRA de una variable seleccionada por ID | JSON, `/economic-indicators/v1/principales-variables/variables/{id}.json/`. Requiere ID y fechas `from` y `to` |
| Clearing Risk | Márgenes, exposición y garantías de cuentas autorizadas | BYMA la publica como productiva. La prueba funcional requiere acceso de un agente miembro, ambiente habilitado y una cuenta o nodo de riesgo autorizado. El manual distingue portal de homologación y producción |
| Market Fees | Derechos por operación y bonificaciones, orientados a conciliación | Diferido. Se gestiona mediante el acceso operativo del agente miembro |

## Habilitación

Para Market Data, el instructivo indica solicitar el portal y los productos en
BYMA Point y esperar la invitación de `apis@byma.com.ar`. El catálogo comercial
también ofrece planes para no miembros. BYMA puede confirmar en
`marketdata@byma.com.ar` qué plan, cuota y derechos de uso aplican a cada cuenta.
El botón de registro del portal devolvió 403 en la verificación pública. El
endpoint EOD respondió 401 en una consulta sin token, lo que acredita que el
gateway respondió y exige autorización. La verificación autenticada sigue
pendiente de las credenciales y los permisos de la aplicación.

Configurá las variables `BYMA_*` de [`.env.example`](../../.env.example) en el
entorno local. Para EOD y Delay20, tomá el `scope` exacto de cada método desde
el portal. Los demás permisos implementados figuran en sus manuales públicos.
La aplicación OAuth se toma desde **Mis aplicaciones** del portal.

```sh
python tools/smoke_byma.py eod
python tools/smoke_byma.py delay20
python tools/smoke_byma.py placements --raw
python tools/smoke_byma.py indices --param fromdate=2026-11-02 --param todate=2026-11-17
python tools/smoke_byma.py dollar-eod --param date=2026-11-17
python tools/smoke_byma.py economic-indicators
python tools/smoke_byma.py economic-series --param id=1 --param from=2026-11-02 --param to=2026-11-17
python tools/smoke_byma.py instruments --param group=OBLIGACIONESNEGOC
python tools/smoke_byma.py news --param date=2026-11-17
```

Las consultas de cotizaciones arrancan con Letras del Tesoro en PPT, contado,
pesos y 24 horas. Pasá `--param group=OBLIGACIONESNEGOC` para consultar ON.
En EOD y Primarias, `--param page=1` solicita la segunda página. El resultado
de Primarias conserva `meta.nextPage` cuando el proveedor lo informa. Para
acotar la búsqueda se pueden indicar `fromStartDate`, `toStartDate`, `issuerId`,
`underwriterId` o `placementId`. El histórico del índice de caución y la serie
de variables económicas requieren fechas ISO.

Las respuestas se utilizan para cotejar fecha, moneda, plazo, mercado, identidad
del instrumento, base del precio y significado de los ceros antes de integrar
BYMA a SQLite, al tablero o a cálculos. Los valores del Índice Dólar BYMA se
consumen tal como los publica BYMA. La consulta macro usa el catálogo y las
series públicas y deja fuera los métodos que buscan por CUIT o por cheque.

## Fuentes oficiales

- [Catálogo técnico BYMA](https://www.byma.com.ar/byma-apis) y [planes de Market Data](https://www.byma.com.ar/productos/productos-de-datos/market-data/apis).
- [Portal](https://apiportal.byma.com.ar/) e [instructivo de usuarios](https://jira-tecval.atlassian.net/wiki/external/NmExOGJhY2FhNDBlNDA1YWFkYzkzMjA4ZTQ2NDc0YWM).
- [Delay20](https://jira-tecval.atlassian.net/wiki/external/MzRjNWJmYjUxZmMxNDQ2YzgwMWM1OGI2MWE0MTQ4ZWE), [EOD](https://jira-tecval.atlassian.net/wiki/external/ZTVjZmYyZTkyYjJhNDM2MjkzYWJlZmQwOTRhNmQyYjQ) y [Primarias](https://jira-tecval.atlassian.net/wiki/external/ZThiZTE3OTUyZWExNGI0NWFmYjIwZGQzNjU2M2QzNGU).
- [Índices](https://jira-tecval.atlassian.net/wiki/external/NzFjYmU4MDNmNTI2NGYwZjhhZDUzMTMyNjQ0Njg5ZTM), [Índice Dólar BYMA](https://jira-tecval.atlassian.net/wiki/external/YTk5NDc1NGFmMjA0NGM3M2JlMTM4NWMyOWFhNzRkMTU), [Instruments](https://jira-tecval.atlassian.net/wiki/external/NzU4NzVkODAwOTY3NGI2YThhMjQ4YmJlYTIwODBmYjE), [News](https://jira-tecval.atlassian.net/wiki/external/YWI0NjVkOTQ2Mzc5NDhjNzg3ZWMyODU2MmI1OTM1NWI) e [Indicadores Económicos](https://jira-tecval.atlassian.net/wiki/external/NzQ4NmU0ODZjMmQyNGNjNzk2MDhlYTkzODJiNmY4NmY).
- [Clearing Risk](https://jira-tecval.atlassian.net/wiki/external/Nzc5ZjZjYWQ3YTZkNDgyYmJmNDA4MWVjZTFmMjQ5NDM) y [Market Fees](https://jira-tecval.atlassian.net/wiki/external/YTBlMzEyZmRhMjM2NGVhMGIzNDU0OWU3MDNjZmI5YjE).
