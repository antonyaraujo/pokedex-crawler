import requests
from bs4 import BeautifulSoup


def extrair_array_pokemons():
    url = "https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_category"

    # Define a User-Agent to simulate a common browser and avoid blocking
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        # Make the request to the website
        resposta = requests.get(url, headers=headers)
        resposta.raise_for_status()

        # Feed BeautifulSoup with the page HTML
        soup = BeautifulSoup(resposta.text, "html.parser")

        # Find the Pokémon table (Bulbapedia uses the 'wikitable' class)
        tabela = soup.find("tbody")                
        array_pokemons = []

        if tabela:
            # Skip the first row (table header) and iterate over the rest
            linhas = tabela.find_all("tr")[1:]
            for linha in linhas:
                #print(linha)
                celulas = linha.find_all(["td", "th"])

                # In the structure of this table:
                # celulas[0] = Pokédex number
                # celulas[1] = Image
                # celulas[2] = Pokémon name
                if len(celulas) >= 3:
                    nome = celulas[2].get_text(strip=True)

                    # Validate the name is not empty and not a repeated header
                    if nome and nome != "Name":
                        array_pokemons.append(nome)

        return array_pokemons

    except Exception as e:
        print(f"Error extracting page data: {e}")
        return []


# Create the variable and store the complete array in it
todos_os_pokemons = extrair_array_pokemons()

# Example usage: checking the size and displaying the first 10
print(f"Total Pokémon in array: {len(todos_os_pokemons)}")
for pk in todos_os_pokemons[500::]:
    print(pk)
#print("First 10:", todos_os_pokemons)