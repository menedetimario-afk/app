import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Sistema Inventario", layout="wide", page_icon="🛡️")

# --- ZONA HORARIA ---
ZONA_HORARIA = pytz.timezone('America/Mexico_City')

def obtener_ahora_local():
    return datetime.now(ZONA_HORARIA)

# --- 2. CONFIGURACIÓN DE API ---
try:
    API_BASE_URL = st.secrets["api"]["url"].rstrip("/")
    API_KEY = st.secrets["api"]["key"]
    HEADERS = {"X-API-KEY": API_KEY}
except Exception:
    st.error("⚠️ Error en st.secrets: Verifica la sección [api] con 'url' y 'key'.")
    st.stop()

# --- 3. FUNCIÓN DE PETICIÓN ---
def peticion_api(endpoint, metodo="GET", params=None, json_data=None):
    url = f"{API_BASE_URL}/{endpoint.lstrip('/')}"
    try:
        if metodo == "GET":
            r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        else:
            r = requests.post(url, headers=HEADERS, json=json_data, timeout=10)
        
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None

# --- 4. SISTEMA DE AUTENTICACIÓN ---
def gestionar_login():
    if "auth_user" not in st.session_state:
        st.session_state["auth_user"] = None

    if st.session_state["auth_user"]:
        return True

    st.markdown("<br><h2 style='text-align: center;'>🔐 Acceso al Sistema</h2>", unsafe_allow_html=True)
    _, col_form, _ = st.columns([1, 1.2, 1])
    
    with col_form:
        with st.form("login_form"):
            correo = st.text_input("Correo Electrónico")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar al Sistema"):
                res = peticion_api("/api/auth/login", json_data={"correo": correo.strip(), "password": password}, metodo="POST")
                if res and res.get("estado") == "Activo":
                    st.session_state["auth_user"] = res
                    st.rerun()
                else:
                    st.error("Credenciales inválidas o cuenta inactiva.")
    return False

# --- 5. MÓDULOS DE LA INTERFAZ ---

def modulo_usuarios():
    st.title("👥 Administración de Personal")
    t_lista, t_registro = st.tabs(["📋 Lista de Usuarios", "➕ Registrar Nuevo"])

    with t_registro:
        with st.form("reg_user"):
            c1, c2 = st.columns(2)
            n_nom = c1.text_input("Nombre Completo")
            n_ema = c2.text_input("Correo Electrónico")
            n_pas = c1.text_input("Contraseña Temporal", type="password")
            n_rol = c2.selectbox("Rol de Usuario", ["Vendedor", "Administrador"])
            if st.form_submit_button("Confirmar Registro"):
                payload = {"nombre": n_nom.strip(), "correo": n_ema.strip(), "password": n_pas, "rol": n_rol}
                if peticion_api("/api/usuarios/registrar", json_data=payload, metodo="POST"):
                    st.success("Usuario dado de alta correctamente.")
                    st.rerun()

    with t_lista:
        usuarios = peticion_api("/api/usuarios/listar")
        if usuarios:
            df_u = pd.DataFrame(usuarios)
            st.dataframe(df_u[["nombre", "correo", "rol", "estado"]], use_container_width=True, hide_index=True)
            st.divider()
            st.subheader("Modificar Estado de Acceso")
            with st.container(border=True):
                u_sel = st.selectbox("Usuario:", df_u['correo'])
                nuevo_estado = st.radio("Nuevo estado:", ["Activo", "Inactivo"], horizontal=True)
                if st.button("Actualizar Estado"):
                    peticion_api("/api/usuarios/actualizar-estado", params={"correo": u_sel, "estado": nuevo_estado}, metodo="POST")
                    st.rerun()

def modulo_dashboard(rol):
    st.title("📊 Panel de Control General")
    res = peticion_api("/api/admin/dashboard/resumen")
    if res:
        m1, m2, m3 = st.columns(3)
        m1.metric("Ventas Hoy", f"$ {res['ventas_hoy']:,.2f}")
        m2.metric("Alertas Stock", f"{res['alertas_count']} Prod.")
        m3.metric("Rol", rol)

