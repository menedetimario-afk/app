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
    opciones = ["🏠 Dashboard General", "🛒 Ventas", "💰 Corte de Caja"]
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
    st.title("🚚 Gestión de Suministros y Proveedores")
    
    # Creamos pestañas para organizar las opciones que pediste
    t_entrada, t_sugeridos, t_nuevo_prod, t_nuevo_prov = st.tabs([
        "📥 Insertar Entrada", 
        "📋 Pedidos Sugeridos", 
        "✨ Crear Producto", 
        "🤝 Crear Proveedor"
    ])

    # --- 1. INSERTAR ENTRADA (STOCK) ---
    with t_entrada:
        st.subheader("Registrar Ingreso de Mercancía")
        productos = peticion_api("/listar_productos")
        proveedores = peticion_api("/api/admin/proveedores")
        
        if productos and proveedores:
            df_p = pd.DataFrame(productos)
            df_prov = pd.DataFrame(proveedores)
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1:
                    prov_sel = st.selectbox("Proveedor que entrega", df_prov['nombre_empresa'].unique(), key="re_prov")
                    prod_sel = st.selectbox("Producto a recibir", df_p['nombre_producto'].unique(), key="re_prod")
                    info = df_p[df_p['nombre_producto'] == prod_sel].iloc[0]
                with c2:
                    cantidad = st.number_input("Cantidad", min_value=1, step=1, key="re_cant")
                    costo_u = st.number_input("Costo Unitario ($)", value=float(info['precio_compra']), key="re_costo")
                
                if st.button("Confirmar Ingreso de Stock", use_container_width=True):
                    payload = {"codigo": str(info['codigo_barras']), "cantidad": int(cantidad)}
                    if peticion_api("/api/admin/inventario/registrar-entrada", metodo="POST", json_data=payload):
                        st.success(f"✅ Se agregaron {cantidad} unidades a {prod_sel}")
                        st.balloons()
        else:
            st.warning("Faltan productos o proveedores para registrar entradas.")

    # --- 2. PEDIDOS SUGERIDOS (STOCK BAJO) ---
    with t_sugeridos:
        st.subheader("Productos por debajo del Stock Mínimo")
        # Usamos el endpoint de dashboard que ya cuenta las alertas
        resumen = peticion_api("/api/admin/dashboard/resumen")
        prods_todos = peticion_api("/listar_productos")
        
        if prods_todos:
            df_todos = pd.DataFrame(prods_todos)
            # Filtramos localmente los que tienen existencias <= stock_minimo (si tienes esa columna)
            # Si no, mostramos los que tienen menos de 5 unidades como sugerencia
            bajo_stock = df_todos[df_todos['existencias'] <= 5] 
            
            if not bajo_stock.empty:
                st.warning(f"Hay {len(bajo_stock)} productos que necesitan reabastecimiento urgente.")
                st.dataframe(bajo_stock[['nombre_producto', 'existencias', 'precio_compra']], use_container_width=True)
            else:
                st.success("✅ El inventario está en niveles óptimos.")

    # --- 3. CREAR PRODUCTO NUEVO ---
    with t_nuevo_prod:
        st.subheader("Dar de alta nuevo producto")
        if proveedores:
            df_prov = pd.DataFrame(proveedores)
            with st.form("form_nuevo_prod"):
                f1, f2 = st.columns(2)
                f_cod = f1.text_input("Código de Barras")
                f_nom = f2.text_input("Nombre del Producto")
                f_pre_v = f1.number_input("Precio Venta", min_value=0.0)
                f_pre_c = f2.number_input("Precio Compra", min_value=0.0)
                f_stock = f1.number_input("Stock Inicial", min_value=0)
                f_min = f2.number_input("Stock Mínimo", min_value=1)
                f_prov_id = st.selectbox("Proveedor", df_prov['nombre_empresa'].unique())
                
                id_p = df_prov[df_prov['nombre_empresa'] == f_prov_id]['id_proveedor'].values[0]
                
                if st.form_submit_button("Guardar Producto"):
                    p_load = {
                        "codigo": f_cod, "nombre": f_nom, "stock": int(f_stock),
                        "minimo": int(f_min), "id_prov": int(id_p), 
                        "precio": float(f_pre_v), "precio_c": float(f_pre_c)
                    }
                    if peticion_api("/api/admin/inventario/crear-producto", metodo="POST", json_data=p_load):
                        st.success("Producto creado exitosamente")
                        st.rerun()

    # --- 4. CREAR PROVEEDOR ---
    with t_nuevo_prov:
        st.subheader("Registro de Proveedores")
        with st.form("form_prov"):
            pr_nom = st.text_input("Nombre de la Empresa / Proveedor")
            pr_con = st.text_input("Nombre del Contacto")
            pr_tel = st.text_input("Teléfono")
            
            if st.form_submit_button("Registrar Proveedor"):
                # Enviamos por parámetros como lo pide tu endpoint
                if peticion_api("/api/admin/proveedores/crear", metodo="POST", 
                                params={"nombre": pr_nom, "contacto": pr_con, "tel": pr_tel}):
                    st.success("Proveedor guardado")
                    st.rerun()

