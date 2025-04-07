import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import altair as alt
from matplotlib.ticker import MaxNLocator

# Configuración de la página
st.set_page_config(
    page_title="Dashboard NBA",
    layout="wide"
)

# Estilo de Matplotlib
plt.style.use('ggplot')

# Título de la página
st.title("Dashboard NBA")

# Cargar datos
@st.cache_data
def cargar_datos():
    df = pd.read_csv('nba_all_elo.csv')
    return df

# Intentar cargar los datos
try:
    df = cargar_datos()
    datos_cargados = True

    # Línea opcional para depuración
    # st.sidebar.expander("Debug - Nombres de columnas").write(df.columns.tolist())

except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.error("Asegúrate de que el archivo 'nba_all_elo.csv' esté en el mismo directorio que esta app.")
    datos_cargados = False

if datos_cargados:
    # Sidebar
    st.sidebar.header("Filtros")

    # Filtro por año
    años = sorted(df['year_id'].unique().tolist())
    año_seleccionado = st.sidebar.selectbox("Selecciona el año", años)

    # Filtro por equipo
    equipos = sorted(set(df['fran_id'].unique()) | set(df['opp_fran'].unique()))
    equipo_seleccionado = st.sidebar.selectbox("Selecciona el equipo", equipos)

    # Filtro por tipo de partido
    opciones_tipo = ["Temporada regular", "Playoffs", "Ambos"]
    tipo_partido = st.sidebar.radio("Selecciona el tipo de partido", opciones_tipo, key="tipo_partido")

    # Filtros
    filtro_año = df['year_id'] == año_seleccionado
    filtro_equipo = (df['fran_id'] == equipo_seleccionado) | (df['opp_fran'] == equipo_seleccionado)

    df_filtrado = df[filtro_año & filtro_equipo].copy()

    if tipo_partido != "Ambos":
        if tipo_partido == "Playoffs":
            df_filtrado = df_filtrado[df_filtrado['is_playoffs'] == 1]
        else:
            df_filtrado = df_filtrado[df_filtrado['is_playoffs'] == 0]

    if 'date_game' in df_filtrado.columns:
        df_filtrado['date_game'] = pd.to_datetime(df_filtrado['date_game'])
        df_filtrado = df_filtrado.sort_values('date_game')

    df_filtrado['es_equipo'] = df_filtrado['fran_id'] == equipo_seleccionado
    df_filtrado['resultado_equipo'] = df_filtrado.apply(
        lambda fila: fila['game_result'] if fila['es_equipo'] else
        ('W' if fila['game_result'] == 'L' else 'L'),
        axis=1
    )

    df_filtrado = df_filtrado.reset_index(drop=True)
    df_filtrado['numero_partido'] = range(1, len(df_filtrado) + 1)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Victorias y derrotas acumuladas de {equipo_seleccionado} ({año_seleccionado})")

        if not df_filtrado.empty:
            victorias = df_filtrado[df_filtrado['resultado_equipo'] == 'W'].copy()
            derrotas = df_filtrado[df_filtrado['resultado_equipo'] == 'L'].copy()

            fig, ax = plt.subplots(figsize=(10, 6))

            if not victorias.empty:
                victorias = victorias.sort_values('numero_partido')
                victorias['victorias_acumuladas'] = range(1, len(victorias) + 1)
                ax.plot(victorias['numero_partido'], victorias['victorias_acumuladas'],
                        marker='o', linestyle='-', color='green', label='Victorias')

            if not derrotas.empty:
                derrotas = derrotas.sort_values('numero_partido')
                derrotas['derrotas_acumuladas'] = range(1, len(derrotas) + 1)
                ax.plot(derrotas['numero_partido'], derrotas['derrotas_acumuladas'],
                        marker='o', linestyle='-', color='red', label='Derrotas')

            ax.set_xlabel('Número de partido')
            ax.set_ylabel('Cantidad acumulada')
            ax.set_title(f'Progresión de victorias y derrotas de {equipo_seleccionado} ({año_seleccionado})')
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            st.pyplot(fig)

            # Gráfico interactivo con Altair
            if not victorias.empty:
                datos_victorias = pd.DataFrame({
                    'Partido': victorias['numero_partido'],
                    'Cantidad': victorias['victorias_acumuladas'],
                    'Tipo': ['Victorias'] * len(victorias)
                })
            else:
                datos_victorias = pd.DataFrame(columns=['Partido', 'Cantidad', 'Tipo'])

            if not derrotas.empty:
                datos_derrotas = pd.DataFrame({
                    'Partido': derrotas['numero_partido'],
                    'Cantidad': derrotas['derrotas_acumuladas'],
                    'Tipo': ['Derrotas'] * len(derrotas)
                })
            else:
                datos_derrotas = pd.DataFrame(columns=['Partido', 'Cantidad', 'Tipo'])

            datos_grafico = pd.concat([datos_victorias, datos_derrotas])

            if not datos_grafico.empty:
                grafico = alt.Chart(datos_grafico).mark_line(point=True).encode(
                    x='Partido:Q',
                    y='Cantidad:Q',
                    color=alt.Color('Tipo:N', scale=alt.Scale(domain=['Victorias', 'Derrotas'], range=['green', 'red'])),
                    tooltip=['Partido', 'Cantidad', 'Tipo']
                ).properties(
                    width=600,
                    height=300
                ).interactive()

                st.altair_chart(grafico, use_container_width=True)
        else:
            st.write("No hay datos disponibles para los filtros seleccionados.")

    with col2:
        st.subheader(f"Distribución de victorias y derrotas de {equipo_seleccionado} ({año_seleccionado})")

        if not df_filtrado.empty:
            conteo = df_filtrado['resultado_equipo'].value_counts()
            victorias = conteo.get('W', 0)
            derrotas = conteo.get('L', 0)
            total = victorias + derrotas

            if total > 0:
                fig, ax = plt.subplots(figsize=(5, 5))
                etiquetas = ['Victorias', 'Derrotas']
                tamaños = [victorias, derrotas]
                colores = ['green', 'red']
                explotar = (0.1, 0)

                ax.pie(tamaños, explode=explotar, labels=etiquetas, colors=colores,
                       autopct='%1.1f%%', shadow=True, startangle=90)
                ax.axis('equal')
                ax.set_title(f'Porcentaje de victorias y derrotas de {equipo_seleccionado} ({año_seleccionado})')

                st.pyplot(fig)

                st.metric("Total de partidos", total)
                col_vic, col_der = st.columns(2)
                with col_vic:
                    st.metric("Victorias", victorias)
                    st.metric("Porcentaje de victorias", f"{(victorias / total * 100):.1f}%")
                with col_der:
                    st.metric("Derrotas", derrotas)
                    st.metric("Porcentaje de derrotas", f"{(derrotas / total * 100):.1f}%")
            else:
                st.write("No se encontraron resultados claros para los filtros seleccionados.")
        else:
            st.write("No hay datos disponibles para los filtros seleccionados.")

    # Pie de página
    st.markdown("---")
    st.info("Dashboard de la NBA con datos del archivo nba_all_elo.csv")
else:
    st.error("No se pudieron cargar los datos. Verifica que el archivo exista y esté bien formateado.")
