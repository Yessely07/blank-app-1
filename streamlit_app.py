import streamlit as st

import pandas as pd

import os

import urllib.parse

from datetime import datetime

from io import BytesIO

from PIL import Image

from supabase import create_client, Client

# --- CONFIGURACIÓN DE SUPABASE ---

# Asegúrate de tener SUPABASE_URL y SUPABASE_KEY en los Secrets de Streamlit Cloud

SUPABASE_URL = st.secrets["SUPABASE_URL"]

SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CONFIGURACIÓN DE PÁGINA ---

st.set_page_config(

    page_title="Control de Seguridad Digital",

    layout="wide",

    page_icon="🛡️"

)



# --- ESTILOS CSS ---

st.markdown("""

<style>

body { background-color: #F4F6F9; }

.main-title {

    font-size: 32px; font-weight: 700; color: white;

    background: linear-gradient(90deg, #0E4667, #1C7ED6);

    padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 25px;

}

[data-testid="stSidebar"] {

    background: linear-gradient(180deg, #0E4667, #1C7ED6);

}

[data-testid="stSidebar"] * { color: white !important; }

.stButton>button {

    width: 100%; border-radius: 8px;

    background: linear-gradient(90deg, #1C7ED6, #0E4667);

    color: white; font-weight: 600;

}

</style>

""", unsafe_allow_html=True)

# --- FUNCIONES DE BASE DE DATOS ---
def get_all_data():

    """Obtiene todos los registros de la tabla gestiones en Supabase."""

    try:

        response = supabase.table("gestiones").select("*").order("id", desc=True).execute()

        return pd.DataFrame(response.data)

    except Exception as e:

        st.error(f"Error al obtener datos: {e}")

        return pd.DataFrame()



def save_record(equipo, usuario, fecha_reporte, file):

    """Guarda un nuevo registro y sube la imagen al Storage de Supabase."""

    path_publico = ""

    if file:

        # Generar nombre único para la imagen

        file_extension = file.name.split('.')[-1]

        file_name = f"{equipo}_{datetime.now().strftime('%H%M%S')}.{file_extension}"

        try:

            # Subir bytes directamente al bucket 'evidencias'

            file_bytes = file.getvalue()

            supabase.storage.from_("evidencias").upload(

                path=file_name,

                file=file_bytes,

                file_options={"content-type": file.type}

            )

            # Obtener la URL pública de la imagen

            path_publico = supabase.storage.from_("evidencias").get_public_url(file_name)

        except Exception as e:

            st.error(f"Error al subir evidencia: {e}")

    # Insertar datos en la tabla

    data = {

        "equipo": equipo,

        "usuario": usuario,

        "fecha_reporte": fecha_reporte,

        "captura_path": path_publico,

        "fecha_atencion": "",

        "comentarios": ""

    }

    try:

        supabase.table("gestiones").insert(data).execute()

        st.success("Registro guardado exitosamente ✅")

    except Exception as e:

        st.error(f"Error al insertar registro: {e}")

def update_record(id_reg, f_atencion, comentario):

    """Actualiza la atención y comentarios de un registro."""

    try:

        supabase.table("gestiones").update({

            "fecha_atencion": f_atencion,

            "comentarios": comentario

        }).eq("id", id_reg).execute()

        st.toast("Cambios guardados")

    except Exception as e:

        st.error(f"Error al actualizar: {e}")
def delete_record(id_reg):

    """Elimina un registro de la tabla."""

    try:

        supabase.table("gestiones").delete().eq("id", id_reg).execute()

        st.toast("Registro eliminado")

    except Exception as e:

        st.error(f"Error al eliminar: {e}")

# --- EXPORTACIÓN A EXCEL ---

def exportar_excel_pro(df):

    output = BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:

        df.to_excel(writer, index=False, sheet_name='Reporte')

        worksheet = writer.sheets['Reporte']

        worksheet.set_column('A:G', 20)

    return output.getvalue()

# --- SIDEBAR ---

with st.sidebar:

    st.markdown("## 🛡️ Panel de Control")

    st.markdown("---")

    opcion = st.radio(

        "Seleccione Operación:",

        ["GESTIÓN DE VULNERABILIDADES TÉCNICAS", "GESTIÓN DE ...", "GESTION DE..."]

    )

# --- TÍTULO PRINCIPAL ---

st.markdown('<div class="main-title">🛡️ CONTROLES DE SEGURIDAD DIGITAL</div>', unsafe_allow_html=True)

# --- LÓGICA DE CONTENIDO ---

