import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import base64

# Configuração da página
st.set_page_config(
    page_title="Simulador de Absorção com Validação Experimental",
    page_icon=":test_tube:",
    layout="wide"
)

# CSS personalizado
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 24px;
    }
    .stFileUploader>div>div>button {
        background-color: #2196F3;
        color: white;
    }
    .plot-container {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .header {
        color: #2c3e50;
        border-bottom: 2px solid #4CAF50;
        padding-bottom: 10px;
    }
    .error-box {
        background-color: #ffebee;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #f44336;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# Título
st.title("🔬 Simulador de Absorção com Validação Experimental")
st.markdown("""
Este simulador permite comparar dados experimentais de célula de Arnold com modelos teóricos 
de coeficiente de difusão (D<sub>AB</sub>), calculando erros e gerando visualizações.
""", unsafe_allow_html=True)

# Sidebar - Parâmetros teóricos
with st.sidebar:
    st.header("⚙️ Parâmetros Teóricos")

    # Sistema químico
    sistema = st.selectbox("Sistema químico:",
                           ["Acetona-Ar", "Água-Ar", "CO₂-Água", "Personalizado"])

    if sistema == "Personalizado":
        M_A = st.number_input("Massa molar do soluto (g/mol):", value=58.08)
        rho_A = st.number_input("Densidade do soluto (kg/m³):", value=791.0)
    else:
        if sistema == "Acetona-Ar":
            M_A = 58.08
            rho_A = 791.0
        elif sistema == "Água-Ar":
            M_A = 18.02
            rho_A = 997.0
        else:  # CO₂-Água
            M_A = 44.01
            rho_A = 997.0

        st.info(f"Parâmetros para {sistema}:")
        st.write(f"- Massa molar: {M_A} g/mol")
        st.write(f"- Densidade: {rho_A} kg/m³")

    # Pressão e temperatura
    P = st.number_input("Pressão total (atm):", value=1.0, step=0.1)
    T = st.number_input("Temperatura (K):", value=318.0, step=1.0)

    # Coeficiente teórico
    D_AB_teorico = st.number_input("D_AB teórico (m²/s ×10^(-5)):",
                                   value=1.09, step=0.01) * 1e-5

# Função para cálculo teórico de D_AB (Fuller et al.)


def calcular_D_AB_teorico(T, D_AB_ref, T_ref=273.0):
    return D_AB_ref * (T/T_ref)**1.75

# Função modelo para ajuste dos dados experimentais


def modelo_diffusao(t, D_AB):
    R = 8.314  # J/(mol·K)
    P_A1 = 0.66782e5  # Pa (pressão de vapor da acetona a 45°C)
    P_A2 = 0
    P_total = P * 101325  # Convertendo atm para Pa

    termo = (2 * M_A * D_AB * P_total) / (rho_A * R * T)
    log_term = np.log((P_total - P_A2)/(P_total - P_A1))
    return np.sqrt(termo * log_term * t)

# Processamento de dados


def processar_dados(df):
    try:
        # Verificar colunas necessárias
        if 'tempo' not in df.columns or 'altura' not in df.columns:
            st.error("O arquivo CSV deve conter colunas 'tempo' (s) e 'altura' (m)")
            return None

        # Converter altura para metros se estiver em cm
        if df['altura'].max() < 1:  # Assume que está em metros
            pass
        else:
            df['altura'] = df['altura'] / 100  # Convertendo cm para m

        # Calcular Z² - Z0²
        z0 = df['altura'].iloc[0]
        df['delta_z2'] = df['altura']**2 - z0**2

        return df

    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        return None


# Conteúdo principal
tab1, tab2, tab3 = st.tabs(["Importar Dados", "Simulação", "Resultados"])

with tab1:
    st.header("📤 Importar Dados Experimentais")

    uploaded_file = st.file_uploader("Carregue seu arquivo CSV com dados da célula de Arnold:",
                                     type=["csv"])

    if uploaded_file is not None:
        try:
            df_exp = pd.read_csv(uploaded_file)
            st.success("Arquivo carregado com sucesso!")

            # Processar dados
            df_exp = processar_dados(df_exp)

            if df_exp is not None:
                st.write("Visualização dos dados:")
                st.dataframe(df_exp.head())

                # Plotar dados brutos
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(df_exp['tempo'], df_exp['altura']*100,
                        'bo-', label='Dados Experimentais')
                ax.set_xlabel('Tempo (s)')
                ax.set_ylabel('Altura (cm)')
                ax.set_title('Variação da Altura do Menisco vs Tempo')
                ax.grid(True)
                ax.legend()
                st.pyplot(fig)

                # Salvar dados processados na sessão
                st.session_state.df_exp = df_exp

        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {str(e)}")

with tab2:
    st.header("📊 Simulação e Ajuste de Curva")

    if 'df_exp' not in st.session_state:
        st.warning(
            "Por favor, importe dados experimentais na aba 'Importar Dados'.")
    else:
        df_exp = st.session_state.df_exp

        # Ajuste de curva para determinar D_AB experimental
        try:
            popt, pcov = curve_fit(modelo_diffusao,
                                   df_exp['tempo'],
                                   df_exp['altura'],
                                   p0=[1e-5])  # Valor inicial para D_AB

            D_AB_exp = popt[0]
            st.session_state.D_AB_exp = D_AB_exp

            # Calcular valores ajustados
            t_range = np.linspace(0, df_exp['tempo'].max(), 100)
            h_ajustado = modelo_diffusao(t_range, D_AB_exp)

            # Plotar ajuste
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(df_exp['tempo'], df_exp['altura'] *
                    100, 'bo', label='Dados Experimentais')
            ax.plot(t_range, h_ajustado*100, 'r-',
                    label=f'Ajuste (D_AB = {D_AB_exp:.2e} m²/s)')
            ax.set_xlabel('Tempo (s)')
            ax.set_ylabel('Altura (cm)')
            ax.set_title('Ajuste de Curva para Determinar D_AB')
            ax.grid(True)
            ax.legend()
            st.pyplot(fig)

            # Plotar Z² vs tempo
            fig2, ax2 = plt.subplots(figsize=(10, 5))
            ax2.plot(df_exp['tempo'], df_exp['delta_z2'],
                     'go-', label='Dados Experimentais')

            # Calcular linha teórica
            z2_teorico = modelo_diffusao(
                df_exp['tempo'], D_AB_exp)**2 - df_exp['altura'].iloc[0]**2
            ax2.plot(df_exp['tempo'], z2_teorico,
                     'm--', label='Modelo Teórico')

            ax2.set_xlabel('Tempo (s)')
            ax2.set_ylabel('Z² - Z0² (m²)')
            ax2.set_title('Análise de Difusão: Z² vs Tempo')
            ax2.grid(True)
            ax2.legend()
            st.pyplot(fig2)

        except Exception as e:
            st.error(f"Erro no ajuste de curva: {str(e)}")

with tab3:
    st.header("📈 Resultados e Comparação")

    if 'D_AB_exp' not in st.session_state:
        st.warning("Execute a simulação na aba anterior para ver os resultados.")
    else:
        D_AB_exp = st.session_state.D_AB_exp
        D_AB_teorico_ajustado = calcular_D_AB_teorico(T, D_AB_teorico)

        # Calcular erros
        erro_absoluto = abs(D_AB_teorico_ajustado - D_AB_exp)
        erro_relativo = erro_absoluto / D_AB_teorico_ajustado * 100

        # Mostrar resultados
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("D_AB Experimental",
                      f"{D_AB_exp:.2e} m²/s",
                      help="Valor obtido do ajuste dos dados experimentais")

        with col2:
            st.metric("D_AB Teórico Ajustado",
                      f"{D_AB_teorico_ajustado:.2e} m²/s",
                      help=f"Valor teórico ajustado para T = {T} K")

        with col3:
            st.metric("Erro Relativo",
                      f"{erro_relativo:.1f}%",
                      delta=f"{erro_absoluto:.2e} m²/s (absoluto)",
                      delta_color="inverse")

        # Explicação dos resultados
        with st.expander("Interpretação dos Resultados"):
            st.markdown("""
            - **D_AB Experimental**: Valor obtido através do ajuste dos dados da célula de Arnold, 
            utilizando o modelo de difusão pseudo-estacionária.
            
            - **D_AB Teórico Ajustado**: Valor de referência da literatura ajustado para a temperatura 
            do experimento usando a correlação de Fuller et al. (D<sub>AB</sub> ∝ T<sup>1.75</sup>).
            
            - **Erros**: 
              - Valores abaixo de 15% são considerados excelentes para experimentos didáticos.
              - Erros elevados podem indicar problemas na coleta de dados (vazamentos, temperatura não uniforme) 
              ou limitações do modelo teórico.
            """, unsafe_allow_html=True)

        # Exportar resultados
        st.download_button(
            label="📥 Exportar Resultados (CSV)",
            data=pd.DataFrame({
                'Parametro': ['D_AB_Experimental', 'D_AB_Teorico', 'Erro_Relativo'],
                'Valor': [D_AB_exp, D_AB_teorico_ajustado, erro_relativo],
                'Unidade': ['m²/s', 'm²/s', '%']
            }).to_csv(index=False),
            file_name="resultados_difusao.csv",
            mime="text/csv"
        )

# Rodapé
st.markdown("---")
st.markdown("""
**Desenvolvido para o Laboratório de Processos - UFAM**  
Luis Henrique - Engenharia Química  
Baseado nos experimentos com a Célula de Arnold UpControl
""")