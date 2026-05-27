# main.py
import asyncio
from fastapi import FastAPI, Query
from crawler import crawl

app = FastAPI(title="PokeCrawler API")

@app.get("/crawl")
async def trigger_crawler(names: str = Query(..., description="Nomes dos pokémons separados por vírgula")):
    # Transforma a string "Pikachu, Charizard" em uma lista ['Pikachu', 'Charizard']
    lista_nomes = [name.strip() for name in names.split(",")]
    
    # IMPORTANTE: Como o seu crawler original usa 'asyncio.run()' internamente,
    # precisamos rodá-lo em uma thread separada para não travar o FastAPI
    # e evitar erros de loops assíncronos conflitantes.
    await asyncio.to_thread(crawl, lista_nomes)
    
    return {
        "status": "Processamento concluído com sucesso!",
        "solicitados": lista_nomes
    }