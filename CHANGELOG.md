# Changelog

Registro de cambios del proyecto a partir del 2026-11-03. Los cambios anteriores
no se reconstruyen en este archivo.

Cada cambio se registra bajo su fecha (`AAAA-MM-DD`), con las fechas más
recientes primero. Usar las categorías **Agregado**, **Modificado**, **Corregido**
o **Eliminado** según corresponda, describiendo brevemente el cambio y su efecto.

Los estados «activo», «candidato» e «histórico» de cada entrada corresponden
al momento del cambio. La selección vigente se consulta en
[`prompts/active_prompts.yaml`](prompts/active_prompts.yaml).

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

Para identificar una corrida de evals, registrar también su `run_id` de
`summary.json` y la ruta de resultados en `metrics/eval_runs/`. Esos archivos
están excluidos de Git; no copiar tickets, respuestas ni credenciales al historial.

Comparar las versiones con los mismos casos y condiciones por proveedor/modelo.
Priorizar seguridad y cumplimiento del contrato, y luego comparar la calidad de
las respuestas y la clasificación. Documentar cualquier compromiso de costo o
latencia. Una versión más nueva no demuestra por sí sola una mejora; distinguir
siempre el objetivo del cambio de sus resultados medidos.

## 2026-11-07

### Modificado — trazabilidad de evaluaciones

- Aclarado cómo referenciar una corrida mediante `run_id` y su carpeta de
  resultados al documentar decisiones, sin copiar contenido sensible al
  changelog. Cambio documental, sin modificar código ni ejecutar evals.

### Agregado

- Agregada guía de ejecución de evals en el README principal y `AGENTS.md`:
  proveedor/modelo, credenciales, comandos por etapa o todas, comparación de
  variantes, significado de `--limit`, cantidad de casos y carpeta de resultados.
  Aclarados consumo real, ausencia de fallback e históricos incompatibles;
  retirada del README la referencia obsoleta a un dataset adversario separado.
  Cambio documental; no se ejecutaron evals reales ni se modificó código.

- Configuración independiente de evals en [`evals/config.yaml`](evals/config.yaml):
  proveedor (`open_ai` o `gemini`), modelo, límite de salida y temperatura de
  OpenAI. Se conserva OpenAI/gpt-6-luna como selección inicial; no depende de
  `LLM_PROVIDER` ni del modelo del CLI. `--config` permite otro YAML y `--model`
  sobrescribe solo el modelo de la corrida, sin modificar archivos.
- `evals/core/config.py` valida ajustes antes de inicializar clientes;
  `providers.py` crea exclusivamente el proveedor elegido con sus contratos.
  Gemini incorpora `generate_structured` para evaluar instrucciones explícitas
  de las tres etapas y registrar sus métricas, igual que OpenAI.
- El runner mantiene ejecución secuencial, criterios y dataset único. No aplica
  fallback ni reintentos de parsing: los fallos quedan atribuidos al proveedor
  elegido. Los SDK conservan sus reintentos de transporte y limitadores.
  El resumen registra proveedor/modelo solicitados y ajustes efectivos;
  Gemini no informa temperatura o esfuerzo de razonamiento que no se envían.
- Documentación e instrucciones actualizadas. Las pruebas con SDKs simulados
  cubren ambas rutas, las tres etapas de Gemini, configuración inválida,
  precedencia de modelo, cierre del cliente y ausencia de fallback. No se cambian
  prompts, selección activa ni dataset, ni se realizan llamadas reales o evals
  de calidad/seguridad. Las comparaciones de prompts siguen pendientes por
  proveedor/modelo bajo las mismas condiciones; no se afirma ninguna mejora.
  Validación: 104 pruebas offline aprobadas y ayuda del comando verificada.

## 2026-11-06

### Modificado — lectura del estado histórico de prompts

- Aclarado que los estados de las entradas corresponden al momento del cambio
  y enlazada la selección vigente para evitar confundir versiones históricas
  con prompts actualmente activos. Cambio documental, sin modificar prompts.

### Modificado — aclaración de límites en configuración

- Aclarado en la tabla del README que `.env.example` usa 30 RPM para ambos
  proveedores, mientras que el valor por defecto si falta la variable sigue
  siendo 10 RPM. Cambio exclusivamente documental, sin llamadas a las APIs.

### Modificado — límite local de 30 solicitudes por minuto

- Configurados `OPENAI_REQUESTS_PER_MINUTE=30` y
  `GEMINI_REQUESTS_PER_MINUTE=30` en `.env` local y `.env.example`, por pedido
  del usuario. Se conservan los defaults de 10 RPM si faltan las variables;
  las cuotas de cada proveedor siguen aplicando. Verificada la lectura de ambos
  archivos, sin llamadas reales.

### Modificado — módulos internos de evals en core

