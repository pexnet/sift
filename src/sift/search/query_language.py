from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal


class SearchQuerySyntaxError(ValueError):
    pass


TokenKind = Literal["WORD", "PHRASE", "LPAREN", "RPAREN", "AND", "OR", "NOT", "EOF"]


@dataclass(frozen=True, slots=True)
class _Token:
    kind: TokenKind
    value: str
    index: int


@dataclass(frozen=True, slots=True)
class _WordNode:
    value: str


@dataclass(frozen=True, slots=True)
class _PhraseNode:
    value: str


@dataclass(frozen=True, slots=True)
class _PrefixNode:
    prefix: str


@dataclass(frozen=True, slots=True)
class _FuzzyNode:
    value: str
    distance: int


@dataclass(frozen=True, slots=True)
class _NotNode:
    child: _ExprNode


@dataclass(frozen=True, slots=True)
class _BinaryNode:
    op: Literal["AND", "OR"]
    left: _ExprNode
    right: _ExprNode


_ExprNode = _WordNode | _PhraseNode | _PrefixNode | _FuzzyNode | _NotNode | _BinaryNode


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"\s+", " ", normalized).strip()


def _tokenize(value: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    while i < len(value):
        char = value[i]
        if char.isspace():
            i += 1
            continue
        if char == "(":
            tokens.append(_Token(kind="LPAREN", value=char, index=i))
            i += 1
            continue
        if char == ")":
            tokens.append(_Token(kind="RPAREN", value=char, index=i))
            i += 1
            continue
        if char == '"':
            start = i + 1
            i += 1
            while i < len(value) and value[i] != '"':
                i += 1
            if i >= len(value):
                raise SearchQuerySyntaxError("Unterminated quoted phrase")
            phrase = value[start:i]
            tokens.append(_Token(kind="PHRASE", value=phrase, index=start - 1))
            i += 1
            continue

        start = i
        while i < len(value) and (not value[i].isspace()) and value[i] not in {'(', ')', '"'}:
            i += 1
        raw = value[start:i]
        normalized = _normalize_text(raw)
        if normalized == "and":
            kind: TokenKind = "AND"
        elif normalized == "or":
            kind = "OR"
        elif normalized == "not":
            kind = "NOT"
        else:
            kind = "WORD"
        tokens.append(_Token(kind=kind, value=raw, index=start))

    tokens.append(_Token(kind="EOF", value="", index=len(value)))
    return tokens


class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self._tokens = tokens
        self._index = 0

    def parse(self) -> _ExprNode:
        if self._peek().kind == "EOF":
            raise SearchQuerySyntaxError("Search query cannot be empty")
        expr = self._parse_or()
        if self._peek().kind != "EOF":
            token = self._peek()
            raise SearchQuerySyntaxError(f"Unexpected token '{token.value}' at index {token.index}")
        return expr

    def _peek(self) -> _Token:
        return self._tokens[self._index]

    def _consume(self) -> _Token:
        token = self._tokens[self._index]
        self._index += 1
        return token

    def _parse_or(self) -> _ExprNode:
        left = self._parse_and()
        while self._peek().kind == "OR":
            self._consume()
            right = self._parse_and()
            left = _BinaryNode(op="OR", left=left, right=right)
        return left

    def _parse_and(self) -> _ExprNode:
        left = self._parse_not()
        while True:
            token = self._peek()
            if token.kind == "AND":
                self._consume()
                right = self._parse_not()
                left = _BinaryNode(op="AND", left=left, right=right)
                continue
            if token.kind in {"WORD", "PHRASE", "LPAREN", "NOT"}:
                right = self._parse_not()
                left = _BinaryNode(op="AND", left=left, right=right)
                continue
            break
        return left

    def _parse_not(self) -> _ExprNode:
        if self._peek().kind == "NOT":
            self._consume()
            return _NotNode(child=self._parse_not())
        return self._parse_primary()

    def _parse_primary(self) -> _ExprNode:
        token = self._peek()
        if token.kind == "LPAREN":
            self._consume()
            expr = self._parse_or()
            if self._peek().kind != "RPAREN":
                raise SearchQuerySyntaxError(f"Expected ')' at index {self._peek().index}")
            self._consume()
            return expr
        if token.kind == "PHRASE":
            self._consume()
            phrase = _normalize_text(token.value)
            if not phrase:
                raise SearchQuerySyntaxError("Quoted phrase cannot be empty")
            return _PhraseNode(value=phrase)
        if token.kind == "WORD":
            self._consume()
            return self._parse_word_token(token)

        raise SearchQuerySyntaxError(f"Unexpected token '{token.value}' at index {token.index}")

    def _parse_word_token(self, token: _Token) -> _ExprNode:
        raw = token.value.strip()
        if not raw:
            raise SearchQuerySyntaxError(f"Invalid empty token at index {token.index}")

        if "*" in raw:
            if raw.count("*") > 1 or not raw.endswith("*") or len(raw) <= 1:
                raise SearchQuerySyntaxError(
                    f"Only suffix wildcard is supported (invalid token '{token.value}')"
                )
            prefix = _normalize_text(raw[:-1])
            if not prefix:
                raise SearchQuerySyntaxError(f"Invalid wildcard token '{token.value}'")
            if "~" in prefix:
                raise SearchQuerySyntaxError(f"Wildcard and fuzzy cannot be combined ('{token.value}')")
            return _PrefixNode(prefix=prefix)

        fuzzy_match = re.fullmatch(r"(.+?)~([0-9]+)", raw)
        if fuzzy_match:
            value = _normalize_text(fuzzy_match.group(1))
            distance = int(fuzzy_match.group(2))
            if not value:
                raise SearchQuerySyntaxError(f"Invalid fuzzy token '{token.value}'")
            if distance < 1 or distance > 2:
                raise SearchQuerySyntaxError(f"Fuzzy distance must be 1 or 2 (invalid token '{token.value}')")
            return _FuzzyNode(value=value, distance=distance)
        if "~" in raw:
            raise SearchQuerySyntaxError(f"Invalid fuzzy token '{token.value}'")

        word = _normalize_text(raw)
        if not word:
            raise SearchQuerySyntaxError(f"Invalid token '{token.value}'")
        return _WordNode(value=word)


@dataclass(frozen=True, slots=True)
class ParsedSearchQuery:
    expression: _ExprNode

    def matches(
        self,
        *,
        title: str,
        content_text: str,
        source_text: str | None = None,
    ) -> bool:
        normalized_corpus = _normalize_text("\n".join([title, content_text, source_text or ""]))
        words = re.findall(r"\w+", normalized_corpus, flags=re.UNICODE)
        return _evaluate_node(self.expression, normalized_corpus=normalized_corpus, words=words)


def parse_search_query(value: str) -> ParsedSearchQuery:
    parser = _Parser(_tokenize(value))
    return ParsedSearchQuery(expression=parser.parse())


def requires_advanced_search(value: str) -> bool:
    return bool(re.search(r'["()~*]|\b(?:and|or|not)\b', value, flags=re.IGNORECASE))


def _evaluate_node(node: _ExprNode, *, normalized_corpus: str, words: list[str]) -> bool:
    if isinstance(node, _WordNode):
        return node.value in normalized_corpus
    if isinstance(node, _PhraseNode):
        return node.value in normalized_corpus
    if isinstance(node, _PrefixNode):
        return any(word.startswith(node.prefix) for word in words)
    if isinstance(node, _FuzzyNode):
        return any(_levenshtein_with_limit(node.value, word, node.distance) <= node.distance for word in words)
    if isinstance(node, _NotNode):
        return not _evaluate_node(node.child, normalized_corpus=normalized_corpus, words=words)
    if isinstance(node, _BinaryNode):
        if node.op == "AND":
            return _evaluate_node(node.left, normalized_corpus=normalized_corpus, words=words) and _evaluate_node(
                node.right, normalized_corpus=normalized_corpus, words=words
            )
        return _evaluate_node(node.left, normalized_corpus=normalized_corpus, words=words) or _evaluate_node(
            node.right, normalized_corpus=normalized_corpus, words=words
        )
    return False


def _levenshtein_with_limit(left: str, right: str, limit: int) -> int:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > limit:
        return limit + 1

    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        row_min = current[0]
        for j, right_char in enumerate(right, start=1):
            insertion = previous[j] + 1
            deletion = current[j - 1] + 1
            substitution = previous[j - 1] + (0 if left_char == right_char else 1)
            distance = min(insertion, deletion, substitution)
            current.append(distance)
            if distance < row_min:
                row_min = distance
        if row_min > limit:
            return limit + 1
        previous = current
    return previous[-1]
