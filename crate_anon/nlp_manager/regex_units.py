#!/usr/bin/env python
# crate_anon/nlp_manager/regex_units.py

"""
===============================================================================
    Copyright (C) 2015-2017 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of CRATE.

    CRATE is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    CRATE is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with CRATE. If not, see <http://www.gnu.org/licenses/>.
===============================================================================
"""

from typing import List, Optional, Tuple
from crate_anon.nlp_manager.regex_test import test_text_regex
from crate_anon.nlp_manager.regex_numbers import (
    BILLION,
    MULTIPLY_OR_SPACE,
    PLAIN_INTEGER,
    POWER,
)


# =============================================================================
# Physical units
# =============================================================================

OUT_OF_SEPARATOR = r"(?: \/ | \b out \s+ of \b )"


def per(numerator: str, denominator: str,
        include_power_minus1: bool = True) -> str:
    # Copes with blank/optional numerators, too.
    options = [
        r"(?: {numerator} \s* (?: \/ | \b per \b) \s* {denominator} )".format(
            numerator=numerator, denominator=denominator),
    ]
    if include_power_minus1:
        options.append(
            r"(?: {numerator} \s* \b {denominator} \s* -1 )".format(
                numerator=numerator, denominator=denominator))
    return r"(?: {} )".format(r" | ".join(options))
    # Use of "\s* \b" rather than "\s+" is so we can have a BLANK numerator.


def _out_of_str(n_as_regex: str):
    # / n
    # out of n
    return r"(?: {out_of} \s* {n} \b)".format(out_of=OUT_OF_SEPARATOR,
                                              n=n_as_regex)


def out_of(n: int) -> str:
    return _out_of_str(str(n))


def out_of_anything() -> str:
    # out_of(n) where n is any number
    return _out_of_str(PLAIN_INTEGER)


def power(x: str, n: int, allow_no_operator: bool=False) -> str:
    return r"(?: {x} \s* {power}{optional} \s* {n})".format(
        x=x,
        power=POWER,
        optional="?" if allow_no_operator else "",
        n=n,
    )


def units_times(*args: str) -> str:
    """For units, where they are notionally multiplied."""
    multiply = MULTIPLY_OR_SPACE + "?"
    joined = multiply.join(args)
    return r"(?: {} )".format(joined)


def units_by_dimension(*args: Tuple[Tuple[str, int], ...],
                       allow_no_operator: bool=False) -> str:
    multiply = " " + MULTIPLY_OR_SPACE + " "
    power_elements = []  # type: List[str]
    for i, unit_exponent in enumerate(args):
        unit, exponent = unit_exponent
        assert(exponent != 0)
        power_elements.append(
            power(unit, exponent, allow_no_operator=allow_no_operator))
    joined_power_elements = multiply.join(power_elements)
    power_style = r"(?: {} )".format(joined_power_elements)
    options = [power_style]
    # noinspection PyChainedComparisons
    if len(args) == 2 and args[0][1] > 0 and args[1][1] < 0:
        # x per y
        options.append(per(args[0][0], args[1][0],
                           include_power_minus1=False))
    return r"(?: {} )".format(r" | ".join(options))


# -----------------------------------------------------------------------------
# Distance
# -----------------------------------------------------------------------------

M = r"(?: met(?:re|er)s? | m )"  # m, metre(s), meter(s)
CM = r"(?: cm | centimet(?:re|er)s? )"   # cm, centimetre(s), centimeter(s)
MM = r"(?: mm | millimet(?:re|er)s? )"   # mm, millimetre(s), millimeter(s)

FEET = r"""(?: f(?:ee|oo)?t | \' | ’ | ′ )"""
# ... feet, foot, ft
# ... apostrophe, right single quote (U+2019), prime (U+2032)
INCHES = r'''(?: in(?:ch(?:e)?)?s? | \" | ” | ″)'''
# ... in, ins, inch, inches, [inchs = typo but clear]
# ... ", right double quote (U+2014), double prime (U+2033)

# -----------------------------------------------------------------------------
# Mass
# -----------------------------------------------------------------------------

