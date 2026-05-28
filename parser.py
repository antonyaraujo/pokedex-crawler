from bs4 import BeautifulSoup
from pokeTypes import BaseStats, Evolution, Pokemon 
import logging
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)
OUTPUT_DIR = Path("src/images")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PokeCrawler/1.0; "
        "+https://github.com/example/poke-crawler)"
    )
}

CONCURRENCY = 5  # max requests
MAX_RETRIES = 3
BACKOFF_BASE = 2.0   # delay to attempt

async def parse_pokemon(soup: BeautifulSoup) -> Pokemon:    
    """ Gets the HTML soup and returns a Pokemon object with all the data filled in. """
    pokemon = Pokemon()

    ## Crawl all data and fill the pokemon object with it. Each function is responsible for filling a specific field of the pokemon object, and they all receive the soup as input to extract the data from it.
    _parse_name(soup, pokemon)
    _parse_national_pokedex_number(soup, pokemon)
    _parse_category(soup, pokemon)
    _parse_types(soup, pokemon)
    _parse_stats(soup, pokemon)
    _parse_abilities(soup, pokemon)
    _parse_evolution(soup, pokemon)
    _parse_image_path(soup, pokemon)
    
    ## If the pokemon has an image URL, we try to download it and save the local path in the pokemon object. If the download fails, we log the error and keep the image_path as None.
    if pokemon.image_path:
        connector = aiohttp.TCPConnector(limit=CONCURRENCY)
        async with aiohttp.ClientSession(connector=connector) as session:
            await download_image(session, pokemon.image_path, OUTPUT_DIR / f"{pokemon.name}.png")
        local_path = f"src/images/{pokemon.name}.png"
        pokemon.image_path = local_path

    logger.info("Parsed Pokémon: %s (National #%d)", pokemon.name, pokemon.national_number)
    logger.debug("Details: %s", pokemon)
    return pokemon

## Gets Pokemon name from the soup and fills the pokemon object with it.
def _parse_name(soup: BeautifulSoup, pokemon: Pokemon) -> None:
    name = soup.find('big')
    if(name is None): 
        logger.warning("Pokemon's name not found")
        pokemon.name = "Unknown"
    else:
        pokemon.name = name.text
    return

## Gets the National Pokedex number from the soup and fills the pokemon object with it.
def _parse_national_pokedex_number(soup: BeautifulSoup, pokemon: Pokemon)-> None:
    value_search = soup.find_all('a', {'title': "List of Pokémon by National Pokédex number"})
    national_pokedex_number = -999
    if(len(value_search) == 0):
        logger.warning("National Pokedex number not found.")
        pokemon.national_number = 0
        return
    else:
        national_pokedex_number = (value_search[1].text).replace("#", '')    
        try:
            pokemon.national_number = int(national_pokedex_number)
        except Exception as exc:
            logger.error("Could not convert national number value %s to integer. Exception: %s", national_pokedex_number, exc)
    return

## Gets the Pokémon category from the soup and fills the pokemon object with it.
def _parse_category(soup: BeautifulSoup, pokemon: Pokemon)-> None:
    category = soup.find_all('a', {'title': "Pokémon category"})
    if(category is None or len(category) == 0):
        logger.warning("Category of the Pokémon not found.")
        pokemon.category = "Unknown"
    else:
        pokemon.category = category[0].text
    return

## Gets the Pokémon types from the soup and fills the pokemon object with them. 
def _parse_types(soup: BeautifulSoup, pokemon: Pokemon)-> None:
    types_extract = soup.select("table.roundy a[href*='_(type)'], td a[href*='_(type)']")
    seen: set[str] = set()
    types = []
    if(types_extract is None or len(types_extract) == 0):
        logger.warning("Types of the Pokémon not found.")
        pokemon.types = []
        return
    else:
        try:
            for a in types_extract:
                type_name = (a.text)
                if type_name and type_name not in seen:
                    seen.add(type_name)
                    if(type_name != 'Unknown'): 
                        types.append(type_name)
                    else: break
                if len(types) == 2:
                        break        
        except Exception as exc:
            logger.warning("Types not found: %s", exc)

        pokemon.types = types
    return

