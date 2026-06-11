from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Pivot:
    current_level: float = 0.0
    last_level: float = 0.0
    crossed: bool = False
    bar_time: int = 0
    bar_index: int = 0


@dataclass
class OrderBlock:
    bar_high: float = 0.0
    bar_low: float = 0.0
    bar_time: int = 0
    bias: int = 0


@dataclass
class FVG:
    top: float = 0.0
    bottom: float = 0.0
    bias: int = 0
    start_time: int = 0
    end_time: int = 0


@dataclass
class EqualLevel:
    price: float = 0.0
    bar_time: int = 0
    bar_index: int = 0
    matched_price: float = 0.0
    matched_time: int = 0
    matched_index: int = 0
    is_high: bool = True


@dataclass
class StructureLine:
    price: float = 0.0
    bar_time: int = 0
    bar_index: int = 0
    tag: str = ""
    bias: int = 0
    is_internal: bool = False


@dataclass
class TrailingExtremes:
    top: float = 0.0
    bottom: float = 0.0
    bar_time: int = 0
    bar_index: int = 0
    last_top_time: int = 0
    last_bottom_time: int = 0
