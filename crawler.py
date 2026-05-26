import json
from typing import Any, Dict, List
import asyncio
from pathlib import Path
import aiohttp
from bs4 import BeautifulSoup
from parser import parse_pokemon
from pokeTypes import Pokemon, BaseStats, Evolution, Ability
from storage import save_json as storage_save_json
import logging

logger = logging.getLogger(__name__)
pokemons = []

## Gets the HTML soup and returns a Pokemon object with all the data filled in. 
# Each field of the pokemon object is filled by a specific function that extracts the data from the soup.
async def _fetch_and_parse(name: str, session: aiohttp.ClientSession) -> Pokemon | None:
    url = f'https://bulbapedia.bulbagarden.net/wiki/{name}'
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            resp.raise_for_status()
            text = await resp.text()
        soup = BeautifulSoup(text, "html.parser")
        pokemon = await parse_pokemon(soup)
        return pokemon
    except Exception as exc:
        logger.error("Error to fetch/parse %s: %s", name, exc)
        return None


## Main function to crawl a list of Pokémon names. 
# It checks if the Pokémon already exists in the JSON file, and if not, it fetches and parses the data, then saves it to the JSON file.
def crawl(names: list[str]):
    if not names:
        return

    async def _run_all(names_list: list[str], concurrency: int = 5):
        semaphore = asyncio.Semaphore(concurrency)
        connector = aiohttp.TCPConnector(limit=concurrency)
        async with aiohttp.ClientSession(connector=connector) as session:
            async def worker(name: str):
                async with semaphore:
                    return await _fetch_and_parse(name, session)

            tasks = [asyncio.create_task(worker(name)) for name in names_list]
            return await asyncio.gather(*tasks)

    existing = get_pokemons(Path('pokemons.json'))
    existing_by_name = {p.name.lower(): p for p in existing}
    to_fetch = [name for name in names if name.lower() not in existing_by_name]
    if not to_fetch:        
        logging.Logger.info("All pokémons already exist in JSON. Nothing to do.")
        return

    results = asyncio.run(_run_all(to_fetch, concurrency=5))
    new_pokemons = [p for p in results if p]
    if not new_pokemons:        
        logger.warning("No Pokémon obtained.")
        return

    added = 0
    for p in new_pokemons:
        if p.name.lower() not in existing_by_name:
            existing.append(p)
            existing_by_name[p.name.lower()] = p
            added += 1
        else:            
            logger.info(f"Pokémon {p.name} already exists — skipping save.")


    if added:
        storage_save_json(existing, Path('pokemons.json'))        
        logger.info(f"Added {added} new pokémons to the file.")
    else:        
        logger.info("There's not anything new to add.")

def pokemon_from_dict(data: Dict[str, Any]) -> Pokemon:
    stats_data = data.get("stats") or {}
    evolution_data = data.get("evolution") or {}
    abilities_data = data.get("abilities") or []

    abilities = []
    for item in abilities_data:
        if isinstance(item, dict):
            abilities.append(Ability(
                name=item.get("name", ""),
                category=item.get("type", item.get("category", ""))
            ))
        else:
            abilities.append(item)

    return Pokemon(
        name=data.get("name", ""),
        national_number=data.get("national_number", 0),
        category=data.get("category", ""),
        types=data.get("types", []),
        stats=BaseStats(**stats_data) if isinstance(stats_data, dict) else BaseStats(),
        evolution=Evolution(**evolution_data) if isinstance(evolution_data, dict) else Evolution(),
        abilities=abilities,
        image_path=data.get("image_path")
    )

## Reads a JSON file containing an array of Pokémon and returns a list of Pokemon instances.
def get_pokemons(caminho_arquivo: str | Path) -> List[Pokemon]:    
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
            lista_pokemons = json.load(arquivo)
            pokemons = [pokemon_from_dict(item) for item in lista_pokemons if isinstance(item, dict)]            
            logger.info(f"Loaded pokémons from {caminho_arquivo}: {len(pokemons)}")
            return pokemons

    except FileNotFoundError:        
        logger.error(f"Error: File '{caminho_arquivo}' not found.")
        return []
    except json.JSONDecodeError:        
        logger.error(f"Error: File '{caminho_arquivo}' does not contain valid JSON.")
        return []

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if not args:        
        logger.info("Example: python crawler.py Pikachu Bulbasaur Charmander")
    else:
        crawl(args)        