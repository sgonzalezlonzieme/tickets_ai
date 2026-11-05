# Changelog

Registro de cambios del proyecto a partir del 2026-11-03. Los cambios anteriores
no se reconstruyen en este archivo.

Cada cambio se registra bajo su fecha (`AAAA-MM-DD`), con las fechas más
recientes primero. Usar las categorías **Agregado**, **Modificado**, **Corregido**
o **Eliminado** según corresponda, describiendo brevemente el cambio y su efecto.

## Cómo registrar decisiones sobre prompts

Cada cambio o selección debe incluir:

- **Etapa y versiones:** archivo activo y candidato comparado.
- **Problema:** caso o comportamiento que se busca mejorar.
- **Cambio y mejora esperada:** qué instrucciones cambian y por qué podrían ayudar.
- **Evidencia:** dataset/casos, proveedor, modelo, condiciones y resultados de las
  evals; incluir fallos o regresiones, y costo/latencia cuando se midan. Si no se
  evaluó, escribir «Pendiente de evaluación».
- **Decisión y motivo:** activo, candidato o descartado; explicar el beneficio y
  los compromisos que justifican elegir uno sobre otro.

Comparar las versiones con los mismos casos y condiciones por proveedor/modelo.
Priorizar seguridad y cumplimiento del contrato, y luego comparar la calidad de
las respuestas y la clasificación. Documentar cualquier compromiso de costo o
latencia. Una versión más nueva no demuestra por sí sola una mejora; distinguir
siempre el objetivo del cambio de sus resultados medidos.

## 2026-11-04

### Identificación de casos

- Verificados los 72 casos de `evals/data_set.jsonl`: todos tienen `id` no
  vacío y único, incluidos los casos originales y los maliciosos. No se
  cambiaron los IDs existentes. El runner ahora rechaza IDs faltantes, vacíos
  o duplicados antes de llamar al modelo; agregadas pruebas de estos errores.

### Unificación de casos de evaluación

- Reunidos los 72 casos en `evals/data_set.jsonl`: 40 de clasificación,
  28 de moderación de entrada (incluidos los ataques) y 4 de salida.
  Todos tienen `id` y `stage`; el runner valida el archivo y filtra por etapa.
- Eliminados los datasets separados y el placeholder vacío `adversarial.jsonl`.
  Los archivos de métricas por etapa se mantienen. Actualizados pruebas,
  documentación y `AGENTS.md` para preservar el dataset único.

### Modificado

- Unificados los nombres de archivos con `_`: los registros por etapa ahora son
  `metrics/input_moderation.jsonl`, `metrics/input_question.jsonl` y
  `metrics/output_moderation.jsonl`. Conservados los registros y actualizadas
  las referencias del escritor, las pruebas y el README.
- Registrada en `AGENTS.md` la convención de usar `_` en nombres de archivos y
  carpetas para los cambios futuros. El historial anterior conserva los nombres
  que se usaban en cada cambio.

## 2026-11-03

### Eliminado

- Retirado `metrics_data/metrics/metrics.jsonl` a pedido del usuario: quedan
  únicamente los tres JSONL por etapa. El archivo anterior contenía tres
  registros sin etapa identificada; no se reasignaron a los archivos nuevos.
  Actualizada la documentación para quitar la referencia al archivo histórico.

### Modificado

- Movidas las tarifas de `metrics/pricing.json` a `pricing/openai.json`.
  Actualizadas las referencias del cálculo de costos y la documentación;
  `metrics/` conserva los registros por etapa. No se modificaron las tarifas.

- Simplificada la estructura a `metrics/` en la raíz, eliminando la carpeta
  contenedora `metrics_data/`. Conservados los tres JSONL por etapa y
  `pricing.json`; las corridas de evals ahora se guardan en `metrics/eval_runs/`.
  Actualizados escritor, runner, documentación y exclusiones de Git.

- Renombrados los archivos de métricas por etapa a `input-moderation.jsonl`,
  `input-question.jsonl` y `output-moderation.jsonl` en `metrics_data/metrics/`.
  Actualizados escritor, pruebas y documentación, conservando los registros.