## Gets the Pokémon base stats from the soup and fills the pokemon object with them.
def _parse_stats(soup: BeautifulSoup, pokemon: Pokemon)-> None:
     
    # HP Value
    hp_base = soup.find('a', {'title': "HP"})    
    parent = hp_base.find_parent('div')
    if(hp_base is None or parent is None):
        logger.warning("HP stats of the Pokémon not found.")
        pokemon.stats = BaseStats()
        return
    else:
        try:
            hp = int((parent.find_next_sibling('div')).text)
        except Exception as exc:
            logger.error("Could not convert HP value to integer. Exception: %s", exc)
            hp = 0

    # Attack Value
    attack_base = soup.find('span', string="Attack")    
    parent = attack_base.find_parent('div')
    if(attack_base is None or parent is None):
        logger.warning("Attack stats of the Pokémon not found.")
        pokemon.stats = BaseStats(hp=hp)
        return
    else:
        try:
            attack = int((parent.find_next_sibling('div')).text)
        except Exception as exc:
            logger.error("Could not convert Attack value to integer. Exception: %s", exc)
            attack = 0

    # Defense Value
    defense_base = soup.find('span', string="Defense")    
    parent = defense_base.find_parent('div')
    if(defense_base is None or parent is None):
        logger.warning("Defense stats of the Pokémon not found.")
        pokemon.stats = BaseStats(hp=hp, attack=attack)
        return
    else:    
        try:
            defense = int((parent.find_next_sibling('div')).text)
        except Exception as exc:
            logger.error("Could not convert Defense value to integer. Exception: %s", exc)
            defense = 0

    # Sp Atk Value
    spatk_base = soup.find('span', string="Sp. Atk")        
    parent = spatk_base.find_parent('div')    
    if(spatk_base is None or parent is None):
        logger.warning("Sp. Atk stats of the Pokémon not found.")
        pokemon.stats = BaseStats(hp=hp, attack=attack, defense=defense)
        return
    else:
        try:
            spatk = int((parent.find_next_sibling('div')).text)
        except Exception as exc:
            logger.error("Could not convert Sp. Atk value to integer. Exception: %s", exc)
    

    # Sp Def Value
    spdef_base = soup.find('span', string="Sp. Def")    
    parent = spdef_base.find_parent('div')    
    if(spdef_base is None or parent is None):
        logger.warning("Sp. Def stats of the Pokémon not found.")
        pokemon.stats = BaseStats(hp=hp, attack=attack, defense=defense, sp_atk=spatk)
        return
    else:
        try:
            spdef = int((parent.find_next_sibling('div')).text)
        except Exception as exc:
            logger.error("Could not convert Sp. Def value to integer. Exception: %s", exc)
            spdef = 0    

    # Speed Value
    speed_base = soup.find('span', string="Speed")    
    parent = speed_base.find_parent('div')    
    if(speed_base is None or parent is None):
        logger.warning("Speed stats of the Pokémon not found.")
        pokemon.stats = BaseStats(hp=hp, attack=attack, defense=defense, sp_atk=spatk, sp_def=spdef)
        return
    else:
        try:
            speed = int((parent.find_next_sibling('div')).text)
        except Exception as exc:
            logger.error("Could not convert Speed value to integer. Exception: %s", exc)
            speed = 0

    stats = BaseStats(hp=hp, attack=attack, defense=defense, sp_atk=spatk, sp_def=spdef, speed=speed)
    pokemon.stats= stats
    return

## Gets the Pokémon evolution from the soup and fills the pokemon object with them.
## Handles linear chains (Bulbasaur), branched evolutions (Tyrogue) and
## table-only cases where the paragraph omits names entirely (Eevee).
def _parse_evolution(soup: BeautifulSoup, pokemon: Pokemon) -> None:
    evolution_extract = soup.find('span', {'id': 'Evolution'})
    previous = None
    next_pokes = []

    if evolution_extract is not None:
        evolution_extract = evolution_extract.find_parent('h3')
        base = evolution_extract.find_next_sibling('p')

        if base:
            # Tracks whether we already entered a "evolves into" context in this paragraph.
            # Once set, subsequent Pokémon links are treated as additional next evolutions
            # (e.g. "evolves into either Hitmonlee, Hitmonchan or Hitmontop").
            in_next_chain = False

            # Runs all <a> links inside the paragraph [Gets all evolution line]
            for link in base.find_all('a'):
                href = link.get('href', '').lower()

                # Skip "evolution/eeveelution" word links — they're not Pokémon pages
                if '_(pok%c3%a9mon)' not in href and '_(pokemon)' not in href:
                    continue

                accumulated = ""
                for sib in link.previous_siblings:
                    # If we find another Pokémon link, stop looking backwards
                    if sib.name == 'a' and '_(pok%c3%a9mon)' in sib.get('href', '').lower():
                        break
                    # Sum previous siblings until we find another Pokémon link or run out of siblings
                    if isinstance(sib, str):
                        accumulated = sib + accumulated
                    else:
                        accumulated = sib.get_text() + accumulated

                text_string = accumulated.lower()

                ## Verifies if the text contains "evolves from" or "evolves into" to determine
                ## the relationship of the Pokémon in the evolution line
                if "evolves from" in text_string:
                    previous = link.get_text(strip=True)
                    in_next_chain = False
                ## It means that it's an intermediate in the chain (e.g. Ivysaur in Bulbasaur's page), so we skip it
                elif "which evolves into" in text_string:
                    continue
                ## First explicit "evolves into" — enters next-chain context
                elif "evolves into" in text_string or "evolve into" in text_string:
                    next_pokes.append(link.get_text(strip=True))
                    in_next_chain = True
                ## Continuation of a branched list ("either X, [Y] or [Z]") — no "evolves into" prefix
                elif in_next_chain:
                    next_pokes.append(link.get_text(strip=True))

        # --- FIX HERE ---
        # If no valid next evolutions were extracted from the text (like Eevee, where the paragraph 
        # mentions "evolve into" but the actual links inside are skipped by the href filter),
        # we safely fall back to the evolution table.
        if not next_pokes:
            next_pokes = _parse_evolution_from_table(soup, pokemon.name)
            
    else:
        logger.warning("Evolution section not found for this Pokémon.")

    pokemon.evolution = Evolution(previous=previous, next=next_pokes)
    return


