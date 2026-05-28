import json
import re
from dataclasses import asdict
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
    """Fetch and parse a single Pokémon page."""
    if name is None or name.strip() == "":
        logger.warning("Empty name provided, skipping.")
        return None

    # allow Unicode word chars, spaces and common punctuation used in Pokémon names
    if not re.match(r"^[\w\s\-\.'♂♀:]+$", name, re.UNICODE):
        logger.warning("Name '%s' contains unsupported characters, skipping.", name)
        return None

    # Normalize name into Bulbapedia page form: spaces -> underscores
    name_part = name.strip().replace(" ", "_")
    # Percent-encode but keep characters Bulbapedia typically allows in-page titles
    from urllib.parse import quote
    encoded_name = quote(name_part, safe="'._-()♂♀:")
    page = f"{encoded_name}_(Pok%C3%A9mon)"
    url = f"https://bulbapedia.bulbagarden.net/wiki/{page}"

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            resp.raise_for_status()
            text = await resp.text()
        soup = BeautifulSoup(text, "html.parser")
        pokemon = await parse_pokemon(soup)
        return pokemon
    except Exception as exc:
        logger.error("Error to fetch/parse %s (url=%s): %s", name, url, exc)
        return None


def pokemon_to_dict(pokemon: Pokemon) -> Dict[str, Any]:
    return asdict(pokemon)


def _print_search_results(requested_names: list[str], existing_by_name: Dict[str, Pokemon], fetched_by_requested: Dict[str, Pokemon]):
    results = []
    print("\n=== Search Results ===")
    for name in requested_names:
        key = name.lower()
        if key in fetched_by_requested:
            pokemon = fetched_by_requested[key]
            source = "crawler"
            print(f"✔ {name}: obtained via crawler ({pokemon.name})")
        elif key in existing_by_name:
            pokemon = existing_by_name[key]
            source = "json"
            print(f"✔ {name}: present in local JSON ({pokemon.name})")
        else:
            pokemon = None
            source = "failed"
            print(f"✖ {name}: could not be obtained")

        if pokemon is not None:
            item = pokemon_to_dict(pokemon)
            item["source"] = source
            results.append(item)

    if results:
        print("\n--- Organized data ---")
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("No valid results to display.")


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

    print(f"Starting search for: {', '.join(names)}")
    existing = get_pokemons(Path('pokemons.json'))
    existing_by_name = {p.name.lower(): p for p in existing}
    to_fetch = [name for name in names if name.lower() not in existing_by_name]

    if existing_by_name:
        existing_matches = [name for name in names if name.lower() in existing_by_name]
        if existing_matches:
            print(f"Already present in JSON: {', '.join(existing_matches)}")

    if not to_fetch:
        print("All Pokémon already exist in JSON. Nothing to do.")
        _print_search_results(names, existing_by_name, {})
        return

    print(f"Searching for {len(to_fetch)} new Pokémon via crawler: {', '.join(to_fetch)}")
    results = asyncio.run(_run_all(to_fetch, concurrency=5))
    fetched_by_requested = {to_fetch[i].lower(): p for i, p in enumerate(results) if p}
    new_pokemons = [p for p in results if p]

    if not new_pokemons:
        logger.warning("No Pokémon obtained.")
        _print_search_results(names, existing_by_name, fetched_by_requested)
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
        print(f"Added {added} new Pokémon to the file.")
    else:
        print("No new Pokémon to add.")

    _print_search_results(names, existing_by_name, fetched_by_requested)

def pokemon_from_dict(data: Dict[str, Any]) -> Pokemon:
    stats_data = data.get("stats") or {}
    evolution_data = data.get("evolution") or {}
    if isinstance(evolution_data, dict):
        next_val = evolution_data.get("next")
        if isinstance(next_val, str):
            evolution_data["next"] = [next_val] if next_val else []
        elif next_val is None:
            evolution_data["next"] = []

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
    caminho_arquivo = Path(caminho_arquivo)
    try:
        with caminho_arquivo.open("r", encoding="utf-8") as arquivo:
            lista_pokemons = json.load(arquivo)
            pokemons = [pokemon_from_dict(item) for item in lista_pokemons if isinstance(item, dict)]            
            logger.info(f"Loaded Pokémon from {caminho_arquivo}: {len(pokemons)}")
            return pokemons

    except FileNotFoundError:
        caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
        caminho_arquivo.write_text("[]", encoding="utf-8")
        logger.info(f"File '{caminho_arquivo}' not found. Created new empty JSON array.")
        return []
    except json.JSONDecodeError:        
        logger.error(f"Error: File '{caminho_arquivo}' does not contain valid JSON.")
        return []

if __name__ == "__main__":
    import sys

    def _parse_cli_names(tokens: list[str]) -> list[str]:
        """Group CLI tokens into Pokémon names when users omit quotes.

        Examples:
        - ['Mr.', 'Mime'] -> ['Mr. Mime']
        - ['Mr', 'Mime'] -> ['Mr Mime']
        - ['Pikachu'] -> ['Pikachu']
        """
        if not tokens:
            return []
        grouped: list[str] = []
        i = 0
        prefixes = {"Mr", "Mr.", "Mrs", "Mrs.", "Ms", "Ms.", "Dr", "Dr.", "Sr", "Sr.", "Jr", "Jr."}
        while i < len(tokens):
            tok = tokens[i]
            # If token is a known prefix or ends with a dot, join with the next token
            if (tok in prefixes or tok.endswith('.')) and i + 1 < len(tokens):
                grouped.append(f"{tok} {tokens[i+1]}")
                i += 2
                continue
            # If the NEXT token is a known prefix (e.g., 'Mime' followed by 'Jr.'), join current + next
            if i + 1 < len(tokens) and tokens[i+1] in prefixes:
                grouped.append(f"{tok} {tokens[i+1]}")
                i += 2
                continue
            # If next token is a gender symbol, combine without space (e.g., Nidoran ♀)
            if i + 1 < len(tokens) and tokens[i+1] in {"♀", "♂"}:
                grouped.append(f"{tok}{tokens[i+1]}")
                i += 2
                continue
            grouped.append(tok)
            i += 1
        return grouped

    args = sys.argv[1:]
    names = _parse_cli_names(args)
    if not names:
        logger.info("Example: python crawler.py Pikachu 'Mr. Mime' 'Farfetch\'d'")
    else:
        crawl(names)