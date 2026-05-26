from typing import Sequence
from dataclasses import asdict
import json
from pathlib import Path
from pokeTypes import Pokemon
import logging

logger = logging.getLogger(__name__)

## Storage functions
def save_json(pokemons: Sequence[Pokemon], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(p) for p in pokemons]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("JSON salvo em %s (%d pokémons)", path, len(data))