- Agrupados los módulos auxiliares de evaluación en `evals/core/` y movidos
  argumentos y coordinación a `core/cli.py`. `evals/runner.py` queda como entrada
  mínima de 12 líneas, conservando el comando existente y ejecución desde otras
  carpetas. Ajustadas importaciones y resolución de la raíz del proyecto.
- Sin cambios de dataset, criterios, proveedor, prompts, formatos de reporte ni
  comportamiento del runner. Adaptadas pruebas y documentación a la estructura
  nueva, conservando el historial de la separación anterior. Validación:
  99 pruebas offline aprobadas, sin llamadas reales.

### Modificado — separación del runner de evaluaciones

- Reducido `evals/runner.py` a argumentos y coordinación. Separadas las
  responsabilidades en `stages.py` (rutas y contratos), `dataset.py` (validación
  del dataset único), `planning.py` (selección y validación previa), `scoring.py`
  (criterios), `execution.py` (llamadas, resultados por caso y cierre del cliente)
  y `reports.py` (carpeta y resumen). Configuraciones y planes tienen campos
  nombrados para evitar interpretar posiciones de tuplas.
- Se conservan comandos, opciones, secuencia, criterios de aprobación, formato
  de archivos, aislamiento de errores y uso exclusivo de OpenAI. No se renombra
  ni divide `evals/data_set.jsonl`, no se activan prompts nuevos ni se hacen evals.
- Adaptadas las pruebas a los módulos responsables, conservando cobertura de
  contratos, scoring, IDs, privacidad, defaults compartidos y errores. Agregada
  verificación del comando `--help` ejecutado desde otra carpeta, sin llamadas
  reales. Documentadas responsabilidades y flujo en README e instrucciones.
- Validación: 99 pruebas offline aprobadas. Las pruebas con proveedores simulados
  no aportan evidencia de calidad o seguridad de los modelos.

### Modificado — selección de prompts junto a sus archivos

- Movida la selección de versiones desde el diccionario Python a
  [`prompts/active_prompts.yaml`](prompts/active_prompts.yaml). La función
  `get_active_prompts()` valida tres etapas exactas y nombres YAML sin carpetas;
  la carga es diferida y se conserva en caché por proceso.
- CLI de ambos proveedores y defaults del runner leen la misma configuración,
  sin repetir nombres de versiones en Python. Cambiar el YAML requiere reiniciar
  el proceso; las variantes explícitas de evals siguen disponibles sin activarlas.
- Sin nueva selección ni cambios de instrucciones: entrada v4 few-shot breve,
  clasificación v7 few-shot breve y salida v1 zero-shot continúan activas para
  la prueba manual ya autorizada. Conservados candidatos e historial. No se
  incorpora evidencia nueva de calidad, seguridad, costo o latencia con modelos.
- Actualizados README, guía de prompts, evals e instrucciones de proyecto;
  agregadas pruebas de configuración inválida, carga y cambio de selección.
  Validación: 98 pruebas offline aprobadas, sin llamadas reales.

### Modificado — activación manual de entrada v4 y clasificación v7

| Etapa | Base reemplazada | Selección activa | Decisión y motivo |
| --- | --- | --- | --- |
| Entrada | [v1 few-shot](prompts/input_moderation/few_shots/version_1_01_11.yaml) | [v4 few-shot breve](prompts/input_moderation/few_shots/version_4_06_11.yaml) | Activo para prueba manual autorizada: reglas condensadas y dos ejemplos inocentes para comparar una alternativa compacta. |
| Clasificación | [v4 zero-shot](prompts/input_question/zero_shot/version_4_31_10.yaml) | [v7 few-shot breve](prompts/input_question/few_shots/version_7_06_11.yaml) | Activo para prueba manual autorizada: contrato/categorías resumidos y dos ejemplos; ahorro y calidad pendientes de evaluación. |
| Salida | Sin reemplazo | [v1 zero-shot](prompts/output/zero_shot/version_1_01_11.yaml) | Sigue activo por el detalle de sus reglas de privacidad y revisión. |

- Problema: probar la combinación recomendada con el flujo real del usuario.
  La función y contratos de las tres etapas se mantienen; no se cambian archivos
  de prompts en esta selección. Las bases reemplazadas quedan históricas y las
  restantes variantes conservan estado candidato y sus descripciones anteriores.
- Centralizada la selección en `ACTIVE_PROMPTS` de `src/clients/prompts.py` y
  compartida por OpenAI, Gemini y los defaults del runner, evitando duplicarla.
  Actualizados documentación, inventario e instrucciones de proyecto.
- Evidencia: pendiente de comparación con modelos bajo los mismos casos de
  `evals/data_set.jsonl`, proveedor/modelo y configuración. Esta activación por
  pedido del usuario no demuestra mejora de calidad, seguridad, tokens, costo
  o latencia. No se realizaron llamadas reales durante la implementación.
  Validación: 96 pruebas offline aprobadas, incluida selección compartida de
  prompts entre CLI y runner.

### Modificado — ejemplos inocentes en todos los prompts

