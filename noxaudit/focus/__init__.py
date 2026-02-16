"""Focus areas for audits."""

from noxaudit.focus.base import BaseFocus
from noxaudit.focus.dependencies import DependenciesFocus
from noxaudit.focus.docs import DocsFocus
from noxaudit.focus.hygiene import HygieneFocus
from noxaudit.focus.patterns import PatternsFocus
from noxaudit.focus.performance import PerformanceFocus
from noxaudit.focus.security import SecurityFocus
from noxaudit.focus.testing import TestingFocus

FOCUS_AREAS: dict[str, type[BaseFocus]] = {
    "security": SecurityFocus,
    "docs": DocsFocus,
    "patterns": PatternsFocus,
    "testing": TestingFocus,
    "hygiene": HygieneFocus,
    "dependencies": DependenciesFocus,
    "performance": PerformanceFocus,
}

__all__ = [
    "FOCUS_AREAS",
    "BaseFocus",
    "SecurityFocus",
    "DocsFocus",
    "PatternsFocus",
    "TestingFocus",
    "HygieneFocus",
    "DependenciesFocus",
    "PerformanceFocus",
]
