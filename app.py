import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Sistema Resiliente - Gestión", layout="wide", page_icon="🛡️")

# --- CONFIGURACIÓN DE ZONA HORARIA ---
ZONA_HORARIA = pytz.timezone('America/Mexico_City')

def obtener_ahora_local():
    return datetime.now(ZONA_HORARIA)

# --- CARGA DE CONFIGURACIÓN ---
# Se asume que estos datos están en el panel de Secrets de Streamlit
try:
    API_BASE_URL = st.secrets["api"]["url"]
    API_KEY = st.secrets["api"]["key"]
    HEADERS = {"X-API-KEY": API_KEY}
except Exception:
    st.error("⚠️ Configuración incompleta en st.secrets. Verifique la sección [api].")
    st.stop()

# --- NÚCLEO DE COMUNICACIÓN CON FASTAPI ---
def peticion_api(endpoint, params=None, json_data=None, metodo="GET"):
    """Función centralizada para peticiones HTTP."""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if metodo == "POST":
            response = requests.post(url, headers=HEADERS, params=params, json=json_data, timeout=10)
        else:
            response = requests.get(url, headers=HEADERS, params=params, timeout=10)
            
        if response.status_code == 200:
            return response.json()
        else:
            error_msg = response.json().get('detail', 'Error desconocido')
            st.sidebar.error(f"Error {response.status_code}: {error_msg}")
            return None
    except Exception as e:
        st.sidebar.error(f"Fallo de conexión: {e}")
        return None

# --- SISTEMA DE AUTENTICACIÓN ---
def gestionar_login():
    """Maneja el estado de sesión y el formulario de acceso."""
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
            # --- Dentro de gestionar_login() ---
            if st.form_submit_button("Ingresar al Sistema"):
                # Limpiamos correo y password de espacios en blanco
                datos_login = {
                    "correo": correo.strip(), 
                    "password": password
                }
                res = peticion_api("/api/auth/login", json_data=datos_login, metodo="POST")
                
                if res and res.get("estado") == "Activo":
                    st.session_state["auth_user"] = res
                    st.rerun()
                elif res and res.get("estado") == "Inactivo":
                    st.error("🚫 Cuenta desactivada. Contacte soporte.")
                else:
                    st.error("Credenciales inválidas.")
    return False

# --- COMPONENTES DE LA INTERFAZ ---

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
                # .strip() elimina espacios accidentales al inicio o final
                payload = {
                    "nombre": n_nom.strip(), 
                    "correo": n_ema.strip(), 
                    "password": n_pas, # Ya no necesitas [:72]
                    "rol": n_rol
                }
                if peticion_api("/api/usuarios/registrar", json_data=payload, metodo="POST"):
                    st.success("Usuario dado de alta correctamente.")
    with t_lista:
        usuarios = peticion_api("/api/usuarios/listar")
        if usuarios:
            df_u = pd.DataFrame(usuarios)
            st.dataframe(df_u[["nombre", "correo", "rol", "estado"]], use_container_width=True)
            
            st.divider()
            st.subheader("Modificar Estado de Acceso")
            u_sel = st.selectbox("Seleccionar usuario:", df_u['correo'])
            nuevo_estado = st.radio("Nuevo estado:", ["Activo", "Inactivo"], horizontal=True)
            if st.button("Actualizar Usuario"):
                peticion_api("/api/usuarios/actualizar-estado", params={"correo": u_sel, "estado": nuevo_estado}, metodo="POST")
                st.rerun()

def modulo_dashboard(user_rol):
    st.title("📊 Panel de Control General")
    data = peticion_api("/api/admin/dashboard/resumen")
    if data:
        m1, m2, m3 = st.columns(3)
        m1.metric("Ventas Hoy", f"$ {data['ventas_hoy']:,.2f}")
        m2.metric("Alertas Stock", f"{data['alertas_count']} Prod.")
        m3.metric("Sesión Actual", user_rol)
        # Aquí podrías agregar el gráfico de Plotly que tenías originalmente

# --- CONSTRUCCIÓN DE LA APLICACIÓN ---

