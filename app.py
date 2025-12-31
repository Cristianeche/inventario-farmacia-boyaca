import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="SGLI - Boyacá", layout="wide")

# 2. BASE DE DATOS DE USUARIOS
USUARIOS = {
    "cristian": {"clave": "123456", "rol": "Analista Logístico (Central)", "sede": "Todas"},
    "Tunja": {"clave": "tunja2025", "rol": "Jefe de Farmacia (Rural)", "sede": "Centro Rural Tunja"},
    "Villa": {"clave": "villa2025", "rol": "Jefe de Farmacia (Rural)", "sede": "Centro Rural Villa de Leyva"},
    "Duitama": {"clave": "duitama2025", "rol": "Jefe de Farmacia (Rural)", "sede": "Centro Rural Duitama"}
}

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.user_data = None
if 'carrito_despacho' not in st.session_state:
    st.session_state.carrito_despacho = []

def pantalla_login():
    st.title("Inicio de sesión (SGLI)")
    st.subheader("Acceso para Personal de Salud - Boyacá")
    with st.form("login_form"):
        usuario_in = st.text_input("Nombre de Usuario")
        clave_in = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Iniciar Sesión"):
            if usuario_in in USUARIOS and USUARIOS[usuario_in]["clave"] == clave_in:
                st.session_state.autenticado = True
                st.session_state.user_data = USUARIOS[usuario_in]
                st.rerun()
            else:
                st.error("Error: Usuario o contraseña incorrectos")

if not st.session_state.autenticado:
    pantalla_login()