MCG = r"(?: mcg | microgram(?:me)?s? | [μu]g )"  # you won't stop people using ug...  # noqa
MG = r"(?: mg | milligram(?:me)?s? )"  # mg, milligram, milligrams, milligramme, milligrammes  # noqa
G = r"(?: gram(?:me)?s? | g )"  # g, gram, grams, gramme, grammes  # noqa
KG = r"(?: kgs? | kilo(?:gram(?:me)?)?s? )"  # kg, kgs, kilos ... kilogrammes etc.  # noqa
LB = r"(?: pounds? | lbs? )"  # pound(s), lb(s)
STONES = r"(?: stones? | st\.? )"  # stone(s), st, st.

# -----------------------------------------------------------------------------
# Volume
# -----------------------------------------------------------------------------

L = r"(?: lit(?:re|er)s? | L )"  # L, litre(s), liter(s)
DL = r"(?: d(?:eci)?{L} )".format(L=L)
ML = r"(?: m(?:illi)?{L} )".format(L=L)
CUBIC_MM = r"""(?: (?:\b cubic \s+ {mm}) | {mm_cubed} )""".format(
    mm=MM,
    mm_cubed=power(MM, 3, allow_no_operator=True)
)
# cubic mm, etc. | mm^3, mm3, mm 3, etc.

# -----------------------------------------------------------------------------
# Inverse volume
# -----------------------------------------------------------------------------

PER_CUBIC_MM = per("", CUBIC_MM)

# -----------------------------------------------------------------------------
# Time
# -----------------------------------------------------------------------------

HOUR = r"(?:h(?:rs?|ours?)?)"   # h, hr, hrs, hour, hours

# -----------------------------------------------------------------------------
# Counts, proportions
# -----------------------------------------------------------------------------

PERCENT = r"""(?:%|pe?r?\s?ce?n?t)"""
# must have pct, other characters optional

# -----------------------------------------------------------------------------
# Arbitrary count things
# -----------------------------------------------------------------------------

CELLS = r"(?:\b cells? \b)"
OPTIONAL_CELLS = CELLS + "?"
MILLIMOLES = r"(?: m(?:illi)?mol(?:es?)? )"
MILLIEQ = r"(?:m(?:illi)?Eq)"

UNITS = r"(?:[I]?U)"  # U units, IU international units
MILLIUNITS = r"(?:m[I]?U)"
MICROUNITS = r"(?:[μu][I]?U)"

SCORE = r"(?:scored?)"  # score(d)

# -----------------------------------------------------------------------------
# Concentration
# -----------------------------------------------------------------------------

MILLIMOLAR = r"(?:mM)"  # NB case-insensitive... confusable with millimetres
MG_PER_DL = per(MG, DL)
MG_PER_L = per(MG, L)
MILLIMOLES_PER_L = per(MILLIMOLES, L)
MILLIEQ_PER_L = per(MILLIEQ, L)
BILLION_PER_L = per(BILLION, L)
CELLS_PER_CUBIC_MM = per(OPTIONAL_CELLS, CUBIC_MM)

MILLIUNITS_PER_L = per(MILLIUNITS, L)
MICROUNITS_PER_ML = per(MICROUNITS, ML)

# -----------------------------------------------------------------------------
# Speed
# -----------------------------------------------------------------------------

MM_PER_H = per(MM, HOUR)

# -----------------------------------------------------------------------------
# Pressure
# -----------------------------------------------------------------------------

MM_HG = r"(?: mm \s* Hg )"  # mmHg, mm Hg
# ... likelihood of "millimetres of mercury" quite small?

# -----------------------------------------------------------------------------
# Things to powers
# -----------------------------------------------------------------------------

SQ_M = r"""
    (?:  # square metres
        (?: sq(?:uare)? \s+ {m} )       # sq m, square metres, etc.
        | (?: {m} \s+ sq(?:uared?)? )   # m sq, metres square(d), etc.
        | {m_sq}                        # m ^ 2, etc.
    )
""".format(m=M, m_sq=power(M, 2))

# BMI
KG_PER_SQ_M = r"(?: {kg_per_sqm} | {kg_sqm_pow_minus2} )".format(
    kg_per_sqm=per(KG, SQ_M, include_power_minus1=False),
    kg_sqm_pow_minus2=units_times(KG, power(M, -2)),
)


