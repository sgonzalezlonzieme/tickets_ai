# Revisión y variantes de prompts

La selección activa para prueba manual es entrada v4 few-shot breve,
clasificación v7 few-shot breve y salida v1 zero-shot. Se configura en
[`active_prompts.yaml`](active_prompts.yaml), compartida por ambos proveedores y
los defaults del runner. El código solo lee y valida esta configuración;
los nombres deben ser archivos YAML únicos dentro de cada etapa, sin carpetas.
Reiniciá el CLI tras editar la selección, ya que se carga en caché. Entrada v1 y clasificación v4 anteriores quedan como
bases históricas para comparación. Las otras variantes permanecen candidatas.
Se conservan archivos y descripciones; la selección no demuestra superioridad.

La revisión cubre todos los archivos. Los históricos v1 y v2 de clasificación
son más breves, pero v1 no cumple el contrato JSON actual y v2 no explicita el
alcance de Nubbix. No son sustitutos equivalentes por ser más cortos. La v3
histórica prescribe rechazo fijo; la v4 anterior y la v7 activa conservan redacción flexible.
Los seis candidatos previos repiten las reglas completas de la base y añaden
criterios y ejemplos: son útiles como referencia extendida, con mayor texto.

Las variantes nuevas condensan reglas repetidas en un núcleo por etapa y usan
JSON de ejemplo compacto. Las breves tienen dos ejemplos; las extendidas cuatro
más aclaraciones de casos límite. Las de `chain_of_thought` agregan revisión
interna y también ejemplos: son híbridas con few-shot, sin publicar razonamiento.
Difieren tanto en longitud como en ejemplos; no permiten atribuir un resultado
solo a la técnica o al largo sin diseñar una comparación controlada adicional.

## Contratos y reglas

- Entrada: recibe el ticket no confiable; solo `allowed` booleano. Debe cumplir
  seguridad y alcance simultáneamente; preserva soporte defensivo, consultas
  comerciales/laborales y la distinción entre reporte de daño y facilitación.
- Clasificación: recibe el ticket; solo `answer`, `confidence`, `category`,
  `actions`. Texto castellano, categorías en inglés y confianza entre 0 y 1.
  Consultas ajenas no se resuelven: `other`, explicación breve y acciones vacías.
  Las acciones siguen siendo sugerencias, sin inventar hechos ni compromisos.
- Salida: recibe únicamente borrador `answer` y `actions`; devuelve esos dos
  campos revisados. Retira datos personales, identificadores privados, secretos,
  ofensas, peligros y afirmaciones sin fundamento. Usa canales oficiales seguros,
  preserva contenido adecuado y contempla alternativa segura con acciones vacías.

## Nuevas variantes separadas

Se compara cada candidato con el activo de su etapa y con el candidato previo
indicado. La reducción es de caracteres de `instructions` ya cargadas del YAML,
no tokens medidos. Los ejemplos son ficticios e inocentes, no salidas reales de un modelo. Las
consultas rechazadas ilustran alcance con cuentos, cocina y cultura general;
no se incluyen pedidos de daño, ataques ni extracción de secretos. Esto no
evalúa ni demuestra la efectividad de las reglas de seguridad.

