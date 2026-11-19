# Seguridad: qué hace el código fuera de sí mismo

Para quien revise el repositorio antes de correrlo, por ejemplo el área de sistemas de Boston. Detalla cada
conexión, cada credencial, cada programa externo y cada tarea programada, para que se pueda comprobar que no
hay nada oculto.

## Resumen

- **Lenguaje:** Python 3.9, solo con la biblioteca estándar más `openpyxl` ([pyproject.toml](../pyproject.toml)).
  Las pruebas usan `pytest`.
- **Sin binarios:** solo código Python, scripts de shell legibles (`*.command`, `*.sh`), documentación y datos
  de prueba (JSON, Excel, PDF de publicaciones de mercado). No hay ejecutables, instaladores ni macros.
- **Credenciales fuera del repositorio:** las claves de A3 y BYMA se leen de variables de entorno, cargadas
  desde un `.env` local que está excluido en `.gitignore`. [`.env.example`](../.env.example) muestra los nombres
  de las variables, vacías. No hay ninguna clave escrita en el código.
- **Solo lectura de mercado:** las consultas son `GET` de datos de mercado. La única excepción es el pedido
  `POST` que obtiene el token OAuth de BYMA, que es como funciona ese protocolo. No se envían órdenes ni datos
  de clientes.
- **Pruebas sin red:** las 189 pruebas usan respuestas simuladas.

## Conexiones de red

| Destino | Para qué | Credencial | Dónde |
|---|---|---|---|
| `api.mae.com.ar`, `apiuat.mae.com.ar` | A3 Mercados (MAE) Market Data: precios de renta fija, cauciones, forex, futuros | `A3_MARKETDATA_API_KEY_*` | `src/market_data/providers/a3mae/`, `config/settings.py` |
| `apigw.byma.com.ar` | APIs de BYMA (EOD, Delay20 y otras), todavía sin acceso autorizado | `BYMA_CLIENT_ID`, `BYMA_CLIENT_SECRET` | `src/market_data/providers/byma.py` |
| `matbarofex.primary.ventures` | Datos de futuros de dólar | Ninguna | `src/market_data/config/settings.py` |
| `www.argentina.gob.ar` | Listado de licitaciones del Tesoro | Ninguna | `src/market_data/providers/treasury/` |

## Procesos y servicios locales

| Qué | Para qué | Dónde |
|---|---|---|
| Servidor HTTP local en `127.0.0.1:8765` | Sirve el tablero al navegador. Escucha solo en la propia máquina, no en la red | `src/local_dashboard/server.py` |
| `open -a "Google Chrome"` | Abre el tablero en el navegador | `tools/serve_local_dashboard.py` |
| Subprocesos de Python | Lanzan juntos el tablero y el programador de consultas | `tools/run_local_toolkit.py`, `tools/run_futures_toolkit.py` |
| `Abrir Modelo LECAP BONCAP.command`, `Abrir Futuros Dolar.command` | Accesos directos de macOS que buscan Python y arrancan el tablero | Raíz del proyecto |

Los subprocesos reciben los argumentos como lista, sin pasar por una shell. No hay `eval`, `exec` dinámico ni
`pickle`.

## Tarea programada (opcional, no se instala sola)

`tools/com.fixedincome.morningsync.plist` es una tarea de `launchd` que, si se instala a mano en
`~/Library/LaunchAgents`, corre `tools/morning_sync.command` a las 9:30 para descargar los cierres de letras del
Tesoro. Tiene escritas las rutas de la Mac de Felipe: en otra máquina hay que adaptarlas. Ningún script la
instala automáticamente.

## Escrituras en disco

Dentro de la carpeta del proyecto: la base `data/market/market_data.sqlite` con los datos descargados,
`outputs/` (modelos generados y logs) y nada más. La base y los logs no se suben al repositorio: los datos de
A3 tienen licencia de uso.

## Qué no está en el repositorio

- `.env` con las claves reales.
- `bibliography/`: libros de referencia con derechos de autor.
- `data/market/`: datos descargados de A3, con licencia.
- Logs, archivos `.zip` (copias del propio código) y el entorno `.venv/`.

## Cómo verificarlo

```bash
# Todas las direcciones que aparecen en el código
grep -rhoE "https?://[a-zA-Z0-9.-]+" src tools | sort | uniq -c

# Conexiones, procesos y evaluación dinámica
grep -rnE "urlopen|Request\(|subprocess|os\.system|eval\(|exec\(|pickle|shell=True" src tools

# Credenciales leídas del entorno
grep -rnE "environ|getenv" src tools
```

Para probarlo aislado, sin red ni claves:

```bash
python3 -m venv /tmp/fit-venv
/tmp/fit-venv/bin/pip install -e ".[test]"
/tmp/fit-venv/bin/python -m pytest
```
