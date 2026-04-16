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
        if metodo == "GET": r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        elif metodo == "POST": r = requests.post(url, headers=HEADERS, json=json_data, timeout=10)
        elif metodo == "PUT": r = requests.put(url, headers=HEADERS, timeout=10) # Añadir esta
        elif metodo == "DELETE": r = requests.delete(url, headers=HEADERS, timeout=10) # Añadir esta
        
        if r.status_code == 200: return r.json()
        else:
            st.error(f"Error {r.status_code}: {r.text}")
            return None
    except Exception as e:
        st.error(f"Error de conexión: {e}")
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
    st.title("👥 Gestión de Personal")
    
    t_registro, t_lista = st.tabs(["🆕 Registrar Usuario", "📋 Lista de Usuarios"])
    
    with t_registro:
        st.subheader("Crear nueva cuenta")
        with st.form("form_registro_usuario", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre Completo")
            correo = col2.text_input("Correo Electrónico")
            
            password = col1.text_input("Contraseña Temporal", type="password")
            rol = col2.selectbox("Rol del Usuario", ["Administrador","Vendedor"])
            
            submit = st.form_submit_button("🚀 Crear Usuario", use_container_width=True)
            
            if submit:
                if nombre and correo and password:
                    payload = {
                        "nombre": nombre,
                        "correo": correo,
                        "password": password,
                        "rol": rol
                    }
                    # Llamada a la API
                    res = peticion_api("/api/usuarios/registrar", metodo="POST", json_data=payload)
                    
                    if res:
                        st.success(f"✅ ¡Éxito! El usuario **{nombre}** ha sido registrado como **{rol}**.")
                        # No hacemos rerun inmediato para que el usuario alcance a leer el mensaje
                    else:
                        st.error("❌ No se pudo registrar el usuario. Verifica si el correo ya existe.")
                else:
                    st.warning("⚠️ Por favor, rellena todos los campos obligatorios.")

    with t_lista:
            st.subheader("📋 Control de Personal")
            usuarios = peticion_api("/api/usuarios/listar")
            
            if usuarios:
                df_u = pd.DataFrame(usuarios)
                df_u.columns = ["ID", "Nombre", "Email", "Rol", "Estado"]
                
                # Mostramos la tabla
                st.dataframe(df_u, use_container_width=True, hide_index=True)
                
                st.divider()
                col_sel, col_act = st.columns([2, 1])
                
                # Selector de usuario para acciones
                dict_users = {f"{u['id_usuario']} - {u['nombre']}": u['id_usuario'] for u in usuarios}
                seleccion = col_sel.selectbox("Seleccionar usuario para gestionar:", dict_users.keys())
                id_sel = dict_users[seleccion]
                
                st.write(f"**Acciones para:** {seleccion}")
                btn_des, btn_eli = st.columns(2)
                
                # BOTÓN DESACTIVAR
                if btn_des.button("🚫 Desactivar Usuario", use_container_width=True):
                    if peticion_api(f"/api/usuarios/desactivar/{id_sel}", metodo="PUT"):
                        st.success(f"✅ El usuario ha sido marcado como 'Inactivo'.")
                        st.rerun()
                
                # BOTÓN ELIMINAR
                if btn_eli.button("🗑️ Eliminar Definitivamente", type="primary", use_container_width=True):
                    if peticion_api(f"/api/usuarios/eliminar/{id_sel}", metodo="DELETE"):
                        st.success(f"💥 Usuario borrado permanentemente con éxito.")
                        st.rerun()
            else:
                st.info("No hay usuarios registrados.")
                
def modulo_dashboard(rol):
    st.title("📊 Panel de Control General")
    res = peticion_api("/api/admin/dashboard/resumen")
    if res:
        m1, m2, m3 = st.columns(3)
        m1.metric("Ventas Hoy", f"$ {res['ventas_hoy']:,.2f}")
        m2.metric("Alertas Stock", f"{res['alertas_count']} Prod.")
        m3.metric("Rol", rol)

def modulo_reabastecimiento():
    st.title("🚚 Gestión de Suministros y Proveedores")
    
    # Creamos las 4 pestañas solicitadas
    t_entrada, t_sugeridos, t_nuevo_prod, t_nuevo_prov = st.tabs([
        "📥 Insertar Entrada", 
        "📋 Pedidos Sugeridos", 
        "✨ Crear Producto", 
        "🤝 Crear Proveedor"
    ])

    # --- 1. CREAR PROVEEDOR (Siempre disponible) ---
    with t_nuevo_prov:
        st.subheader("Registro de Proveedores")
        with st.form("form_prov_nuevo"):
            pr_nom = st.text_input("Nombre de la Empresa / Proveedor")
            pr_con = st.text_input("Nombre del Contacto")
            pr_tel = st.text_input("Teléfono")
            
            if st.form_submit_button("Registrar Proveedor"):
                if pr_nom:
                    # Creamos el diccionario con los datos
                    datos_proveedor = {
                        "nombre": pr_nom,
                        "contacto": pr_con,
                        "tel": pr_tel
                    }
                    # IMPORTANTE: Usamos json_data= en lugar de params=
                    res = peticion_api("/api/admin/proveedores/crear", metodo="POST", json_data=datos_proveedor)
                    if res:
                        st.success(f"✅ Proveedor '{pr_nom}' guardado correctamente.")
                        st.rerun()
                else:
                    st.error("El nombre del proveedor es obligatorio.")

    # --- 2. CREAR PRODUCTO NUEVO (Depende de que exista un proveedor) ---
    with t_nuevo_prod:
        st.subheader("Dar de alta nuevo producto")
        proveedores = peticion_api("/api/admin/proveedores")
        
        if proveedores:
            df_prov = pd.DataFrame(proveedores)
            with st.form("form_nuevo_prod_si"):
                f1, f2 = st.columns(2)
                f_cod = f1.text_input("Código de Barras")
                f_nom = f2.text_input("Nombre del Producto")
                f_pre_v = f1.number_input("Precio Venta ($)", min_value=0.0)
                f_pre_c = f2.number_input("Precio Compra ($)", min_value=0.0)
                f_stock = f1.number_input("Stock Inicial", min_value=0, value=0)
                f_min = f2.number_input("Stock Mínimo", min_value=1, value=5)
                f_prov_id = st.selectbox("Asignar Proveedor", df_prov['nombre_empresa'].unique())
                
                # Obtener ID del proveedor seleccionado
                id_p = df_prov[df_prov['nombre_empresa'] == f_prov_id]['id_proveedor'].values[0]
                
                if st.form_submit_button("Guardar Producto"):
                    p_load = {
                        "codigo": str(f_cod),
                        "nombre": str(f_nom),
                        "stock": int(f_stock),
                        "minimo": int(f_min),
                        "id_prov": int(id_p), 
                        "precio": float(f_pre_v), 
                        "precio_c": float(f_pre_c)
                    }
                    if peticion_api("/api/admin/inventario/crear-producto", metodo="POST", json_data=p_load):
                        st.success(f"✅ Producto '{f_nom}' creado con éxito.")
                        st.rerun()
        else:
            st.info("👋 Para crear un producto, primero registra un proveedor en la pestaña 'Crear Proveedor'.")

    # --- 3. INSERTAR ENTRADA (STOCK) (Depende de que existan productos) ---
    with t_entrada:
        st.subheader("Registrar Ingreso de Mercancía")
        productos = peticion_api("/listar_productos")
        
        if productos:
            df_p = pd.DataFrame(productos)
            with st.container(border=True):
                prod_sel = st.selectbox("Producto a recibir", df_p['nombre_producto'].unique(), key="sel_entrada")
                info = df_p[df_p['nombre_producto'] == prod_sel].iloc[0]
                
                c1, c2 = st.columns(2)
                cantidad = c1.number_input("Cantidad", min_value=1, step=1)
                costo_u = c2.metric("Costo Unitario Actual", f"${info['precio_compra']:,.2f}")
                
                if st.button("Confirmar Ingreso de Stock", use_container_width=True):
                    payload = {"codigo": str(info['codigo_barras']), "cantidad": int(cantidad)}
                    if peticion_api("/api/admin/inventario/registrar-entrada", metodo="POST", json_data=payload):
                        st.success(f"✅ Se agregaron {cantidad} unidades a {prod_sel}")
                        st.rerun()
        else:
            st.info("No hay productos registrados. Ve a la pestaña 'Crear Producto'.")

    # --- 4. PEDIDOS SUGERIDOS (Análisis de Stock) ---
    with t_sugeridos:
        st.subheader("Análisis de Reposición")
        prods_todos = peticion_api("/listar_productos")
        
        if prods_todos:
            df_todos = pd.DataFrame(prods_todos)
            # Simulación de stock bajo (puedes ajustar el criterio)
            bajo_stock = df_todos[df_todos['existencias'] <= 5] 
            
            if not bajo_stock.empty:
                st.warning(f"Se detectaron {len(bajo_stock)} productos con stock bajo.")
                st.dataframe(bajo_stock[['nombre_producto', 'existencias', 'precio_compra']], use_container_width=True, hide_index=True)
            else:
                st.success("✅ Todos los productos tienen stock suficiente.")
        else:
            st.info("Sin datos para analizar.")

def modulo_ventas():
    st.title("🛒 Terminal de Ventas")
    
    # 1. Inicializar carrito si no existe
    if "carrito" not in st.session_state: 
        st.session_state.carrito = []
    
    # 2. Definir pestañas
    t_v, t_h = st.tabs(["🆕 Nueva Venta", "📜 Historial Hoy"])
    
    with t_v:
        prods = peticion_api("/listar_productos")
        
        # --- CORRECCIÓN DE INDENTACIÓN ---
        if not prods:
            st.warning("🛍️ La tienda está vacía. Registra productos en el módulo de Reabastecimiento para comenzar a vender.")
            return  # Detiene la ejecución de esta pestaña si no hay productos
        
        # Si hay productos, el código sigue aquí (ya no necesitas "if prods:")
        df_p = pd.DataFrame(prods)
        
        with st.container(border=True):
            p_sel = st.selectbox("Seleccione Producto", df_p['nombre_producto'].unique())
            # Obtenemos la info del producto seleccionado
            info = df_p[df_p['nombre_producto'] == p_sel].iloc[0]
            
            col1, col2 = st.columns(2)
            cant = col1.number_input("Cantidad", min_value=1, value=1)
            # Buscamos precio_venta, si no existe usamos precio_compra por seguridad
            precio = float(info.get('precio_venta', info.get('precio_compra', 0)))
            col2.metric("Precio Unitario", f"${precio:,.2f}")
            
            if st.button("➕ Agregar al Carrito", use_container_width=True):
                st.session_state.carrito.append({
                    "codigo_barras": info['codigo_barras'], 
                    "nombre": p_sel, 
                    "cantidad": cant, 
                    "total": precio, 
                    "subtotal": cant * precio
                })
                st.rerun()
        
        # Mostrar carrito si tiene items
        if st.session_state.carrito:
            st.write("---")
            st.subheader("Lista de Compra")
            st.dataframe(pd.DataFrame(st.session_state.carrito)[['nombre', 'cantidad', 'subtotal']], use_container_width=True)
            
            total = sum(i['subtotal'] for i in st.session_state.carrito)
            
            c1, c2 = st.columns(2)
            if c1.button("🗑️ Vaciar Carrito", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()
                
            if c2.button(f"✅ Confirmar Venta (${total:,.2f})", type="primary", use_container_width=True):
                payload = {
                    "id_venta": 0, 
                    "total": total, 
                    "productos": st.session_state.carrito, 
                    "fecha": obtener_ahora_local().strftime("%Y-%m-%d %H:%M:%S")
                }
                if peticion_api("/api/ventas/registrar", metodo="POST", json_data=payload):
                    st.session_state.carrito = []
                    st.success("¡Venta Exitosa!")
                    st.rerun()

    with t_h:
        st.subheader("Ventas realizadas hoy")
        # Aquí puedes llamar a tu endpoint de historial de ventas si lo tienes
        st.info("El historial de hoy se mostrará aquí.")

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
    
    # Definimos las opciones (ASEGÚRATE DE QUE LOS EMOJIS Y ESPACIOS SEAN IGUALES)
    opciones = ["🏠 Dashboard", "🛒 Ventas", "💰 Corte de Caja"]
    
    if user['rol'] == "Administrador":
        # Insertamos Reabastecimiento en la posición 1 y Usuarios al final
        opciones.append("📦 Reabastecimiento")
        opciones.append("👥 Usuarios")
    
    # Creamos el menú
    menu = st.sidebar.radio("Navegar a:", opciones)
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.auth_user = None
        st.rerun()

    # --- DESPLIEGUE DE MÓDULOS ---
    # Usamos "in" o comparaciones exactas para evitar errores de lectura
    if menu == "🏠 Dashboard":
        modulo_dashboard(user['rol'])
        
    elif menu == "🛒 Ventas":
        modulo_ventas()
        
    elif menu == "💰 Corte de Caja":
        modulo_corte()
        
    elif menu == "📦 Reabastecimiento":
        modulo_reabastecimiento()
        
    elif menu == "👥 Usuarios":
        modulo_usuarios()

    st.sidebar.divider()
    st.sidebar.caption(f"🕒 {obtener_ahora_local().strftime('%d/%m/%Y %H:%M')}")