| Etapa / técnica | Archivo candidato | Variante | Ejemplos | Caracteres | Candidato previo | Reducción de caracteres |
| --- | --- | --- | --- | --- | --- | --- |
| input_moderation / few_shots | [version_4_06_11](input_moderation/few_shots/version_4_06_11.yaml) | breve | 2 | 1354 | [version_2_06_11](input_moderation/few_shots/version_2_06_11.yaml) | 55.0% |
| input_moderation / few_shots | [version_5_06_11](input_moderation/few_shots/version_5_06_11.yaml) | extendida | 4 | 1977 | [version_2_06_11](input_moderation/few_shots/version_2_06_11.yaml) | 34.4% |
| input_moderation / chain_of_thought | [version_6_06_11](input_moderation/chain_of_thought/version_6_06_11.yaml) | breve | 2 | 1538 | [version_3_06_11](input_moderation/chain_of_thought/version_3_06_11.yaml) | 53.5% |
| input_moderation / chain_of_thought | [version_7_06_11](input_moderation/chain_of_thought/version_7_06_11.yaml) | extendida | 4 | 2251 | [version_3_06_11](input_moderation/chain_of_thought/version_3_06_11.yaml) | 32.0% |
| input_question / few_shots | [version_7_06_11](input_question/few_shots/version_7_06_11.yaml) | breve | 2 | 1711 | [version_5_06_11](input_question/few_shots/version_5_06_11.yaml) | 65.2% |
| input_question / few_shots | [version_8_06_11](input_question/few_shots/version_8_06_11.yaml) | extendida | 4 | 2705 | [version_5_06_11](input_question/few_shots/version_5_06_11.yaml) | 45.0% |
| input_question / chain_of_thought | [version_9_06_11](input_question/chain_of_thought/version_9_06_11.yaml) | breve | 2 | 1926 | [version_6_06_11](input_question/chain_of_thought/version_6_06_11.yaml) | 57.7% |
| input_question / chain_of_thought | [version_10_06_11](input_question/chain_of_thought/version_10_06_11.yaml) | extendida | 4 | 2971 | [version_6_06_11](input_question/chain_of_thought/version_6_06_11.yaml) | 34.8% |
| output / few_shots | [version_4_06_11](output/few_shots/version_4_06_11.yaml) | breve | 2 | 1718 | [version_2_06_11](output/few_shots/version_2_06_11.yaml) | 51.8% |
| output / few_shots | [version_5_06_11](output/few_shots/version_5_06_11.yaml) | extendida | 4 | 2631 | [version_2_06_11](output/few_shots/version_2_06_11.yaml) | 26.3% |
| output / chain_of_thought | [version_6_06_11](output/chain_of_thought/version_6_06_11.yaml) | breve | 2 | 1831 | [version_3_06_11](output/chain_of_thought/version_3_06_11.yaml) | 48.2% |
| output / chain_of_thought | [version_7_06_11](output/chain_of_thought/version_7_06_11.yaml) | extendida | 4 | 3023 | [version_3_06_11](output/chain_of_thought/version_3_06_11.yaml) | 14.5% |

## Inventario revisado

