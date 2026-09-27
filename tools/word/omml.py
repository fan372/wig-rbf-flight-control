# -*- coding: utf-8 -*-
"""LaTeX-subset -> OMML (Office Math Markup Language) converter.

Pure standard library.  No third-party dependencies.

Public API
----------
``latex_to_omml(latex)``
    Convert a LaTeX math fragment into the *inner* XML of an ``<m:oMath>``
    element (the children only -- no ``<m:oMath>`` wrapper, no namespace
    declarations).
``inline_omml(latex)``
    Same, wrapped in ``<m:oMath>...</m:oMath>`` (suitable for inline use inside
    a ``<w:p>``).
``display_omml(latex, jc="center")``
    Wrapped in ``<m:oMathPara>`` (display / "professional" style math).
``omml_paragraph(latex, number=None, ...)``
    A complete ``<w:p>`` paragraph holding the equation, optionally with a
    right-tabbed equation number.
``equation_table(latex, number, ...)``
    A borderless 1-row / 2-column ``<w:tbl>`` that centres the equation and
    right-aligns its number.  This is the layout ``Report.eq`` uses by default.
``UNKNOWN_MACROS``
    Module level list; every macro / environment that could not be translated
    is appended here (as ``"\\name"`` or ``"\\begin{env}"``).  The converter
    never raises on unknown input -- it falls back to the literal macro text.

The emitted OMML is ``m:``-namespace-only; it never emits ``w:`` elements, so a
fragment can be validated standalone by wrapping it in a root element that
declares the ``m`` namespace.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence
from xml.sax.saxutils import escape

__all__ = [
    "latex_to_omml",
    "inline_omml",
    "display_omml",
    "omml_paragraph",
    "equation_table",
    "UNKNOWN_MACROS",
    "M_NS",
    "W_NS",
]

# --------------------------------------------------------------------------
# Namespaces and unit constants
# --------------------------------------------------------------------------

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

CM_TO_TWIPS = 567
"""1 cm = 567 twips (1/20 pt; 1 cm = 28.3465 pt)."""

#: Recorded (in order, with duplicates) whenever an unknown macro is met.
UNKNOWN_MACROS: list[str] = []


# --------------------------------------------------------------------------
# Symbol tables
# --------------------------------------------------------------------------

GREEK_LOWER: dict[str, str] = {
    "alpha": "\u03b1", "beta": "\u03b2", "gamma": "\u03b3", "delta": "\u03b4",
    "epsilon": "\u03f5", "varepsilon": "\u03b5", "zeta": "\u03b6", "eta": "\u03b7",
    "theta": "\u03b8", "vartheta": "\u03d1", "iota": "\u03b9", "kappa": "\u03ba",
    "lambda": "\u03bb", "mu": "\u03bc", "nu": "\u03bd", "xi": "\u03be",
    "omicron": "\u03bf", "pi": "\u03c0", "varpi": "\u03d6", "rho": "\u03c1",
    "varrho": "\u03f1", "sigma": "\u03c3", "varsigma": "\u03c2", "tau": "\u03c4",
    "upsilon": "\u03c5", "phi": "\u03d5", "varphi": "\u03c6", "chi": "\u03c7",
    "psi": "\u03c8", "omega": "\u03c9",
}

GREEK_UPPER: dict[str, str] = {
    "Gamma": "\u0393", "Delta": "\u0394", "Theta": "\u0398", "Lambda": "\u039b",
    "Xi": "\u039e", "Pi": "\u03a0", "Sigma": "\u03a3", "Upsilon": "\u03a5",
    "Phi": "\u03a6", "Psi": "\u03a8", "Omega": "\u03a9",
}

#: Uppercase Greek is upright in LaTeX; lowercase is italic (OMML default).
_UPRIGHT_GREEK = set(GREEK_UPPER)

SYMBOLS: dict[str, str] = {
    # binary operators
    "times": "\u00d7", "cdot": "\u22c5", "pm": "\u00b1", "mp": "\u2213",
    "div": "\u00f7", "ast": "\u2217", "star": "\u22c6", "circ": "\u2218",
    "bullet": "\u2219", "oplus": "\u2295", "otimes": "\u2297", "odot": "\u2299",
    "cup": "\u222a", "cap": "\u2229", "setminus": "\u2216",
    "wedge": "\u2227", "vee": "\u2228", "land": "\u2227", "lor": "\u2228",
    # relations
    "leq": "\u2264", "le": "\u2264", "geq": "\u2265", "ge": "\u2265",
    "neq": "\u2260", "ne": "\u2260", "approx": "\u2248", "equiv": "\u2261",
    "sim": "\u223c", "simeq": "\u2243", "cong": "\u2245", "propto": "\u221d",
    "ll": "\u226a", "gg": "\u226b", "lll": "\u22d8", "ggg": "\u22d9",
    "prec": "\u227a", "succ": "\u227b", "asymp": "\u224d", "doteq": "\u2250",
    # arrows
    "to": "\u2192", "rightarrow": "\u2192", "longrightarrow": "\u27f6",
    "leftarrow": "\u2190", "longleftarrow": "\u27f5",
    "leftrightarrow": "\u2194", "Leftrightarrow": "\u21d4",
    "Rightarrow": "\u21d2", "Leftarrow": "\u21d0",
    "mapsto": "\u21a6", "uparrow": "\u2191", "downarrow": "\u2193",
    "updownarrow": "\u2195", "nearrow": "\u2197", "searrow": "\u2198",
    # sets / logic
    "in": "\u2208", "notin": "\u2209", "ni": "\u220b",
    "subset": "\u2282", "subseteq": "\u2286", "supset": "\u2283",
    "supseteq": "\u2287", "emptyset": "\u2205", "varnothing": "\u2205",
    "forall": "\u2200", "exists": "\u2203", "nexists": "\u2204",
    "neg": "\u00ac", "lnot": "\u00ac", "therefore": "\u2234", "because": "\u2235",
    # misc symbols
    "infty": "\u221e", "partial": "\u2202", "nabla": "\u2207",
    "angle": "\u2220", "perp": "\u22a5", "parallel": "\u2225",
    "square": "\u25a1", "triangle": "\u25b3", "prime": "\u2032",
    "degree": "\u00b0", "hbar": "\u210f", "ell": "\u2113",
    "Re": "\u211c", "Im": "\u2111", "aleph": "\u2135", "wp": "\u2118",
    "ldots": "\u2026", "dots": "\u2026", "cdots": "\u22ef",
    "vdots": "\u22ee", "ddots": "\u22f1",
    # delimiters used bare (without \left/\right)
    "langle": "\u27e8", "rangle": "\u27e9",
    "lceil": "\u2308", "rceil": "\u2309",
    "lfloor": "\u230a", "rfloor": "\u230b",
    "vert": "|", "Vert": "\u2016", "lvert": "|", "rvert": "|",
    "lVert": "\u2016", "rVert": "\u2016", "lbrace": "{", "rbrace": "}",
    "lbrace": "{", "rbrace": "}",
    # spacing macros that carry an explicit character
    "quad": "\u2003", "qquad": "\u2003\u2003",
    "enspace": "\u2002", "thinspace": "\u2009",
}

#: Big operators rendered as ``<m:nary>``:  name -> (character, limit location).
BIG_OPERATORS: dict[str, tuple[str, str]] = {
    "sum": ("\u2211", "undOvr"),
    "prod": ("\u220f", "undOvr"),
    "coprod": ("\u2210", "undOvr"),
    "bigcup": ("\u22c3", "undOvr"),
    "bigcap": ("\u22c2", "undOvr"),
    "bigoplus": ("\u2a01", "undOvr"),
    "bigotimes": ("\u2a02", "undOvr"),
    "bigodot": ("\u2a00", "undOvr"),
    "bigvee": ("\u22c1", "undOvr"),
    "bigwedge": ("\u22c0", "undOvr"),
    "int": ("\u222b", "subSup"),
    "iint": ("\u222c", "subSup"),
    "iiint": ("\u222d", "subSup"),
    "oint": ("\u222e", "subSup"),
    "oiint": ("\u222f", "subSup"),
    "smallint": ("\u222b", "subSup"),
}

#: Upright function names (``<m:sty m:val="p"/>``).
FUNCTIONS: set[str] = {
    "sin", "cos", "tan", "cot", "sec", "csc",
    "arcsin", "arccos", "arctan", "arccot",
    "sinh", "cosh", "tanh", "coth",
    "exp", "ln", "log", "lg", "lb",
    "max", "min", "sup", "inf", "lim", "det", "dim", "deg", "gcd",
    "hom", "ker", "arg", "sgn", "sat", "tr", "diag", "erf", "prob",
}

#: Functions whose scripts are placed *underneath* the name (``<m:limLow>``).
LIMIT_FUNCTIONS: set[str] = {"lim", "max", "min", "sup", "inf", "det", "dim", "gcd"}

#: Accent macros:  name -> combining character used by ``<m:acc>``.
ACCENTS: dict[str, str] = {
    "dot": "\u0307", "ddot": "\u0308", "hat": "\u0302", "widehat": "\u0302",
    "tilde": "\u0303", "widetilde": "\u0303", "vec": "\u20d7",
    "acute": "\u0301", "grave": "\u0300", "check": "\u030c",
    "breve": "\u0306", "mathring": "\u030a",
}

#: ``<m:bar>`` macros:  name -> "top" | "bot".
BARS: dict[str, str] = {"bar": "top", "overline": "top", "underline": "bot"}

#: Math alphabet macros:  style stack value pushed while parsing the group.
MATH_ALPHABETS: dict[str, str] = {
    "mathrm": "p", "mathbf": "b", "boldsymbol": "b", "mathit": "i",
    "mathsf": "p", "mathtt": "p", "mathcal": "p", "mathfrak": "p",
    "mathbb": "p", "mathnormal": "i",
}

#: ``\mathbb{X}`` shortcuts for the common blackboard-bold letters.
BLACKBOARD: dict[str, str] = {
    "R": "\u211d", "N": "\u2115", "Z": "\u2124", "Q": "\u211a", "C": "\u2102",
    "P": "\u2119", "H": "\u210d", "F": "\U0001d53d", "E": "\U0001d53c",
}

MATRIX_ENVS: dict[str, tuple[str, str, str]] = {
    # env -> (begin delimiter, end delimiter, default cell justification)
    "matrix": ("", "", "center"),
    "smallmatrix": ("", "", "center"),
    "pmatrix": ("(", ")", "center"),
    "bmatrix": ("[", "]", "center"),
    "Bmatrix": ("{", "}", "center"),
    "vmatrix": ("|", "|", "center"),
    "Vmatrix": ("\u2016", "\u2016", "center"),
    "cases": ("{", "", "left"),
    "array": ("", "", "center"),
    "aligned": ("", "", "right"),
    "alignedat": ("", "", "right"),
    "split": ("", "", "right"),
    "gathered": ("", "", "center"),
    "subarray": ("", "", "center"),
}

#: Environments that consume a ``{ccc}`` column specification right after
#: ``\begin{env}``.
_ENVS_WITH_COLSPEC = {"array", "alignedat", "subarray"}

#: ``\left`` / ``\right`` delimiter names -> character.
DELIMITER_MACROS: dict[str, str] = {
    "langle": "\u27e8", "rangle": "\u27e9",
    "lceil": "\u2308", "rceil": "\u2309",
    "lfloor": "\u230a", "rfloor": "\u230b",
    "lvert": "|", "rvert": "|", "vert": "|",
    "lVert": "\u2016", "rVert": "\u2016", "Vert": "\u2016",
    "lbrace": "{", "rbrace": "}",
    "uparrow": "\u2191", "downarrow": "\u2193", "updownarrow": "\u2195",
}

#: Characters accepted as a literal delimiter after ``\left``/``\right``.
_DELIM_CHARS: frozenset[str] = frozenset("()[]|.{}<>/\u2016\u27e8\u27e9\u2308\u2309\u230a\u230b\u2191\u2193\u2195")

#: ``\bigl(`` / ``\Bigr]`` ... -- size hints that carry no OMML meaning; the
#: delimiter is emitted and Word auto-sizes it anyway.
_BIG_DELIM_MACROS: frozenset[str] = frozenset({
    "big", "Big", "bigg", "Bigg", "bigm", "Bigm",
    "bigl", "bigr", "Bigl", "Bigr", "biggl", "biggr", "Biggl", "Biggr",
})

#: Macros that are pure no-ops in OMML.
_NOOP_MACROS: frozenset[str] = frozenset({
    "limits", "nolimits", "displaystyle", "textstyle", "scriptstyle",
    "scriptscriptstyle", ",",
})

#: Single character escapes:  ``\x`` -> produced character.
_SINGLE_ESCAPES: dict[str, str] = {
    "{": "{", "}": "}", "|": "\u2016",
    "%": "%", "$": "$", "&": "&", "#": "#", "_": "_",
    "(": "(", ")": ")", "[": "[", "]": "]", " ": " ",
    ",": "\u2009", ";": "\u2005", ":": "\u2004", "!": "",
    "/": "/", "-": "-", "'": "\u2032", ".": ".",
}


def _is_variable_char(ch: str) -> bool:
    """True for characters typeset italic (LaTeX variable letters).

    Latin (incl. extended), Greek and the mathematical alphanumeric block.
    CJK / punctuation / digits are upright.
    """
    o = ord(ch)
    return (0x41 <= o <= 0x24F) or (0x370 <= o <= 0x3FF) or (0x1D400 <= o <= 0x1D7FF)


# --------------------------------------------------------------------------
# Small XML helpers
# --------------------------------------------------------------------------


def _attr(value: str) -> str:
    """Escape a value for use inside a double-quoted XML attribute."""
    return escape(value, {'"': "&quot;"})


def _m_run(text: str, style: str | None = None, nor: bool = False) -> str:
    """Build one ``<m:r>`` run.

    ``style`` is an ``m:sty`` value: ``"p"`` (upright), ``"b"`` (bold),
    ``"i"`` (italic), ``"bi"``.  ``None`` means "Word default" (italic
    variable).  ``nor=True`` marks normal (non-math) text via ``<m:nor/>``.
    """
    if nor:
        rpr = "<m:rPr><m:nor/></m:rPr>"
    elif style is not None:
        rpr = f'<m:rPr><m:sty m:val="{_attr(style)}"/></m:rPr>'
    else:
        rpr = ""
    return f'<m:r>{rpr}<m:t xml:space="preserve">{escape(text)}</m:t></m:r>'


# --------------------------------------------------------------------------
# Tokenizer
# --------------------------------------------------------------------------

# Token kinds
CMD = "CMD"          # \name
LBRACE = "LBRACE"    # {
RBRACE = "RBRACE"    # }
LBRACKET = "LBRACKET"  # [
RBRACKET = "RBRACKET"  # ]
CARET = "CARET"      # ^
UNDER = "UNDER"      # _
AMP = "AMP"          # &
ROWSEP = "ROWSEP"    # \\
CHAR = "CHAR"        # any other single character


@dataclass
class _Token:
    kind: str
    value: str
    space: str = ""   # whitespace that preceded this token (normalised to " ")


_STRUCTURAL: dict[str, str] = {
    "{": LBRACE, "}": RBRACE, "[": LBRACKET, "]": RBRACKET,
    "^": CARET, "_": UNDER, "&": AMP,
}


def _tokenize(src: str) -> list[_Token]:
    """Split a LaTeX math fragment into tokens.

    Whitespace is not dropped: it is attached to the *following* token in the
    ``space`` field.  Math mode ignores it (as LaTeX does) while ``\\text{}``
    can reconstruct the original spacing.
    """
    toks: list[_Token] = []
    i, n = 0, len(src)
    pend = ""
    while i < n:
        c = src[i]
        if c.isspace():
            j = i
            while j < n and src[j].isspace():
                j += 1
            pend = " " if pend == "" else pend
            i = j
            continue
        sp, pend = pend, ""
        if c == "\\":
            if i + 1 >= n:
                toks.append(_Token(CHAR, "\\", sp))
                i += 1
                continue
            d = src[i + 1]
            if d.isalpha():
                j = i + 1
                while j < n and src[j].isalpha():
                    j += 1
                toks.append(_Token(CMD, src[i + 1:j], sp))
                i = j
                continue
            if d == "\\":
                toks.append(_Token(ROWSEP, "\\\\", sp))
                i += 2
                continue
            mapped = _SINGLE_ESCAPES.get(d)
            toks.append(_Token(CHAR, d if mapped is None else mapped, sp))
            i += 2
            continue
        kind = _STRUCTURAL.get(c)
        if kind is not None:
            toks.append(_Token(kind, c, sp))
            i += 1
            continue
        toks.append(_Token(CHAR, c, sp))
        i += 1
    return toks


def _token_text(tok: _Token) -> str:
    """Best-effort plain text for a token (used by ``\\text{}``)."""
    if tok.kind == CHAR:
        return tok.value
    if tok.kind == CMD:
        for table in (GREEK_LOWER, GREEK_UPPER, SYMBOLS):
            if tok.value in table:
                return table[tok.value]
        return "\\" + tok.value
    if tok.kind == ROWSEP:
        return "\\\\"
    return tok.value


# --------------------------------------------------------------------------
# Atom model
# --------------------------------------------------------------------------


@dataclass
class _Atom:
    """One typesettable unit produced by the parser."""

    kind: str = "seq"            # "seq" | "nary" | "lim"
    body: str = ""               # OMML for kind == "seq"
    sub: str | None = None
    sup: str | None = None
    nary_chr: str = ""
    nary_lim: str = "subSup"
    lim_name: str = ""


def _render(atom: _Atom) -> str:
    """Render an atom (with its scripts) to OMML."""
    if atom.kind == "nary":
        pr = (
            "<m:naryPr>"
            f'<m:chr m:val="{_attr(atom.nary_chr)}"/>'
            f'<m:limLoc m:val="{_attr(atom.nary_lim)}"/>'
        )
        if atom.sub is None:
            pr += '<m:subHide m:val="1"/>'
        if atom.sup is None:
            pr += '<m:supHide m:val="1"/>'
        pr += "</m:naryPr>"
        return (
            f"<m:nary>{pr}"
            f'<m:sub>{atom.sub or ""}</m:sub>'
            f'<m:sup>{atom.sup or ""}</m:sup>'
            f'<m:e>{atom.body}</m:e>'
            "</m:nary>"
        )
    if atom.kind == "lim":
        base = _m_run(atom.lim_name, style="p")
        if atom.sub is None:
            # A bare \lim / \max with no subscript must not become an <m:limLow>
            # with an empty <m:lim/> -- Word renders that as a placeholder box.
            return base
        return (
            f"<m:limLow><m:e>{base}</m:e><m:lim>{atom.sub}</m:lim></m:limLow>"
        )
    body = atom.body
    if not body:
        body = ""
    if atom.sub is not None and atom.sup is not None:
        return (
            f"<m:sSubSup><m:e>{body}</m:e>"
            f"<m:sub>{atom.sub}</m:sub><m:sup>{atom.sup}</m:sup></m:sSubSup>"
        )
    if atom.sub is not None:
        return f"<m:sSub><m:e>{body}</m:e><m:sub>{atom.sub}</m:sub></m:sSub>"
    if atom.sup is not None:
        return f"<m:sSup><m:e>{body}</m:e><m:sup>{atom.sup}</m:sup></m:sSup>"
    return body


def _render_all(atoms: Iterable[_Atom]) -> str:
    return "".join(_render(a) for a in atoms)


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


class _Parser:
    """Recursive-descent LaTeX -> OMML parser."""

    def __init__(self, toks: Sequence[_Token]) -> None:
        self.toks: list[_Token] = list(toks)
        self.i = 0
        self.styles: list[str] = ["i"]   # math-alphabet stack; "i" == default
        self.depth = 0

    # -- token helpers ----------------------------------------------------
    def peek(self, k: int = 0) -> _Token | None:
        j = self.i + k
        return self.toks[j] if 0 <= j < len(self.toks) else None

    def next(self) -> _Token | None:
        t = self.peek()
        if t is not None:
            self.i += 1
        return t

    def at_end(self) -> bool:
        return self.i >= len(self.toks)

    # -- run helpers ------------------------------------------------------
    def _style(self) -> str:
        return self.styles[-1]

    def _var(self, text: str) -> str:
        st = self._style()
        return _m_run(text, style=None if st == "i" else st)

    def _up(self, text: str) -> str:
        return _m_run(text, style=self._style() if self._style() == "b" else "p")

    # -- entry point ------------------------------------------------------
    def parse(self) -> str:
        atoms, _ = self.parse_seq()
        return _render_all(atoms)

    # -- sequences --------------------------------------------------------
    def parse_seq(
        self,
        stop_kinds: frozenset[str] | set[str] = frozenset(),
        stop_cmds: frozenset[str] | set[str] = frozenset(),
        stop_chars: frozenset[str] | set[str] = frozenset(),
    ) -> tuple[list[_Atom], _Token | None]:
        """Parse atoms until EOF or one of the stop conditions.

        The stopping token is **not** consumed.  Returns ``(atoms, stop_token)``
        where ``stop_token`` is ``None`` at end of input.

        An "open" big operator keeps accepting its scripts and then swallows
        exactly one following operand into its ``<m:e>`` slot -- this mirrors
        Word's own representation and avoids an empty argument placeholder.
        """
        self.depth += 1
        if self.depth > 200:
            raise ValueError("latex_to_omml: expression nested too deeply")

        completed: list[_Atom] = []
        tail: list[_Atom] = []
        open_nary: _Atom | None = None
        target: _Atom | None = None

        def commit() -> None:
            nonlocal tail, open_nary
            if not tail:
                return
            if open_nary is not None and not open_nary.body:
                open_nary.body = _render_all(tail)
                open_nary = None
            else:
                completed.extend(tail)
            tail = []

        try:
            while True:
                tok = self.peek()
                if tok is None:
                    commit()
                    return completed, None
                if tok.kind in stop_kinds:
                    commit()
                    return completed, tok
                if tok.kind == CMD and tok.value in stop_cmds:
                    commit()
                    return completed, tok
                if tok.kind == CHAR and tok.value in stop_chars:
                    commit()
                    return completed, tok

                self.next()

                if tok.kind in (CARET, UNDER):
                    tgt = tail[-1] if tail else target
                    if tgt is None:
                        tgt = _Atom(kind="seq", body="")
                        tail.append(tgt)
                    self._apply_script(tgt, tok.kind)
                    target = tgt
                    continue

                commit()
                target = None
                new_atoms, nary = self._parse_one(tok)
                if nary is not None:
                    completed.extend(new_atoms)
                    open_nary = nary
                    target = nary
                    tail = []
                else:
                    tail = new_atoms
                    target = tail[-1] if tail else None
        finally:
            self.depth -= 1

    # -- single token -----------------------------------------------------
    def _parse_one(self, tok: _Token) -> tuple[list[_Atom], _Atom | None]:
        """Turn one (already consumed) token into atoms.

        Returns ``(atoms, open_nary)``; ``open_nary`` is non-``None`` only for a
        big operator that still wants an operand.
        """
        kind = tok.kind
        if kind == LBRACE:
            inner, _ = self.parse_seq(stop_kinds={RBRACE})
            if self.peek() is not None and self.peek().kind == RBRACE:
                self.next()
            return [_Atom(kind="seq", body=_render_all(inner))], None
        if kind == LBRACKET:
            return [self._bracket_group("[")], None
        if kind == CHAR:
            ch = tok.value
            if not ch:
                return [], None
            if ch in "([":
                return [self._bracket_group(ch)], None
            return [self._char_atom(ch)], None
        if kind == CMD:
            return self._command(tok.value)
        if kind == AMP:
            return [self._char_atom("&")], None
        if kind == ROWSEP:
            return [self._char_atom("\\\\")], None
        if kind == RBRACE:
            return [], None
        return [self._char_atom(tok.value)], None

    # -- characters -------------------------------------------------------
    def _char_atom(self, ch: str) -> _Atom:
        if _is_variable_char(ch):
            return _Atom(kind="seq", body=self._var(ch))
        return _Atom(kind="seq", body=self._up(ch))

    def _bracket_group(self, opener: str) -> _Atom:
        """Parse ``(...)`` / ``[...]`` into an auto-sized ``<m:d>``.

        If the matching closer never appears the opener is emitted literally and
        the body is left as plain math (never raises).
        """
        if opener == "(":
            inner, stop = self.parse_seq(stop_chars={")"})
            body = _render_all(inner)
            if stop is None:
                return _Atom(kind="seq", body=self._up("(") + body)
            self.next()
            return _Atom(kind="seq", body=_delim_xml(body, "(", ")"))
        inner, stop = self.parse_seq(stop_kinds={RBRACKET})
        body = _render_all(inner)
        if stop is None:
            return _Atom(kind="seq", body=self._up("[") + body)
        self.next()
        return _Atom(kind="seq", body=_delim_xml(body, "[", "]"))

    # -- scripts ----------------------------------------------------------
    def _apply_script(self, atom: _Atom, kind: str) -> None:
        arg = self._script_arg()
        if kind == UNDER:
            atom.sub = arg
        else:
            atom.sup = arg

    def _script_arg(self) -> str:
        tok = self.peek()
        if tok is None:
            return ""
        if tok.kind == LBRACE:
            self.next()
            inner, _ = self.parse_seq(stop_kinds={RBRACE})
            if self.peek() is not None and self.peek().kind == RBRACE:
                self.next()
            return _render_all(inner)
        self.next()
        atoms, _ = self._parse_one(tok)
        return _render_all(atoms)

    def _required_arg(self) -> str:
        """Read a mandatory ``{...}`` argument (falls back to a single atom)."""
        tok = self.peek()
        if tok is None:
            return ""
        if tok.kind == LBRACE:
            self.next()
            inner, _ = self.parse_seq(stop_kinds={RBRACE})
            if self.peek() is not None and self.peek().kind == RBRACE:
                self.next()
            return _render_all(inner)
        self.next()
        atoms, _ = self._parse_one(tok)
        return _render_all(atoms)

    def _optional_bracket_arg(self) -> str | None:
        tok = self.peek()
        if tok is None or tok.kind != LBRACKET:
            return None
        self.next()
        inner, _ = self.parse_seq(stop_kinds={RBRACKET})
        if self.peek() is not None and self.peek().kind == RBRACKET:
            self.next()
        return _render_all(inner)

    # -- delimiters -------------------------------------------------------
    def _read_delimiter(self) -> str | None:
        """Read one delimiter token after ``\\left`` / ``\\right`` / ``\\middle``."""
        tok = self.peek()
        if tok is None:
            return None
        if tok.kind in (LBRACKET, RBRACKET):
            self.next()
            return tok.value
        if tok.kind == CHAR and tok.value in _DELIM_CHARS:
            self.next()
            return tok.value
        if tok.kind == CMD:
            mapped = DELIMITER_MACROS.get(tok.value)
            if mapped is not None:
                self.next()
                return mapped
        return None

    def _cmd_left(self) -> list[_Atom]:
        beg = self._read_delimiter()
        if beg is None:
            self._note_unknown("\\left")
            return [_Atom(kind="seq", body=self._up("left"))]
        inner, stop = self.parse_seq(stop_cmds={"right"})
        end = ""
        if stop is not None and stop.kind == CMD and stop.value == "right":
            self.next()
            end = self._read_delimiter() or ""
        return [_Atom(kind="seq", body=_delim_xml(_render_all(inner), beg, end))]

    # -- text-styled groups ----------------------------------------------
    def _text_group(self, *, nor: bool) -> str:
        """Reconstruct the literal source text of a ``{...}`` group."""
        tok = self.peek()
        if tok is None:
            return ""
        if tok.kind != LBRACE:
            self.next()
            return _token_text(tok)
        self.next()
        depth = 1
        parts: list[str] = []
        while not self.at_end():
            t = self.next()
            if t is None:
                break
            if t.kind == LBRACE:
                depth += 1
            elif t.kind == RBRACE:
                depth -= 1
                if depth == 0:
                    break
            parts.append(t.space + _token_text(t))
        return "".join(parts)

    # -- commands ---------------------------------------------------------
    def _command(self, name: str) -> tuple[list[_Atom], _Atom | None]:
        # 1. big operators -------------------------------------------------
        if name in BIG_OPERATORS:
            ch, lim = BIG_OPERATORS[name]
            atom = _Atom(kind="nary", nary_chr=ch, nary_lim=lim)
            return [atom], atom

        # 1b. size hints / style toggles ------------------------------------
        if name in _NOOP_MACROS:
            return [], None
        if name in _BIG_DELIM_MACROS:
            delim = self._read_delimiter()
            if delim is None:
                self._note_unknown("\\" + name)
                return [_Atom(kind="seq", body=self._up("\\" + name))], None
            return [_Atom(kind="seq", body=self._up(delim))], None

        # 2. fractions -----------------------------------------------------
        if name in ("frac", "dfrac", "tfrac", "cfrac"):
            num = self._required_arg()
            den = self._required_arg()
            # \dfrac/\tfrac differ in display size in LaTeX; OMML has no
            # text-style fraction, so all three map to <m:f>.
            return [_Atom(kind="seq", body=_frac_xml(num, den))], None

        if name == "binom" or name == "dbinom" or name == "tbinom":
            num = self._required_arg()
            den = self._required_arg()
            inner = _frac_xml(num, den, no_bar=True)
            return [_Atom(kind="seq", body=_delim_xml(inner, "(", ")"))], None

        # 3. radicals ------------------------------------------------------
        if name == "sqrt":
            deg = self._optional_bracket_arg()
            arg = self._required_arg()
            if deg is None:
                body = (
                    '<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr>'
                    f"<m:deg/><m:e>{arg}</m:e></m:rad>"
                )
            else:
                body = f"<m:rad><m:radPr/><m:deg>{deg}</m:deg><m:e>{arg}</m:e></m:rad>"
            return [_Atom(kind="seq", body=body)], None

        # 4. accents / bars ------------------------------------------------
        if name in ACCENTS:
            arg = self._required_arg()
            ch = ACCENTS[name]
            return [
                _Atom(
                    kind="seq",
                    body=(
                        "<m:acc>"
                        f'<m:accPr><m:chr m:val="{_attr(ch)}"/></m:accPr>'
                        f"<m:e>{arg}</m:e></m:acc>"
                    ),
                )
            ], None
        if name in BARS:
            arg = self._required_arg()
            pos = BARS[name]
            return [
                _Atom(
                    kind="seq",
                    body=(
                        "<m:bar>"
                        f'<m:barPr><m:pos m:val="{pos}"/></m:barPr>'
                        f"<m:e>{arg}</m:e></m:bar>"
                    ),
                )
            ], None

        # 5. delimiters ----------------------------------------------------
        if name == "left":
            return self._cmd_left(), None
        if name == "right":
            # A stray \right (no matching \left): swallow its delimiter.
            self._read_delimiter()
            return [], None
        if name == "middle":
            delim = self._read_delimiter()
            if delim is None:
                self._note_unknown("\\middle")
                return [_Atom(kind="seq", body=self._up("middle"))], None
            return [_Atom(kind="seq", body=self._up(delim))], None

        # 6. text / math alphabets ----------------------------------------
        if name in ("text", "textrm", "textnormal", "mbox", "operatorname"):
            txt = self._text_group(nor=True)
            return [_Atom(kind="seq", body=_m_run(txt, nor=True))], None
        if name in ("textbf",):
            txt = self._text_group(nor=True)
            return [_Atom(kind="seq", body=_m_run(txt, style="b", nor=False))], None
        if name in MATH_ALPHABETS:
            style = MATH_ALPHABETS[name]
            body = self._alpha_group(name, style)
            return [_Atom(kind="seq", body=body)], None

        # 7. environments ---------------------------------------------------
        if name == "begin":
            return self._environment()

        # 8. function names --------------------------------------------------
        if name in FUNCTIONS:
            if name in LIMIT_FUNCTIONS:
                return [_Atom(kind="lim", lim_name=name)], None
            return [_Atom(kind="seq", body=_m_run(name, style="p"))], None

        # 9. symbol tables ---------------------------------------------------
        for table in (GREEK_LOWER, SYMBOLS, GREEK_UPPER):
            if name in table:
                ch = table[name]
                body = _m_run(ch, style="p") if name in _UPRIGHT_GREEK else self._var(ch)
                return [_Atom(kind="seq", body=body)], None

        # 10. unknown macro -- never crash, record and fall back to literal text
        self._note_unknown("\\" + name)
        return [_Atom(kind="seq", body=self._up("\\" + name))], None

    # -- math alphabet groups ---------------------------------------------
    def _alpha_group(self, macro: str, style: str) -> str:
        tok = self.peek()
        if tok is None:
            return ""
        self.styles.append(style)
        try:
            if tok.kind != LBRACE:
                self.next()
                atoms, _ = self._parse_one(tok)
                return _render_all(atoms)
            self.next()
            inner, _ = self.parse_seq(stop_kinds={RBRACE})
            if self.peek() is not None and self.peek().kind == RBRACE:
                self.next()
            raw = _render_all(inner)
        finally:
            self.styles.pop()
        if macro == "mathbb":
            raw = self._blackboard_rewrite(raw)
        return raw

    @staticmethod
    def _blackboard_rewrite(raw: str) -> str:
        for letter, glyph in BLACKBOARD.items():
            raw = raw.replace(
                f'<m:t xml:space="preserve">{letter}</m:t>',
                f'<m:t xml:space="preserve">{glyph}</m:t>',
            )
        return raw

    # -- environments ------------------------------------------------------
    def _environment(self) -> tuple[list[_Atom], _Atom | None]:
        env = self._text_group(nor=False).strip()
        if env not in MATRIX_ENVS:
            self._note_unknown("\\begin{%s}" % env)
            return [_Atom(kind="seq", body="")], None

        beg, end, jc = MATRIX_ENVS[env]
        if env in _ENVS_WITH_COLSPEC and self.peek() is not None and self.peek().kind == LBRACE:
            self._text_group(nor=False)   # discard the column specification

        rows: list[list[str]] = []
        cur: list[str] = []
        while True:
            atoms, stop = self.parse_seq(
                stop_kinds={AMP, ROWSEP}, stop_cmds={"end"}
            )
            cur.append(_render_all(atoms))
            if stop is None:
                break
            if stop.kind == AMP:
                self.next()
                continue
            if stop.kind == ROWSEP:
                self.next()
                rows.append(cur)
                cur = []
                continue
            break   # CMD "end" -- left unconsumed for the code below
        rows.append(cur)

        # \end{env}: consume the command and its environment name.
        if self.peek() is not None and self.peek().kind == CMD and self.peek().value == "end":
            self.next()
            if self.peek() is not None and self.peek().kind == LBRACE:
                self._text_group(nor=False)

        # Drop a trailing all-empty row produced by a terminal "\\".
        while len(rows) > 1 and all(c.strip() == "" for c in rows[-1]):
            rows.pop()
        ncols = max(len(r) for r in rows) if rows else 1
        for r in rows:
            while len(r) < ncols:
                r.append("")

        body = _matrix_xml(rows, ncols, jc)
        if beg or end:
            body = _delim_xml(body, beg, end)
        return [_Atom(kind="seq", body=body)], None

    # -- bookkeeping -------------------------------------------------------
    @staticmethod
    def _note_unknown(name: str) -> None:
        UNKNOWN_MACROS.append(name)


# --------------------------------------------------------------------------
# OMML building blocks
# --------------------------------------------------------------------------


def _delim_xml(inner: str, beg: str, end: str, grow: bool = True) -> str:
    """``<m:d>`` delimiter object.  ``"."`` means "empty delimiter"."""
    if beg == ".":
        beg = ""
    if end == ".":
        end = ""
    pr = (
        "<m:dPr>"
        f'<m:begChr m:val="{_attr(beg)}"/>'
        f'<m:endChr m:val="{_attr(end)}"/>'
        f'<m:grow m:val="{1 if grow else 0}"/>'
        "</m:dPr>"
    )
    return f"<m:d>{pr}<m:e>{inner}</m:e></m:d>"


def _frac_xml(num: str, den: str, no_bar: bool = False) -> str:
    pr = '<m:fPr><m:type m:val="noBar"/></m:fPr>' if no_bar else "<m:fPr/>"
    return f"<m:f>{pr}<m:num>{num}</m:num><m:den>{den}</m:den></m:f>"


def _matrix_xml(rows: list[list[str]], ncols: int, jc: str) -> str:
    mcs = (
        "<m:mcs><m:mc><m:mcPr>"
        f'<m:count m:val="{ncols}"/>'
        f'<m:mcJc m:val="{_attr(jc)}"/>'
        "</m:mcPr></m:mc></m:mcs>"
    )
    body = "".join("<m:mr>" + "".join(f"<m:e>{c}</m:e>" for c in r) + "</m:mr>" for r in rows)
    return f"<m:m><m:mPr>{mcs}</m:mPr>{body}</m:m>"


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def latex_to_omml(latex: str) -> str:
    """Convert LaTeX math to the children of an ``<m:oMath>`` element.

    Unknown macros never raise: they are recorded in :data:`UNKNOWN_MACROS` and
    emitted as literal escaped text.
    """
    src = latex or ""
    toks = _tokenize(src)
    parser = _Parser(toks)
    return parser.parse()


def inline_omml(latex: str) -> str:
    """``<m:oMath>`` wrapper, for inline use inside a ``<w:p>``.

    ``CT_OMath`` requires at least one child element, so an empty conversion
    degrades to an empty run rather than an invalid ``<m:oMath/>``.
    """
    body = latex_to_omml(latex)
    if not body:
        body = _m_run("")
    return f"<m:oMath>{body}</m:oMath>"


def display_omml(latex: str, jc: str = "center") -> str:
    """``<m:oMathPara>`` wrapper: display-style ("professional") math."""
    body = latex_to_omml(latex)
    if not body:
        body = _m_run("")
    return (
        "<m:oMathPara>"
        f'<m:oMathParaPr><m:jc m:val="{_attr(jc)}"/></m:oMathParaPr>'
        f"<m:oMath>{body}</m:oMath>"
        "</m:oMathPara>"
    )


def omml_paragraph(
    latex: str,
    number: str | None = None,
    *,
    jc: str = "center",
    number_width_cm: float = 2.0,
    text_width_cm: float = 15.4,
    before: int = 120,
    after: int = 120,
) -> str:
    """A complete ``<w:p>`` holding a display equation.

    When ``number`` is given the paragraph uses two tab stops (centred at half
    the text width, right-aligned at the text width) so the equation stays
    centred while the number hugs the right margin.  :func:`equation_table`
    offers the (default) borderless-table alternative.
    """
    eq = display_omml(latex, jc=jc)
    if number is None:
        ppr = (
            "<w:pPr>"
            f'<w:spacing w:before="{before}" w:after="{after}" w:line="360" w:lineRule="auto"/>'
            f'<w:ind w:firstLine="0" w:firstLineChars="0"/>'
            f'<w:jc w:val="{_attr(jc)}"/>'
            "</w:pPr>"
        )
        return f"<w:p>{ppr}{eq}</w:p>"

    total = int(round(text_width_cm * CM_TO_TWIPS))
    half = total // 2
    ppr = (
        "<w:pPr>"
        f'<w:tabs><w:tab w:val="center" w:pos="{half}"/>'
        f'<w:tab w:val="right" w:pos="{total}"/></w:tabs>'
        f'<w:spacing w:before="{before}" w:after="{after}" w:line="360" w:lineRule="auto"/>'
        '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
        '<w:jc w:val="left"/>'
        "</w:pPr>"
    )
    num_run = (
        f'<w:r><w:t xml:space="preserve">{escape(str(number))}</w:t></w:r>'
    )
    return (
        f"<w:p>{ppr}<w:r><w:tab/></w:r>{eq}"
        "<w:r><w:tab/></w:r>"
        f"{num_run}</w:p>"
    )


def equation_table(
    latex: str,
    number: str | None = None,
    *,
    jc: str = "center",
    number_width_cm: float = 2.0,
    text_width_cm: float = 15.4,
    before: int = 120,
    after: int = 120,
    font_half_points: int | None = None,
) -> str:
    """Borderless 1-row / 2-column table: centred equation + right-aligned number.

    This is the layout :meth:`report_docx.Report.eq` uses by default.  Cell 1
    holds the display equation, cell 2 the equation number (default width
    2.0 cm).  All borders are ``none`` and every cell margin is zero so the
    equation is optically centred on the page.
    """
    total = int(round(text_width_cm * CM_TO_TWIPS))
    nw = int(round(number_width_cm * CM_TO_TWIPS))
    cw = max(total - nw, 1000)

    eq = display_omml(latex, jc=jc)
    sz = f'<w:sz w:val="{font_half_points}"/><w:szCs w:val="{font_half_points}"/>' if font_half_points else ""

    tbl_pr = (
        "<w:tblPr>"
        f'<w:tblW w:w="{total}" w:type="dxa"/>'
        '<w:jc w:val="center"/>'
        "<w:tblBorders>"
        '<w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        "</w:tblBorders>"
        '<w:tblLayout w:type="fixed"/>'
        "<w:tblCellMar>"
        '<w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/>'
        "</w:tblCellMar>"
        "</w:tblPr>"
    )
    grid = (
        "<w:tblGrid>"
        f'<w:gridCol w:w="{cw}"/><w:gridCol w:w="{nw}"/>'
        "</w:tblGrid>"
    )
    eq_ppr = (
        "<w:pPr>"
        f'<w:spacing w:before="{before}" w:after="{after}" w:line="240" w:lineRule="auto"/>'
        '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
        "</w:pPr>"
    )
    num_ppr = (
        "<w:pPr>"
        f'<w:spacing w:before="{before}" w:after="{after}" w:line="240" w:lineRule="auto"/>'
        '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
        '<w:jc w:val="right"/>'
        "</w:pPr>"
    )
    num_run = f'<w:r><w:rPr>{sz}</w:rPr><w:t xml:space="preserve">{escape(str(number or ""))}</w:t></w:r>'
    return (
        "<w:tbl>"
        f"{tbl_pr}{grid}"
        "<w:tr>"
        "<w:trPr><w:cantSplit/></w:trPr>"
        f'<w:tc><w:tcPr><w:tcW w:w="{cw}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
        f"<w:p>{eq_ppr}{eq}</w:p></w:tc>"
        f'<w:tc><w:tcPr><w:tcW w:w="{nw}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
        f"<w:p>{num_ppr}{num_run}</w:p></w:tc>"
        "</w:tr>"
        "</w:tbl>"
    )
