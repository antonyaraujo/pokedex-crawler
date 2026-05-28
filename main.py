import asyncio
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException

# Importing utility functions from their original files
from crawler import crawl, get_pokemons, pokemon_to_dict
from storage import save_json

app = FastAPI(
    title="PokeCrawler API",
    description="API to search, list, and manage Pokémon locally"
)

# JSON file path defined in your scripts
JSON_PATH = Path("pokemons.json")
TXT_PATH = Path("pokemons.txt")  # New path for the cloud text file

# -----------------------------------------------------------------------------
# 1. RUN CRAWLER BY POKÉMON (Returns the full object)
# -----------------------------------------------------------------------------
@app.post("/pokemons/crawl", summary="Runs the crawler for new Pokémon and returns the objects")
async def trigger_crawler(
    names: str = Query(..., description="Pokémon names separated by commas. E.g.: Pikachu, Charizard")
):
    # Transforms the received string into a list of cleaned names
    name_list = [name.strip() for name in names.split(",") if name.strip()]
    
    if not name_list:
        raise HTTPException(status_code=400, detail="Please provide at least one valid name.")
    
    # Runs the original crawler in a separate thread so it doesn't block FastAPI
    await asyncio.to_thread(crawl, name_list)
    
    # Loads the updated list of Pokémon from the JSON file
    updated_list = get_pokemons(JSON_PATH)
    
    # Filters and converts to a dictionary only the Pokémon requested in this request
    pokemon_results = []
    requested_names_lower = [n.lower() for n in name_list]
    
    for poke in updated_list:
        if poke.name.lower() in requested_names_lower:
            pokemon_results.append(pokemon_to_dict(poke))
            
    return {
        "status": "Success",
        "message": "Crawler finished. Below are the requested Pokémon data.",
        "pokemons": pokemon_results
    }


# -----------------------------------------------------------------------------
# 2. GET ALL EXISTING POKÉMON FROM JSON
# -----------------------------------------------------------------------------
@app.get("/pokemons", summary="Lists all Pokémon saved in the JSON file")
def list_all_pokemons():
    poke_list = get_pokemons(JSON_PATH)
    return [pokemon_to_dict(p) for p in poke_list]


# -----------------------------------------------------------------------------
# 3. NEW ROUTE: GET A SPECIFIC POKÉMON BY NAME
# -----------------------------------------------------------------------------
@app.get("/pokemons/{name}", summary="Returns the JSON object of a specific Pokémon by name")
def get_single_pokemon(name: str):
    poke_list = get_pokemons(JSON_PATH)
    
    # Searches for the corresponding Pokémon in the list (case-insensitive)
    for poke in poke_list:
        if poke.name.lower() == name.lower():
            return pokemon_to_dict(poke)
            
    # If not found, raises an HTTP 404 exception
    raise HTTPException(
        status_code=404, 
        detail=f"The Pokémon '{name}' was not found in the records file."
    )


# -----------------------------------------------------------------------------
# 4. DELETE A POKÉMON FROM JSON
# -----------------------------------------------------------------------------
@app.delete("/pokemons/{name}", summary="Deletes a Pokémon from the JSON file by name")
def delete_pokemon(name: str):
    poke_list = get_pokemons(JSON_PATH)
    original_size = len(poke_list)
    
    filtered_list = [p for p in poke_list if p.name.lower() != name.lower()]
    
    if len(filtered_list) == original_size:
        raise HTTPException(
            status_code=404, 
            detail=f"The Pokémon '{name}' was not found in the JSON file."
        )
    
    save_json(filtered_list, JSON_PATH)
    
    return {
        "status": "Success",
        "message": f"The Pokémon '{name}' was successfully removed from the file.",
        "remaining_total": len(filtered_list)
    }


# -----------------------------------------------------------------------------
# NEW ROUTE: GET NAME LIST FROM TXT IN THE CLOUD
# -----------------------------------------------------------------------------
@app.get("/listAll", summary="Returns the names from the pokemons.txt file as a string array")
def get_list_from_txt():
    # TXT_PATH must be defined pointing to Path("pokemons.txt")
    if not TXT_PATH.exists():
        raise HTTPException(
            status_code=404, 
            detail="The file 'pokemons.txt' was not found on the Render server."
        )
        
    try:
        with TXT_PATH.open("r", encoding="utf-8") as file:
            # Reads each line, cleans whitespaces (\n) and ignores blank lines
            name_list = [line.strip() for line in file if line.strip()]
            
        # Returns the raw string array directly
        return name_list
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading the text file on the server: {str(e)}"
        )