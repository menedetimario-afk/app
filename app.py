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
                payload = {
                    "nombre": n_nom.strip(), 
                    "correo": n_ema.strip(), 
                    "password": n_pas, 
                    "rol": n_rol
                }
                if peticion_api("/api/usuarios/registrar", json_data=payload, metodo="POST"):
                    st.success("Usuario dado de alta correctamente.")
                    st.rerun()

    with t_lista:
        usuarios = peticion_api("/api/usuarios/listar")
        if usuarios:
            df_u = pd.DataFrame(usuarios)
            # Mostramos la tabla principal
            st.dataframe(df_u[["nombre", "correo", "rol", "estado"]], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("Modificar Estado de Acceso")
            
            # Formulario pequeño para activar/desactivar
            with st.container(border=True):
                col_sel, col_est, col_btn = st.columns([2, 1, 1])
                
                with col_sel:
                    u_sel = st.selectbox("Seleccionar usuario por correo:", df_u['correo'])
                
                with col_est:
                    # Buscamos el estado actual para sugerir el cambio
                    estado_actual = df_u[df_u['correo'] == u_sel]['estado'].values[0]
                    opciones_estado = ["Activo", "Inactivo"]
                    # Ponemos primero la opción que NO tiene actualmente
                    nuevo_estado = st.radio("Nuevo estado:", opciones_estado, horizontal=True)
                
                with col_btn:
                    st.write("") # Espaciador para alinear el botón
                    st.write("") 
                    if st.button("Actualizar Estado", use_container_width=True):
                        # Enviamos por params como lo requiere tu API
                        res = peticion_api(
                            "/api/usuarios/actualizar-estado", 
                            params={"correo": u_sel, "estado": nuevo_estado}, 
                            metodo="POST"
                        )
                        st.success(f"Usuario {u_sel} actualizado a {nuevo_estado}")
                        st.rerun()
        else:
            st.info("No hay usuarios registrados en la base de datos.")

# --- 6. CONSTRUCCIÓN DE LA APP (Lógica Principal) ---

if gestionar_login():
    user = st.session_state["auth_user"]
    
    # Barra Lateral
    st.sidebar.title("🏪 Menú Principal")
    st.sidebar.markdown(f"Bienvenido, **{user['nombre']}**")
    
    # Opciones por Rol
    opciones = ["🏠 Dashboard General", "💰 Corte de Caja"]
    if user['rol'] == "Administrador":
        opciones.insert(1, "📦 Reabastecimiento")
        opciones.append("👥 Usuarios")
    
    menu = st.sidebar.radio("Navegar a:", opciones)
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["auth_user"] = None
        st.rerun()

    # --- DESPLIEGUE DE MÓDULOS (Todo dentro del bloque IF AUTH) ---
    if menu == "🏠 Dashboard General":
        modulo_dashboard(user['rol'])
    
    elif menu == "👥 Usuarios":
        modulo_usuarios()

    elif menu == "📦 Reabastecimiento":
        st.title("🚚 Gestión de Suministros")
        productos = peticion_api("/listar_productos")
        proveedores = peticion_api("/api/admin/proveedores")
        
        if productos and proveedores:
            df_prod = pd.DataFrame(productos)
            df_prov = pd.DataFrame(proveedores)
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1:
                    prov_sel = st.selectbox("Proveedor", df_prov['nombre_empresa'].unique())
                    prod_sel = st.selectbox("Producto", df_prod['nombre_producto'].unique())
                    info = df_prod[df_prod['nombre_producto'] == prod_sel].iloc[0]
                with c2:
                    cantidad = st.number_input("Cantidad", min_value=1, step=1)
                    costo_u = st.number_input("Costo Unitario ($)", value=float(info['precio_compra']))
                
                if st.button("Confirmar Ingreso", use_container_width=True):
                    payload = {"codigo": str(info['codigo_barras']), "cantidad": int(cantidad)}
                    if peticion_api("/api/admin/inventario/registrar-entrada", metodo="POST", json_data=payload):
                        st.success("✅ Stock actualizado")
                        st.balloons()
        else:
            st.warning("No hay productos o proveedores registrados.")

    elif menu == "💰 Corte de Caja":
        st.title("💸 Análisis de Ventas")
        fecha_corte = st.date_input("Seleccionar fecha", obtener_ahora_local())
        f_str = fecha_corte.strftime("%Y-%m-%d")
        
        data_corte = peticion_api("/api/admin/reporte/corte-detallado", params={"fecha": f_str})
        
        if data_corte:
            m1, m2, m3 = st.columns(3)
            m1.metric("Ingresos Totales", f"$ {data_corte.get('ingresos', 0):,.2f}")
            if user['rol'] == "Administrador":
                m2.metric("Ganancia Neta", f"$ {data_corte.get('ganancia', 0):,.2f}")
            
            detalles = data_corte.get('detalles', [])
            m3.metric("Tickets", f"{len(detalles)} Ventas")
            
            if detalles:
                st.divider()
                df_ventas = pd.DataFrame(detalles)
                if df_ventas.shape[1] >= 3:
                    df_ventas = df_ventas.iloc[:, :3]
                    df_ventas.columns = ['ID Venta', 'Total ($)', 'Hora de Registro']
                st.dataframe(df_ventas, use_container_width=True, hide_index=True)
            else:
                st.info("Sin ventas en esta fecha.")
        else:
            st.error("No se pudo conectar con la API.")

    st.sidebar.divider()
    st.sidebar.caption(f"🕒 {obtener_ahora_local().strftime('%d/%m/%Y %H:%M')}")