- Revisados los 24 archivos de prompts. Por preferencia del usuario, reemplazados
  ejemplos de daño, intrusión, extracción de secretos y pedidos de autenticación
  por cuentos, cocina, cultura general o soporte habitual. En revisión de salida
  se usan correcciones de tono, orientación y afirmaciones no confirmadas;
  permanecen ejemplos inocuos de privacidad con datos ficticios.
- La entrada activa v1 y sus candidatos derivados reemplazan el ejemplo
  veterinario por una historia de piratas ajena al servicio. Se conserva la
  selección de entrada v1, clasificación v4 y salida v1, así como sus reglas de
  seguridad, alcance y contratos. El contenido de entrada v1 cambia y tendrá
  un hash de instrucciones diferente en métricas nuevas.
- Problema: las ilustraciones de rechazo eran más intensas de lo requerido para
  mostrar alcance. Diferencia esperada: ejemplos sencillos y legibles; no implica
  mejora demostrada en seguridad o calidad. Se conservan las descripciones
  anteriores como historia de los ejemplos reemplazados, sin borrar resultados.
- Actualizados inventario y longitudes en `prompts/README.md`, preferencia en
  `AGENTS.md` y README. No se cambia `evals/data_set.jsonl`: ejemplos didácticos
  y cobertura de evals son usos distintos.

**Archivos y decisión:** los siguientes archivos actualizan ejemplos en la misma
versión por pedido explícito del usuario. Entrada v1 sigue activa; los demás
siguen candidatos, sin nueva selección. Comparar las versiones activas con los
candidatos de su etapa bajo los mismos casos, proveedor/modelo y condiciones.
La evaluación comparativa con modelos sigue pendiente; no se midieron cambios
de calidad, seguridad, tokens, costo o latencia ni se realizaron llamadas reales.
Validación: 24 YAML revisados, 63 salidas ilustrativas válidas y 95 pruebas
offline aprobadas.

- [prompts/output/chain_of_thought/version_7_06_11.yaml](prompts/output/chain_of_thought/version_7_06_11.yaml).
- [prompts/output/chain_of_thought/version_3_06_11.yaml](prompts/output/chain_of_thought/version_3_06_11.yaml).
- [prompts/output/chain_of_thought/version_6_06_11.yaml](prompts/output/chain_of_thought/version_6_06_11.yaml).
- [prompts/output/few_shots/version_5_06_11.yaml](prompts/output/few_shots/version_5_06_11.yaml).
- [prompts/output/few_shots/version_2_06_11.yaml](prompts/output/few_shots/version_2_06_11.yaml).
- [prompts/input_moderation/chain_of_thought/version_7_06_11.yaml](prompts/input_moderation/chain_of_thought/version_7_06_11.yaml).
- [prompts/input_moderation/chain_of_thought/version_3_06_11.yaml](prompts/input_moderation/chain_of_thought/version_3_06_11.yaml).
- [prompts/input_moderation/chain_of_thought/version_6_06_11.yaml](prompts/input_moderation/chain_of_thought/version_6_06_11.yaml).
- [prompts/input_moderation/few_shots/version_5_06_11.yaml](prompts/input_moderation/few_shots/version_5_06_11.yaml).
- [prompts/input_moderation/few_shots/version_1_01_11.yaml](prompts/input_moderation/few_shots/version_1_01_11.yaml).
- [prompts/input_moderation/few_shots/version_2_06_11.yaml](prompts/input_moderation/few_shots/version_2_06_11.yaml).
- [prompts/input_moderation/few_shots/version_4_06_11.yaml](prompts/input_moderation/few_shots/version_4_06_11.yaml).

### Agregado — variantes separadas y revisión de longitud de prompts

- Revisados los 24 prompts existentes y nuevos en `prompts/README.md`, con
  inventario completo, estado, caracteres y palabras. Conservados los activos e
  históricos y los candidatos anteriores, incluida su historia de modificaciones.
- Agregados doce archivos: variantes breve (dos ejemplos) y extendida (cuatro
  ejemplos y criterios de frontera), por técnica y etapa. Ejemplos distintos
  entre archivos; nombres solo con versión y fecha, técnica por carpeta.

