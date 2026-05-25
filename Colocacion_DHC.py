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
REGLAS_SISTEMA = (
    "Eres un asistente automatizado de edición de texto y control de calidad de datos. "
    "Tu tarea consiste en recibir una frase corta, corregir de inmediato cualquier error ortográfico, "
    "de tipeo o palabras mal escritas, y reordenar la información bajo la estructura estricta: "
    "[Acción Principal] + [Sujeto o Componente Objeto] + [Detalle o Plazo de Contexto]. "
    "Aplica reglas de puntuación perfectas (mayúscula inicial, puntos, comas necesarias). "
    "REGLA CRÍTICA: Devuelve únicamente la frase final formateada. Está estrictamente prohibido "
    "agregar introducciones, explicaciones, saludos, viñetas o notas de tu parte."
)

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