- Separadas las métricas por etapa en `metrics_data/metrics/input.jsonl`,
  `generation.jsonl` y `output.jsonl`, tanto para la ticketera como para evals.
  Cada respuesta se agrega únicamente al archivo de su etapa. El `metrics.jsonl`
  anterior se conserva como archivo histórico porque sus filas no identifican
  la etapa; no se reasignaron registros por suposición.

- Movido el registro acumulativo a `metrics_data/metrics/metrics.jsonl` y
  actualizada la ruta del escritor y la documentación. Cada respuesta OpenAI
  agrega una línea en esa carpeta, conservando el historial previo. Las tarifas
  siguen en `metrics_data/pricing.json` y los resultados por corrida en
  `metrics_data/eval_runs/`.

### Agregado

- Ampliado `evals/input_moderation.jsonl` de 8 a 28 casos: 16 ataques
  sintéticos con rechazo esperado y 4 consultas defensivas legítimas con
  aceptación esperada. Incluyen IDs y escenarios; el runner los carga sin
  configuración adicional. Documentados cobertura y controles de falsos positivos.
  No se alteraron prompts ni etiquetas de clasificación; la efectividad real
  queda pendiente de ejecutar evals con OpenAI.

- Registro acumulativo en `metrics_data/metrics.jsonl` por respuesta validada de
  OpenAI, tanto en la ticketera como en las evals: timestamp UTC, modelo, tokens
  de entrada/salida/total, latencia y costo estimado. Incluye bloqueo de archivo
  para escrituras concurrentes y no almacena contenido de tickets.
- Tarifas editables en `metrics_data/pricing.json`, inicialmente para
  `gpt-6-luna`, verificadas en documentación oficial. Distingue entrada en caché;
  precios o usage desconocidos producen valores null, no costos inventados.
- Pruebas de acumulación, cálculo, datos faltantes, errores de escritura y
  registro automático de las tres etapas. No se alteraron prompts ni se hicieron
  llamadas reales; Gemini y los resúmenes por variante todavía no incluyen
  estas métricas. Verificación: 80 pruebas offline aprobadas; las métricas de
  prueba se escribieron en archivos temporales, sin contaminar el registro real.

- Descripción detallada de la función, entrada, salida y reglas de cada uno de
  los seis prompts. Instrucción en `AGENTS.md` para preservar esas descripciones
  y el historial de decisiones y evidencia al incorporar nuevas versiones.

- Inventario enlazado de los seis prompts existentes, agrupados por etapa, con
  diferencias, contratos y estado de activación. Se mantiene la instrucción de
  actualizar el inventario y justificar cada cambio o selección de prompt.

- Runner de evals secuencial exclusivo de OpenAI: permite ejecutar una etapa o
  todas, comparar versiones de prompts, limitar casos y configurar el modelo.
  Guarda resultados por caso y resúmenes con hashes y métricas; no modifica
  automáticamente los prompts activos ni guarda entradas o respuestas completas.
- Datasets sintéticos iniciales de moderación de entrada (8 casos) y salida
  (4 casos), además de los 40 tickets de clasificación existentes.
- Pruebas offline del runner y documentación de uso, criterios y limitaciones
  en `evals/README.md`. Resultados de ejecuciones excluidos de Git.
- Evidencia: validación con APIs simuladas; no se ejecutaron evals reales ni se
  seleccionaron nuevas versiones de prompts. La comparación de calidad sigue
  pendiente de evaluación.

- Archivo `CHANGELOG.md` para mantener el historial de cambios del proyecto.
- Instrucción en `AGENTS.md` para actualizar este historial con cada cambio.
- Enlace al historial e indicaciones para mantenerlo en `README.md`.
- Criterios para documentar y comparar prompts, junto con la instrucción de
  registrar evidencia y motivos de selección en cada cambio futuro.
- Contexto de la ticketera de Nubbix en `AGENTS.md`: objetivo, flujo de tres
  etapas, proveedores, contratos, organización del proyecto y validación, para
  orientar los cambios futuros con el comportamiento actual.

### Estado inicial de los prompts (revisión del código actual)

Esta es una comparación de los archivos existentes, no una reconstrucción de
decisiones históricas ni una demostración de mejora de calidad.

