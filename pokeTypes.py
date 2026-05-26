from dataclasses import dataclass, field

@dataclass
class Ability:
    name: str
    category: str    

@dataclass
class Evolution:
    previous: str = None   # predecessor
    next: str = None       # sucessor


@dataclass
class BaseStats:
    hp: int = 0
    attack: int = 0
    defense: int = 0
    sp_atk: int = 0
    sp_def: int = 0
    speed: int = 0


@dataclass
class Pokemon:
    name: str = ""
    national_number: int = 0
    category: str = ""
    types: list[str] = field(default_factory=list)
    stats: BaseStats = field(default_factory=BaseStats)
    evolution: Evolution = field(default_factory=Evolution)
    abilities: list[Ability] = field(default_factory=list)
    image_path: str = None   # preenchido após o download