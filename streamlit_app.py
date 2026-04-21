import streamlit as st
import pandas as pd
import sqlite3
import os
import urllib.parse
from datetime import datetime
from io import BytesIO
from PIL import Image
from supabase import create_client, Client

# --- CONFIGURACIÓN DE SUPABASE ---
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

# --- FUNCIONES ---

def get_all_data():
    try:
        response = supabase.table("gestiones").select("*").order("id", desc=True).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return pd.DataFrame()

def save_record(equipo, usuario, fecha_reporte, file):
    path_publico = ""
    if file:
        file_extension = file.name.split('.')[-1]
        file_name = f"{equipo}_{datetime.now().strftime('%H%M%S')}.{file_extension}"
        try:
            file_bytes = file.getvalue()
            supabase.storage.from_("evidencias").upload(
                path=file_name,
                file=file_bytes,
                file_options={"content-type": file.type}
            )
            path_publico = supabase.storage.from_("evidencias").get_public_url(file_name)
        except Exception as e:
            st.error(f"Error al subir evidencia: {e}")

    data = {
        "equipo": equipo,
        "usuario": usuario,
        "fecha_reporte": fecha_reporte,
        "captura_path": path_publico,
        "fecha_atencion": "",
        "comentarios": "",
        "comentario_imagen": ""
    }

    try:
        supabase.table("gestiones").insert(data).execute()
        st.success("Registro guardado exitosamente ✅")
    except Exception as e:
        st.error(f"Error al insertar registro: {e}")

def delete_record(id_reg):
    try:
        supabase.table("gestiones").delete().eq("id", id_reg).execute()
        st.toast("Registro eliminado")
    except Exception as e:
        st.error(f"Error al eliminar: {e}")

# --- EXPORTACIÓN ---
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

# --- TÍTULO ---
st.markdown('<div class="main-title">🛡️ CONTROLES DE SEGURIDAD DIGITAL</div>', unsafe_allow_html=True)

# --- CONTENIDO ---
if opcion == "GESTIÓN DE VULNERABILIDADES TÉCNICAS":

    col_izq, col_der = st.columns([1, 2.2])

    # --- IZQUIERDA ---
    with col_izq:
        st.markdown("### 📝 Registro")
        with st.form("nuevo_registro", clear_on_submit=True):
            eq = st.text_input("Equipo")
            us = st.text_input("Usuario")
            f_r = st.date_input("Fecha Reporte", datetime.now())
            evid = st.file_uploader("Evidencia", type=['png','jpg','jpeg'])

            if st.form_submit_button("💾 Guardar"):
                if eq and us:
                    save_record(eq, us, f_r.strftime("%Y-%m-%d"), evid)
                    st.rerun()

        st.markdown("### 📊 Dashboard")
        df_dash = get_all_data()

        if not df_dash.empty:
            total = len(df_dash)
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

            # EXPORTAR
            excel = exportar_excel_pro(df_dash)
            st.download_button("📥 Exportar Excel", excel, "reporte.xlsx")

    # --- DERECHA ---
    with col_der:
        st.markdown("### 📋 Seguimiento")
        df_db = get_all_data()

        for _, row in df_db.iterrows():
            estado = "🟢 Atendido" if row['fecha_atencion'] else "🔴 Pendiente"

            with st.expander(f"{row['equipo']} | {row['usuario']} | {estado}"):

                c1, c2, c3, c4 = st.columns([1.5,2,1,1.2])

                # --- IMAGEN PRINCIPAL ---
                with c1:
                    if row['captura_path']:
                        st.image(row['captura_path'])
                    else:
                        st.info("Sin imagen")

                    nueva_evid = st.file_uploader("Actualizar Imagen", key=f"upd_img_{row['id']}")

                # --- COMENTARIOS ---
                with c2:
                    f_at = st.text_input("Fecha Atención", value=row['fecha_atencion'], key=f"f_{row['id']}")
                    com = st.text_area("Comentarios", value=row['comentarios'], key=f"c_{row['id']}")

                    # NUEVO
                    img_com = st.file_uploader("Adjuntar imagen al comentario", key=f"img_com_{row['id']}")

                    if row.get("comentario_imagen"):
                        st.image(row["comentario_imagen"], caption="Imagen del comentario")

                    if st.button("Actualizar Todo", key=f"btn_{row['id']}"):

                        nuevo_path = row['captura_path']
                        comentario_img_url = row.get("comentario_imagen", "")

                        if nueva_evid:
                            name = f"upd_{datetime.now().strftime('%H%M%S')}.png"
                            supabase.storage.from_("evidencias").upload(name, nueva_evid.getvalue())
                            nuevo_path = supabase.storage.from_("evidencias").get_public_url(name)

                        if img_com:
                            name = f"coment_{datetime.now().strftime('%H%M%S')}.png"
                            supabase.storage.from_("evidencias").upload(name, img_com.getvalue())
                            comentario_img_url = supabase.storage.from_("evidencias").get_public_url(name)

                        supabase.table("gestiones").update({
                            "fecha_atencion": f_at,
                            "comentarios": com,
                            "captura_path": nuevo_path,
                            "comentario_imagen": comentario_img_url
                        }).eq("id", row['id']).execute()

                        st.success("Actualizado 🚀")
                        st.rerun()

                # --- ELIMINAR ---
                with c3:
                    if st.button("Eliminar", key=f"del_{row['id']}"):
                        delete_record(row['id'])
                        st.rerun()

                # --- CORREO ---
                with c4:
                    asunto = f"Actualizar sistema operativo - {row['equipo']}"
                    cuerpo = f"Estimados,\n\nSolicito actualización del equipo {row['equipo']}."
                    mail_url = f"mailto:yaliaga@mincetur.gob.pe?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"

                    st.markdown(f'<a href="{mail_url}"><button style="width:100%">📧 Enviar</button></a>', unsafe_allow_html=True)

elif opcion == "GESTIÓN DE ...":
    st.subheader("Módulo en desarrollo...")

elif opcion == "GESTION DE...":
    st.subheader("Módulo en desarrollo...")
