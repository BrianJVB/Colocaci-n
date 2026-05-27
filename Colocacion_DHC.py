import streamlit as st
import pandas as pd
import io
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Configuración visual de la interfaz de usuario
st.set_page_config(
    page_title="Procesador y Formateador de Excel", 
    page_icon="📝", 
    layout="centered"
)

# Estilo personalizado básico
st.title("📝 Asistente de Colocación")
st.write("Sube un archivo Excel para corregir y formatear.")

# --- Gestión de la API Key ---
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Introduce tu Gemini API Key:", type="password")

if not api_key:
    st.info("🔑 Por favor, configura la API Key de Gemini para activar la aplicación.", icon="ℹ️")
    st.stop()

# Inicializar el cliente oficial de Gemini
client = genai.Client(api_key=api_key)

# --- Configuración de Reglas del Sistema ---
REGLAS_SISTEMA = ("""
    Actúa como revisor experto de informes técnicos de construcción, especializado en control de formato según normativa interna.
    Tu tarea es recibir un archivo excel y leer cada fila de la columna llamada "UBICACION" y reescribirlas cumpliendo estrictamente las siguientes reglas:
    1. Estructura obligatoria
    - Cada descripción debe seguir este formato, puede contener o no todos los elementos del formato, si no está descrito, no agregar frases extras:
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
    Cada frase debe terminar con punto.
    6. Reglas especiales
    Separar siempre elemento y piso con coma
    Ejemplo: Muros, 1° piso
    Respetar nombres específicos indicados por el usuario
    Ejemplo: “Viga de fundación” no se simplifica
    7. Instrucción de salida
    Entrega ÚNICAMENTE el archivo corregido listo para usar. No agregues saludos, explicaciones, introducciones ni viñetas adicionales de tu parte.
""")

# --- Interfaz de Entrada de Archivo ---
archivo_subido = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if archivo_subido is not None:
    try:
        # Leer el archivo Excel usando pandas
        df = pd.read_excel(archivo_subido)
        
        st.success("¡Archivo cargado con éxito!")
        st.write("Vista previa de los datos:")
        st.dataframe(df.head(5)) # Muestra las primeras 5 filas de muestra
        
        # Permitir al usuario elegir qué columna contiene los textos a corregir
        columnas = df.columns.tolist()
        columna_seleccionada = st.selectbox("Selecciona la columna que contiene las descripciones a procesar:", columnas)
        
        # --- Procesamiento del Archivo ---
        if st.button("Procesar Archivo Completo", type="primary"):
            
            # Crear listas para almacenar los resultados
            resultados_corregidos = []
            
            # Barra de progreso visual
            barra_progreso = st.progress(0)
            estado_texto = st.empty()
            total_filas = len(df)
            
            for index, fila in df.iterrows():
                texto_original = str(fila[columna_seleccionada])
                
                # Omitir procesamiento si la celda está vacía
                if pd.isna(fila[columna_seleccionada]) or texto_original.strip() == "" or texto_original.lower() == "nan":
                    resultados_corregidos.append("")
                    continue
                
                estado_texto.text(f"Procesando fila {index + 1} de {total_filas}...")
                
                try:
                    # Llamada a la API de Gemini para cada celda
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=texto_original,
                        config=types.GenerateContentConfig(
                            system_instruction=REGLAS_SISTEMA,
                            temperature=0.1,
                        )
                    )
                    resultados_corregidos.append(response.text.strip())
                    
                except APIError as e:
                    if e.code == 429:
                        st.error("⏳ Límite de cuota por minuto de la API alcanzado. Por favor, espera un momento.")
                        st.stop()
                    else:
                        resultados_corregidos.append(f"Error API: {e.message}")
                except Exception as e:
                    resultados_corregidos.append(f"Error inesperado: {str(e)}")
                
                # Actualizar barra de progreso
                barra_progreso.progress((index + 1) / total_filas)
            
            estado_texto.text("¡Procesamiento completo!")
            
            # Insertar los datos procesados en una nueva columna en nuestro DataFrame
            df["Texto Corregido (IA)"] = resultados_corregidos
            
            st.write("Muestra de los resultados procesados:")
            st.dataframe(df.head(5))
            
            # --- Convertir el DataFrame modificado a un archivo Excel en memoria para descargarlo ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Resultados_Corregidos')
            datos_excel = output.getvalue()
            
            # Botón de descarga
            st.download_button(
                label="📥 Descargar Excel Corregido",
                data=datos_excel,
                file_name="informe_colocacion_corregido.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except Exception as e:
        st.error(f"Error al leer el archivo Excel: {e}")
