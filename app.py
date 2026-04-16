import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
import pytz
import plotly.express as px

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
def peticion_api(endpoint, metodo="GET", json=None):
    # Sustituye con tu URL real de Railway
    url = f"https://tu-app-railway.app{endpoint}" 
    headers = {"X-API-KEY": st.secrets["API_SECRET_KEY"]}
    
    try:
        if metodo == "GET":
            response = requests.get(url, headers=headers)
        else:
            response = requests.post(url, headers=headers, json=json)
        
        if response.status_code == 200:
            return response.json()
        return None
    except:
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
    
    # 1. Obtener métricas rápidas
    data_resumen = peticion_api("/api/admin/dashboard/resumen")
    
    if data_resumen:
        m1, m2, m3 = st.columns(3)
        m1.metric("Ventas Hoy", f"$ {data_resumen['ventas_hoy']:,.2f}")
        m2.metric("Alertas Stock", f"{data_resumen['alertas_count']} Prod.")
        m3.metric("Sesión Actual", user_rol)
        
        st.divider()
        
        # 2. Obtener datos para el gráfico
        st.subheader("📈 Tendencia de Ventas (Últimos 7 días)")
        data_grafico = peticion_api("/api/admin/dashboard/grafico-ventas")
        
        if data_grafico:
            df_grafico = pd.DataFrame(data_grafico)
            
            # Crear el gráfico con Plotly
            fig = px.line(
                df_grafico, 
                x='fecha', 
                y='total_dia',
                labels={'fecha': 'Fecha', 'total_dia': 'Ventas ($)'},
                markers=True,
                template="plotly_dark" # Opcional: estilo oscuro
            )
            
            # Personalizar colores del área y la línea
            fig.update_traces(line_color='#00d1b2', line_width=3, fill='tozeroy')
            fig.update_layout(
                hovermode="x unified",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay suficientes datos históricos para mostrar el gráfico aún.")
            
    else:
        st.error("No se pudo cargar el resumen del dashboard.")

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
    
    productos = peticion_api("/listar_productos")
    proveedores = peticion_api("/api/admin/proveedores")
    
    # Validamos que la respuesta sea una lista y no un error
    if isinstance(productos, list) and isinstance(proveedores, list):
        if len(productos) > 0 and len(proveedores) > 0:
            df_prod = pd.DataFrame(productos)
            df_prov = pd.DataFrame(proveedores)
            
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1:
                    prov_sel = st.selectbox("Seleccionar Proveedor", df_prov['nombre_empresa'].unique())
                    prod_sel = st.selectbox("Producto a recibir", df_prod['nombre_producto'].unique())
                
                # Extraemos info del producto seleccionado
                prod_info = df_prod[df_prod['nombre_producto'] == prod_sel].iloc[0]
                cod_barras = prod_info['codigo_barras']
                
                with c2:
                    cantidad = st.number_input("Cantidad que ingresa", min_value=1, step=1)
                    # Tomamos el precio de compra actual como sugerencia
                    costo_u = st.number_input("Costo Unitario ($)", min_value=0.0, value=float(prod_info['precio_compra']))
                
                total_compra = cantidad * costo_u
                st.metric("Inversión Total", f"$ {total_compra:,.2f}")
                
                if st.button("Confirmar Ingreso a Almacén", use_container_width=True):
                    datos_entrada = {"codigo": str(cod_barras), "cantidad": int(cantidad)}
                    
                    res = peticion_api("/api/admin/inventario/registrar-entrada", 
                                       metodo="POST", 
                                       json=datos_entrada)
                    
                    if res:
                        st.success(f"✅ Stock actualizado: {prod_sel} (+{cantidad})")
                        st.balloons()
                    else:
                        st.error("Hubo un problema al actualizar el inventario.")
        else:
            st.warning("⚠️ No hay productos o proveedores registrados en el sistema.")
    else:
        st.error("❌ No se pudo conectar con la base de datos. Verifica la API KEY.")
        
elif menu == "💰 Corte de Caja":
    st.title("💸 Análisis de Ventas")
    
    fecha_corte = st.date_input("Seleccionar fecha de consulta", obtener_ahora_local())
    fecha_str = fecha_corte.strftime("%Y-%m-%d")
    
    # IMPORTANTE: Asegúrate de pasar 'fecha_str' como un parámetro de consulta (query param)
    data_corte = peticion_api("/api/admin/reporte/corte-detallado", params={"fecha": fecha_str})
    
    if data_corte:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Ingresos Totales", f"$ {data_corte['ingresos']:,.2f}")
        with m2:
            if st.session_state.rol == "Administrador":
                st.metric("Ganancia Neta", f"$ {data_corte['ganancia']:,.2f}")
            else:
                st.metric("Estado", "Corte en Proceso")
        with m3:
            num_ventas = len(data_corte['detalles'])
            st.metric("Tickets Generados", f"{num_ventas} Ventas")
        
        st.divider()
        
        if num_ventas > 0:
            st.subheader("📋 Detalle de Transacciones")
            df_ventas = pd.DataFrame(data_corte['detalles'])
            
            # BLINDAJE: Si por alguna razón el SQL trae más o menos columnas, esto evita el error:
            if df_ventas.shape[1] == 3:
                df_ventas.columns = ['ID Venta', 'Total ($)', 'Hora de Registro']
            
            st.dataframe(df_ventas, use_container_width=True, hide_index=True)
        else:
            st.info(f"No se registraron ventas el día {fecha_str}")
    else:
        st.error("🚫 Error 404 o 403: No se pudo obtener la información. Verifica la URL de la API.")

    # Pie de página lateral
    st.sidebar.caption(f"🕒 {obtener_ahora_local().strftime('%d/%m/%Y %H:%M')}")