# =============================================================================
#  Generic conversion functions
# =============================================================================

def kg_from_st_lb_oz(stones: float = 0,
                     pounds: float = 0,
                     ounces: float = 0) -> Optional[float]:
    # 16 ounces in a pound
    # 14 pounds in a stone
    # 1 avoirdupois pound = 0.45359237 kg
    # https://en.wikipedia.org/wiki/Pound_(mass)
    # Have you the peas? "Goods of weight"; aveir de peis (OFr.; see OED).
    try:
        total_pounds = (stones * 14) + pounds + (ounces / 16)
        return 0.45359237 * total_pounds
    except (TypeError, ValueError):
        return None


def m_from_ft_in(feet: float = 0, inches: float = 0) -> Optional[float]:
    # 12 inches in a foot
    # 1 inch = 25.4 mm
    try:
        total_inches = (feet * 12) + inches
        return total_inches * 25.4 / 1000
    except (TypeError, ValueError):
        return None


def m_from_m_cm(metres: float = 0, centimetres: float = 0) -> Optional[float]:
    try:
        return metres + (centimetres / 100)
    except (TypeError, ValueError):
        return None


def assemble_units(components: List[Optional[str]]) -> str:
    """Takes e.g. ["ft", "in"] and makes "ft in"."""
    active_components = [c for c in components if c]
    return " ".join(active_components)


# =============================================================================
#  Tests
# =============================================================================

