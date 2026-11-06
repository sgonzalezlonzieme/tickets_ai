# Cómo leer las métricas

Cada línea JSON representa una respuesta de API y su etapa se identifica por el
archivo: `input_moderation.jsonl` (entrada), `input_question.jsonl`
(clasificación) u `output_moderation.jsonl` (revisión de salida).
Ambos proveedores escriben en estos mismos archivos. Cada registro nuevo
comienza con `system_prompt`, que separa etapa y versión:

```json
{"system_prompt": {"stage": "input_moderation", "version": "version_1_01_11"}}
```

`stage` indica `input_moderation`, `input_question` u `output`; `version` es el
nombre completo del archivo sin `.yaml`. Si no se identifica un archivo único,
la versión queda null. Después se conservan `prompt_file` y `prompt_sha256`.

| Campo | Significado | Ejemplo |
| --- | --- | --- |
| `system_prompt` | Etapa (`stage`) y versión (`version`) del prompt, al principio del registro. | `{"stage": "input_moderation", "version": "version_1_01_11"}`. |
| `timestamp` | Fecha y hora UTC de registro; `+00:00` indica UTC. | `2026-11-06T12:10:57.211466+00:00` equivale a las 09:10:57 en Argentina ese día. |
| `provider` | Proveedor que atendió esta llamada. | `openai` o `gemini`. |
| `model` | Modelo informado por la API; Gemini usa el configurado si no lo informa. | `gemini-3.8-flash`. |
| `prompt_file` | Archivo cuyas instrucciones coinciden exactamente con las enviadas. | `prompts/input_question/zero_shot/version_4_31_10.yaml`. |
| `prompt_sha256` | Huella de las instrucciones efectivamente enviadas, no del ticket ni del YAML completo. Permite detectar cambios de contenido. | Cadena hexadecimal de 64 caracteres. |
| `prompt_tokens` | Tokens de entrada: unidades de texto/contexto procesadas, no palabras ni caracteres. | `507` tokens. |
| `completion_tokens` | Tokens generados, incluido razonamiento cuando corresponde. | `39` tokens. |
| `total_tokens` | Total informado por la API; no se reconstruye a partir de datos parciales. | `546` tokens. |
| `latency_s` | Duración de la llamada SDK en segundos, con tres decimales; incluye esperas del limitador y reintentos de transporte. | `3.578` segundos = `3578` milisegundos. |
| `cost_usd` | Costo estimado en dólares estadounidenses, escrito sin notación científica. No es la factura del proveedor. | `0.0000702` USD; equivale a `7.02e-05`, no a USD 7,02. |
| `readable` | Los mismos datos expresados con etiquetas en castellano y unidades para lectura humana. | `duracion: "3.578 segundos"`, `costo_estimado: "USD 0.0000702"`. |

Los campos originales siguen siendo números JSON para sumar costos y calcular
promedios. Se usa punto decimal, conforme al formato JSON. En `readable` los
valores se presentan como texto. `null` y «No disponible» significan que no hay
dato o tarifa válida, nunca que el consumo haya sido gratuito.

La identidad del prompt se calcula con las instrucciones reales de cada llamada,
incluidas variantes de evals y llamadas al respaldo. Si no coincide con un único
archivo de su etapa, `prompt_file` queda null, pero la huella se conserva. No se
guarda el texto de los prompts, tickets, respuestas ni credenciales. La huella
identifica contenido; para recuperar una versión modificada hace falta conservar
el archivo y su historial.

Los nuevos campos y el formato decimal se aplican a registros nuevos. Los
históricos no se reescriben ni reciben una versión de prompt supuesta. Una
respuesta bloqueada o cuyo texto luego falle la validación puede tener consumo;
ver los detalles de registro y tarifas en el README principal.
