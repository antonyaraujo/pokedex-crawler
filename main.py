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
TXT_PATH = Path("pokemons.txt")  # Novo caminho para o arquivo de texto na nuvem

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

# -----------------------------------------------------------------------------
# NOVA ROTA: OBTENER LISTA DE NOMES DO TXT NA NUVEM
# -----------------------------------------------------------------------------
@app.get("/listAll", summary="Retorna os nomes do arquivo pokemons.txt como um array de strings")
def obter_lista_do_txt():
    # TXT_PATH deve estar definido apontando para Path("pokemons.txt")
    if not TXT_PATH.exists():
        raise HTTPException(
            status_code=404, 
            detail="O arquivo 'pokemons.txt' não foi encontrado no servidor do Render."
        )
        
    try:
        with TXT_PATH.open("r", encoding="utf-8") as arquivo:
            # Lê cada linha, limpa os espaços vazios (\n) e ignora linhas que estejam em branco
            lista_nomes = [linha.strip() for linha in arquivo if linha.strip()]
            
        # Retorna diretamente o array de strings Puro
        return lista_nomes
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao ler o arquivo de texto no servidor: {str(e)}"
        )