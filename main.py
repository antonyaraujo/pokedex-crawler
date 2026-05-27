import asyncio
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException

# Importando as funções utilitárias dos seus arquivos originais
from crawler import crawl, get_pokemons, pokemon_to_dict
from storage import save_json

app = FastAPI(
    title="PokeCrawler API",
    description="API para buscar, listar e gerenciar Pokémons localmente"
)

# Caminho do arquivo JSON definido nos seus scripts
JSON_PATH = Path("pokemons.json")

# -----------------------------------------------------------------------------
# 1. EXECUTAR CRAWLER POR POKÉMON (Retorna o objeto completo)
# -----------------------------------------------------------------------------
@app.post("/pokemons/crawl", summary="Executa o crawler para novos pokémons e retorna os objetos")
async def trigger_crawler(
    names: str = Query(..., description="Nomes dos pokémons separados por vírgula. Ex: Pikachu, Charizard")
):
    # Transforma a string recebida em uma lista de nomes limpos
    lista_nomes = [name.strip() for name in names.split(",") if name.strip()]
    
    if not lista_nomes:
        raise HTTPException(status_code=400, detail="Por favor, forneça ao menos um nome válido.")
    
    # Executa o crawler original em uma thread separada para não travar o FastAPI
    await asyncio.to_thread(crawl, lista_nomes)
    
    # Carrega a lista atualizada de pokémons do arquivo JSON
    lista_atualizada = get_pokemons(JSON_PATH)
    
    # Filtra e transforma em dicionário apenas os Pokémons que foram solicitados nesta requisição
    resultado_pokemons = []
    nomes_solicitados_lower = [n.lower() for n in lista_nomes]
    
    for poke in lista_atualizada:
        if poke.name.lower() in nomes_solicitados_lower:
            resultado_pokemons.append(pokemon_to_dict(poke))
            
    return {
        "status": "Sucesso",
        "mensagem": "Crawler finalizado. Abaixo estão os dados dos pokémons solicitados.",
        "pokemons": resultado_pokemons
    }


# -----------------------------------------------------------------------------
# 2. PEGAR TODOS OS POKÉMONS JÁ EXISTENTES NO JSON
# -----------------------------------------------------------------------------
@app.get("/pokemons", summary="Lista todos os pokémons salvos no arquivo JSON")
def list_all_pokemons():
    lista_pokes = get_pokemons(JSON_PATH)
    return [pokemon_to_dict(p) for p in lista_pokes]


# -----------------------------------------------------------------------------
# 3. NOVA ROTA: PEGAR UM POKÉMON ESPECÍFICO PELO NOME
# -----------------------------------------------------------------------------
@app.get("/pokemons/{name}", summary="Retorna o objeto JSON de um pokémon específico pelo nome")
def get_single_pokemon(name: str):
    lista_pokes = get_pokemons(JSON_PATH)
    
    # Procura o pokémon correspondente na lista (ignorando maiúsculas/minúsculas)
    for poke in lista_pokes:
        if poke.name.lower() == name.lower():
            return pokemon_to_dict(poke)
            
    # Caso não encontre, gera uma exceção HTTP 404
    raise HTTPException(
        status_code=404, 
        detail=f"O Pokémon '{name}' não foi encontrado no arquivo de registros."
    )


# -----------------------------------------------------------------------------
# 4. DELETAR UM POKÉMON DO JSON
# -----------------------------------------------------------------------------
@app.delete("/pokemons/{name}", summary="Deleta um pokémon do arquivo JSON pelo nome")
def delete_pokemon(name: str):
    lista_pokes = get_pokemons(JSON_PATH)
    tamanho_original = len(lista_pokes)
    
    lista_filtrada = [p for p in lista_pokes if p.name.lower() != name.lower()]
    
    if len(lista_filtrada) == tamanho_original:
        raise HTTPException(
            status_code=404, 
            detail=f"O Pokémon '{name}' não foi encontrado no arquivo JSON."
        )
    
    save_json(lista_filtrada, JSON_PATH)
    
    return {
        "status": "Sucesso",
        "mensagem": f"O Pokémon '{name}' foi removido com sucesso do arquivo.",
        "total_restante": len(lista_filtrada)
    }

def obter_nomes_do_txt(caminho_arquivo: str | Path = "pokemons.txt") -> list[str]:
    caminho = Path(caminho_arquivo)
    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            # Lê cada linha, remove espaços/quebras de linha (\n) e ignora linhas vazias
            return [linha.strip() for linha in arquivo if linha.strip()]
    except FileNotFoundError:
        print(f"Aviso: O arquivo '{caminho}' não foi encontrado. Retornando lista vazia.")
        return []

import requests
from pathlib import Path

def sincronizar_txt_com_api(txt_path="pokemons.txt", api_url="http://127.0.0.1:8000"):
    caminho = Path(txt_path)
    if not caminho.exists():
        print(f"Erro: Arquivo '{txt_path}' não foi encontrado para leitura.")
        return
    
    # 1. Extrai a lista de strings do arquivo TXT
    with caminho.open("r", encoding="utf-8") as arquivo:
        nomes = [linha.strip() for linha in arquivo if linha.strip()]
        
    if not nomes:
        print("O arquivo TXT está vazio. Nada para enviar.")
        return
        
    # 2. Formata os nomes em uma única string separada por vírgula
    nomes_query = ",".join(nomes)
    
    # 3. Dispara a requisição POST para o servidor
    print(f"Enviando {len(nomes)} pokémons para o Crawler na API...")
    try:
        response = requests.post(f"{api_url}/pokemons/crawl", params={"names": nomes_query})
        if response.status_code == 200:
            print("Sucesso na execução! Resposta da API:", response.json())
        else:
            print(f"Falha na API (Status {response.status_code}):", response.text)
    except requests.exceptions.ConnectionError:
        print("Não foi possível conectar à API. O servidor está rodando?")

# Execução do utilitário de envio
if __name__ == "__main__":
    sincronizar_txt_com_api()