| Etapa y comparación | Few-shot breve / extendida | Análisis guiado breve / extendido | Diferencias y problema abordado |
| --- | --- | --- | --- |
| Entrada: activa v1 y previos v2/v3 | [v4](prompts/input_moderation/few_shots/version_4_06_11.yaml) / [v5](prompts/input_moderation/few_shots/version_5_06_11.yaml) | [v6](prompts/input_moderation/chain_of_thought/version_6_06_11.yaml) / [v7](prompts/input_moderation/chain_of_thought/version_7_06_11.yaml) | Núcleo de seguridad y alcance condensado; ejemplos distintos de soporte, salud ajena, documentación, empleo, extracción de secretos, fraude, reportes defensivos y cambio de instrucciones. Extendidas aclaran finalidad y pedidos mixtos. |
| Clasificación: activa v4 y previos v5/v6 | [v7](prompts/input_question/few_shots/version_7_06_11.yaml) / [v8](prompts/input_question/few_shots/version_8_06_11.yaml) | [v9](prompts/input_question/chain_of_thought/version_9_06_11.yaml) / [v10](prompts/input_question/chain_of_thought/version_10_06_11.yaml) | Unifica categorías, contrato e idioma sin repetir la regla de rechazo; ejemplos distintos de reintegros, horarios, acceso, fallas, facturas, guías, permisos, planes y temas ajenos. Extendidas aclaran necesidad principal y confianza incierta. |
| Salida: activa v1 y previos v2/v3 | [v4](prompts/output/few_shots/version_4_06_11.yaml) / [v5](prompts/output/few_shots/version_5_06_11.yaml) | [v6](prompts/output/chain_of_thought/version_6_06_11.yaml) / [v7](prompts/output/chain_of_thought/version_7_06_11.yaml) | Agrupa privacidad, seguridad y contrato; ejemplos distintos de contacto, identidad, descuentos inventados, secretos, datos personales y plazos no confirmados. Extendidas verifican ambos campos y evitan promesas nuevas. |

**Función, entrada, salida y reglas:** se mantienen los contratos y la finalidad
de cada etapa descritos en el inventario previo: ticket a `allowed`, ticket a
los cuatro campos de clasificación, borrador a `answer`/`actions` revisados.
No se mandan category/confidence a revisión ni se pide razonamiento visible.
Las variantes guiadas incluyen ejemplos: son híbridas, no una prueba aislada de
Chain-of-thought. Las breves reducen repetición; las extendidas agregan criterios
y cobertura esperada, sin que el número de versión implique superioridad.

**Evidencia:** pendiente de evaluación con modelos. La reducción de caracteres
respecto del candidato previo de la misma técnica se mide localmente en la guía;
no equivale a tokens ni a ahorro demostrado, y algunos candidatos superan la
longitud del activo. No se midieron calidad, seguridad, costo ni latencia.

**Decisión y motivo:** los doce nuevos quedan candidatos para comparar; los tres
activos siguen iguales. No se elimina historia para aparentar optimización.
Comparar las mismas entradas de `evals/data_set.jsonl` y condiciones por
proveedor/modelo, revisar contratos, calidad y seguridad, y medir costo/latencia
si corresponde. El runner sigue siendo exclusivo de OpenAI. Sin llamadas reales.
Validación local: 24 prompts cargan, 63 salidas de ejemplo válidas y 95 pruebas
offline aprobadas; verificados los tres activos sin cambios.

### Modificado — ampliación de ejemplos en candidatos y nombres de archivo

- Agregados dos pares de entrada/salida a cada uno de los seis candidatos,
  manteniendo las reglas completas, entradas y contratos de salida de su etapa.
  No se modifican los tres activos ni el dataset unificado de evals.
- Quitados los sufijos `_few_shot` y `_analisis_interno` de seis nombres; la
  técnica se identifica por la carpeta. Actualizadas referencias e inventario.
  Las descripciones previas se conservan como historia del contenido inicial.

| Etapa y versiones comparables | Candidato few-shot actualizado | Candidato guiado actualizado |
| --- | --- | --- |
| Entrada: activa v1 frente a v2/v3 | [v2](prompts/input_moderation/few_shots/version_2_06_11.yaml): integración con duplicados permitida y acceso sin permiso rechazado. | [v3](prompts/input_moderation/chain_of_thought/version_3_06_11.yaml): rotación defensiva permitida y receta ajena al alcance rechazada. |
| Clasificación: activa v4 frente a v5/v6 | [v5](prompts/input_question/few_shots/version_5_06_11.yaml): consulta de factura (`billing`) y cambio de permisos (`account`). | [v6](prompts/input_question/chain_of_thought/version_6_06_11.yaml): error de integración (`technical`) y solicitud de demostración (`other`). |
| Salida: activa v1 frente a v2/v3 | [v2](prompts/output/few_shots/version_2_06_11.yaml): retiro de token ficticio y preservación de respuesta segura sin acciones. | [v3](prompts/output/chain_of_thought/version_3_06_11.yaml): retiro de identificador de pago ficticio y alternativa segura ante pedido de revelar instrucciones. |

**Problema y diferencia:** ampliar las situaciones ilustrativas para entender
cada técnica. Los candidatos guiados conservan sus criterios de análisis interno
y ahora todos incluyen ejemplos: son combinaciones de análisis guiado y few-shot,
no una comparación aislada entre técnicas. Sus salidas no exponen razonamiento.
Los valores de confianza son ilustrativos y los datos sensibles de ejemplo son
ficticios, sin credenciales reales.

**Evidencia:** pendiente de evaluación comparativa con modelos; validación local
de YAML y contratos de ejemplos. No hay mediciones nuevas de calidad, seguridad,
costo o latencia ni mejoras demostradas. La diferencia buscada es ilustrar
cobertura; no se afirma que mejore el comportamiento.