def test_unit_regexes(verbose: bool = False) -> None:
    test_text_regex("per(n, d)", per("n", "d"), [
        ("blah n per d blah", ["n per d"]),
        ("blah n/d blah", ["n/d"]),
        ("n / d", ["n / d"]),
        ("n d -1", ["n d -1"]),
        ("n d -1", ["n d -1"]),
        ("n blah d", []),
    ], verbose=verbose)
    test_text_regex("out_of(5)", out_of(5), [
        ("4 out of 5", ["out of 5"]),
        ("4/5", ["/5"]),
        ("4 / 5", ["/ 5"]),
    ], verbose=verbose)

    test_text_regex("M", M, [
        ("5 metres long", ["metres"]),
        ("5 meters long", ["meters"]),
        ("5m long", ["m"]),
    ], verbose=verbose)
    test_text_regex("CM", CM, [
        ("5 centimetres long", ["centimetres"]),
        ("5 centimeters long", ["centimeters"]),
        ("5cm long", ["cm"]),
    ], verbose=verbose)
    test_text_regex("MM", MM, [
        ("5 millimetres long", ["millimetres"]),
        ("5 millimeters long", ["millimeters"]),
        ("5mm long", ["mm"]),
    ], verbose=verbose)
    test_text_regex("FEET", FEET, [
        ("5 feet long", ["feet"]),
        ("5 foot long", ["foot"]),
        ("5' long", ["'"]),  # ASCII apostrophe
        ("5’ long", ["’"]),  # right single quote (U+2019)
        ("5′ long", ["′"]),  # prime (U+2032)
    ], verbose=verbose)
    test_text_regex("INCHES", INCHES, [
        ("5 inches long", ["inches"]),
        ("5 in long", ["in"]),
        ('5" long', ['"']),  # ASCII double quote
        ("5” long", ["”"]),  # right double quote (U+2014)
        ("5″ long", ["″"]),  # double prime (U+2033)
    ], verbose=verbose)

    test_text_regex("MCG", MCG, [
        ("5 micrograms", ["micrograms"]),
        ("5 mcg", ["mcg"]),
        ("5 ug", ["ug"]),
        ("5 μg", ["μg"]),
    ], verbose=verbose)
    test_text_regex("MG", MG, [
        ("5 milligrams", ["milligrams"]),
        ("5 mg", ["mg"]),
    ], verbose=verbose)
    test_text_regex("G", G, [
        ("5 grams", ["grams"]),
        ("5 g", ["g"]),
    ], verbose=verbose)
    test_text_regex("KG", KG, [
        ("5 kilograms", ["kilograms"]),
        ("5 kg", ["kg"]),
    ], verbose=verbose)
    test_text_regex("LB", LB, [
        ("5 pounds", ["pounds"]),
        ("5 lb", ["lb"]),
    ], verbose=verbose)
    test_text_regex("STONES", STONES, [
        ("5 stones", ["stones"]),
        ("5 stone", ["stone"]),
        ("5 st", ["st"]),
    ], verbose=verbose)

    test_text_regex("L", L, [
        ("5 litres", ["litres"]),
        ("5 liters", ["liters"]),
        ("5 l", ["l"]),
        ("5 L", ["L"]),
    ], verbose=verbose)
    test_text_regex("DL", DL, [
        ("5 decilitres", ["decilitres"]),
        ("5 deciliters", ["deciliters"]),
        ("5 dl", ["dl"]),
        ("5 dL", ["dL"]),
    ], verbose=verbose)
    test_text_regex("ML", ML, [
        ("5 millilitres", ["millilitres"]),
        ("5 milliliters", ["milliliters"]),
        ("5 ml", ["ml"]),
        ("5 mL", ["mL"]),
    ], verbose=verbose)
    test_text_regex("CUBIC_MM", CUBIC_MM, [
        ("5 mm^3", ["mm^3"]),
        ("5 cubic mm", ["cubic mm"]),
        ("5 cubic millimetres", ["cubic millimetres"]),
    ], verbose=verbose)

    test_text_regex("HOUR", HOUR, [
        ("5 hours", ["hours"]),
        ("5 hr", ["hr"]),
        ("5 h", ["h"]),
    ], verbose=verbose)

    test_text_regex("PERCENT", PERCENT, [
        ("5 percent", ["percent"]),
        ("5 per cent", ["per cent"]),
        ("5 pct", ["pct"]),
        ("5%", ["%"]),
    ], verbose=verbose)

    test_text_regex("CELLS", CELLS, [
        ("5 cells", ["cells"]),
        ("5 cell", ["cell"]),
    ], verbose=verbose)

    test_text_regex("MILLIMOLES", MILLIMOLES, [
        ("5 millimoles", ["millimoles"]),
        ("5 millimol", ["millimol"]),
        ("5 mmol", ["mmol"]),
    ], verbose=verbose)
    test_text_regex("MILLIEQ", MILLIEQ, [
        ("5 mEq", ["mEq"]),
    ], verbose=verbose)

    test_text_regex("UNITS", UNITS, [
        ("5 U", ["U"]),
        ("5 IU", ["IU"]),
    ], verbose=verbose)
    test_text_regex("MILLIUNITS", MILLIUNITS, [
        ("5 mU", ["mU"]),
        ("5 mIU", ["mIU"]),
    ], verbose=verbose)
    test_text_regex("MICROUNITS", MICROUNITS, [
        ("5 uU", ["uU"]),
        ("5 μU", ["μU"]),
        ("5 uIU", ["uIU"]),
        ("5 μIU", ["μIU"]),
    ], verbose=verbose)

    test_text_regex("SCORE", SCORE, [
        ("I scored 5", ["scored"]),
        ("MMSE score 5", ["score"]),
    ], verbose=verbose)

    test_text_regex("MILLIMOLAR", MILLIMOLAR, [
        ("5 mM", ["mM"]),
    ], verbose=verbose)

    test_text_regex("MM_HG", MM_HG, [
        ("5 mmHg", ["mmHg"]),
        ("5 mm Hg", ["mm Hg"]),
    ], verbose=verbose)

    test_text_regex("SQ_M", SQ_M, [
        ("5 square metres", ["square metres"]),
        ("5 sq m", ["sq m"]),
        ("5 m^2", ["m^2"]),
    ], verbose=verbose)

    test_text_regex("KG_PER_SQ_M", KG_PER_SQ_M, [
        ("5 kg per square metre", ["kg per square metre"]),
        ("5 kg/sq m", ["kg/sq m"]),
        ("5 kg/m^2", ["kg/m^2"]),
        ("5 kg*m^-2", ["kg*m^-2"]),
    ], verbose=verbose)


def test_all(verbose: bool = False) -> None:
    test_unit_regexes(verbose=verbose)


if __name__ == '__main__':
    test_all()