## Fallback parser: extracts next evolutions directly from the Game data evolution table.
## Used when the Evolution section paragraph does not list the Pokémon names (e.g. Eevee).
def _parse_evolution_from_table(soup: BeautifulSoup, current_name: str) -> list[str]:
    evo_data_span = soup.find('span', {'id': 'Evolution_data'})
    if evo_data_span is None:
        logger.warning("Evolution_data table not found as fallback.")
        return []

    # The table sits right after the h3/h4 heading that wraps the span
    heading = evo_data_span.find_parent(['h3', 'h4'])
    if heading is None:
        return []

    table = heading.find_next_sibling('table')
    if table is None:
        return []

    seen: set[str] = set()
    evolutions: list[str] = []
        
    # We should only start collecting evolutions AFTER we pass the current Pokémon link in the table structure.
    found_current = False

    # Collect all Pokémon links inside the table
    for a in table.find_all('a'):
        name = a.get_text(strip=True)
        if not name:
            continue
            
        # If we find the current Pokémon, we flag it so we can start collecting subsequent stages
        if name.lower() == current_name.lower():
            found_current = True
            continue
            
        # If the flag is active, this Pokémon comes later in the evolution chain
        if found_current and name not in seen:
            href = a.get('href', '').lower()
            if '_(pok%c3%a9mon)' in href or '_(pokemon)' in href:
                seen.add(name)
                evolutions.append(name)

    logger.info("Evolution fallback found %d evolution(s) for %s via table.", len(evolutions), current_name)
    return evolutions

## Gets the Pokémon abilities from the soup and fills the pokemon object with them.
def _parse_abilities(soup: BeautifulSoup, pokemon: Pokemon)-> None:
    evolution_extract = soup.find('a', {'title': 'Ability'})    
    container = evolution_extract.find_parent('b')    
    table = container.find_next_sibling('table')
    
    abilities = []
    if(table is None):
        logger.warning("Abilities table section not found for this Pokémon.")
        pokemon.abilities = []
        return
    else:        
        # Runs all table cells
        for td in table.find_all('td'):                        
            # Security Filter: If the cell is hidden on the site, ignore it
            style = td.get('style', '')
            if 'display: none' in style:
                continue
                            
            # find ability link and the smaller description
            a_tag = td.find('a')
            small_tag = td.find('small')
            
            # if there's an ability link, we consider it as an ability and we try to get the name and type of the ability
            if a_tag:
                ability_name = a_tag.get_text(strip=True)
                ability_type = small_tag.get_text(strip=True) if small_tag else ""                            
                abilities.append({
                    "name": ability_name,
                    "type": ability_type
                })

        pokemon.abilities = abilities
    return

## Gets the Pokémon image URL from the soup and fills the pokemon object with it.
def _parse_image_path(soup: BeautifulSoup, pokemon: Pokemon)-> None:
    img_url = soup.find('a', {'class': 'mw-file-description'})
    if(img_url is None):
        logger.warning("Image URL not found for this Pokémon.")
        pokemon.image_path = None
        return
    else:
        img_tag = img_url.find('img')
        img_url = img_tag.get('src')
        if(img_url is None):
            logger.warning("Image URL not found for this Pokémon.")
            pokemon.image_path = None
        else:
            pokemon.image_path = img_url
    return

## Gets the Pokémon image URL from the soup and fills the pokemon object with it.
async def download_image(session: aiohttp.ClientSession, url: str, dest: Path) -> Path:    
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                async with aiofiles.open(dest, "wb") as f:
                    await f.write(await resp.read())
            logger.info("Image saved in %s", dest)
            return dest
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            wait = BACKOFF_BASE ** attempt
            logger.warning("Image download failed (attempt %d): %s", attempt + 1, exc)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(wait)
            else:
                logger.error("Failed to download image: %s", url)
                raise