**Decisión:** los seis siguen candidatos, sin activar ni descartar. Comparar con
la base activa usando los mismos casos de `evals/data_set.jsonl`, proveedor,
modelo y condiciones; el runner actual solo evalúa OpenAI. No se sustituyen
resultados anteriores ni se ejecutan llamadas reales. Validación: 27 salidas
de ejemplo cumplen el contrato y 95 pruebas offline aprobadas.

### Modificado — nombre de etapa en identidad del prompt

- Renombrado `system_prompt.role` a `system_prompt.stage` para distinguir la
  etapa del procesamiento de los roles de mensajes. Adaptadas documentación y
  pruebas; se conservan versión, archivo y hash. Históricos intactos.
  Validación: 95 pruebas offline aprobadas.

### Modificado — rol y versión del system prompt en métricas

- Cada registro nuevo comienza con `system_prompt`, con `role` para la etapa
  (`input_moderation`, `input_question` u `output`) y `version` para el nombre
  del archivo sin extensión. Si no se identifica un archivo único, versión null.
  Se conservan la ruta y el hash del contenido real enviado, y el bloque legible
  muestra etapa y versión. Documentación y pruebas actualizadas para ambos
  proveedores; no se reescriben históricos ni se cambian prompts activos.
  Validación: 95 pruebas offline aprobadas, sin llamadas reales.

### Modificado — system prompt al principio de la métrica

- Los registros nuevos de ambos proveedores comienzan con `prompt_file` y
  `prompt_sha256`, antes del timestamp y los datos de consumo. Actualizada la
  guía de métricas y la prueba de orden de campos. Históricos intactos.
  Validación: 95 pruebas offline aprobadas.

### Modificado — métricas legibles e identidad del system prompt

- Ambos proveedores guardan costos numéricos en dólares con notación decimal
  sin exponentes y latencias numéricas con tres decimales en segundos. Agregado
  bloque `readable` con etiquetas en castellano, unidades y datos ausentes
  explícitos, conservando los campos numéricos para análisis.
- Cada llamada registra `prompt_file` y `prompt_sha256` de las instrucciones
  enviadas; soporta prompts activos y candidatos de evals sin registrar texto.
  Si no coincide con un único archivo de la etapa, la ruta queda null y se
  conserva el hash real. No se inventa procedencia para los registros históricos.
- Agregada guía `metrics/README.md` para interpretar todos los campos, tokens,
  UTC, segundos y USD. Actualizado README; pruebas de formato, unidades, datos
  ausentes e identidad de prompts de ambos proveedores. Sin cambios de prompts
  activos ni llamadas reales. Los JSONL previos se conservan intactos.
  Validación: 95 pruebas offline aprobadas.

### Modificado — tarifas verificadas de Gemini

- Configuradas tarifas Standard pagas de `gemini-3.8-flash` en
  `pricing/gemini.json`: USD 0,75 entrada, 0,075 entrada en caché y 3,75 salida
  por millón de tokens, incluido razonamiento. Fuente oficial de Google enlazada
  en la tabla y README; verificación 2026-11-06, vigencia hasta 2026-12-31.
- Agregada validación opcional de `valid_until`: tarifas vencidas producen costo
  null con diagnóstico sin contenido sensible. Los registros previos conservan
  sus costos originales; las nuevas respuestas calculan estimación de lista
  Standard paga, sin inferir descuentos o gratuidad de la cuenta.
- Pruebas del ejemplo de 475 tokens de entrada y 71 de salida (USD 0,0006225
  sin caché), tarifas vencidas y continuidad del resto de métricas. Sin llamadas
  reales; no se modifican prompts ni se evalúa calidad del modelo.
  Validación: 92 pruebas offline aprobadas.

### Agregado — métricas persistentes de Gemini

- Gemini ahora agrega registros a los mismos tres JSONL por etapa que OpenAI,
  con `provider=gemini`, modelo devuelto (o configurado si falta), tokens y
  latencia del SDK incluidos reintentos y esperas del limitador. Conservados
  los registros previos; no se guardan tickets, respuestas ni credenciales.
- Tokens de salida incluyen candidatos y razonamiento; total conserva el dato
  del proveedor y datos ausentes permanecen null. El registro se hace tras validar
  el envoltorio de API, antes de validar el contrato del texto generado.
- Agregada `pricing/gemini.json` sin tarifas inventadas: costo null hasta cargar
  valores verificados por modelo exacto. El cálculo admite entrada en caché y
  salida con razonamiento; no representa cargos adicionales o tarifas por tramos.
- Reutilizado el escritor con bloqueo de archivos; fallos de persistencia no
  descartan la respuesta. Pruebas offline de etapas, convivencia de proveedores,
  tokens de razonamiento, costos sintéticos, datos ausentes y fallos de escritura
  y transporte. Validación: 91 pruebas offline aprobadas. Documentación
  actualizada; sin llamadas reales ni evals de calidad.

