def carregar_nomes_do_txt(caminho_arquivo: str | Path) -> List[str]:
    """Reads a .txt file line by line, trims spaces, and returns a list of names."""
    try:
        caminho = Path(caminho_arquivo)
        with open(caminho, "r", encoding="utf-8") as arquivo:
            # Read each line, strip whitespace/newlines, and ignore empty lines
            nomes = [linha.strip() for linha in arquivo if linha.strip()]

        logger.info(
            "Loaded %d Pokémon names from file %s",
            len(nomes),
            caminho.name,
        )
        return nomes

    except FileNotFoundError:
        logger.error("Error: TXT file '%s' not found.", caminho_arquivo)
        return []
    except Exception as exc:
        logger.error("Error reading TXT file '%s': %s", caminho_arquivo, exc)
        return []

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if not args:        
        logger.info("Example: python crawler.py Pikachu Bulbasaur Charmander")
    else:
        primeiro_arg = args[0]
        caminho_txt = Path(primeiro_arg)

        # Verifica se o argumento é um arquivo .txt existente
        if caminho_txt.suffix.lower() == ".txt":
            if caminho_txt.exists():
                lista_nomes = carregar_nomes_do_txt(caminho_txt)
                crawl(lista_nomes)
            else:
                logger.error("The file '%s' does not exist.", primeiro_arg)
        else:
            # If it's not .txt, run the crawler with the names passed directly
            crawl(args)