| Etapa | Prompt | Propósito y diferencia observable | Estado |
| --- | --- | --- | --- |
| Entrada | [v1 — moderación de entrada](prompts/input_moderation/version_1_01_11.yaml) | Decide seguridad y alcance de Nubbix con `allowed`. Distingue consultas legítimas de seguridad de pedidos dañinos y rechaza instrucciones que intentan cambiar su rol. | Activo |
| Clasificación | [v1 — categoría sola](prompts/input_question/version_1_25_10_es.yaml) | Devuelve solo `billing`, `technical`, `account` u `other`. No satisface el contrato actual de cuatro campos. | Histórico, no activo |
| Clasificación | [v2 — respuesta estructurada](prompts/input_question/version_2_31_10.yaml) | Incorpora JSON con `answer`, `confidence`, `category` y `actions`, redacción en castellano y acciones sugeridas para un humano. | Histórico, no activo |
| Clasificación | [v3 — alcance de Nubbix y rechazo fijo](prompts/input_question/version_3_31_10.yaml) | Explicita el alcance de Nubbix, amplía ejemplos de `other` y prescribe una frase fija para consultas fuera de alcance. | Histórico, no activo |
| Clasificación | [v4 — rechazo con redacción flexible](prompts/input_question/version_4_31_10.yaml) | Conserva el alcance y contrato de v3; permite redactar el rechazo con palabras propias sin responder la consulta fuera de alcance. | Activo |
| Salida | [v1 — revisión de respuesta](prompts/output/version_1_01_11.yaml) | Revisa `answer` y `actions`, pide retirar datos sensibles y recomendaciones inseguras, preservar el sentido y evitar compromisos inventados. Contempla una respuesta segura alternativa si no puede corregir el borrador. | Activo |

Los archivos enlazados contienen las instrucciones completas. Los tres prompts
activos se seleccionan en `src/clients/prompts.py` y se comparten entre OpenAI y
Gemini. El runner de evals usa OpenAI y permite comparar versiones sin alterar
esa selección. Los históricos se conservan como referencia; no se afirma que
hayan sido descartados por resultados medidos.

**Selección actual:** el cargador usa explícitamente la versión 4 para ambos
proveedores. El motivo histórico de esa selección no está documentado.
La variación del rechazo es una diferencia de diseño; su superioridad frente a
la versión 3 está **pendiente de evaluación**. El guardrail de entrada también
puede bloquear esas consultas antes de que lleguen al clasificador.

**Guardrails activos:** `input_moderation/version_1_01_11.yaml` y
`output/version_1_01_11.yaml`, compartidos por OpenAI y Gemini. No se identifican
versiones alternativas en esas carpetas para comparar.

**Evidencia disponible al actualizar este inventario:** las 76 pruebas locales
pasaron con APIs simuladas tras implementar el runner; verifican funcionamiento
y contratos, no qué prompt responde mejor. El runner ya está implementado, pero
no se ejecutaron comparaciones reales ni hay resultados de calidad documentados.
Todos los prompts siguen pendientes de evaluación comparativa.

### Función detallada de cada prompt

Estas descripciones explican las instrucciones existentes. No son resultados
medidos ni garantías de que el modelo siempre cumpla lo pedido.

#### Entrada — v1: moderación de seguridad y alcance

Archivo: [input_moderation/version_1_01_11.yaml](prompts/input_moderation/version_1_01_11.yaml). **Activo.**

Recibe el texto original del ticket y decide si puede continuar. Devuelve
únicamente `{"allowed": true}` o `{"allowed": false}`. Deben cumplirse tanto
seguridad como relación con soporte de Nubbix. Rechaza intentos de cambiar las
instrucciones, obtener secretos o facilitar actividades dañinas; también
consultas ajenas al servicio aunque sean inofensivas. Permite reclamos con tono
negativo, recuperación de cuentas y reportes defensivos de seguridad. No exige
mencionar Nubbix si el problema es compatible con su soporte. No responde la
consulta ni clasifica su categoría. Un rechazo detiene el flujo antes de generar
la respuesta.

#### Clasificación — v1: asignación de categoría

