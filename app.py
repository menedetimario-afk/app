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
        elif metodo == "PUT": r = requests.put(url, headers=HEADERS, timeout=10)
        elif metodo == "DELETE": r = requests.delete(url, headers=HEADERS, timeout=10)
        
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
                    payload = {"nombre": nombre, "correo": correo, "password": password, "rol": rol}
                    res = peticion_api("/api/usuarios/registrar", metodo="POST", json_data=payload)
                    if res:
                        st.success(f"✅ ¡Operación Éxito! El usuario **{nombre}** ha sido registrado.")
                    else:
                        st.error("❌ No se pudo registrar el usuario.")
                else:
                    st.warning("⚠️ Por favor, rellena todos los campos obligatorios.")

    with t_lista:
        st.subheader("📋 Control de Personal")
        usuarios = peticion_api("/api/usuarios/listar")
        
        if usuarios:
            df_u = pd.DataFrame(usuarios)
            df_u.columns = ["ID", "Nombre", "Email", "Rol", "Estado"]
            st.dataframe(df_u, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("⚙️ Gestión de Estado y Cuenta")
            
            dict_users = {f"{u['id_usuario']} - {u['nombre']} ({u['estado']})": u['id_usuario'] for u in usuarios}
            seleccion = st.selectbox("Seleccionar usuario:", dict_users.keys())
            id_sel = dict_users[seleccion]
            
            col_act, col_des, col_eli = st.columns(3)
            
            if col_act.button("✅ Activar Usuario", use_container_width=True):
                if peticion_api(f"/api/usuarios/activar/{id_sel}", metodo="PUT"):
                    st.success(f"✅ ¡Operación Éxito! Usuario Activo.")
                    st.rerun()
            
            if col_des.button("🚫 Desactivar Usuario", use_container_width=True):
                if peticion_api(f"/api/usuarios/desactivar/{id_sel}", metodo="PUT"):
                    st.success(f"✅ ¡Operación Éxito! Usuario Desactivado.")
                    st.rerun()
            
            if col_eli.button("🗑️ Eliminar", type="primary", use_container_width=True):
                if peticion_api(f"/api/usuarios/eliminar/{id_sel}", metodo="DELETE"):
                    st.success(f"✅ ¡Operación Éxito! Usuario borrado.")
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
    
    t_entrada, t_sugeridos, t_nuevo_prod, t_nuevo_prov = st.tabs([
        "📥 Insertar Entrada", 
        "📋 Pedidos Sugeridos", 
        "✨ Crear Producto", 
        "🤝 Crear Proveedor"
    ])

    with t_nuevo_prov:
        st.subheader("Registro de Proveedores")
        with st.form("form_prov_nuevo", clear_on_submit=True):
            pr_nom = st.text_input("Nombre de la Empresa / Proveedor")
            pr_con = st.text_input("Nombre del Contacto")
            pr_tel = st.text_input("Teléfono")
            
            if st.form_submit_button("Registrar Proveedor", use_container_width=True):
                if pr_nom:
                    datos = {"nombre": pr_nom, "contacto": pr_con, "tel": pr_tel}
                    if peticion_api("/api/admin/proveedores/crear", metodo="POST", json_data=datos):
                        st.success(f"✅ ¡Operación Éxito! Proveedor '{pr_nom}' guardado.")
                else:
                    st.error("El nombre del proveedor es obligatorio.")

    with t_nuevo_prod:
        st.subheader("Dar de alta nuevo producto")
        proveedores = peticion_api("/api/admin/proveedores")
        if proveedores:
            df_prov = pd.DataFrame(proveedores)
            with st.form("form_nuevo_prod_si", clear_on_submit=True):
                f1, f2 = st.columns(2)
                f_cod = f1.text_input("Código de Barras")
                f_nom = f2.text_input("Nombre del Producto")
                f_pre_v = f1.number_input("Precio Venta ($)", min_value=0.0)
                f_pre_c = f2.number_input("Precio Compra ($)", min_value=0.0)
                f_stock = f1.number_input("Stock Inicial", min_value=0, value=0)
                f_min = f2.number_input("Stock Mínimo", min_value=1, value=5)
                f_prov_id = st.selectbox("Asignar Proveedor", df_prov['nombre_empresa'].unique())
                id_p = df_prov[df_prov['nombre_empresa'] == f_prov_id]['id_proveedor'].values[0]
                
                if st.form_submit_button("Guardar Producto", use_container_width=True):
                    p_load = {
                        "codigo": str(f_cod), "nombre": str(f_nom), "stock": int(f_stock),
                        "minimo": int(f_min), "id_prov": int(id_p), 
                        "precio": float(f_pre_v), "precio_c": float(f_pre_c)
                    }
                    if peticion_api("/api/admin/inventario/crear-producto", metodo="POST", json_data=p_load):
                        st.success(f"✅ ¡Operación Éxito! Producto '{f_nom}' creado.")
        else:
            st.info("Registra un proveedor primero.")

    with t_entrada:
        st.subheader("📥 Registro de Entrada")
        proveedores = peticion_api("/api/admin/proveedores")
        todos_productos = peticion_api("/listar_productos")
        
        if proveedores and todos_productos:
            df_prov = pd.DataFrame(proveedores)
            df_prod = pd.DataFrame(todos_productos)
            col_izq, col_der = st.columns([1, 1.5])
            
            with col_izq:
                prov_nom = st.selectbox("1. Proveedor", [""] + list(df_prov['nombre_empresa'].unique()))
                prod_nom = None
                if prov_nom:
                    id_p_sel = df_prov[df_prov['nombre_empresa'] == prov_nom]['id_proveedor'].values[0]
                    prods_filtrados = df_prod[df_prod['id_proveedor'] == id_p_sel]
                    if not prods_filtrados.empty:
                        prod_nom = st.radio("2. Producto", prods_filtrados['nombre_producto'].unique())
            
            with col_der:
                if prod_nom:
                    info_p = df_prod[df_prod['nombre_producto'] == prod_nom].iloc[0]
                    with st.form("form_update_stock", clear_on_submit=True):
                        st.info(f"Stock actual: {info_p['existencias']}")
                        c1, c2 = st.columns(2)
                        nueva_cant = c1.number_input("Cantidad entrante", min_value=1, step=1)
                        nuevo_precio_c = c2.number_input("Nuevo Precio Compra", value=float(info_p['precio_compra']))
                        
                        if st.form_submit_button("💾 Guardar Entrada", use_container_width=True):
                            payload = {"codigo": str(info_p['codigo_barras']), "cantidad": int(nueva_cant), "precio_compra": float(nuevo_precio_c)}
                            if peticion_api("/api/admin/inventario/registrar-entrada", metodo="POST", json_data=payload):
                                st.success("✅ ¡Operación Éxito! Inventario actualizado.")

    with t_sugeridos:
        st.subheader("📋 Pedidos Sugeridos Inteligentes")
        datos_sugeridos = peticion_api("/api/admin/inventario/sugeridos-avanzado")
        if datos_sugeridos:
            df = pd.DataFrame(datos_sugeridos)
            with st.expander("🔍 Filtros de Búsqueda", expanded=True):
                c1, c2, c3 = st.columns(3)
                f_p = c1.selectbox("Proveedor", ["Todos"] + list(df['proveedor'].unique()))
                f_n = c2.text_input("Nombre")
                f_c = c3.text_input("Código")
            
            df_f = df.copy()
            if f_p != "Todos": df_f = df_f[df_f['proveedor'] == f_p]
            if f_n: df_f = df_f[df_f['nombre_producto'].str.contains(f_n, case=False)]
            if f_c: df_f = df_f[df_f['codigo_barras'].str.contains(f_c)]
            
            def calcular_p(row):
                v, e, m = row['ventas_periodo'], row['existencias'], row['stock_minimo']
                return int(v + (m - e)) if e <= m else int(v)

            df_f['Sugerencia'] = df_f.apply(calcular_p, axis=1)
            st.dataframe(df_f[['nombre_producto', 'proveedor', 'existencias', 'Sugerencia']], use_container_width=True, hide_index=True)
            if st.button("📊 Actualizar Reporte"):
                st.success("✅ ¡Operación Éxito! Reporte actualizado.")

def modulo_ventas():
    st.title("🛒 Terminal de Ventas")
    if "carrito" not in st.session_state: st.session_state.carrito = []
    t_v, t_h = st.tabs(["🆕 Nueva Venta", "📜 Historial Hoy"])
    
    with t_v:
        prods = peticion_api("/listar_productos")
        if not prods:
            st.warning("No hay productos disponibles.")
        else:
            df_p = pd.DataFrame(prods)
            with st.container(border=True):
                p_sel = st.selectbox("Producto", df_p['nombre_producto'].unique())
                info = df_p[df_p['nombre_producto'] == p_sel].iloc[0]
                c1, c2 = st.columns(2)
                cant = c1.number_input("Cantidad", min_value=1, value=1)
                precio = float(info.get('precio_venta', 0))
                c2.metric("Precio", f"${precio:,.2f}")
                
                if st.button("➕ Agregar", use_container_width=True):
                    st.session_state.carrito.append({"codigo_barras": info['codigo_barras'], "nombre": p_sel, "cantidad": cant, "subtotal": cant * precio})
                    st.rerun()

        if st.session_state.carrito:
            st.divider()
            st.dataframe(pd.DataFrame(st.session_state.carrito), use_container_width=True)
            total = sum(i['subtotal'] for i in st.session_state.carrito)
            if st.button(f"✅ Confirmar Venta (${total:,.2f})", type="primary"):
                payload = {"id_venta": 0, "total": total, "productos": st.session_state.carrito, "fecha": obtener_ahora_local().strftime("%Y-%m-%d %H:%M:%S")}
                if peticion_api("/api/ventas/registrar", metodo="POST", json_data=payload):
                    st.session_state.carrito = []
                    st.success("✅ ¡Operación Éxito! Venta guardada.")
                    st.rerun()

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
    opciones = ["🏠 Dashboard", "🛒 Ventas", "💰 Corte de Caja"]
    if user['rol'] == "Administrador":
        opciones.extend(["📦 Reabastecimiento", "👥 Usuarios"])
    
    menu = st.sidebar.radio("Navegar a:", opciones)
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.auth_user = None
        st.rerun()

    if menu == "🏠 Dashboard": modulo_dashboard(user['rol'])
    elif menu == "🛒 Ventas": modulo_ventas()
    elif menu == "💰 Corte de Caja": modulo_corte()
    elif menu == "📦 Reabastecimiento": modulo_reabastecimiento()
    elif menu == "👥 Usuarios": modulo_usuarios()

    st.sidebar.divider()
    st.sidebar.caption(f"🕒 {obtener_ahora_local().strftime('%d/%m/%Y %H:%M')}")