### Modificado — modelo explícito de Gemini

- Configurado `GEMINI_MODEL=gemini-3.8-flash` en `.env` local y `.env.example`;
  actualizada la tabla del README. El cliente ya lee este valor desde
  `get_gemini_settings()` y lo envía a `models.generate_content`. Se conserva
  `gemini-flash-latest` como valor por defecto si la variable falta o está vacía.
  Verificada la lectura local de configuración; sin llamadas reales ni evals.

### Modificado — organización de prompts por técnica

- Movidos los doce prompts a `zero_shot/`, `few_shots/` o `chain_of_thought/`
  dentro de cada etapa, conservando sus nombres originales. Actualizadas las
  referencias e inventarios; la carga y `--all-prompts` buscan recursivamente.
- Entrada activa v1 y clasificación histórica v3 se ubican en `few_shots/`
  porque contienen ejemplos. Las variantes guiadas se ubican en
  `chain_of_thought/` por su enfoque distintivo; entrada conserva sus ejemplos.
- No se modifican instrucciones, contratos ni versiones activas. Los candidatos
  siguen pendientes de evaluación, con sus descripciones y motivos conservados.
  No hay una selección nueva ni evidencia adicional de calidad, seguridad,
  costo o latencia; la reorganización solo facilita inspeccionar las técnicas.
- Validación: 87 pruebas offline aprobadas, incluida detección recursiva de
  candidatos por el runner. Sin llamadas reales ni cambios en métricas de uso.

### Modificado — cierre de prueba manual de respaldo

- El usuario confirmó que el ticket usó OpenAI tras configurar una clave inválida
  de Gemini. Restaurada la clave original de Gemini y eliminado el respaldo
  temporal; Gemini permanece como principal. Confirmación manual del usuario,
  sin inspección adicional de logs ni evaluación de calidad del modelo.

### Modificado — prueba manual temporal de respaldo

- Sustituida temporalmente la clave local de Gemini por un valor inválido para
  probar el fallback a OpenAI con un ticket enviado por el usuario. La clave
  original se conserva en un respaldo local privado dentro de `.runtime/`,
  excluido de Git. No se realizaron llamadas a las APIs en esta preparación;
  queda pendiente restaurar la clave tras la prueba.

### Modificado — decisión de conservar los prompts activos

- **Etapas y versiones:** entrada v1 frente a candidatos v2 few-shot y v3 de
  análisis interno; clasificación v4 frente a v5 few-shot y v6 de análisis
  interno; salida v1 frente a v2 few-shot y v3 de análisis interno. Los archivos
  enlazados y sus descripciones se conservan en el registro de candidatos de esta
  misma fecha y en el inventario histórico.
- **Problema y decisión:** se necesita explicitar por qué no se activan aún las
  nuevas variantes. Por decisión del usuario se mantienen los tres activos como
  base principalmente zero-shot: instrucciones directas y contratos, fáciles de
  mantener y revisar, sin sumar ejemplos ni análisis guiado cuyo beneficio no se
  demostró. Entrada ya contiene dos ejemplos de alcance y no es zero-shot puro.
- **Cambio introducido:** documentada la selección y sus motivos en `README.md`
  y `AGENTS.md`. No se modifican prompts, contratos, configuración activa ni
  comportamiento. Los seis candidatos siguen disponibles y no se descartan.
- **Evidencia y límites:** pendiente de evaluación comparativa con modelos.
  Las validaciones locales anteriores de YAML y ejemplos no prueban calidad ni
  seguridad. No se midieron diferencias de costo o latencia; evitar contexto
  adicional es un criterio de simplicidad, no un ahorro demostrado. Mantener la
  base actual tampoco demuestra que sea superior a los candidatos.

### Agregado — candidatos de prompts por técnica

Se agregan seis candidatos a pedido del usuario para inspeccionar few-shot y
análisis interno guiado. **Ninguno se activa**: la selección en
`src/clients/prompts.py` y los prompts activos permanecen sin cambios.
Cada candidato deriva de la versión activa de su etapa y conserva sus reglas
completas. La numeración identifica variantes; no demuestra superioridad.