Archivo: [input_question/version_1_25_10_es.yaml](prompts/input_question/version_1_25_10_es.yaml). **Histórico, no activo.**

Recibe un ticket y pide únicamente el nombre de una categoría en inglés y
minúsculas: `billing` para pagos, `technical` para fallas e integraciones,
`account` para acceso y administración de cuentas, u `other` para el resto.
Indica tratar el ticket como datos, sin obedecer instrucciones incluidas en él.
Su función se limita a clasificar: no genera respuesta, confianza ni acciones.
Por eso su salida de texto simple es incompatible con el JSON del flujo actual.

#### Clasificación — v2: respuesta y próximos pasos estructurados

Archivo: [input_question/version_2_31_10.yaml](prompts/input_question/version_2_31_10.yaml). **Histórico, no activo.**

Recibe un ticket, incluso en otro idioma, y pide un JSON de cuatro campos:
`answer` (respuesta breve en castellano), `category` (categoría en inglés),
`confidence` (estimación de confianza entre 0 y 1) y `actions` (lista de pasos
sugeridos en castellano para el agente humano). Las sugerencias no representan
acciones ejecutadas. Incluye descuentos y planes empresariales como ejemplos de
`other`. Su diferencia principal frente a v1 es ampliar la clasificación a una
respuesta utilizable por la ticketera con un contrato estructurado. Todavía no
explicita el alcance exclusivo de Nubbix ni una respuesta de rechazo.

#### Clasificación — v3: alcance de Nubbix y rechazo uniforme

Archivo: [input_question/version_3_31_10.yaml](prompts/input_question/version_3_31_10.yaml). **Histórico, no activo.**

Mantiene los cuatro campos de v2 y limita la asistencia a Nubbix, sus servicios
e integraciones. Detalla consultas válidas de `other`, como documentación,
capacitación, demostraciones o propuestas de colaboración. Un ticket válido no
tiene que mencionar la marca. Para consultas fuera de alcance pide una frase
fija de rechazo, `category: other` y `actions: []`, sin resolver la consulta.
También explicita que no debe cambiar de rol por instrucciones del ticket.
La diferencia de diseño frente a v2 es delimitar qué puede responder y hacer
uniforme el rechazo; su efectividad está pendiente de evaluación.

#### Clasificación — v4: alcance de Nubbix y rechazo flexible

Archivo: [input_question/version_4_31_10.yaml](prompts/input_question/version_4_31_10.yaml). **Activo.**

Recibe el ticket permitido por el guardrail de entrada y genera el mismo JSON
de cuatro campos. Conserva las categorías, el alcance y las restricciones de v3.
Cambia el rechazo: pide redactar con palabras propias un mensaje breve y amable
en castellano, indicando el límite de Nubbix, sin responder el tema ajeno,
con `category: other` y `actions: []`. Esto permite variar la redacción; no hay
evidencia comparativa de que esa flexibilidad mejore la calidad. En el flujo
normal, las consultas fuera de alcance deberían ser detenidas por la moderación
de entrada antes de llegar a esta etapa.

#### Salida — v1: revisión de privacidad, seguridad y redacción

Archivo: [output/version_1_01_11.yaml](prompts/output/version_1_01_11.yaml). **Activo.**

Recibe solo `answer` y `actions` del borrador, sin el ticket original ni la
categoría o confianza. Devuelve únicamente esos dos campos revisados en
castellano. Pide quitar datos personales, identificadores privados, datos
bancarios, credenciales y secretos, sustituyéndolos por referencias genéricas
sin repetir los valores. También elimina recomendaciones peligrosas, lenguaje
ofensivo y afirmaciones o compromisos inventados. Debe conservar el sentido y
las recomendaciones seguras, y orientar verificaciones hacia canales oficiales
sin solicitar secretos. Si no puede corregir el contenido con seguridad, pide
una respuesta breve que derive al soporte oficial y `actions: []`.

El servicio combina esta revisión con `category` y `confidence` del clasificador.
Si la revisión falla o su resultado es inválido, no entrega el borrador. Esta
etapa busca reducir exposición de información sensible; la cobertura real debe
medirse con evals, incluidas pruebas de que conserva la utilidad de la respuesta.