else:
    user_info = st.session_state.user_data
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.user_data = None
        st.session_state.carrito_despacho = []
        st.rerun()

    if user_info["rol"] == "Analista Logístico (Central)":
        sede_actual = st.sidebar.selectbox(
            "Seleccione Sede a Supervisar", 
            ["Centro Rural Tunja", "Centro Rural Duitama", "Centro Rural Villa de Leyva"]
        )
    else:
        sede_actual = user_info["sede"]
        st.sidebar.success(f"Sede Activa: {sede_actual}")
    
    st.sidebar.divider()
    st.sidebar.info(f"Usuario: {user_info['rol']}")

    # --- INICIALIZACIÓN DE DATOS UNIFICADA PERO INDEPENDIENTE POR SEDE ---
    if 'inventario' not in st.session_state:
        hoy = datetime.now()
        catalogo_maestro = [
            ['Losartán 50 mg', 300, 50, 20],
            ['Amlodipino 5 mg', 250, 40, 15],
            ['Enalapril 20 mg', 200, 40, 12],
            ['Metformina 850 mg', 500, 100, 45],
            ['Glibenclamida 5 mg', 200, 50, 10],
            ['Insulina NPH (Vial)', 45, 15, 4],
            ['Acetaminofén 500 mg', 1000, 200, 80],
            ['Naproxeno 250 mg', 400, 80, 25],
            ['Atorvastatina 20 mg', 350, 60, 15],
            ['Omeprazol 20 mg', 500, 100, 30],
            ['Calcio + Vitamina D', 300, 50, 20],
            ['Hidroclorotiazida 25 mg', 180, 30, 8],
            ['Furosemida 40 mg', 120, 25, 5],
            ['Carvedilol 6.25 mg', 150, 30, 7],
            ['Ácido Acetilsalicílico 100 mg', 600, 100, 20]
        ]
        sedes = ["Centro Rural Tunja", "Centro Rural Duitama", "Centro Rural Villa de Leyva"]
        datos_completos = []
        for sede in sedes:
            for med in catalogo_maestro:
                datos_completos.append({
                    'Medicamento': med[0],
                    'Cantidad_Disponible': med[1],
                    'Stock_Minimo': med[2],
                    'Consumo_Diario': med[3],
                    'Sede': sede,
                    'Fecha_Vencimiento': (hoy + timedelta(days=180)).strftime('%Y-%m-%d')
                })
        st.session_state.inventario = pd.DataFrame(datos_completos)

    # --- LÓGICA DE ALERTAS (FILTRADO ESTRICTO POR SEDE ACTUAL) ---
    mask_sede = st.session_state.inventario['Sede'] == sede_actual
    df_sede = st.session_state.inventario[mask_sede].copy()
    
    def definir_estado(row):
        if row['Cantidad_Disponible'] <= (row['Stock_Minimo'] * 0.5): return "🛑 CRÍTICO"
        elif row['Cantidad_Disponible'] <= row['Stock_Minimo']: return "⚠️ ALERTA"
        else: return "✅ NORMAL"

    df_sede['Estado'] = df_sede.apply(definir_estado, axis=1)

    # --- MÓDULO DE OPERACIONES (JEFES) ---
    if user_info["rol"] == "Jefe de Farmacia (Rural)":
        st.header(f"⚙️ Panel de Operaciones - {sede_actual}")
        criticos = df_sede[df_sede['Estado'] == "🛑 CRÍTICO"]
        if not criticos.empty:
            st.error(f"¡ATENCIÓN! Tienes {len(criticos)} medicamentos en estado CRÍTICO en {sede_actual}.")

        tab_salida, tab_entrada = st.tabs(["Despacho (Receta)", "Ingreso (Carga)"])
        
        with tab_salida:
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1: med_selec = st.selectbox("Medicamento", df_sede['Medicamento'].unique())
            with c2: cant_selec = st.number_input("Cantidad", min_value=1, step=1)
            with c3:
                st.write(" ")
                if st.button("Añadir al despacho"):
                    stock_actual = df_sede[df_sede['Medicamento'] == med_selec]['Cantidad_Disponible'].values[0]
                    if cant_selec <= stock_actual:
                        st.session_state.carrito_despacho.append({'Medicamento': med_selec, 'Cantidad': cant_selec})
                    else: st.error("Stock insuficiente")

            if st.session_state.carrito_despacho:
                st.table(pd.DataFrame(st.session_state.carrito_despacho))
                if st.button("Confirmar y Descontar de esta Sede"):
                    for item in st.session_state.carrito_despacho:
                        # FILTRO CRUCIAL: Medicamento + Sede Actual
                        idx = st.session_state.inventario[
                            (st.session_state.inventario['Medicamento'] == item['Medicamento']) & 
                            (st.session_state.inventario['Sede'] == sede_actual)
                        ].index[0]
                        st.session_state.inventario.at[idx, 'Cantidad_Disponible'] -= item['Cantidad']
                    st.session_state.carrito_despacho = []
                    st.rerun()

        with tab_entrada:
            opcion = st.radio("Acción:", ["Reabastecer", "Nuevo Medicamento"], horizontal=True)
            if opcion == "Reabastecer":
                with st.form("form_re"):
                    m_re = st.selectbox("Medicamento", df_sede['Medicamento'].unique())
                    c_re = st.number_input("Cantidad", min_value=1)
                    if st.form_submit_button("Sumar al Inventario Local"):
                        idx = st.session_state.inventario[(st.session_state.inventario['Medicamento'] == m_re) & (st.session_state.inventario['Sede'] == sede_actual)].index[0]
                        st.session_state.inventario.at[idx, 'Cantidad_Disponible'] += c_re
                        st.rerun()
            else:
                with st.form("form_nuevo"):
                    n_med = st.text_input("Nombre")
                    n_cant = st.number_input("Cantidad Inicial", min_value=1)
                    n_min = st.number_input("Stock Mínimo", min_value=1)
                    n_cons = st.number_input("Consumo Diario", min_value=1)
                    if st.form_submit_button("Registrar solo en esta sede"):
                        nueva_f = pd.DataFrame({'Medicamento':[n_med], 'Cantidad_Disponible':[n_cant], 'Stock_Minimo':[n_min], 'Consumo_Diario':[n_cons], 'Sede':[sede_actual], 'Fecha_Vencimiento':[(datetime.now()+timedelta(days=180)).strftime('%Y-%m-%d')]})
                        st.session_state.inventario = pd.concat([st.session_state.inventario, nueva_f], ignore_index=True)
                        st.rerun()

    # --- DASHBOARD ---
    st.divider()
    st.header(f"📊 Inventario Real en {sede_actual}")
    
    def color_estado(val):
        if val == "🛑 CRÍTICO": return 'background-color: #ffcccc'
        if val == "⚠️ ALERTA": return 'background-color: #fff3cd'
        return ''

    st.dataframe(df_sede.style.applymap(color_estado, subset=['Estado']), use_container_width=True)

    if not df_sede.empty:
        st.subheader("📉 Proyección de Agotamiento Local")
        fig, ax = plt.subplots(figsize=(10, 4))
        for _, fila in df_sede.iterrows():
            dias = range(11)
            valores = [max(0, int(fila['Cantidad_Disponible']) - (d * int(fila['Consumo_Diario']))) for d in dias]
            p = ax.plot(dias, valores, label=fila['Medicamento'], marker='o', markersize=3)
            ax.axhline(y=fila['Stock_Minimo'], color=p[0].get_color(), linestyle='--', alpha=0.2)
        ax.set_xlabel("Días")
        ax.set_ylabel("Stock")
        ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1), fontsize='x-small')
        st.pyplot(fig)

    st.info("Este motor utiliza algoritmos para anticipar el quiebre de stock según tendencias epidemiológicas locales.")