def modulo_ventas():
    # Esta línea DEBE tener 4 espacios de sangría respecto al 'def'
    st.title("🛒 Terminal de Ventas")
    
    # Inicializar el "carrito" en la sesión si no existe
    if "carrito" not in st.session_state:
        st.session_state.carrito = []

    t_venta, t_historial = st.tabs(["🆕 Nueva Venta", "📜 Historial Reciente"])

    with t_venta:
        productos = peticion_api("/listar_productos")
        if productos:
            df_p = pd.DataFrame(productos)
            
            # --- SELECCIÓN DE PRODUCTOS ---
            with st.expander("Añadir Productos", expanded=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    p_nombre = st.selectbox("Seleccione Producto", df_p['nombre_producto'].unique())
                    # Filtrar info del producto seleccionado
                    info = df_p[df_p['nombre_producto'] == p_nombre].iloc[0]
                with c2:
                    cant = st.number_input("Cantidad", min_value=1, value=1, key="cant_v")
                with c3:
                    st.write("Precio Unit.")
                    # Usamos precio_compra si no tienes precio_venta en tu tabla
                    precio_u = float(info.get('precio_compra', 0))
                    st.subheader(f"${precio_u:,.2f}")

                if st.button("➕ Agregar al Carrito", use_container_width=True):
                    item = {
                        "codigo_barras": info['codigo_barras'],
                        "nombre": p_nombre,
                        "cantidad": cant,
                        "total": precio_u, # El backend espera 'total' por cada item
                        "subtotal": cant * precio_u
                    }
                    st.session_state.carrito.append(item)
                    st.toast(f"Agregado: {p_nombre}")

            # --- VISUALIZACIÓN DEL CARRITO ---
            if st.session_state.carrito:
                st.divider()
                df_carrito = pd.DataFrame(st.session_state.carrito)
                st.table(df_carrito[['nombre', 'cantidad', 'total', 'subtotal']])
                
                total_venta = df_carrito['subtotal'].sum()
                st.subheader(f"Total a Pagar: ${total_venta:,.2f}")

                col_v1, col_v2 = st.columns(2)
                if col_v1.button("🗑️ Vaciar Carrito", use_container_width=True):
                    st.session_state.carrito = []
                    st.rerun()

                if col_v2.button("✅ Confirmar Venta", type="primary", use_container_width=True):
                    payload = {
                        "id_venta": 0, 
                        "total": float(total_venta),
                        "fecha": obtener_ahora_local().strftime("%Y-%m-%d %H:%M:%S"),
                        "productos": st.session_state.carrito
                    }
                    # Asegúrate de que el endpoint sea el correcto en tu FastAPI
                    if peticion_api("/api/ventas/registrar", metodo="POST", json_data=payload):
                        st.success("¡Venta realizada con éxito!")
                        st.session_state.carrito = []
                        st.balloons()
                        st.rerun()
            else:
                st.info("El carrito está vacío. Agrega productos arriba.")

    with t_historial:
        st.subheader("Ventas del día de hoy")
        hoy = obtener_ahora_local().strftime("%Y-%m-%d")
        # Usamos el endpoint de historial que ya tienes en el backend
        historial = peticion_api("/api/admin/historial/ventas", params={"inicio": hoy, "fin": hoy})
        if historial:
            st.dataframe(pd.DataFrame(historial), use_container_width=True, hide_index=True)
        else:
            st.write("No se han registrado ventas hoy.")
            
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



