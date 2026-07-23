"""Prompt generation using Wonder Words nouns."""

from __future__ import annotations

from wonderwords import RandomWord

_WORD_GEN = RandomWord()


def random_soup_noun() -> str:
    """Return a random noun to drop into the soup prompt."""
    noun = _WORD_GEN.word(
        include_parts_of_speech=["nouns"],
        word_min_length=3,
        word_max_length=14,
    )
    if not isinstance(noun, str) or not noun:
        return "fly"
    return noun.lower()


def build_prompt(noun: str) -> str:
    return f"Waiter, there's a {noun} in my soup!"
