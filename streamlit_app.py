import streamlit as st
import pandas as pd
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

# --- FUNCIONES DE BASE DE DATOS ---
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
        "comentarios": ""
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

    # IZQUIERDA
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
                    st.warning("Complete Equipo y Usuario")

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

    # DERECHA
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
                        if row['captura_path']:
                            st.image(row['captura_path'], use_container_width=True)
                        else:
                            st.info("Sin imagen")

                        nueva_evid = st.file_uploader("Actualizar Imagen", type=['png','jpg','jpeg'], key=f"upd_{row['id']}")

                    with c2:
                        st.text_input("Fecha Reporte", value=row['fecha_reporte'], disabled=True, key=f"fr_{row['id']}")
                        f_at = st.text_input("Fecha Atención", value=f_at_val, key=f"f_{row['id']}")

                        com = st.text_area("Comentarios", value=row['comentarios'] or "", key=f"c_{row['id']}")

                        # subir imagen en comentario
                        img_com = st.file_uploader("Adjuntar imagen en comentario", type=['png','jpg','jpeg'], key=f"img_{row['id']}")

                        # PREVISUALIZACIÓN
                        if row['comentarios'] and "http" in row['comentarios']:
                            try:
                                url = row['comentarios'].split("Imagen: ")[-1].strip()
                                st.image(url, caption="Imagen del comentario", use_container_width=True)
                            except:
                                pass

                        if st.button("Actualizar Todo", key=f"btn_{row['id']}"):

                            nuevo_path = row['captura_path']

                            if nueva_evid:
                                file_name = f"{row['equipo']}_{datetime.now().strftime('%H%M%S')}.jpg"
                                file_bytes = nueva_evid.getvalue()
                                supabase.storage.from_("evidencias").upload(file_name, file_bytes)
                                nuevo_path = supabase.storage.from_("evidencias").get_public_url(file_name)

                            comentario_final = com

                            if img_com:
                                file_name = f"coment_{row['id']}_{datetime.now().strftime('%H%M%S')}.jpg"
                                file_bytes = img_com.getvalue()
                                supabase.storage.from_("evidencias").upload(file_name, file_bytes)
                                url = supabase.storage.from_("evidencias").get_public_url(file_name)
                                comentario_final = f"{com}\n\n📎 Imagen: {url}"

                            supabase.table("gestiones").update({
                                "fecha_atencion": f_at,
                                "comentarios": comentario_final,
                                "captura_path": nuevo_path
                            }).eq("id", row['id']).execute()

                            st.success("Actualizado")
                            st.rerun()

                    with c3:
                        if st.button("Eliminar", key=f"del_{row['id']}"):
                            delete_record(row['id'])
                            st.rerun()

                    with c4:
                        asunto = f"Actualizar sistema operativo - {row['equipo']}"
                        cuerpo = f"Solicito actualizar equipo {row['equipo']}"
                        url = f"mailto:yaliaga@mincetur.gob.pe?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
                        st.markdown(f'<a href="{url}"><button style="width:100%">📧 Enviar Correo</button></a>', unsafe_allow_html=True)

elif opcion == "GESTIÓN DE ...":
    st.subheader("Módulo en desarrollo...")

elif opcion == "GESTION DE...":
    st.subheader("Módulo en desarrollo...")
