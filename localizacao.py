import streamlit as st
import requests
import unicodedata

# =====================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# =====================================
st.set_page_config(
    page_title="Assistente de Trânsito Leonardo Medina 🚗",
    page_icon="🚗",
    layout="centered"
)

# =====================================
# CONFIGURAÇÃO DA API
# =====================================
# ⚠️ SUBSTITUA PELO SEU TOKEN REAL DO CONSOLE DA TOMTOM
API_KEY = "oUYseAomdG8aVyfJXWu0wRyaO53mC19L" 

# =====================================
# FUNÇÕES AUXILIARES E APIS
# =====================================
def limpar_endereco(endereco):
    """Melhora a busca adicionando contexto do Brasil automaticamente"""
    endereco_normalizado = unicodedata.normalize('NFKD', endereco).encode('ascii', 'ignore').decode('utf-8')
    return f"{endereco_normalizado}, Brazil"

def obter_coordenadas_tomtom(endereco):
    """Busca coordenadas usando Search & Places API da TomTom"""
    endereco_limpo = limpar_endereco(endereco)
    url = f"https://api.tomtom.com/search/2/search/{endereco_limpo}.json"

    params = {
        "key": API_KEY,
        "limit": 1,
        "countrySet": "BR",
        "language": "pt-BR"
    }

    try:
        resposta = requests.get(url, params=params)
        if resposta.status_code != 200:
            return None
            
        dados = resposta.json()
        if "results" not in dados or len(dados["results"]) == 0:
            return None

        pos = dados["results"][0]["position"]
        return (pos["lat"], pos["lon"])
    except Exception:
        return None

def consultar_rota_tomtom(origem, destino):
    coord_origem = obter_coordenadas_tomtom(origem)
    if not coord_origem:
        return {"erro": f"Não foi possível localizar a origem: '{origem}'"}

    coord_destino = obter_coordenadas_tomtom(destino)
    if not coord_destino:
        return {"erro": f"Não foi possível localizar o destino: '{destino}'"}

    url = (
        "https://api.tomtom.com/routing/1/calculateRoute/"
        f"{coord_origem[0]},{coord_origem[1]}:"
        f"{coord_destino[0]},{coord_destino[1]}/json"
    )

    params = {
        "key": API_KEY,
        "traffic": "true"
    }

    try:
        resposta = requests.get(url, params=params)
        if resposta.status_code != 200:
            return {"erro": f"Código de erro da API: {resposta.status_code}"}
            
        dados = resposta.json()
        if "routes" not in dados or len(dados["routes"]) == 0:
            return {"erro": "Não foi possível calcular a rota entre esses pontos"}

        summary = dados["routes"][0]["summary"]
        
        distancia_km = round(summary["lengthInMeters"] / 1000, 1)
        tempo_minutos = round(summary["travelTimeInSeconds"] / 60)
        atraso_minutos = round(summary.get("trafficDelayInSeconds", 0) / 60)

        return {
            "origem": origem,
            "destino": destino,
            "distancia": distancia_km,
            "tempo": tempo_minutos,
            "atraso": atraso_minutos
        }
    except Exception as e:
        return {"erro": f"Erro interno ao calcular rota: {str(e)}"}

@st.cache_data(show_spinner=False)
def validar_api_key():
    """Verifica se a API Key está funcionando (com cache para não repetir a cada clique)"""
    url = "https://api.tomtom.com/routing/1/calculateRoute/0,0:1,1/json"
    params = {"key": API_KEY, "traffic": "false"}
    try:
        resposta = requests.get(url, params=params, timeout=5)
        return resposta.status_code == 200
    except Exception:
        return False

# =====================================
# INTERFACE INTERATIVA (STREAMLIT)
# =====================================
st.title("🚗 Assistente de Trânsito — TomTom")
st.markdown("Calcule rotas, distância e a situação do trânsito em tempo real.")

# Validação visual da API Key
if API_KEY in ["SUA_CHAVE_TOMTOM_AQUI", ""]:
    st.error("⚠️ **Aviso Crítico:** API KEY não configurada!")
    st.info("""
    **Passo a passo para ativar:**
    1. Acesse o [TomTom Developer Portal](https://developer.tomtom.com/).
    2. Crie sua conta e vá em *Console* ➡️ *API Keys*.
    3. Copie sua chave e cole na variável `API_KEY` deste código.
    """)
else:
    if not validar_api_key():
        st.warning("⚠️ **Chave inválida ou sem permissões.** Certifique-se de ativar 'Search' e 'Routing' no painel da TomTom.")

# Formulário de entrada de dados
with st.form("form_rota"):
    st.subheader("📍 Planeje seu Trajeto")
    
    origem = st.text_input("Local de PARTIDA (Origem):", placeholder="Ex: Av. Paulista, 1000 - São Paulo")
    destino = st.text_input("Destino DESEJADO:", placeholder="Ex: Aeroporto de Congonhas - São Paulo")
    
    # Botão de envio do formulário
    botao_calcular = st.form_submit_button("Calcular Rota")

# Processamento do clique do botão
if botao_colored := botao_calcular:
    if not origem.strip() or not destino.strip():
        st.error("❌ Os campos de Origem e Destino não podem ficar vazios.")
    else:
        with st.spinner("📡 Consultando dados na TomTom API..."):
            resultado = consultar_rota_tomtom(origem, destino)
            
        if "erro" in resultado:
            st.error(f"❌ ERRO: {resultado['erro']}")
            if "localizar" in resultado["erro"].lower():
                st.info("💡 **Dica:** Tente fornecer endereços mais completos (incluindo cidade e estado).")
        else:
            st.success("✅ Rota calculada com sucesso!")
            
            # Layout em colunas para os resultados numéricos
            col1, col2, col3 = st.columns(3)
            col1.metric(label="📏 Distância", value=f"{resultado['distancia']} km")
            col2.metric(label="⏱️ Tempo Estimado", value=f"{resultado['tempo']} min")
            col3.metric(label="🚦 Atraso por Trânsito", value=f"{resultado['atraso']} min")
            
            # Alerta sobre as condições de trânsito
            st.markdown("---")
            st.subheader("📊 Análise do Tráfego")
            if resultado["atraso"] > 15:
                st.error("🔴 **ATENÇÃO:** Trânsito muito **PESADO** neste trajeto! Considere rotas alternativas ou adie a saída.")
            elif resultado["atraso"] > 5:
                st.warning("🟡 **Atenção:** Há registros de trânsito **LEVE** ou moderado no caminho.")
            else:
                st.success("🟢 **Trânsito NORMAL:** Fluxo livre. Boa viagem! 🚗")
