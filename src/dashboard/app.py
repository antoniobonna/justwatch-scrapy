import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine

# Configuração da página
st.set_page_config(
    page_title="Comparação de Plataformas de Streaming",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Função para conectar ao banco de dados PostgreSQL
def get_connection():
    import os

    # Obter a string de conexão da variável de ambiente
    conn_string = os.environ.get("POSTGRES_URI")
    if not conn_string:
        st.error("Variável de ambiente DATABASE_URL não encontrada. Usando dados de demonstração.")
        return None

    # Criar engine
    engine = create_engine(conn_string)
    return engine


# Função para executar consultas SQL e obter dataframes
def get_dataframe(query, engine):
    if engine is None:
        return None

    df = pd.read_sql_query(query, engine)

    # Converter os IDs dos provedores para nomes legíveis
    if "provedor" in df.columns:
        provider_display_names = get_provider_display_names()
        df["provedor"] = df["provedor"].map(provider_display_names).fillna(df["provedor"])

    return df


# Definição das consultas SQL
def get_queries():
    queries = {
        "tamanho_diversidade": """
        SELECT 
            p.provedor,
            p.mensalidade,
            COUNT(*) AS total_titulos,
            COUNT(*) FILTER (WHERE j.categoria = 'filmes') AS qtd_filmes,
            COUNT(*) FILTER (WHERE j.categoria = 'series') AS qtd_series,
            ROUND((COUNT(*) FILTER (WHERE j.categoria = 'filmes'))::numeric * 100.0 / NULLIF(COUNT(*)::numeric, 0), 1) AS perc_filmes,
            ROUND((COUNT(*) FILTER (WHERE j.categoria = 'series'))::numeric * 100.0 / NULLIF(COUNT(*)::numeric, 0), 1) AS perc_series
        FROM 
            streaming_s.justwatch_tb j
        JOIN 
            streaming_s.provider_tb p ON j.provedor = p.provedor_id
        GROUP BY 
            p.provedor, p.mensalidade
        ORDER BY 
            total_titulos DESC;
        """,
        "qualidade_catalogo": """
        SELECT 
            p.provedor,
            ROUND(AVG(j.imdb_score) FILTER (WHERE j.imdb_count > 1000)::numeric, 2) AS imdb_score_medio,
            COUNT(*) FILTER (WHERE j.imdb_score >= 7 AND j.imdb_count > 1000) AS qtd_titulos_7plus,
            COUNT(*) FILTER (WHERE j.imdb_score >= 8 AND j.imdb_count > 1000) AS qtd_titulos_8plus,
            ROUND((COUNT(*) FILTER (WHERE j.imdb_score >= 7 AND j.imdb_count > 1000))::numeric * 100.0 / 
                NULLIF((COUNT(*) FILTER (WHERE j.imdb_count > 1000))::numeric, 0), 1) AS perc_titulos_7plus,
            ROUND((COUNT(*) FILTER (WHERE j.imdb_score >= 8 AND j.imdb_count > 1000))::numeric * 100.0 / 
                NULLIF((COUNT(*) FILTER (WHERE j.imdb_count > 1000))::numeric, 0), 1) AS perc_titulos_8plus
        FROM 
            streaming_s.justwatch_tb j
        JOIN 
            streaming_s.provider_tb p ON j.provedor = p.provedor_id
        GROUP BY 
            p.provedor
        ORDER BY 
            imdb_score_medio DESC;
        """,
        "atualidade_catalogo": """
        SELECT 
            p.provedor,
            ROUND(AVG(j.ano)::numeric, 1) AS ano_medio_lancamento,
            COUNT(*) FILTER (WHERE j.ano >= EXTRACT(YEAR FROM CURRENT_DATE) - 5) AS qtd_ultimos_5_anos,
            COUNT(*) FILTER (WHERE j.ano >= EXTRACT(YEAR FROM CURRENT_DATE) - 2) AS qtd_ultimos_2_anos,
            ROUND((COUNT(*) FILTER (WHERE j.ano >= EXTRACT(YEAR FROM CURRENT_DATE) - 5))::numeric * 100.0 / 
                NULLIF((COUNT(*) FILTER (WHERE j.ano IS NOT NULL))::numeric, 0), 1) AS perc_ultimos_5_anos,
            ROUND((COUNT(*) FILTER (WHERE j.ano >= EXTRACT(YEAR FROM CURRENT_DATE) - 2))::numeric * 100.0 / 
                NULLIF((COUNT(*) FILTER (WHERE j.ano IS NOT NULL))::numeric, 0), 1) AS perc_ultimos_2_anos
        FROM 
            streaming_s.justwatch_tb j
        JOIN 
            streaming_s.provider_tb p ON j.provedor = p.provedor_id
        GROUP BY 
            p.provedor
        ORDER BY 
            ano_medio_lancamento DESC;
        """,
        "distribuicao_decadas": """
        SELECT 
            p.provedor,
            COUNT(*) FILTER (WHERE j.ano < 1980) AS pre_1980s,
            COUNT(*) FILTER (WHERE j.ano >= 1980 AND j.ano < 1990) AS anos_1980s,
            COUNT(*) FILTER (WHERE j.ano >= 1990 AND j.ano < 2000) AS anos_1990s,
            COUNT(*) FILTER (WHERE j.ano >= 2000 AND j.ano < 2010) AS anos_2000s,
            COUNT(*) FILTER (WHERE j.ano >= 2010 AND j.ano < 2020) AS anos_2010s,
            COUNT(*) FILTER (WHERE j.ano >= 2020) AS anos_2020s
        FROM 
            streaming_s.justwatch_tb j
        JOIN 
            streaming_s.provider_tb p ON j.provedor = p.provedor_id
        GROUP BY 
            p.provedor;
        """,
        "custo_beneficio": """
        SELECT 
            p.provedor,
            p.mensalidade,
            COUNT(*) AS total_titulos,
            ROUND((p.mensalidade / NULLIF(COUNT(*)::numeric, 0))::numeric, 2) AS custo_por_titulo,
            COUNT(*) FILTER (WHERE j.imdb_score >= 7 AND j.imdb_count > 1000) AS titulos_7plus,
            CASE 
                WHEN COUNT(*) FILTER (WHERE j.imdb_score >= 7 AND j.imdb_count > 1000) > 0 
                THEN ROUND((p.mensalidade / (COUNT(*) FILTER (WHERE j.imdb_score >= 7 AND j.imdb_count > 1000))::numeric)::numeric, 2) 
                ELSE NULL 
            END AS custo_por_titulo_7plus,
            ROUND((p.mensalidade / NULLIF((COUNT(*) FILTER (WHERE j.categoria = 'filmes'))::numeric, 0))::numeric, 2) AS custo_por_filme,
            ROUND((p.mensalidade / NULLIF((COUNT(*) FILTER (WHERE j.categoria = 'series'))::numeric, 0))::numeric, 2) AS custo_por_serie
        FROM 
            streaming_s.justwatch_tb j
        JOIN 
            streaming_s.provider_tb p ON j.provedor = p.provedor_id
        GROUP BY 
            p.provedor, p.mensalidade
        ORDER BY 
            custo_por_titulo ASC;
        """,
        "duracao_categoria": """
        SELECT 
            p.provedor,
            ROUND(AVG(j.duracao_minutos) FILTER (WHERE j.categoria = 'filmes')::numeric, 0) AS duracao_media_filmes,
            ROUND(AVG(j.duracao_minutos) FILTER (WHERE j.categoria = 'series')::numeric, 0) AS duracao_media_episodios,
            COUNT(*) FILTER (WHERE j.categoria = 'filmes' AND j.duracao_minutos < 90) AS filmes_curtos,
            COUNT(*) FILTER (WHERE j.categoria = 'filmes' AND j.duracao_minutos >= 90 AND j.duracao_minutos <= 120) AS filmes_medios,
            COUNT(*) FILTER (WHERE j.categoria = 'filmes' AND j.duracao_minutos > 120) AS filmes_longos
        FROM 
            streaming_s.justwatch_tb j
        JOIN 
            streaming_s.provider_tb p ON j.provedor = p.provedor_id
        GROUP BY 
            p.provedor
        ORDER BY 
            p.provedor;
        """,
        "exclusividade": """
        WITH titulo_count AS (
            SELECT 
                titulo,
                COUNT(DISTINCT provedor) AS num_provedores
            FROM 
                streaming_s.justwatch_tb
            GROUP BY 
                titulo
        ),
        provedor_exclusivo AS (
            SELECT 
                j.provedor,
                COUNT(*) FILTER (WHERE tc.num_provedores = 1) AS titulos_exclusivos,
                COUNT(*) AS total_titulos
            FROM 
                streaming_s.justwatch_tb j
            JOIN 
                titulo_count tc ON j.titulo = tc.titulo
            GROUP BY 
                j.provedor
        )
        SELECT 
            p.provedor,
            pe.titulos_exclusivos,
            pe.total_titulos,
            ROUND((pe.titulos_exclusivos::numeric * 100.0 / NULLIF(pe.total_titulos::numeric, 0))::numeric, 1) AS percentual_exclusivo
        FROM 
            provedor_exclusivo pe
        JOIN 
            streaming_s.provider_tb p ON pe.provedor = p.provedor_id
        ORDER BY 
            percentual_exclusivo DESC;
        """,
    }
    return queries


# Mapeamento dos ids dos provedores para nomes legíveis
def get_provider_display_names():
    return {
        "netflix": "Netflix",
        "amazon-prime-video": "Amazon Prime Video",
        "disney-plus": "Disney+",
        "max": "MAX",
        "paramount-plus": "Paramount+",
        "apple-tv-plus": "Apple TV+",
        "globoplay": "Globoplay",
    }


# Mapeamento de cores para cada plataforma
def get_platform_colors():
    return {
        "Netflix": "#E50914",
        "Amazon Prime Video": "#00A8E1",
        "Disney+": "#0063E5",
        "MAX": "#5822B4",  # Antigo HBO Max
        "Globoplay": "#FB8B24",
        "Apple TV+": "#000000",
        "Paramount+": "#0064FF",
    }


# Função para adicionar logo ao sidebar
def add_logo():
    st.sidebar.image("https://via.placeholder.com/150x150.png?text=Streaming+Compare", width=150)


# Função para criar gráfico de barras
def plot_bar_chart(df, x_col, y_col, title, color_col=None, orientation="v", height=400):
    if orientation == "v":
        fig = px.bar(
            df,
            x=x_col,
            y=y_col,
            title=title,
            color=color_col if color_col else None,
            color_discrete_map=get_platform_colors() if color_col == "provedor" else None,
            height=height,
        )
    else:  # horizontal
        fig = px.bar(
            df,
            y=x_col,
            x=y_col,
            title=title,
            color=color_col if color_col else None,
            color_discrete_map=get_platform_colors() if color_col == "provedor" else None,
            height=height,
            orientation="h",
        )

    fig.update_layout(
        xaxis_title=x_col if orientation == "v" else y_col,
        yaxis_title=y_col if orientation == "v" else x_col,
        plot_bgcolor="white",
        legend_title_text=color_col if color_col else "",
    )
    return fig


# Função para criar gráfico de pizza
def plot_pie_chart(df, values, names, title, height=400):
    fig = px.pie(
        df,
        values=values,
        names=names,
        title=title,
        height=height,
        color=names,
        color_discrete_map=get_platform_colors() if names == "provedor" else None,
    )
    return fig


# Função para criar gráfico de dispersão
def plot_scatter_chart(df, x_col, y_col, title, size_col=None, color_col=None, height=400):
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        size=size_col if size_col else None,
        color=color_col if color_col else None,
        color_discrete_map=get_platform_colors() if color_col == "provedor" else None,
        title=title,
        height=height,
    )

    fig.update_layout(xaxis_title=x_col, yaxis_title=y_col, plot_bgcolor="white")
    return fig