def modulo_reabastecimiento():
    st.title("🚚 Gestión de Suministros")
    t_en, t_su, t_np, t_pv = st.tabs(["📥 Entrada", "📋 Sugeridos", "✨ Nuevo Producto", "🤝 Proveedor"])
    
    with t_en:
        prods = peticion_api("/listar_productos")
        provs = peticion_api("/api/admin/proveedores")
        if prods and provs:
            df_p = pd.DataFrame(prods)
            df_v = pd.DataFrame(provs)
            p_sel = st.selectbox("Producto", df_p['nombre_producto'].unique())
            v_sel = st.selectbox("Proveedor", df_v['nombre_empresa'].unique())
            cant = st.number_input("Cantidad", min_value=1)
            info = df_p[df_p['nombre_producto'] == p_sel].iloc[0]
            if st.button("Confirmar Ingreso"):
                if peticion_api("/api/admin/inventario/registrar-entrada", metodo="POST", json_data={"codigo": str(info['codigo_barras']), "cantidad": int(cant)}):
                    st.success("Stock actualizado")

def modulo_ventas():
    st.title("🛒 Terminal de Ventas")
    if "carrito" not in st.session_state: st.session_state.carrito = []
    t_v, t_h = st.tabs(["🆕 Nueva Venta", "📜 Historial Hoy"])
    
    with t_v:
        prods = peticion_api("/listar_productos")
        if prods:
            df_p = pd.DataFrame(prods)
            p_sel = st.selectbox("Seleccione Producto", df_p['nombre_producto'].unique())
            info = df_p[df_p['nombre_producto'] == p_sel].iloc[0]
            cant = st.number_input("Cantidad", min_value=1, value=1)
            precio = float(info.get('precio_compra', 0)) # Ajustar a precio_venta si existe
            st.write(f"Precio: ${precio}")
            
            if st.button("➕ Agregar"):
                st.session_state.carrito.append({"codigo_barras": info['codigo_barras'], "nombre": p_sel, "cantidad": cant, "total": precio, "subtotal": cant * precio})
            
            if st.session_state.carrito:
                st.table(pd.DataFrame(st.session_state.carrito)[['nombre', 'cantidad', 'subtotal']])
                if st.button("✅ Confirmar Venta"):
                    total = sum(i['subtotal'] for i in st.session_state.carrito)
                    payload = {"id_venta": 0, "total": total, "productos": st.session_state.carrito, "fecha": obtener_ahora_local().strftime("%Y-%m-%d %H:%M:%S")}
                    if peticion_api("/api/ventas/registrar", metodo="POST", json_data=payload):
                        st.session_state.carrito = []; st.success("Venta Exitosa"); st.rerun()

def modulo_corte():
    st.title("💰 Corte de Caja")
    fecha = st.date_input("Fecha", obtener_ahora_local())
    res = peticion_api("/api/admin/reporte/corte-detallado", params={"fecha": fecha.strftime("%Y-%m-%d")})
    if res:
        c1, c2 = st.columns(2)
        c1.metric("Ingresos", f"$ {res.get('ingresos', 0):,.2f}")
        if st.session_state.auth_user['rol'] == "Administrador":
            c2.metric("Ganancia", f"$ {res.get('ganancia', 0):,.2f}")
        if res.get('detalles'):
            st.dataframe(pd.DataFrame(res['detalles']), use_container_width=True)

# --- 6. LÓGICA PRINCIPAL ---
if gestionar_login():
    user = st.session_state["auth_user"]
    st.sidebar.title("🏪 Menú Principal")
    st.sidebar.write(f"Usuario: {user['nombre']}")
    
    opciones = ["🏠 Dashboard", "🛒 Ventas", "💰 Corte de Caja"]
    if user['rol'] == "Administrador":
        opciones += ["📦 Reabastecimiento", "👥 Usuarios"]
    
    menu = st.sidebar.radio("Navegar a:", opciones)
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.auth_user = None; st.rerun()

    # Despliegue de Módulos
    if menu == "🏠 Dashboard": modulo_dashboard(user['rol'])
    elif menu == "🛒 Ventas": modulo_ventas()
    elif menu == "💰 Corte de Caja": modulo_corte()
    elif menu == "📦 Reabastecimiento": modulo_reabastecimiento()
    elif menu == "👥 Usuarios": modulo_usuarios()

    st.sidebar.divider()
    st.sidebar.caption(f"🕒 {obtener_ahora_local().strftime('%d/%m/%Y %H:%M')}")



