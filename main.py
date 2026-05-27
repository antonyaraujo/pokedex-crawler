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
# 1. EXECUTAR CRAWLER POR POKÉMON (Apenas se não existirem no JSON)
# -----------------------------------------------------------------------------
@app.post("/pokemons/crawl", summary="Executa o crawler para novos pokémons")
async def trigger_crawler(
    names: str = Query(..., description="Nomes dos pokémons separados por vírgula. Ex: Pikachu, Charizard")
):
    # Transforma a string recebida em uma lista de nomes limpos
    lista_nomes = [name.strip() for name in names.split(",") if name.strip()]
    
    if not lista_nomes:
        raise HTTPException(status_code=400, detail="Por favor, forneça ao menos um nome válido.")
    
    # Como a função crawl() original executa um 'asyncio.run()' internamente,
    # rodamos ela em uma thread separada para não causar conflitos com o loop do FastAPI.
    await asyncio.to_thread(crawl, lista_nomes)
    
    return {
        "status": "Sucesso",
        "mensagem": "O processo do crawler foi finalizado. Verifique os logs para detalhes.",
        "solicitados": lista_nomes
    }


# -----------------------------------------------------------------------------
# 2. PEGAR TODOS OS POKÉMONS JÁ EXISTENTES NO JSON
# -----------------------------------------------------------------------------
@app.get("/pokemons", summary="Lista todos os pokémons salvos no arquivo JSON")
def list_all_pokemons():
    # Reutiliza sua função original para ler o arquivo JSON
    lista_pokes = get_pokemons(JSON_PATH)
    
    # Transforma os objetos Python Dataclass em dicionários JSON válidos
    return [pokemon_to_dict(p) for p in lista_pokes]


# -----------------------------------------------------------------------------
# 3. DELETAR UM POKÉMON DO JSON
# -----------------------------------------------------------------------------
@app.delete("/pokemons/{name}", summary="Deleta um pokémon do arquivo JSON pelo nome")
def delete_pokemon(name: str):
    # Carrega a lista atual de pokémons do arquivo
    lista_pokes = get_pokemons(JSON_PATH)
    
    tamanho_original = len(lista_pokes)
    
    # Filtra a lista mantendo apenas os pokémons que NÃO possuem o nome informado (ignora maiúsculas/minúsculas)
    lista_filtrada = [p for p in lista_pokes if p.name.lower() != name.lower()]
    
    # Se o tamanho da lista não mudou, significa que o Pokémon não estava lá
    if len(lista_filtrada) == tamanho_original:
        raise HTTPException(
            status_code=404, 
            detail=f"O Pokémon '{name}' não foi encontrado no arquivo JSON."
        )
    
    # Sobrescreve o arquivo JSON com a nova lista filtrada
    save_json(lista_filtrada, JSON_PATH)
    
    return {
        "status": "Sucesso",
        "mensagem": f"O Pokémon '{name}' foi removido com sucesso do arquivo.",
        "total_restante": len(lista_filtrada)
    }