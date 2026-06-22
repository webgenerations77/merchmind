_SMALL_WORDS = frozenset([
    "a", "an", "the", "and", "but", "or", "for", "nor",
    "of", "in", "on", "at", "to", "by", "is", "it", "vs",
])


def to_title_case(text: str) -> str:
    if not text:
        return text
    words = text.split(" ")
    result = []
    for i, word in enumerate(words):
        if not word:
            result.append(word)
            continue
        if len(word) > 1 and word == word.upper():
            result.append(word)
            continue
        if word != word.lower() and word[0] == word[0].lower():
            result.append(word)
            continue
        lower = word.lower()
        if i > 0 and lower in _SMALL_WORDS:
            result.append(lower)
            continue
        result.append(lower[0].upper() + lower[1:])
    return " ".join(result)
