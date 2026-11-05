# Evaluaciones de prompts con OpenAI

El runner prueba cada variante contra los mismos casos de su etapa, de forma
secuencial. Usa `OPENAI_MODEL` y la configuración del `.env`, el cliente existente,
sus reintentos de transporte y su límite de solicitudes. No utiliza Gemini ni
reintenta resultados JSON inválidos: estos se registran como fallos de la eval.
Solo se hacen llamadas al ejecutar el runner; consumen tokens de OpenAI.

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

# Sobrescribir el modelo configurado
.venv/bin/python evals/runner.py --stage input_moderation --model NOMBRE_DEL_MODELO
```

`--all-prompts` incluye versiones históricas. La versión 1 del clasificador
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
estimado por respuesta OpenAI (ver `pricing/openai.json`). Estos campos
todavía no se incorporan a los resúmenes por variante ni se vinculan a IDs de
casos; los archivos de la corrida conservan sus métricas de aprobación y duración.
Comparar con el mismo modelo, configuración y casos, y registrar la evidencia y
el motivo de selección en `CHANGELOG.md`. Una sola ejecución no demuestra una
mejora estable: las respuestas del modelo pueden variar entre ejecuciones.
