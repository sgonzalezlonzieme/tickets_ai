# Evaluaciones de prompts con OpenAI o Gemini

El runner compara variantes con los mismos casos de su etapa, secuencialmente.
Elegí proveedor y modelo en [`config.yaml`](config.yaml), independiente de
`LLM_PROVIDER`, `OPENAI_MODEL` y `GEMINI_MODEL` del CLI.

```yaml
provider: gemini
model: gemini-3.8-flash
max_output_tokens: 4000
```

Para OpenAI, usá `provider: open_ai` y su modelo, por ejemplo `gpt-6-luna`.
El archivo incluido conserva OpenAI/gpt-6-luna como selección inicial para no
cambiar corridas existentes. `max_output_tokens` es opcional (4000 por defecto).
`temperature` es opcional (0.2), se usa solo para OpenAI y se omite con
`gpt-6-luna`, que conserva `reasoning.effort=max`. Gemini mantiene la temperatura
por defecto del SDK/modelo; el resumen informa null para esos ajustes no enviados.

Las credenciales se leen del `.env` raíz: solo hace falta la clave del proveedor
elegido. El limitador de solicitudes y los reintentos de transporte de ese
proveedor siguen aplicando. **No hay fallback entre proveedores ni reintentos
por JSON inválido** en evals: los errores se registran como fallos para no mezclar
resultados de distintos proveedores. Ejecutar el runner hace llamadas reales y
consume tokens; no selecciona automáticamente modelos según su disponibilidad.

`--config RUTA` permite usar otra configuración (una ruta relativa se interpreta
desde la carpeta actual); `--model MODELO` sobrescribe solo el modelo de esa
corrida y tiene prioridad sobre el YAML, sin modificarlo. La configuración se
valida antes de crear el cliente o gastar tokens. Las claves de etapa y dataset
permanecen compartidas; se envía y valida el contrato específico del proveedor.

La selección predeterminada de cada etapa se lee de
`prompts/active_prompts.yaml`, igual que en el CLI. `--prompt` permite comparar
otras variantes sin cambiar ese archivo.

## Organización del código

`runner.py` es una entrada mínima que llama a `core/cli.py`. Los módulos
internos están agrupados en `core/`, separados del dataset y la documentación.

```text
evals/
├── runner.py
├── config.yaml
├── data_set.jsonl
├── README.md
└── core/
    ├── cli.py
    ├── config.py
    ├── providers.py
    ├── stages.py
    ├── dataset.py
    ├── planning.py
    ├── scoring.py
    ├── execution.py
    └── reports.py
```

| Archivo | Responsabilidad |
| --- | --- |
| [`runner.py`](runner.py) | Punto de entrada compatible con los comandos existentes. |
| [`core/cli.py`](core/cli.py) | Argumentos, coordinación de la corrida y código de salida. |
| [`core/config.py`](core/config.py) | Validación del proveedor, modelo y ajustes propios de las evals. |
| [`core/providers.py`](core/providers.py) | Configuración y cliente directo del proveedor elegido, con sus contratos, sin fallback. |
| [`core/stages.py`](core/stages.py) | Rutas y configuración por etapa: carpeta, dataset y contrato. |
| [`core/dataset.py`](core/dataset.py) | Validación del JSONL unificado y selección de casos por etapa. |
| [`core/planning.py`](core/planning.py) | Prompts, casos, límite y hash del dataset; validación previa a las llamadas. |
| [`core/scoring.py`](core/scoring.py) | Criterios de aprobación, sin llamadas a modelos. |
| [`core/execution.py`](core/execution.py) | Llamadas secuenciales a OpenAI o Gemini, validación de respuestas, resultados parciales y cierre del cliente. |
| [`core/reports.py`](core/reports.py) | Carpeta de corrida y resumen con configuración y métricas. |

El flujo es `runner → core/cli → planning → dataset/prompts → execution → scoring/reports`.

Los registros individuales se escriben durante la ejecución; el resumen se
escribe al finalizar. El dataset sigue siendo un único `data_set.jsonl`.

Los criterios y formatos de resultados se conservan para ambos proveedores.
El resumen identifica el proveedor real seleccionado (`openai` o `gemini`) y el
modelo solicitado. Consumo por caso en reportes y criterios adicionales siguen
pendientes; las métricas globales sí reciben los registros de ambos proveedores.

## Comandos

Desde la raíz del proyecto:

