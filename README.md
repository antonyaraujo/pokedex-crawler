# 🕷️ Poké-Crawler

Um crawler assíncrono que extrai dados detalhados de Pokémons a partir da [Bulbapedia](https://bulbapedia.bulbagarden.net), realizando parsing do HTML e exportando as informações em formato JSON estruturado.

---

## 📋 Requisitos

- Python 3.11+
- pip

### Dependências

```bash
pip install aiohttp aiofiles beautifulsoup4
```

---

## 🚀 Como rodar

```bash
python crawler.py Pikachu Bulbasaur Charmander
```

Passe os nomes dos Pokémons como argumentos na linha de comando, **exatamente como aparecem na URL da Bulbapedia** (ex: `Pikachu`, `Bulbasaur`, `Mr._Mime`).

O resultado será salvo em `pokemons.json` e as imagens em `output/`.

---

## 🗂️ Estrutura do Projeto

```
poke-crawler/
├── crawler.py       # Ponto de entrada: orquestra o fluxo de crawling
├── parser.py        # Extração e parsing dos dados do HTML (BeautifulSoup)
├── storage.py       # Persistência dos dados em JSON
├── pokeTypes.py     # Dataclasses: Pokemon, BaseStats, Evolution, Ability
├── pokemons.json    # Saída gerada com os dados dos Pokémons
└── output/          # Imagens baixadas de cada Pokémon
```

---

## 🧱 Arquitetura e Decisões Técnicas

O projeto foi estruturado com separação clara de responsabilidades em três camadas:

**Requisição (`crawler.py`)** — gerencia as sessões HTTP, controla a concorrência via `asyncio.Semaphore` e coordena o fluxo geral. Antes de buscar, verifica se o Pokémon já existe no JSON para evitar requisições desnecessárias.

**Extração/Parsing (`parser.py`)** — recebe o HTML como `BeautifulSoup` e extrai cada campo em funções dedicadas (`_parse_name`, `_parse_stats`, `_parse_evolution`, etc.). Cada função trata sua própria ausência de dados com fallbacks e logs de warning, evitando que a falha em um campo quebre o parsing inteiro.

**Armazenamento (`storage.py`)** — responsável exclusivamente por serializar e salvar os dados em disco, convertendo os dataclasses para dicionários via `dataclasses.asdict`.

---

## ⚙️ Concorrência

O crawler utiliza `asyncio` + `aiohttp` para realizar múltiplas requisições de forma assíncrona e não-bloqueante. O nível de concorrência é controlado por:

- `asyncio.Semaphore(5)` — limita até 5 requisições simultâneas às páginas de Pokémon.
- `aiohttp.TCPConnector(limit=5)` — limita as conexões TCP abertas no mesmo nível.
- O download de imagens também é assíncrono via `aiofiles`.

Isso garante eficiência sem sobrecarregar o servidor da Bulbapedia.

---

## 🔁 Resiliência

- **Retries com backoff exponencial**: o download de imagens tenta até 3 vezes (`MAX_RETRIES = 3`), com espera de `2^tentativa` segundos entre as tentativas.
- **Timeout por requisição**: definido em 20s para páginas e 30s para imagens.
- **Parsing defensivo**: cada campo verifica `None` antes de processar. Campos ausentes recebem valores padrão (string vazia, `0`, lista vazia) sem interromper o parsing dos demais.
- **Pokémons duplicados**: o crawler ignora Pokémons que já existem no JSON, evitando sobrescritas acidentais.

---

## 📦 Exemplo de Output (`pokemons.json`)

```json
{
  "name": "Pikachu",
  "national_number": 25,
  "category": "Mouse Pokémon",
  "types": ["Electric"],
  "stats": {
    "hp": 35,
    "attack": 55,
    "defense": 30,
    "sp_atk": 50,
    "sp_def": 40,
    "speed": 90
  },
  "evolution": {
    "previous": "Pichu",
    "next": "Raichu"
  },
  "abilities": [
    { "name": "Static", "category": "" },
    { "name": "Lightning Rod", "category": "Hidden Ability" }
  ],
  "image_path": "/output/Pikachu.png"
}
```

---

## 📚 Bibliotecas Utilizadas

| Biblioteca | Motivo da escolha |
|---|---|
| `aiohttp` | Cliente HTTP assíncrono, ideal para crawling concorrente sem overhead de threads |
| `beautifulsoup4` | API simples e robusta para navegação em árvores HTML com seletores CSS e busca por atributos |
| `aiofiles` | Escrita de arquivos não-bloqueante, mantendo o loop de eventos livre durante o salvamento de imagens |
| `dataclasses` | Estruturas de dados tipadas, limpas e serializáveis com `asdict` sem boilerplate |
| `asyncio` | Concorrência nativa do Python para I/O-bound tasks, sem necessidade de bibliotecas externas |