if gestionar_login():
    user = st.session_state["auth_user"]
    
    # Barra Lateral
    st.sidebar.title("🏪 Menú Principal")
    st.sidebar.markdown(f"Bienvenido, **{user['nombre']}**")
    st.sidebar.caption(f"Rol: {user['rol']}")
    
    # Lógica de Menú por Roles
    opciones = ["🏠 Dashboard General", "💰 Corte de Caja"]
    if user['rol'] == "Administrador":
        opciones.insert(1, "📦 Reabastecimiento")
        opciones.append("👥 Usuarios")
    
    menu = st.sidebar.radio("Navegar a:", opciones)
    
    st.sidebar.divider()
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state["auth_user"] = None
        st.rerun()

    # Despliegue de Módulos
    if menu == "🏠 Dashboard General":
        modulo_dashboard(user['rol'])
    
    elif menu == "👥 Usuarios":
        modulo_usuarios()
    
# --- MÓDULO: REABASTECIMIENTO (ADMIN) ---
    elif menu == "📦 Reabastecimiento":
        st.title("🚚 Gestión de Suministros")
        st.markdown("### Registrar Entrada de Mercancía")
        
        # Obtenemos productos y proveedores de la API
        productos = peticion_api("/listar_productos")
        proveedores = peticion_api("/api/admin/proveedores")
        
        if productos is not None and proveedores is not None:
            df_prod = pd.DataFrame(productos)
            df_prov = pd.DataFrame(proveedores)
            
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1:
                    prov_sel = st.selectbox("Seleccionar Proveedor", df_prov['nombre_empresa'])
                    prod_sel = st.selectbox("Producto a recibir", df_prod['nombre_producto'])
                
                # Extraemos datos del producto seleccionado
                prod_info = df_prod[df_prod['nombre_producto'] == prod_sel].iloc[0]
                cod_barras = prod_info['codigo_barras']
                
                with c2:
                    cantidad = st.number_input("Cantidad que ingresa", min_value=1, step=1)
                    costo_u = st.number_input("Costo Unitario de Compra ($)", min_value=0.0, value=float(prod_info['precio_compra']))
                
                total_compra = cantidad * costo_u
                st.metric("Inversión Total", f"$ {total_compra:,.2f}")
                
                if st.button("Confirmar Ingreso a Almacén", use_container_width=True):
                    # Creamos el diccionario con los nombres exactos que espera el modelo EntradaInventario
                    datos_entrada = {"codigo": cod_barras, "cantidad": cantidad}
                    
                    # Enviamos como JSON (asegúrate de que tu función peticion_api soporte el argumento 'json')
                    res = peticion_api("/api/admin/inventario/registrar-entrada", 
                                       json=datos_entrada, 
                                       metodo="POST")
                    if res:
                        st.success(f"✅ Inventario actualizado: +{cantidad} unidades de {prod_sel}")
                        st.balloons()
                    else:
                        st.warning("No se pudo cargar la lista de productos o proveedores.")

# --- MÓDULO: CORTE DE CAJA (AMBOS) ---
    elif menu == "💰 Corte de Caja":
        st.title("💸 Análisis de Ventas")
        
        # Selector de fecha para el corte
        fecha_corte = st.date_input("Seleccionar fecha de consulta", obtener_ahora_local())
        fecha_str = fecha_corte.strftime("%Y-%m-%d")
        
        # Llamada a la API para obtener los datos del reporte
        data_corte = peticion_api("/api/admin/reporte/corte-detallado", params={"fecha": fecha_str})
        
        if data_corte:
            # Métricas principales en tarjetas
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Ingresos Totales", f"$ {data_corte['ingresos']:,.2f}")
            with m2:
                # Solo el admin ve la ganancia neta
                if user['rol'] == "Administrador":
                    st.metric("Ganancia Neta", f"$ {data_corte['ganancia']:,.2f}", delta_color="normal")
                else:
                    st.metric("Estado", "Corte en Proceso")
            with m3:
                num_ventas = len(data_corte['detalles'])
                st.metric("Tickets Generados", f"{num_ventas} Ventas")
            
            st.divider()
            
            # Tabla detallada de movimientos
            if num_ventas > 0:
                st.subheader("📋 Detalle de Transacciones")
                df_ventas = pd.DataFrame(data_corte['detalles'])
                # Renombrar columnas para que se vea profesional
                df_ventas.columns = ['ID Venta', 'Total ($)', 'Hora de Registro']
                st.dataframe(df_ventas, use_container_width=True, hide_index=True)
            else:
                st.info(f"No se registraron ventas el día {fecha_str}")
        else:
            st.error("No se pudo obtener la información del servidor.")

    # Pie de página lateral
    st.sidebar.caption(f"🕒 {obtener_ahora_local().strftime('%d/%m/%Y %H:%M')}")