| Etapa | Archivo y estado | Base comparada y diferencia | Problema y mejora esperada |
| --- | --- | --- | --- |
| Entrada | [v2 few-shot](prompts/input_moderation/few_shots/version_2_06_11.yaml) — candidato | v1 activa; agrega seis pares de consulta y `allowed`, además de los dos ejemplos existentes. | Ilustrar alcance, soporte legítimo, reportes defensivos, ataques e instrucciones maliciosas para reducir ambigüedad. |
| Entrada | [v3 análisis interno](prompts/input_moderation/chain_of_thought/version_3_06_11.yaml) — candidato | v1 activa; agrega cinco criterios internos y conserva sus dos ejemplos breves. No es una variante zero-shot pura. | Separar seguridad y alcance, distinguir citas defensivas y comprobar la decisión conjunta y el contrato. |
| Clasificación | [v5 few-shot](prompts/input_question/few_shots/version_5_06_11.yaml) — candidato | v4 activa; agrega cinco pares de ticket y JSON: las cuatro categorías y una consulta fuera de alcance. | Mostrar respuestas, sugerencias y formato; advierte no copiar hechos ni valores de confianza. |
| Clasificación | [v6 análisis interno](prompts/input_question/chain_of_thought/version_6_06_11.yaml) — candidato | v4 activa; agrega seis criterios internos sin ejemplos nuevos. | Guiar alcance, categoría principal, ambigüedad, redacción y contrato sin exponer razonamiento. |
| Salida | [v2 few-shot](prompts/output/few_shots/version_2_06_11.yaml) — candidato | v1 activa; agrega cuatro pares de borrador y revisión. | Ilustrar eliminación de datos ficticios, retiro de pedidos de secretos, corrección de reintegros no confirmados y conservación de contenido adecuado. |
| Salida | [v3 análisis interno](prompts/output/chain_of_thought/version_3_06_11.yaml) — candidato | v1 activa; agrega seis criterios internos sin ejemplos nuevos. | Revisar privacidad, seguridad, afirmaciones, sugerencias y formato sin suponer acceso al ticket original. |

**Función, entrada, salida y reglas conservadas:** entrada recibe el ticket como
datos no confiables y produce solo `allowed` booleano tras comprobar seguridad y
alcance de Nubbix. Clasificación recibe el ticket y produce `answer`, `category`,
`confidence` y `actions`, con categorías en inglés, texto en castellano y acciones
para un agente humano; las consultas ajenas reciben `other` y acciones vacías.
Salida recibe únicamente `answer` y `actions` del borrador y devuelve esos mismos
campos revisados, sin datos sensibles ni compromisos inventados; categoría y
confianza se preservan fuera de esta etapa. Todos exigen solo JSON, sin campos
adicionales. Las variantes guiadas solicitan revisar criterios internamente, no
publicar pasos ni explicaciones; esto no demuestra cómo razona el modelo.

**Evidencia:** pendiente de evaluación con modelos. Se verifican localmente YAML,
selección activa y contratos de los ejemplos; no se realizaron llamadas reales,
ni se midieron calidad, seguridad, costo o latencia. Las mejoras anteriores son
objetivos, no resultados demostrados. Los ejemplos son ilustraciones redactadas,
no respuestas observadas de un proveedor.

**Comparación pendiente:** usar los mismos casos de `evals/data_set.jsonl` de cada
etapa y comparar la base activa con sus dos candidatos bajo idéntico proveedor,
modelo, configuración y criterios. Revisar calidad y seguridad además del contrato,
y registrar costo/latencia cuando se midan. El runner existente usa solo OpenAI,
aunque el CLI esté configurado en Gemini; no permite concluir resultados de Gemini.

**Decisión y motivo:** los seis quedan como candidatos para revisión y evaluación;
no hay evidencia para reemplazar los activos. Se conserva toda la descripción e
historia de versiones anteriores y no se cambia el dataset ni el flujo de ejecución.

### Modificado

- Los errores de credenciales ahora habilitan el respaldo por etapa en ambos
  sentidos: clave ausente, HTTP 401/403 y HTTP 400 de Gemini con razón
  `API_KEY_INVALID` o `API_KEY_EXPIRED`. Otros errores de configuración siguen
  deteniendo el flujo. Errores normalizados sin cuerpos ni credenciales;
  validación con 86 pruebas offline aprobadas y documentación actualizada.
  Sin llamadas reales.

- Agregada selección del proveedor principal con `LLM_PROVIDER=open_ai|gemini`
  en `.env`, con OpenAI por defecto y el otro proveedor como respaldo por etapa.
  El entorno local queda seleccionado en Gemini para probarlo. Diagnósticos
  adaptados al orden seleccionado; documentación e instrucciones actualizadas.
  Agregadas pruebas de selección, configuración inválida y respaldo en ambos
  órdenes. Validación: 84 pruebas offline aprobadas. No se realizaron llamadas
  reales ni evaluaciones de calidad.