| Archivo | Estado | Caracteres | Palabras separadas por espacios |
| --- | --- | --- | --- |
| [input_moderation/chain_of_thought/version_3_06_11.yaml](input_moderation/chain_of_thought/version_3_06_11.yaml) | Candidato previo | 3310 | 494 |
| [input_moderation/chain_of_thought/version_6_06_11.yaml](input_moderation/chain_of_thought/version_6_06_11.yaml) | Candidato compacto | 1538 | 203 |
| [input_moderation/chain_of_thought/version_7_06_11.yaml](input_moderation/chain_of_thought/version_7_06_11.yaml) | Candidato compacto | 2251 | 304 |
| [input_moderation/few_shots/version_1_01_11.yaml](input_moderation/few_shots/version_1_01_11.yaml) | Histórico, base anterior | 2178 | 319 |
| [input_moderation/few_shots/version_2_06_11.yaml](input_moderation/few_shots/version_2_06_11.yaml) | Candidato previo | 3012 | 431 |
| [input_moderation/few_shots/version_4_06_11.yaml](input_moderation/few_shots/version_4_06_11.yaml) | Activo para prueba manual | 1354 | 180 |
| [input_moderation/few_shots/version_5_06_11.yaml](input_moderation/few_shots/version_5_06_11.yaml) | Candidato compacto | 1977 | 270 |
| [input_question/chain_of_thought/version_10_06_11.yaml](input_question/chain_of_thought/version_10_06_11.yaml) | Candidato compacto | 2971 | 388 |
| [input_question/chain_of_thought/version_6_06_11.yaml](input_question/chain_of_thought/version_6_06_11.yaml) | Candidato previo | 4554 | 692 |
| [input_question/chain_of_thought/version_9_06_11.yaml](input_question/chain_of_thought/version_9_06_11.yaml) | Candidato compacto | 1926 | 254 |
| [input_question/few_shots/version_3_31_10.yaml](input_question/few_shots/version_3_31_10.yaml) | Histórico | 2534 | 399 |
| [input_question/few_shots/version_5_06_11.yaml](input_question/few_shots/version_5_06_11.yaml) | Candidato previo | 4921 | 718 |
| [input_question/few_shots/version_7_06_11.yaml](input_question/few_shots/version_7_06_11.yaml) | Activo para prueba manual | 1711 | 227 |
| [input_question/few_shots/version_8_06_11.yaml](input_question/few_shots/version_8_06_11.yaml) | Candidato compacto | 2705 | 354 |
| [input_question/zero_shot/version_1_25_10_es.yaml](input_question/zero_shot/version_1_25_10_es.yaml) | Histórico | 632 | 93 |
| [input_question/zero_shot/version_2_31_10.yaml](input_question/zero_shot/version_2_31_10.yaml) | Histórico | 1294 | 201 |
| [input_question/zero_shot/version_4_31_10.yaml](input_question/zero_shot/version_4_31_10.yaml) | Histórico, base anterior | 2653 | 420 |
| [output/chain_of_thought/version_3_06_11.yaml](output/chain_of_thought/version_3_06_11.yaml) | Candidato previo | 3536 | 482 |
| [output/chain_of_thought/version_6_06_11.yaml](output/chain_of_thought/version_6_06_11.yaml) | Candidato compacto | 1831 | 230 |
| [output/chain_of_thought/version_7_06_11.yaml](output/chain_of_thought/version_7_06_11.yaml) | Candidato compacto | 3023 | 378 |
| [output/few_shots/version_2_06_11.yaml](output/few_shots/version_2_06_11.yaml) | Candidato previo | 3568 | 467 |
| [output/few_shots/version_4_06_11.yaml](output/few_shots/version_4_06_11.yaml) | Candidato compacto | 1718 | 222 |
| [output/few_shots/version_5_06_11.yaml](output/few_shots/version_5_06_11.yaml) | Candidato compacto | 2631 | 331 |
| [output/zero_shot/version_1_01_11.yaml](output/zero_shot/version_1_01_11.yaml) | Activo | 1805 | 261 |

## Evidencia y decisión

Pendiente de evaluación con modelos. Se validan YAML, salidas ilustrativas y
carga del runner, pero eso no demuestra que las reglas se cumplan con tickets
reales. Todos los candidatos nuevos tienen menos caracteres que el candidato
previo de la misma técnica; no todos son más cortos que el activo zero-shot.
Tampoco se midió ahorro de tokens, costo, latencia, calidad ni seguridad.

Por decisión del usuario se activan entrada v4 y clasificación v7 para prueba
manual, manteniendo salida v1. La comparación con las bases previas sigue
pendiente: esta activación no demuestra que las variantes sean superiores. Usar los mismos casos de `evals/data_set.jsonl`, configuración,
proveedor/modelo y criterios. El runner solo usa OpenAI; la disponibilidad de
Gemini en el CLI no evalúa estas variantes con Gemini.

Por ejemplo, comparar entrada activa con sus dos candidatos few-shot compactos:

```bash
.venv/bin/python evals/runner.py --stage input_moderation \
  --prompt version_1_01_11.yaml --prompt version_4_06_11.yaml \
  --prompt version_5_06_11.yaml
```

Ese comando hace llamadas reales y consume tokens; no se ejecutó como parte de
esta revisión. Revisar calidad y seguridad además del contrato y registrar
costo/latencia cuando se midan, incluyendo posibles regresiones.
