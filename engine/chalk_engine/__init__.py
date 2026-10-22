"""chalk_engine: the Chalk Talk play engine (CONTRACTS.md sections 3 and 4)."""

from .narration import narrate
from .play import build_play, counter_play, mirror, template_catalog
from .rules import parse_rules
from .templates import TEMPLATES
from .validator import validate

__all__ = ["TEMPLATES", "build_play", "counter_play", "validate", "parse_rules", "template_catalog", "mirror", "narrate"]
