import streamlit as st
import pandas as pd
import os
import urllib.parse
from datetime import datetime
from io import BytesIO
from PIL import Image
from supabase import create_client, Client

# --- CONFIGURACIÓN DE SUPABASE ---
# Configura estos valores en el panel de Streamlit Cloud (Settings > Secrets)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Control de Seguridad Digital",
    layout="wide",
    page_icon="🛡️"
)

# --- ESTILOS ---
st.markdown("""
<style>
body { background-color: #F4F6F9; }
.main-title {
    font-size: 32px; font-weight: 700; color: white;
    background: linear-gradient(90deg, #0E4667, #1C7ED6);
    padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 25px;
}
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0E4667, #1C7ED6); }
[data-testid="stSidebar"] * { color: white !important; }
.stButton>button {
    width: 100%; border-radius: 8px;
    background: linear-gradient(90deg, #1C7ED6, #0E4667); color: white;
}
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE BASE DE DATOS (SUPABASE) ---

def get_data():
    response = supabase.table("gestiones").select("*").order("id").execute()
    return pd.DataFrame(response.data)

def save_record(equipo, usuario, fecha_reporte, file):
    path_publico = ""
    if file:
        file_name = f"{equipo}_{datetime.now().strftime('%H%M%S')}.png"
        # Subir a bucket 'evidencias'
        supabase.storage.from_("evidencias").upload(file_name, file.getbuffer())
        path_publico = supabase.storage.from_("evidencias").get_public_url(file_name)
    
    data = {
        "equipo": equipo,
        "usuario": usuario,
        "fecha_reporte": fecha_reporte,
        "captura_path": path_publico,
        "fecha_atencion": "",
        "comentarios": ""
    }
    supabase.table("gestiones").insert(data).execute()

def update_full_db(id_reg, f_atencion, comentario):
    supabase.table("gestiones").update({
        "fecha_atencion": f_atencion,
        "comentarios": comentario
    }).eq("id", id_reg).execute()

def delete_record(id_reg):
    supabase.table("gestiones").delete().eq("id", id_reg).execute()

# --- EXPORTACIÓN ---
def exportar_excel_pro(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')
        # (Nota: La inserción de imágenes de URL a Excel requiere descarga previa, 
        # para este entorno web, exportamos el reporte con los links directos)
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

st.markdown('<div class="main-title">🛡️ CONTROLES DE SEGURIDAD DIGITAL</div>', unsafe_allow_html=True)

if opcion == "GESTIÓN DE VULNERABILIDADES TÉCNICAS":
    col_izq, col_der = st.columns([1, 2.2])

    # -------- IZQUIERDA (Registro y Dashboard) --------
    with col_izq:
        st.markdown("### 📝 Registro")
        with st.form("nuevo", clear_on_submit=True):
            eq = st.text_input("Equipo")
            us = st.text_input("Usuario")
            f_r = st.date_input("Fecha Reporte", datetime.now())
            evid = st.file_uploader("Evidencia", type=['png', 'jpg'])
            
            if st.form_submit_button("💾 Guardar"):
                if eq and us:
                    save_record(eq, us, f_r.strftime("%Y-%m-%d"), evid)
                    st.success("Guardado en la nube ✅")
                    st.rerun()

        st.markdown("### 📊 Dashboard")
        df_dash = get_data()
        if not df_dash.empty:
            total = len(df_dash)
            atendidos = df_dash[df_dash["fecha_atencion"] != ""].shape[0]
            pendientes = df_dash[df_dash["fecha_atencion"] == ""].shape[0]

            d1, d2, d3 = st.columns(3)
            d1.metric("Total", total)
            d2.metric("Atendidos", atendidos)
            d3.metric("Pendientes", pendientes)

            st.bar_chart(pd.DataFrame({
                "Estado": ["Atendidos", "Pendientes"],
                "Cantidad": [atendidos, pendientes]
            }).set_index("Estado"))
        else:
            st.info("Sin datos")

    # -------- DERECHA (Seguimiento) --------
    with col_der:
        st.markdown("### 📋 Seguimiento")
        df_db = get_data()

        if not df_db.empty:
            for _, row in df_db.iterrows():
                estado = "🟢 Atendido" if row['fecha_atencion'] else "🔴 Pendiente"
                with st.expander(f"{row['equipo']} | {row['usuario']} | {estado}"):
                    c1, c2, c3, c4 = st.columns([1.5, 2, 1, 1.2])
                    
                    with c1:
                        if row['captura_path']:
                            st.image(row['captura_path'], use_container_width=True)
                        st.caption("Evidencia en la nube")

                    with c2:
                        st.text_input("Fecha Reporte", value=row['fecha_reporte'], disabled=True, key=f"fr_{row['id']}")
                        f_at = st.text_input("Fecha Atención", value=row['fecha_atencion'], key=f"f_{row['id']}")
                        com = st.text_area("Comentarios", value=row['comentarios'], key=f"c_{row['id']}")
                        if st.button("Guardar", key=f"b_{row['id']}"):
                            update_full_db(row['id'], f_at, com)
                            st.rerun()

                    with c3:
                        if st.button("Eliminar", key=f"del_{row['id']}"):
                            delete_record(row['id'])
                            st.rerun()

                    with c4:
                        asunto = f"Actualizar sistema operativo - {row['equipo']}"
                        cuerpo = f"Estimados Señores,\n\nPor apoyo en la actualización del sistema operativo del equipo {row['equipo']} de Windows 10 a Windows 11..."
                        mail_url = f"mailto:yaliaga@mincetur.gob.pe?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
                        st.markdown(f'<a href="{mail_url}" target="_blank"><button style="width:100%; padding:8px; border-radius:8px; border:none; background:linear-gradient(90deg, #28a745, #218838); color:white; font-weight:600; cursor:pointer;">📧 Enviar Correo</button></a>', unsafe_allow_html=True)

            st.divider()
            excel = exportar_excel_pro(df_db)
            st.download_button("📥 Descargar Reporte Excel", excel, "reporte_seguridad.xlsx")
        else:
            st.info("No hay datos")

elif opcion in ["GESTIÓN DE ...", "GESTION DE..."]:
    st.subheader("En proceso")