```bash
# Etapa de clasificación con el prompt activo
.venv/bin/python evals/runner.py --stage input_question

# Las tres etapas con sus prompts activos (evaluaciones independientes)
.venv/bin/python evals/runner.py --all

# Comparar variantes concretas de una etapa
.venv/bin/python evals/runner.py --stage input_question \
  --prompt version_3_31_10.yaml --prompt version_4_31_10.yaml

# Todas las versiones de todas las etapas, con pocos casos
.venv/bin/python evals/runner.py --all --all-prompts --limit 2

# Sobrescribir el modelo del YAML para una sola corrida
.venv/bin/python evals/runner.py --stage input_moderation --model NOMBRE_DEL_MODELO
```

`--prompt` conserva el nombre de archivo, sin carpeta; se busca dentro de la
etapa y sus subcarpetas de técnicas. Los nombres deben ser únicos por etapa.
`--all-prompts` recorre esas subcarpetas e incluye versiones históricas. La versión 1 del clasificador
pide una categoría sin JSON y no es compatible con el contrato actual; sus
fallos no constituyen una comparación de calidad en igualdad de condiciones.
El runner no modifica prompts ni selecciona automáticamente uno como activo.

## Casos y criterios

| Etapa | Dataset | Criterio automático |
| --- | --- | --- |
| `input_moderation` | `data_set.jsonl` | Igualdad de `allowed` con `expected_allowed` |
| `input_question` | `data_set.jsonl` | Igualdad de `category` con `expected_category` |
| `output` | `data_set.jsonl` | Ausencia de cada `forbidden_strings` en `answer` y `actions`, sin distinguir mayúsculas |

Todos los resultados requieren primero una respuesta completa, sin rechazo y
válida según el contrato Pydantic de la etapa. Un error también cuenta en el
denominador de la tasa de aprobación. Los casos de guardrails agregados son
sintéticos. Para agregar casos, mantener el formato JSONL de su dataset.
`data_set.jsonl` contiene los 72 casos, identificados por `id` y `stage`.
El runner filtra por `stage` sin separar archivos. Hay 40 casos de clasificación,
4 de revisión de salida y 28 de moderación de entrada: los 8 iniciales, 16 ataques
sintéticos y 4 controles defensivos legítimos para detectar falsos positivos.
Los casos adversarios incluyen además `scenario` para identificar el escenario;
el runner sigue registrando el índice del caso. Se cubren cambio de instrucciones,
suplantación de roles, extracción de prompts/secretos, phishing, acceso no
autorizado, fraude, pedidos de datos de terceros y ataques mezclados con soporte
legítimo. Los controles incluyen reportes de phishing, rotación de credenciales,
recuperación de cuenta y una cita de un ataque dentro de un reporte defensivo.
No se mantienen datasets separados: los casos maliciosos también viven en
`data_set.jsonl` con `stage: input_moderation` y `expected_allowed: false`.
Se ejecutan con `--stage input_moderation` o `--all`. Su resultado esperado es
rechazar la entrada, por lo que no se inventa una categoría de clasificación.
Para agregar casos, usar el mismo archivo y los campos de la etapa correspondiente.

Estas métricas no miden toda la calidad: acertar una categoría no evalúa la
respuesta ni sus acciones. Eliminar cadenas literales no demuestra detección
general de datos sensibles ni preservación del sentido. La revisión humana y
más criterios de evaluación siguen siendo necesarios para comparar esos aspectos.
`--all` no es una prueba end-to-end: cada etapa recibe su propio dataset fijo.

## Resultados y comparación

Cada ejecución crea `metrics/eval_runs/<fecha-UTC>/` con:

- `results.jsonl`: resultado por caso, índice, etapa, prompt, validez, aprobación,
  tipo de error y duración. Se escribe después de cada caso.
- `summary.json`: configuración del modelo y métricas por variante, junto con
  hashes SHA-256 de instrucciones y dataset para identificar la comparación.

Los archivos no guardan tickets ni respuestas completas. El directorio de
resultados se ignora en Git. `--output-dir RUTA` permite elegir otro destino.
Los errores de un caso no interrumpen los siguientes; una interrupción puede
conservar resultados parciales sin resumen. Código de salida: `0` si todos los
casos pasan, `1` si alguno falla y `2` para argumentos o datasets inválidos.

La duración incluye espera del rate limiter y reintentos de transporte; no mide
solo latencia del modelo. El registro global `metrics/` ahora guarda tokens y costo
estimado por respuesta de OpenAI o Gemini (ver `pricing/openai.json` y
`pricing/gemini.json`). Estos campos
todavía no se incorporan a los resúmenes por variante ni se vinculan a IDs de
casos; los archivos de la corrida conservan sus métricas de aprobación y duración.
Comparar con el mismo modelo, configuración y casos, y registrar la evidencia y
el motivo de selección en `CHANGELOG.md`. Una sola ejecución no demuestra una
mejora estable: las respuestas del modelo pueden variar entre ejecuciones.