# Função para criar gráfico de radar
def plot_radar_chart(df, categories, values, title, height=500):
    fig = go.Figure()

    for i, row in df.iterrows():
        fig.add_trace(
            go.Scatterpolar(
                r=[row[val] for val in values],
                theta=categories,
                fill="toself",
                name=row["provedor"],
                line_color=get_platform_colors().get(row["provedor"], "#000000"),
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, df[values].max().max() * 1.1])),
        title=title,
        height=height,
    )
    return fig


# Função para criar gráfico de linha
def plot_line_chart(df, x_col, y_cols, title, height=400):
    fig = go.Figure()

    for y_col in y_cols:
        fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], mode="lines+markers", name=y_col))

    fig.update_layout(
        title=title, xaxis_title=x_col, yaxis_title="Valor", plot_bgcolor="white", height=height
    )
    return fig


# Função para criar gráfico de barras empilhadas
def plot_stacked_bar(df, x_col, y_cols, title, height=400):
    fig = go.Figure()

    for y_col in y_cols:
        fig.add_trace(go.Bar(x=df[x_col], y=df[y_col], name=y_col))

    fig.update_layout(
        title=title,
        xaxis_title=x_col,
        yaxis_title="Quantidade",
        barmode="stack",
        plot_bgcolor="white",
        height=height,
    )
    return fig


