# Proyecto OpenAI M1

## Estructura

```text
src/
├── main.py                         # Punto de entrada (pendiente)
├── clients/
│   ├── __init__.py
│   └── openai.py                    # Cliente del SDK de OpenAI
├── entities/
│   ├── __init__.py
│   └── request/
│       ├── __init__.py
│       └── openai_request.py        # Esquema Pydantic de la consulta
└── utils/
    ├── __init__.py
    └── validation/
        ├── __init__.py
        └── pydantic_validation.py   # Validación y categorías de error
prompts/                            # Prompts en YAML
evals/                              # Datasets y runner de evaluación
metrics_data/                       # Datos de métricas
.env.example                        # Plantilla de configuración
requirements.txt                    # Dependencias
```

La capa que llama al cliente crea un `OpenAIRequest`, validado por Pydantic.
`OpenAIClient.generate()` convierte la entidad a un diccionario sin campos en
`None` y lo envía a Responses. Devuelve la respuesta completa del SDK. Todavía
no hay una capa de servicios ni un endpoint HTTP implementados.

Los ejemplos usan los imports disponibles desde `src/main.py`; para ejecutarlos
desde la raíz, configurá `PYTHONPATH=src`.

## Validación de datos

Instalá las dependencias con `python -m pip install -r requirements.txt`.

`validate_data()` en `src/utils/validation/` centraliza la validación de objetos y JSON con
Pydantic v2. Por ejemplo, desde `src/main.py`:

```python
from pydantic import BaseModel
from utils.validation import DataValidationError, validate_data


class Persona(BaseModel):
    nombre: str
    edad: int


try:
    persona = validate_data(Persona, '{"nombre": "Ana", "edad": "hola"}')
except DataValidationError as error:
    print(error.errors)
```

Cada error incluye `category`, `type` (el código original de Pydantic), `loc`
(la ruta del campo) y `msg`. Las categorías son `invalid_json`, `missing_field`,
`extra_field`, `invalid_type`, `parsing_error` e `invalid_value` (incluye otras
restricciones y validaciones personalizadas).

La función conserva las conversiones y reglas del modelo. Para rechazar campos
extra, el modelo debe configurar `extra="forbid"`. El manejo HTTP debe realizarse
en el límite de la API: un fallo en datos del cliente puede ser 400/422; un fallo
interno no debe convertirse automáticamente en un error del cliente.

## Cliente de OpenAI

Desde `src/main.py` o una futura capa de servicios:

```python
import os
from clients import OpenAIClient
from entities.request import OpenAIRequest

request = OpenAIRequest(
    model=os.environ["OPENAI_MODEL"],
    input="Explicá qué es Pydantic.",
    instructions="Respondé en español y de forma breve.",
    max_output_tokens=500,
)

client = OpenAIClient()

try:
    response = client.generate(request)
    print(response.output_text)

finally:
    client.close()
```

Configurá `OPENAI_API_KEY` en el `.env` de la raíz del proyecto: el cliente la lee
siempre desde ese archivo. `.env.example` es una plantilla sin credenciales.
El ejemplo toma `OPENAI_MODEL` del entorno del proceso.
Reutilizá la instancia y cerrala al finalizar la aplicación. `generate()` devuelve
la respuesta completa del SDK y propaga sus excepciones para manejarlas en la
capa superior, sin asignar códigos HTTP desde el cliente.

`OpenAIRequest` vive en `src/entities/request/openai_request.py` y valida los
campos al crear la instancia. El cliente arma el payload a partir de esa entidad,
omitiendo campos opcionales con valor `None`. Para parsear un JSON también podés
usar `validate_data(OpenAIRequest, texto_json)` desde `utils.validation`.

## Errores y reintentos

El cliente configura el SDK con `max_retries=2`: puede hacer un intento inicial
y hasta dos reintentos automáticos, con esperas entre ellos. No hace falta un
`try/except` en `generate()` para activar esos reintentos.

Los fallos elegibles incluyen problemas de conexión, timeouts y respuestas HTTP
408, 409, 429 y 5xx. El SDK también contempla las indicaciones de reintento del
servidor. Errores como 400 o 401 no se reintentan normalmente.

Si el fallo persiste o no es elegible, el SDK lanza una excepción. `generate()`
actualmente la propaga a la capa llamadora. Esa capa puede distinguir
`APITimeoutError`, `APIConnectionError` y `APIStatusError`; este último incluye
`status_code`. `APITimeoutError` hereda de `APIConnectionError`, por lo que debe
capturarse primero si se quiere tratar por separado.

No agregar otro bucle de reintentos sin contemplar los del SDK: se multiplicaría
el número de intentos. `timeout=60.0` configura los timeouts HTTP; no es un límite
global de duración para toda la operación con sus reintentos.

Los fallos de inicialización se convierten en un `RuntimeError` con el mensaje
genérico `Failed to initialize OpenAI client.`. La clave se lee del `.env` de la
raíz. `close()` libera las conexiones y debe ejecutarse al finalizar el uso del
cliente, incluso si una consulta falla, como muestra el `finally` del ejemplo.

Referencia: [SDK oficial de OpenAI para Python](https://developers.openai.com/api/reference/python).

