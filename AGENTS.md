# Instrucciones del proyecto

## Contexto y objetivo

Este proyecto es una ticketera asistida por IA para el soporte de Nubbix, sus
servicios e integraciones. Ayuda a un agente humano a clasificar consultas,
redactar respuestas y sugerir próximos pasos. Actualmente se implementa como
una aplicación de consola (CLI) en Python; las acciones sugeridas no se ejecutan
automáticamente.

El procesamiento de cada ticket tiene tres etapas secuenciales:

1. Guardrail de entrada: verifica seguridad y relación con el soporte de Nubbix.
   Si rechaza la consulta, se detiene el procesamiento.
2. Clasificación y respuesta: genera `answer`, `category`, `confidence` y
   `actions`. Las categorías son `billing`, `technical`, `account` y `other`;
   las respuestas y sugerencias se redactan en castellano.
3. Guardrail de salida: revisa `answer` y `actions` para mejorar la redacción y
   retirar información sensible, preservando la categoría y confianza originales.

El proveedor principal se selecciona con `LLM_PROVIDER=open_ai|gemini` en `.env`
(OpenAI por defecto). El otro proveedor actúa como respaldo por etapa ante
fallos habilitados por la implementación, incluidos errores de credenciales o acceso (clave ausente, HTTP 401/403 y
clave inválida o expirada identificada por Gemini), errores transitorios y
agotamiento de reintentos de validación. Cada nueva etapa vuelve a intentar
el proveedor principal seleccionado primero. Ambos proveedores usan los prompts compartidos del proyecto.

Los contratos se validan con Pydantic. Solo se imprime el JSON final validado;
si alguna etapa falla, no debe mostrarse un borrador sin revisar. Los diagnósticos
van a stderr y deben evitar exponer tickets, respuestas o credenciales.

## Convención de nombres

- Usar guion bajo (`_`) para separar palabras en nombres de archivos y carpetas
  del proyecto; no usar guion medio (`-`). Mantener esta convención al crear o
  renombrar archivos y actualizar sus referencias.

## Organización y validación

- `src/clients/`: adaptadores de proveedores, respaldo, reintentos y límites de solicitudes.
- `src/services/ticket_service.py`: coordinación de las tres etapas.
- `src/entities/`: contratos de datos y modelos de solicitudes y respuestas.
- `prompts/`: instrucciones versionadas; `src/clients/prompts.py` selecciona las activas.
- `pricing/`: tarifas por proveedor; `openai.json` y `gemini.json` permiten
  estimar costos cuando hay tarifas verificadas para el modelo exacto.
- `metrics/`: registros JSONL compartidos por etapa para OpenAI y Gemini, con
  proveedor, modelo, tokens, latencia y costo estimado (null sin tarifas).
- `tests/`: pruebas unitarias y de integración con APIs simuladas.
- Mantener todos los casos de evals en `evals/data_set.jsonl`, con `id` y
  `stage`; no crear datasets separados por etapa sin pedido del usuario.
- `evals/`: dataset unificado y runner secuencial de OpenAI para evaluar variantes de
  prompts por etapa; ver `evals/README.md` para comandos, criterios y limitaciones.
- `README.md`: configuración, uso y detalles del comportamiento actual.

Para cambios de comportamiento, actualizar las pruebas afectadas y ejecutar
`.venv/bin/python -B -m unittest discover -s tests -v`. Las pruebas con APIs
simuladas verifican funcionamiento, pero no demuestran calidad del modelo ni
efectividad de los guardrails con solicitudes reales.

## Selección vigente de prompts

- Usar ejemplos inocentes en los prompts: soporte habitual para aceptación;
  cuentos, cocina o cultura general ajenos al servicio para rechazo por alcance.
  No incluir demostraciones de violencia, agresión, ataques, robo o extracción
  de secretos. Conservar las reglas de seguridad; esta preferencia sobre ejemplos
  no cambia las reglas ni demuestra efectividad del guardrail. No modificar por
  este motivo el dataset de evals sin un pedido específico.

- Organizar cada etapa de `prompts/` en `zero_shot/`, `few_shots/` y
  `chain_of_thought/`, conservando nombres únicos por etapa. La carpeta indica
  la técnica predominante; análisis interno de entrada conserva ejemplos de su
  base. No pedir que se exponga el razonamiento interno.
- No incluir la técnica en el nombre de los archivos de prompts: identificarla
  por la carpeta y conservar versión y fecha en el archivo. Los candidatos de
  análisis interno ahora también tienen ejemplos y combinan ambas técnicas.

- Mantener activos `input_moderation/few_shots/version_4_06_11.yaml`,
  `input_question/few_shots/version_7_06_11.yaml` y
  `output/zero_shot/version_1_01_11.yaml`, seleccionados en `prompts/active_prompts.yaml`
  (leído y validado por `src/clients/prompts.py`) y compartidos por ambos proveedores y defaults de evals.
- Entrada y clasificación prueban few-shot breve por decisión del usuario;
  salida conserva zero-shot v1 por el detalle de sus reglas de privacidad.
  La motivación es probar instrucciones compactas con dos ejemplos; no afirmar
  superioridad de calidad, seguridad, tokens, costo o latencia sin comparación.
- Entrada v1 y clasificación v4 anteriores quedan históricas, disponibles para
  comparar. Las otras variantes permanecen candidatas, incluidas las guiadas.
  Conservar archivos, descripciones e historial; no cambiar automáticamente la
  selección. Ver `prompts/README.md` para el inventario y revisión de longitud:
  caracteres y palabras no equivalen a tokens medidos ni prueban ahorro o calidad.
- Antes de proponer un reemplazo, comparar los mismos casos de cada etapa bajo
  las mismas condiciones por proveedor/modelo y registrar evidencia y decisión
  en `CHANGELOG.md`, distinguiendo objetivos de resultados demostrados.

## Historial y decisiones sobre prompts

- Actualizar `CHANGELOG.md` en cada cambio del proyecto, incluyendo código,
  prompts, configuración, pruebas y documentación.
- Registrar el cambio bajo la fecha actual en formato `AAAA-MM-DD`, con las
  fechas más recientes primero y las categorías existentes cuando correspondan.
- Describir brevemente qué cambió y su efecto. No inventar cambios históricos
  ni registrar como modificaciones las revisiones que no alteran archivos.
- Mantener en `CHANGELOG.md` el inventario de todas las versiones de prompts,
  con enlaces a sus archivos, etapa, diferencias y estado activo o histórico.
  Actualizarlo al agregar, modificar, eliminar o activar una versión, sin que
  el usuario tenga que solicitarlo.
- Conservar la explicación de cada prompt: función, entrada, salida, reglas,
  diferencia respecto de la versión previa y estado. Al reemplazar una versión,
  mantener su descripción y motivo de reemplazo como historia; no borrar esa
  información ni sobrescribir evidencia anterior con resultados nuevos.
- Para cada cambio o selección de prompt, registrar en `CHANGELOG.md`: etapa,
  versiones comparadas, problema que se busca resolver, diferencia introducida,
  evidencia de evaluación y decisión (activo, candidato o descartado) con su motivo.
- Comparar candidatos con los mismos casos y condiciones por proveedor/modelo;
  documentar calidad, seguridad, cumplimiento del contrato y costo/latencia cuando
  se midan. Distinguir mejoras esperadas de mejoras demostradas. Si no hay evals,
  indicarlo y no afirmar que una versión es superior por tener un número mayor.