# Função para normalizar dados para o radar chart
def normalize_data(df, columns):
    result = df.copy()
    for column in columns:
        max_value = df[column].max()
        min_value = df[column].min()
        result[column] = (df[column] - min_value) / (max_value - min_value) * 10
    return result


# Função principal do dashboard
def main():
    # Adicionar sidebar com logo e opções
    add_logo()
    st.sidebar.title("Navegação")
    page = st.sidebar.radio(
        "Selecione uma página:",
        [
            "Visão Geral",
            "Tamanho e Diversidade",
            "Qualidade do Catálogo",
            "Atualidade",
            "Custo-Benefício",
            "Análise Técnica",
            "Comparação Completa",
        ],
    )

    # Título principal
    st.title("📊 Dashboard de Comparação de Plataformas de Streaming")

    # Nota sobre os dados
    with st.expander("ℹ️ Sobre os dados"):
        st.write("""
        Os dados apresentados neste dashboard são obtidos da tabela justwatch_tb, 
        que contém informações sobre filmes e séries disponíveis nas plataformas de streaming no Brasil.
        
        Os indicadores são calculados com base nas seguintes premissas:
        - Avaliações de qualidade consideram apenas títulos com mais de 1000 avaliações no IMDb
        - Títulos recentes são definidos como lançados nos últimos 5 anos
        - A relação custo-benefício é calculada dividindo o preço da mensalidade pelo número de títulos
        """)

    # Carregar dados apenas para visualização (dados fictícios para o exemplo)
    # Em produção, você usaria: engine = get_connection()

    # Para fins de demonstração, vamos criar dados fictícios para simular os resultados das consultas
    def create_demo_data():
        # Obter nomes legíveis de provedores
        provider_names = list(get_provider_display_names().values())

        # Tamanho e diversidade
        tamanho_diversidade = pd.DataFrame(
            {
                "provedor": provider_names,
                "mensalidade": [49.90, 19.90, 33.90, 34.90, 24.90, 21.90, 29.90],
                "total_titulos": [5000, 4200, 1800, 2500, 1600, 1300, 2200],
                "qtd_filmes": [3500, 3200, 1200, 1500, 1000, 500, 1600],
                "qtd_series": [1500, 1000, 600, 1000, 600, 800, 600],
                "perc_filmes": [70.0, 76.2, 66.7, 60.0, 62.5, 38.5, 72.7],
                "perc_series": [30.0, 23.8, 33.3, 40.0, 37.5, 61.5, 27.3],
            }
        )

        # Qualidade do catálogo
        qualidade_catalogo = pd.DataFrame(
            {
                "provedor": provider_names,
                "imdb_score_medio": [7.1, 6.9, 7.8, 7.6, 6.8, 7.9, 7.0],
                "qtd_titulos_7plus": [1800, 1400, 1200, 1300, 600, 850, 900],
                "qtd_titulos_8plus": [500, 380, 550, 480, 180, 320, 250],
                "perc_titulos_7plus": [36.0, 33.3, 66.7, 52.0, 37.5, 65.4, 40.9],
                "perc_titulos_8plus": [10.0, 9.0, 30.6, 19.2, 11.3, 24.6, 11.4],
            }
        )

        # Atualidade do catálogo
        atualidade_catalogo = pd.DataFrame(
            {
                "provedor": provider_names,
                "ano_medio_lancamento": [2018.5, 2016.2, 2019.8, 2020.1, 2017.8, 2019.5, 2017.2],
                "qtd_ultimos_5_anos": [2200, 1500, 1200, 1600, 800, 900, 950],
                "qtd_ultimos_2_anos": [1100, 600, 700, 900, 300, 550, 400],
                "perc_ultimos_5_anos": [44.0, 35.7, 66.7, 64.0, 50.0, 69.2, 43.2],
                "perc_ultimos_2_anos": [22.0, 14.3, 38.9, 36.0, 18.8, 42.3, 18.2],
            }
        )

        # Distribuição por décadas
        distribuicao_decadas = pd.DataFrame(
            {
                "provedor": provider_names,
                "pre_1980s": [200, 300, 150, 100, 50, 80, 120],
                "anos_1980s": [250, 350, 120, 150, 80, 60, 180],
                "anos_1990s": [450, 600, 180, 200, 150, 100, 250],
                "anos_2000s": [800, 950, 250, 450, 320, 160, 400],
                "anos_2010s": [2300, 1400, 700, 900, 700, 450, 850],
                "anos_2020s": [1000, 600, 400, 700, 300, 450, 400],
            }
        )

        # Custo-benefício
        custo_beneficio = pd.DataFrame(
            {
                "provedor": provider_names,
                "mensalidade": [49.90, 19.90, 33.90, 34.90, 24.90, 21.90, 29.90],
                "total_titulos": [5000, 4200, 1800, 2500, 1600, 1300, 2200],
                "custo_por_titulo": [0.01, 0.005, 0.019, 0.014, 0.016, 0.017, 0.014],
                "titulos_7plus": [1800, 1400, 1200, 1300, 600, 850, 900],
                "custo_por_titulo_7plus": [0.028, 0.014, 0.028, 0.027, 0.042, 0.026, 0.033],
                "custo_por_filme": [0.014, 0.006, 0.028, 0.023, 0.025, 0.044, 0.019],
                "custo_por_serie": [0.033, 0.02, 0.057, 0.035, 0.042, 0.027, 0.05],
            }
        )

        # Duração e categoria
        duracao_categoria = pd.DataFrame(
            {
                "provedor": provider_names,
                "duracao_media_filmes": [112, 105, 98, 118, 110, 95, 108],
                "duracao_media_episodios": [42, 38, 35, 48, 45, 36, 42],
                "filmes_curtos": [800, 900, 400, 300, 250, 180, 350],
                "filmes_medios": [2000, 1800, 600, 800, 500, 220, 950],
                "filmes_longos": [700, 500, 200, 400, 250, 100, 300],
            }
        )

        # Exclusividade
        exclusividade = pd.DataFrame(
            {
                "provedor": provider_names,
                "titulos_exclusivos": [2500, 1800, 1400, 1200, 900, 950, 1100],
                "total_titulos": [5000, 4200, 1800, 2500, 1600, 1300, 2200],
                "percentual_exclusivo": [50.0, 42.9, 77.8, 48.0, 56.3, 73.1, 50.0],
            }
        )

        return {
            "tamanho_diversidade": tamanho_diversidade,
            "qualidade_catalogo": qualidade_catalogo,
            "atualidade_catalogo": atualidade_catalogo,
            "distribuicao_decadas": distribuicao_decadas,
            "custo_beneficio": custo_beneficio,
            "duracao_categoria": duracao_categoria,
            "exclusividade": exclusividade,
        }

    # Tentar conectar ao banco de dados
    engine = get_connection()

    # Verificar se a conexão foi bem-sucedida
    if engine is not None:
        try:
            # Obter queries
            queries = get_queries()

            # Executar queries e obter dataframes
            data = {}
            for key, query in queries.items():
                data[key] = get_dataframe(query, engine)

            st.success("Conectado ao banco de dados com sucesso!")
        except Exception as e:
            st.error(f"Erro ao executar consultas: {e}")
            # Usar dados de demonstração em caso de erro
            data = create_demo_data()
    else:
        # Usar dados de demonstração se não conseguir conectar
        data = create_demo_data()

    # Conteúdo das páginas
    if page == "Visão Geral":
        st.header("Visão Geral das Plataformas")

        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Maior Catálogo", "Netflix", "5.000 títulos")
        with col2:
            st.metric("Melhor Custo-Benefício", "Amazon Prime Video", "R$ 0,005/título")
        with col3:
            st.metric("Melhor Avaliação IMDb", "Disney+", "7,8/10")
        with col4:
            st.metric("Catálogo Mais Recente", "MAX", "64% nos últimos 5 anos")

        # Gráfico de total de títulos
        st.subheader("Total de Títulos por Plataforma")
        col1, col2 = st.columns([3, 1])
        with col1:
            fig = plot_bar_chart(
                data["tamanho_diversidade"],
                "provedor",
                "total_titulos",
                "Total de Títulos por Plataforma",
                color_col="provedor",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.dataframe(
                data["tamanho_diversidade"][["provedor", "total_titulos"]].sort_values(
                    "total_titulos", ascending=False
                ),
                use_container_width=True,
            )

        # Gráfico de radar comparativo
        st.subheader("Comparação Multidimensional")

        # Criando um dataframe para o gráfico radar com dados normalizados
        radar_df = pd.DataFrame(
            {
                "provedor": data["tamanho_diversidade"]["provedor"],
                "Quantidade": data["tamanho_diversidade"]["total_titulos"]
                / data["tamanho_diversidade"]["total_titulos"].max()
                * 10,
                "Qualidade": (data["qualidade_catalogo"]["imdb_score_medio"] - 6)
                / 2
                * 10,  # Normalização para escala 0-10
                "Custo-Benefício": 10
                - (
                    data["custo_beneficio"]["custo_por_titulo"]
                    / data["custo_beneficio"]["custo_por_titulo"].max()
                    * 10
                ),  # Invertido (menor é melhor)
                "Atualidade": data["atualidade_catalogo"]["perc_ultimos_5_anos"] / 10,
                "Exclusividade": data["exclusividade"]["percentual_exclusivo"] / 10,
            }
        )

        fig = plot_radar_chart(
            radar_df,
            ["Quantidade", "Qualidade", "Custo-Benefício", "Atualidade", "Exclusividade"],
            ["Quantidade", "Qualidade", "Custo-Benefício", "Atualidade", "Exclusividade"],
            "Comparação Multidimensional das Plataformas",
        )
        st.plotly_chart(fig, use_container_width=True)

    elif page == "Tamanho e Diversidade":
        st.header("Tamanho e Diversidade do Catálogo")

        col1, col2 = st.columns(2)

        with col1:
            # Gráfico de barras para total de títulos
            fig = plot_bar_chart(
                data["tamanho_diversidade"],
                "provedor",
                "total_titulos",
                "Total de Títulos por Plataforma",
                color_col="provedor",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Distribuição entre filmes e séries
            # Transformar os dados para o formato longo
            distribution_df = pd.melt(
                data["tamanho_diversidade"],
                id_vars=["provedor"],
                value_vars=["qtd_filmes", "qtd_series"],
                var_name="categoria",
                value_name="quantidade",
            )
            distribution_df["categoria"] = distribution_df["categoria"].map(
                {"qtd_filmes": "Filmes", "qtd_series": "Séries"}
            )

            fig = px.bar(
                distribution_df,
                x="provedor",
                y="quantidade",
                color="categoria",
                title="Distribuição entre Filmes e Séries",
                height=400,
                barmode="stack",
            )

            fig.update_layout(
                xaxis_title="Plataforma",
                yaxis_title="Quantidade de Títulos",
                plot_bgcolor="white",
                legend_title_text="Tipo",
            )

            st.plotly_chart(fig, use_container_width=True)

        # Mostrar proporções em gráficos de pizza para cada plataforma
        st.subheader("Proporção Filmes vs. Séries por Plataforma")

        cols = st.columns(5)
        for i, (index, row) in enumerate(data["tamanho_diversidade"].iterrows()):
            with cols[i % 5]:
                pie_data = pd.DataFrame(
                    {
                        "categoria": ["Filmes", "Séries"],
                        "quantidade": [row["qtd_filmes"], row["qtd_series"]],
                    }
                )

                fig = px.pie(
                    pie_data,
                    values="quantidade",
                    names="categoria",
                    title=row["provedor"],
                    color_discrete_sequence=[
                        get_platform_colors().get(row["provedor"], "#000000"),
                        "#888888",
                    ],
                )
                fig.update_traces(textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)

        # Análise detalhada
        st.subheader("Análise Detalhada")
        st.dataframe(data["tamanho_diversidade"], use_container_width=True)

    elif page == "Qualidade do Catálogo":
        st.header("Qualidade do Catálogo")

        col1, col2 = st.columns(2)

        with col1:
            # Gráfico de barras para score médio IMDb
            fig = plot_bar_chart(
                data["qualidade_catalogo"],
                "provedor",
                "imdb_score_medio",
                "Nota Média IMDb por Plataforma",
                color_col="provedor",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Gráfico de barras para percentual de títulos bem avaliados
            quality_df = pd.melt(
                data["qualidade_catalogo"],
                id_vars=["provedor"],
                value_vars=["perc_titulos_7plus", "perc_titulos_8plus"],
                var_name="categoria",
                value_name="percentual",
            )
            quality_df["categoria"] = quality_df["categoria"].map(
                {"perc_titulos_7plus": "Nota IMDb >= 7", "perc_titulos_8plus": "Nota IMDb >= 8"}
            )

            fig = px.bar(
                quality_df,
                x="provedor",
                y="percentual",
                color="categoria",
                title="Percentual de Títulos Bem Avaliados",
                height=400,
                barmode="group",
            )

            fig.update_layout(
                xaxis_title="Plataforma",
                yaxis_title="Percentual (%)",
                plot_bgcolor="white",
                legend_title_text="Nota IMDb",
            )

            st.plotly_chart(fig, use_container_width=True)

        # Quantidade de títulos bem avaliados
        st.subheader("Quantidade de Títulos Bem Avaliados")

        # Transformar os dados para o formato longo
        good_titles_df = pd.melt(
            data["qualidade_catalogo"],
            id_vars=["provedor"],
            value_vars=["qtd_titulos_7plus", "qtd_titulos_8plus"],
            var_name="categoria",
            value_name="quantidade",
        )
        good_titles_df["categoria"] = good_titles_df["categoria"].map(
            {"qtd_titulos_7plus": "Nota IMDb >= 7", "qtd_titulos_8plus": "Nota IMDb >= 8"}
        )

        fig = px.bar(
            good_titles_df,
            x="provedor",
            y="quantidade",
            color="categoria",
            title="Quantidade de Títulos Bem Avaliados",
            height=400,
            barmode="group",
        )

        fig.update_layout(
            xaxis_title="Plataforma",
            yaxis_title="Quantidade de Títulos",
            plot_bgcolor="white",
            legend_title_text="Nota IMDb",
        )

        st.plotly_chart(fig, use_container_width=True)

        # Análise detalhada
        st.subheader("Análise Detalhada")
        st.dataframe(data["qualidade_catalogo"], use_container_width=True)

    elif page == "Atualidade":
        st.header("Atualidade do Catálogo")

        col1, col2 = st.columns(2)

        with col1:
            # Gráfico de barras para ano médio de lançamento
            fig = plot_bar_chart(
                data["atualidade_catalogo"],
                "provedor",
                "ano_medio_lancamento",
                "Ano Médio de Lançamento por Plataforma",
                color_col="provedor",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Gráfico de barras para percentual de títulos recentes
            recent_df = pd.melt(
                data["atualidade_catalogo"],
                id_vars=["provedor"],
                value_vars=["perc_ultimos_5_anos", "perc_ultimos_2_anos"],
                var_name="categoria",
                value_name="percentual",
            )
            recent_df["categoria"] = recent_df["categoria"].map(
                {"perc_ultimos_5_anos": "Últimos 5 anos", "perc_ultimos_2_anos": "Últimos 2 anos"}
            )

            fig = px.bar(
                recent_df,
                x="provedor",
                y="percentual",
                color="categoria",
                title="Percentual de Títulos Recentes",
                height=400,
                barmode="group",
            )

            fig.update_layout(
                xaxis_title="Plataforma",
                yaxis_title="Percentual (%)",
                plot_bgcolor="white",
                legend_title_text="Período",
            )

            st.plotly_chart(fig, use_container_width=True)

        # Distribuição por décadas
        st.subheader("Distribuição de Títulos por Década")

        # Transformar os dados para o formato longo
        decades_df = pd.melt(
            data["distribuicao_decadas"],
            id_vars=["provedor"],
            value_vars=[
                "pre_1980s",
                "anos_1980s",
                "anos_1990s",
                "anos_2000s",
                "anos_2010s",
                "anos_2020s",
            ],
            var_name="decada",
            value_name="quantidade",
        )
        decades_df["decada"] = decades_df["decada"].map(
            {
                "pre_1980s": "Pré-1980",
                "anos_1980s": "Anos 1980",
                "anos_1990s": "Anos 1990",
                "anos_2000s": "Anos 2000",
                "anos_2010s": "Anos 2010",
                "anos_2020s": "Anos 2020",
            }
        )

        # Criar gráficos de área empilhada para cada plataforma
        for plataforma in data["distribuicao_decadas"]["provedor"].unique():
            st.write(f"### {plataforma}")

            platform_data = decades_df[decades_df["provedor"] == plataforma]

            fig = px.bar(
                platform_data,
                x="decada",
                y="quantidade",
                title=f"Distribuição por Década - {plataforma}",
                color="decada",
                height=300,
            )

            fig.update_layout(
                xaxis_title="Década",
                yaxis_title="Quantidade de Títulos",
                plot_bgcolor="white",
                showlegend=False,
            )

            st.plotly_chart(fig, use_container_width=True)

        # Análise detalhada
        st.subheader("Análise Detalhada")
        st.dataframe(data["atualidade_catalogo"], use_container_width=True)

    elif page == "Custo-Benefício":
        st.header("Custo-Benefício das Plataformas")

        col1, col2 = st.columns(2)

        with col1:
            # Gráfico de barras para mensalidades
            fig = plot_bar_chart(
                data["custo_beneficio"],
                "provedor",
                "mensalidade",
                "Preço Mensal por Plataforma (R$)",
                color_col="provedor",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Gráfico de barras para custo por título
            fig = plot_bar_chart(
                data["custo_beneficio"],
                "provedor",
                "custo_por_titulo",
                "Custo por Título (R$)",
                color_col="provedor",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Custo por título bem avaliado
        st.subheader("Custo por Título Bem Avaliado")

        # Transformar os dados para o formato longo
        cost_quality_df = pd.melt(
            data["custo_beneficio"],
            id_vars=["provedor"],
            value_vars=["custo_por_titulo", "custo_por_titulo_7plus"],
            var_name="categoria",
            value_name="custo",
        )
        cost_quality_df["categoria"] = cost_quality_df["categoria"].map(
            {
                "custo_por_titulo": "Todos os títulos",
                "custo_por_titulo_7plus": "Títulos com IMDb >= 7",
            }
        )

        fig = px.bar(
            cost_quality_df,
            x="provedor",
            y="custo",
            color="categoria",
            title="Comparação de Custo por Título",
            height=400,
            barmode="group",
        )

        fig.update_layout(
            xaxis_title="Plataforma",
            yaxis_title="Custo por Título (R$)",
            plot_bgcolor="white",
            legend_title_text="Categoria",
        )

        st.plotly_chart(fig, use_container_width=True)

        # Custo por categoria
        st.subheader("Custo por Categoria")

        # Transformar os dados para o formato longo
        cost_category_df = pd.melt(
            data["custo_beneficio"],
            id_vars=["provedor"],
            value_vars=["custo_por_filme", "custo_por_serie"],
            var_name="categoria",
            value_name="custo",
        )
        cost_category_df["categoria"] = cost_category_df["categoria"].map(
            {"custo_por_filme": "Filmes", "custo_por_serie": "Séries"}
        )

        fig = px.bar(
            cost_category_df,
            x="provedor",
            y="custo",
            color="categoria",
            title="Custo por Categoria (R$)",
            height=400,
            barmode="group",
        )

        fig.update_layout(
            xaxis_title="Plataforma",
            yaxis_title="Custo (R$)",
            plot_bgcolor="white",
            legend_title_text="Categoria",
        )

        st.plotly_chart(fig, use_container_width=True)

        # Gráfico de dispersão combinando preço e qualidade
        st.subheader("Relação entre Preço e Qualidade")

        # Juntar dados de preço e qualidade
        price_quality_df = pd.merge(
            data["custo_beneficio"][["provedor", "mensalidade", "total_titulos"]],
            data["qualidade_catalogo"][["provedor", "imdb_score_medio"]],
            on="provedor",
        )

        fig = px.scatter(
            price_quality_df,
            x="mensalidade",
            y="imdb_score_medio",
            size="total_titulos",
            color="provedor",
            hover_name="provedor",
            text="provedor",
            color_discrete_map=get_platform_colors(),
            title="Relação entre Preço e Qualidade",
            height=500,
        )

        fig.update_traces(textposition="top center")

        fig.update_layout(
            xaxis_title="Mensalidade (R$)", yaxis_title="Nota Média IMDb", plot_bgcolor="white"
        )

        st.plotly_chart(fig, use_container_width=True)

        # Análise detalhada
        st.subheader("Análise Detalhada")
        st.dataframe(data["custo_beneficio"], use_container_width=True)

    elif page == "Análise Técnica":
        st.header("Análise Técnica do Conteúdo")

        col1, col2 = st.columns(2)

        with col1:
            # Gráfico de barras para duração média de filmes
            fig = plot_bar_chart(
                data["duracao_categoria"],
                "provedor",
                "duracao_media_filmes",
                "Duração Média dos Filmes (minutos)",
                color_col="provedor",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Gráfico de barras para duração média de episódios
            fig = plot_bar_chart(
                data["duracao_categoria"],
                "provedor",
                "duracao_media_episodios",
                "Duração Média dos Episódios (minutos)",
                color_col="provedor",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Distribuição de filmes por faixa de duração
        st.subheader("Distribuição de Filmes por Faixa de Duração")

        # Transformar os dados para o formato longo
        duration_df = pd.melt(
            data["duracao_categoria"],
            id_vars=["provedor"],
            value_vars=["filmes_curtos", "filmes_medios", "filmes_longos"],
            var_name="categoria",
            value_name="quantidade",
        )
        duration_df["categoria"] = duration_df["categoria"].map(
            {
                "filmes_curtos": "Curtos (<90 min)",
                "filmes_medios": "Médios (90-120 min)",
                "filmes_longos": "Longos (>120 min)",
            }
        )

        for plataforma in data["duracao_categoria"]["provedor"].unique():
            st.write(f"### {plataforma}")

            platform_data = duration_df[duration_df["provedor"] == plataforma]

            fig = px.pie(
                platform_data,
                values="quantidade",
                names="categoria",
                title=f"Distribuição de Filmes por Duração - {plataforma}",
                color="categoria",
                height=300,
                color_discrete_sequence=px.colors.sequential.Viridis,
            )

            fig.update_traces(textinfo="percent+label")

            st.plotly_chart(fig, use_container_width=True)

        # Análise de exclusividade
        st.subheader("Análise de Exclusividade de Conteúdo")

        fig = px.bar(
            data["exclusividade"],
            x="provedor",
            y="percentual_exclusivo",
            color="provedor",
            title="Percentual de Conteúdo Exclusivo por Plataforma",
            height=400,
            color_discrete_map=get_platform_colors(),
        )

        fig.update_layout(
            xaxis_title="Plataforma", yaxis_title="Conteúdo Exclusivo (%)", plot_bgcolor="white"
        )

        st.plotly_chart(fig, use_container_width=True)

        # Análise detalhada
        st.subheader("Análise Detalhada")
        st.dataframe(data["duracao_categoria"], use_container_width=True)

    elif page == "Comparação Completa":
        st.header("Comparação Completa das Plataformas")

        # Selector para escolher plataforma específica ou todas
        selected_platforms = st.multiselect(
            "Selecione as plataformas para comparar:",
            options=data["tamanho_diversidade"]["provedor"].tolist(),
            default=data["tamanho_diversidade"]["provedor"].tolist(),
        )

        if not selected_platforms:
            st.warning("Por favor, selecione pelo menos uma plataforma.")
        else:
            # Filtrar dados para as plataformas selecionadas
            filtered_data = {
                key: value[value["provedor"].isin(selected_platforms)]
                for key, value in data.items()
            }

            # Criar gráfico de radar completo
            st.subheader("Comparação Multidimensional")

            # Criar um dataframe para o gráfico radar com dados normalizados
            radar_df = pd.DataFrame()
            radar_df["provedor"] = filtered_data["tamanho_diversidade"]["provedor"]

            # Adicionar métricas normalizadas
            radar_df["Quantidade"] = (
                filtered_data["tamanho_diversidade"]["total_titulos"]
                / data["tamanho_diversidade"]["total_titulos"].max()
                * 10
            )
            radar_df["Qualidade"] = (
                (filtered_data["qualidade_catalogo"]["imdb_score_medio"] - 6) / 2 * 10
            )
            radar_df["Custo-Benefício"] = 10 - (
                filtered_data["custo_beneficio"]["custo_por_titulo"]
                / data["custo_beneficio"]["custo_por_titulo"].max()
                * 10
            )
            radar_df["Recência"] = filtered_data["atualidade_catalogo"]["perc_ultimos_5_anos"] / 10
            radar_df["Exclusividade"] = filtered_data["exclusividade"]["percentual_exclusivo"] / 10
            radar_df["Diversidade"] = (
                5 + (filtered_data["tamanho_diversidade"]["perc_series"] - 50) / 10
            )  # Valor mais alto para mix equilibrado

            fig = plot_radar_chart(
                radar_df,
                [
                    "Quantidade",
                    "Qualidade",
                    "Custo-Benefício",
                    "Recência",
                    "Exclusividade",
                    "Diversidade",
                ],
                [
                    "Quantidade",
                    "Qualidade",
                    "Custo-Benefício",
                    "Recência",
                    "Exclusividade",
                    "Diversidade",
                ],
                "Comparação Multidimensional das Plataformas",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tabela de comparação detalhada
            st.subheader("Tabela Comparativa Detalhada")

            # Criar dataframe combinado com as principais métricas
            comparison_df = pd.DataFrame()
            comparison_df["Plataforma"] = filtered_data["tamanho_diversidade"]["provedor"]
            comparison_df["Mensalidade (R$)"] = filtered_data["custo_beneficio"]["mensalidade"]
            comparison_df["Total de Títulos"] = filtered_data["tamanho_diversidade"][
                "total_titulos"
            ]
            comparison_df["Filmes (%)"] = filtered_data["tamanho_diversidade"]["perc_filmes"]
            comparison_df["Séries (%)"] = filtered_data["tamanho_diversidade"]["perc_series"]
            comparison_df["Nota Média IMDb"] = filtered_data["qualidade_catalogo"][
                "imdb_score_medio"
            ]
            comparison_df["Títulos IMDb >= 7 (%)"] = filtered_data["qualidade_catalogo"][
                "perc_titulos_7plus"
            ]
            comparison_df["Conteúdo Recente (%)"] = filtered_data["atualidade_catalogo"][
                "perc_ultimos_5_anos"
            ]
            comparison_df["Duração Média Filmes (min)"] = filtered_data["duracao_categoria"][
                "duracao_media_filmes"
            ]
            comparison_df["Conteúdo Exclusivo (%)"] = filtered_data["exclusividade"][
                "percentual_exclusivo"
            ]
            comparison_df["Custo por Título (R$)"] = filtered_data["custo_beneficio"][
                "custo_por_titulo"
            ]

            st.dataframe(
                comparison_df.style.highlight_max(
                    subset=[
                        "Total de Títulos",
                        "Nota Média IMDb",
                        "Títulos IMDb >= 7 (%)",
                        "Conteúdo Recente (%)",
                        "Conteúdo Exclusivo (%)",
                    ],
                    color="lightgreen",
                ).highlight_min(
                    subset=["Mensalidade (R$)", "Custo por Título (R$)"], color="lightgreen"
                ),
                use_container_width=True,
            )

            # Análise de custo x valor
            st.subheader("Relação Custo x Valor")

            # Criar índice de valor combinado
            value_df = pd.DataFrame()
            value_df["Plataforma"] = filtered_data["tamanho_diversidade"]["provedor"]
            value_df["Mensalidade"] = filtered_data["custo_beneficio"]["mensalidade"]

            # Criar índice ponderado (exemplo simples)
            value_df["Índice de Valor"] = (
                filtered_data["tamanho_diversidade"]["total_titulos"]
                / data["tamanho_diversidade"]["total_titulos"].max()
                * 3
                + (filtered_data["qualidade_catalogo"]["imdb_score_medio"] - 6) / 2 * 3
                + filtered_data["atualidade_catalogo"]["perc_ultimos_5_anos"] / 100 * 2
                + filtered_data["exclusividade"]["percentual_exclusivo"] / 100 * 2
            )

            value_df["Custo-Benefício"] = value_df["Índice de Valor"] / value_df["Mensalidade"]

            fig = px.scatter(
                value_df,
                x="Mensalidade",
                y="Índice de Valor",
                size="Custo-Benefício",
                color="Plataforma",
                hover_name="Plataforma",
                text="Plataforma",
                color_discrete_map=get_platform_colors(),
                title="Relação entre Preço e Valor Agregado",
                height=500,
            )

            fig.update_traces(textposition="top center")

            fig.update_layout(
                xaxis_title="Mensalidade (R$)", yaxis_title="Índice de Valor", plot_bgcolor="white"
            )

            st.plotly_chart(fig, use_container_width=True)

            # Resumo de pontos fortes
            st.subheader("Resumo dos Pontos Fortes")

            strengths = {
                "Netflix": "Maior catálogo total e grande quantidade de conteúdo original.",
                "Amazon Prime Video": "Melhor relação custo-benefício e grande variedade de filmes.",
                "Disney+": "Melhor qualidade média (IMDb) e alto percentual de conteúdo exclusivo.",
                "MAX": "Conteúdo mais recente e excelente qualidade de séries.",
                "Globoplay": "Foco em conteúdo nacional e bom equilíbrio entre filmes e séries.",
                "Apple TV+": "Alta qualidade média (IMDb) e foco em produções exclusivas premiadas.",
                "Paramount+": "Boa variedade de conteúdo e preço competitivo.",
            }

            for platform in selected_platforms:
                if platform in strengths:
                    st.info(f"**{platform}**: {strengths[platform]}")


# Executar o aplicativo Streamlit
if __name__ == "__main__":
    main()