if opcion == "GESTIÓN DE VULNERABILIDADES TÉCNICAS":

    col_izq, col_der = st.columns([1, 2.2])

    # --- COLUMNA IZQUIERDA: REGISTRO Y DASHBOARD ---

    with col_izq:

        st.markdown("### 📝 Registro")

        with st.form("nuevo_registro", clear_on_submit=True):

            eq = st.text_input("Equipo")

            us = st.text_input("Usuario")

            f_r = st.date_input("Fecha Reporte", datetime.now())

            evid = st.file_uploader("Evidencia (Captura)", type=['png', 'jpg', 'jpeg'])

            

            if st.form_submit_button("💾 Guardar"):

                if eq and us:

                    save_record(eq, us, f_r.strftime("%Y-%m-%d"), evid)

                    st.rerun()

                else:

                    st.warning("Por favor complete los campos de Equipo y Usuario.")



        st.markdown("### 📊 Dashboard")

        df_dash = get_all_data()

        if not df_dash.empty:

            total = len(df_dash)

            # Manejo de nulos o vacíos para las métricas

            atendidos = df_dash[df_dash["fecha_atencion"].fillna("") != ""].shape[0]

            pendientes = total - atendidos



            d1, d2, d3 = st.columns(3)

            d1.metric("Total", total)

            d2.metric("Atendidos", atendidos)

            d3.metric("Pendientes", pendientes)

            st.bar_chart(pd.DataFrame({

                "Estado": ["Atendidos", "Pendientes"],

                "Cantidad": [atendidos, pendientes]

            }).set_index("Estado"))

        else:

            st.info("Sin datos para mostrar en el Dashboard.")



    # --- COLUMNA DERECHA: SEGUIMIENTO ---

    # --- COLUMNA DERECHA: SEGUIMIENTO ---

    with col_der:

        st.markdown("### 📋 Seguimiento")

        df_db = get_all_data()



        if not df_db.empty:

            for _, row in df_db.iterrows():

                f_at_val = row['fecha_atencion'] if row['fecha_atencion'] else ""

                estado = "🟢 Atendido" if f_at_val else "🔴 Pendiente"

                

                with st.expander(f"{row['equipo']} | {row['usuario']} | {estado}"):

                    c1, c2, c3, c4 = st.columns([1.5, 2, 1, 1.2])

                    

                    with c1:

                        # Mostrar imagen actual

                        if row['captura_path']:

                            st.image(row['captura_path'], use_container_width=True, caption="Evidencia Actual")

                        else:

                            st.info("Sin imagen")

                        

                        # NUEVA ACCIÓN: Subir nueva imagen para actualizar

                        nueva_evid = st.file_uploader("Actualizar Imagen", type=['png', 'jpg', 'jpeg'], key=f"upd_img_{row['id']}")



                    with c2:

                        st.text_input("Fecha Reporte", value=row['fecha_reporte'], disabled=True, key=f"fr_{row['id']}")

                        f_at = st.text_input("Fecha Atención", value=f_at_val, key=f"f_{row['id']}", placeholder="YYYY-MM-DD")

                        com = st.text_area("Comentarios", value=row['comentarios'] if row['comentarios'] else "", key=f"c_{row['id']}")

                        

                        if st.button("Actualizar Todo", key=f"btn_{row['id']}"):

                            # 1. Lógica para subir la nueva imagen si existe

                            nuevo_path = row['captura_path']

                            if nueva_evid:

                                file_extension = nueva_evid.name.split('.')[-1]

                                file_name = f"{row['equipo']}_UPDATE_{datetime.now().strftime('%H%M%S')}.{file_extension}"

                                file_bytes = nueva_evid.getvalue()

                                

                                try:

                                    supabase.storage.from_("evidencias").upload(

                                        path=file_name,

                                        file=file_bytes,

                                        file_options={"content-type": nueva_evid.type}

                                    )

                                    nuevo_path = supabase.storage.from_("evidencias").get_public_url(file_name)

                                except Exception as e:

                                    st.error(f"Error al subir nueva imagen: {e}")



                            # 2. Actualizar base de datos (incluyendo el nuevo path si cambió)

                            try:

                                supabase.table("gestiones").update({

                                    "fecha_atencion": f_at,

                                    "comentarios": com,

                                    "captura_path": nuevo_path

                                }).eq("id", row['id']).execute()

                                st.success("¡Registro e imagen actualizados!")

                                st.rerun()

                            except Exception as e:

                                st.error(f"Error al actualizar: {e}")



                    with c3:

                        if st.button("Eliminar", key=f"del_{row['id']}"):

                            delete_record(row['id'])

                            st.rerun()



                    with c4:

                        # (Mantiene tu lógica de correo)

                        asunto = f"Actualizar sistema operativo - {row['equipo']}"

                        cuerpo = f"Estimados Señores,\n\nSolicito apoyo para actualizar el equipo {row['equipo']}..."

                        mail_url = f"mailto:yaliaga@mincetur.gob.pe?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"

                        

                        st.markdown(f'<a href="{mail_url}" target="_blank"><button style="width:100%; padding:8px; border-radius:8px; border:none; background:linear-gradient(90deg, #28a745, #218838); color:white; font-weight:600; cursor:pointer;">📧 Enviar Correo</button></a>', unsafe_allow_html=True)

elif opcion == "GESTIÓN DE ...":

    st.subheader("Módulo en desarrollo...")

elif opcion == "GESTION DE...":

    st.subheader("Módulo en desarrollo...")