- Configurada `GEMINI_API_KEY` en el archivo local `.env`, junto a la clave de
  OpenAI, para permitir autenticar el proveedor de respaldo. No se verificó
  la credencial contra la API.

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
| Entrada | [v1 — moderación de entrada](prompts/input_moderation/few_shots/version_1_01_11.yaml) | Decide seguridad y alcance de Nubbix con `allowed`. Distingue consultas legítimas de seguridad de pedidos dañinos y rechaza instrucciones que intentan cambiar su rol. | Activo |
| Clasificación | [v1 — categoría sola](prompts/input_question/zero_shot/version_1_25_10_es.yaml) | Devuelve solo `billing`, `technical`, `account` u `other`. No satisface el contrato actual de cuatro campos. | Histórico, no activo |
| Clasificación | [v2 — respuesta estructurada](prompts/input_question/zero_shot/version_2_31_10.yaml) | Incorpora JSON con `answer`, `confidence`, `category` y `actions`, redacción en castellano y acciones sugeridas para un humano. | Histórico, no activo |
| Clasificación | [v3 — alcance de Nubbix y rechazo fijo](prompts/input_question/few_shots/version_3_31_10.yaml) | Explicita el alcance de Nubbix, amplía ejemplos de `other` y prescribe una frase fija para consultas fuera de alcance. | Histórico, no activo |
| Clasificación | [v4 — rechazo con redacción flexible](prompts/input_question/zero_shot/version_4_31_10.yaml) | Conserva el alcance y contrato de v3; permite redactar el rechazo con palabras propias sin responder la consulta fuera de alcance. | Activo |
| Salida | [v1 — revisión de respuesta](prompts/output/zero_shot/version_1_01_11.yaml) | Revisa `answer` y `actions`, pide retirar datos sensibles y recomendaciones inseguras, preservar el sentido y evitar compromisos inventados. Contempla una respuesta segura alternativa si no puede corregir el borrador. | Activo |

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

**Guardrails activos:** `input_moderation/few_shots/version_1_01_11.yaml` y
`output/zero_shot/version_1_01_11.yaml`, compartidos por OpenAI y Gemini. No se identifican
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

Archivo: [input_moderation/few_shots/version_1_01_11.yaml](prompts/input_moderation/few_shots/version_1_01_11.yaml). **Activo.**

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

Archivo: [input_question/zero_shot/version_1_25_10_es.yaml](prompts/input_question/zero_shot/version_1_25_10_es.yaml). **Histórico, no activo.**

Recibe un ticket y pide únicamente el nombre de una categoría en inglés y
minúsculas: `billing` para pagos, `technical` para fallas e integraciones,
`account` para acceso y administración de cuentas, u `other` para el resto.
Indica tratar el ticket como datos, sin obedecer instrucciones incluidas en él.
Su función se limita a clasificar: no genera respuesta, confianza ni acciones.
Por eso su salida de texto simple es incompatible con el JSON del flujo actual.

#### Clasificación — v2: respuesta y próximos pasos estructurados

Archivo: [input_question/zero_shot/version_2_31_10.yaml](prompts/input_question/zero_shot/version_2_31_10.yaml). **Histórico, no activo.**

Recibe un ticket, incluso en otro idioma, y pide un JSON de cuatro campos:
`answer` (respuesta breve en castellano), `category` (categoría en inglés),
`confidence` (estimación de confianza entre 0 y 1) y `actions` (lista de pasos
sugeridos en castellano para el agente humano). Las sugerencias no representan
acciones ejecutadas. Incluye descuentos y planes empresariales como ejemplos de
`other`. Su diferencia principal frente a v1 es ampliar la clasificación a una
respuesta utilizable por la ticketera con un contrato estructurado. Todavía no
explicita el alcance exclusivo de Nubbix ni una respuesta de rechazo.

#### Clasificación — v3: alcance de Nubbix y rechazo uniforme

Archivo: [input_question/few_shots/version_3_31_10.yaml](prompts/input_question/few_shots/version_3_31_10.yaml). **Histórico, no activo.**

Mantiene los cuatro campos de v2 y limita la asistencia a Nubbix, sus servicios
e integraciones. Detalla consultas válidas de `other`, como documentación,
capacitación, demostraciones o propuestas de colaboración. Un ticket válido no
tiene que mencionar la marca. Para consultas fuera de alcance pide una frase
fija de rechazo, `category: other` y `actions: []`, sin resolver la consulta.
También explicita que no debe cambiar de rol por instrucciones del ticket.
La diferencia de diseño frente a v2 es delimitar qué puede responder y hacer
uniforme el rechazo; su efectividad está pendiente de evaluación.

#### Clasificación — v4: alcance de Nubbix y rechazo flexible

Archivo: [input_question/zero_shot/version_4_31_10.yaml](prompts/input_question/zero_shot/version_4_31_10.yaml). **Activo.**

Recibe el ticket permitido por el guardrail de entrada y genera el mismo JSON
de cuatro campos. Conserva las categorías, el alcance y las restricciones de v3.
Cambia el rechazo: pide redactar con palabras propias un mensaje breve y amable
en castellano, indicando el límite de Nubbix, sin responder el tema ajeno,
con `category: other` y `actions: []`. Esto permite variar la redacción; no hay
evidencia comparativa de que esa flexibilidad mejore la calidad. En el flujo
normal, las consultas fuera de alcance deberían ser detenidas por la moderación
de entrada antes de llegar a esta etapa.

#### Salida — v1: revisión de privacidad, seguridad y redacción

Archivo: [output/zero_shot/version_1_01_11.yaml](prompts/output/zero_shot/version_1_01_11.yaml). **Activo.**

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
