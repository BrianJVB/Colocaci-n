import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Configuración visual de la interfaz de usuario
st.set_page_config(
    page_title="Procesador y Formateador de Texto", 
    page_icon="📝", 
    layout="centered"
)

# Estilo personalizado básico
st.title("📝 Asistente de Formato y Corrección")
st.write("Corrige ortografía y reordena datos de forma automática con IA.")

# --- Gestión de la API Key ---
# Intenta leer desde los Secretos de Streamlit (producción) o de la barra lateral (desarrollo local)
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Introduce tu Gemini API Key:", type="password")

if not api_key:
    st.info("🔑 Por favor, configura la API Key de Gemini para activar la aplicación.", icon="ℹ️")
    st.stop()

# Inicializar el cliente oficial de Gemini
client = genai.Client(api_key=api_key)

# --- Configuración de Reglas del Sistema ---
# Aquí defines de manera estricta cómo estructurar el texto
REGLAS_SISTEMA = ("""
    Actúa como revisor experto de informes técnicos de construcción, especializado en control de formato según normativa interna.
    Tu tarea es recibir descripciones de faenas de hormigonado y reescribirlas cumpliendo estrictamente las siguientes reglas:
    1. Estructura obligatoria
    - Cada descripción debe seguir este formato, puede contener o no todos los elemetos del formato, si no esta descrito, no agregar frases extras
    [Elemento] [Piso], [Información adicional de mayor a menor escala], [Ejes].
    2. Orden y jerarquía de elementos
    Si existen varios elementos, sepáralos en líneas distintas y ordénalos así:
    - Muros (usar “Muro” si es entre 2 ejes, “Muros” si son más); (si contiene contención, agregar como Muros contención)
    - Losas o radier (prohibido “losa radier”)
    - Losa cielo (plural: “Losas cielo”)
    - Fundación
    - Escalera
    - Viga
    - Pila
    - Pilar o columna
    - Pavimento
    - Zapata
    - Vereda (plural: "Veredas")
    - Cama de apoyo soleras
    - Otros
    Además, los elementos deben ordenarse desde el nivel inferior hacia el superior.
    3. Reglas de nomenclatura
    Usar siempre:
    - “X° piso”
    - “X° subterráneo”
    - “edificio N° X”
    - “torre N° X”
    - “casa N° X”
    - “departamento N° X”
    - "ciclo N° X y N° X"
    - “vano N° X”
    - Si no indica n°, no lo agregues.
    En losas, solo agregar si la frase contiene ejes:
    Primero ejes de letras, luego números
    Ejemplo: ejes A-C entre ejes 1-10
    Se cumple solo en caso que diga "ejes" dentro del texto
    En escaleras:
    Usar: desde X° piso hasta X° piso
    En pavimentos:
    Usar: desde Pk XXX.XXX hasta Pk YYY.YYY (de menor a mayor)
    Mantener conectores espaciales como: entre, desde, hasta
    4. Formato y redacción
    No agregar información nueva
    Solo corregir, ordenar y normalizar lo entregado
    Corregir ortografía y coherencia
    Mantener lenguaje técnico simple
    Usar mayúscula solo al inicio y en nombres propios
    “Torre”, “Casa”, “Departamento” siempre con minúscula
    5. Puntuación y unidades
    - Punto (.) → separador de miles
    - Coma (,) → separador decimal
    Cada frase debe terminar con punto
    6. Reglas especiales
    Separar siempre elemento y piso con coma
    Ejemplo: Muros, 1° piso
    Respetar nombres específicos indicados por el usuario
    Ejemplo: “Viga de fundación” no se simplifica
    7. Instrucción de salida
    Entrega:
    Texto corregido listo para copiar
    Breve justificación de los cambios, basada en las reglas aplicadas
""")

# --- Interfaz de Entrada ---
texto_entrada = st.text_area(
    "Ingresa la frase o apuntes a procesar:", 
    placeholder="Ejemplo: urgente enviar informe brian mañana a primera hora"
)

# --- Procesamiento ---
if st.button("Procesar y Formatear", type="primary"):
    if not texto_entrada.strip():
        st.warning("Por favor, escribe un texto antes de procesar.")
    else:
        with st.spinner("La IA está ordenando y corrigiendo el texto..."):
            try:
                # Llamada al modelo gratuito Gemini 2.5 Flash
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=texto_entrada,
                    config=types.GenerateContentConfig(
                        system_instruction=REGLAS_SISTEMA,
                        temperature=0.1,  # Temperatura muy baja para máxima consistencia y evitar creatividad
                    )
                )
                
                # Despliegue de resultados limpios
                st.success("¡Texto procesado correctamente!")
                st.markdown("### 📋 Resultado Final:")
                st.code(response.text, language=None)
                
            except APIError as e:
                # Manejo de cuellos de botella por exceso de peticiones por minuto en el plan gratis
                if e.code == 429:
                    st.error("⏳ Se alcanzó el límite de solicitudes por minuto del plan gratuito. Por favor, espera unos segundos e intenta nuevamente.")
                else:
                    st.error(f"Error de la API de Google: {e.message}")
            except Exception as e:
                st.error(f"Ocurrió un error inesperado: {e}")
