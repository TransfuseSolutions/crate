#!/usr/bin/env python
# crate_anon/nlp_manager/parse_haematology.py

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

import logging
import typing.re
from typing import Optional

from crate_anon.nlp_manager.nlp_definition import NlpDefinition
from crate_anon.nlp_manager.regex_parser import (
    OPTIONAL_RESULTS_IGNORABLES,
    RELATION,
    SimpleNumericalResultParser,
    TENSE_INDICATOR,
    ValidatorBase,
    WORD_BOUNDARY,
)
from crate_anon.nlp_manager.regex_numbers import SIGNED_FLOAT
from crate_anon.nlp_manager.regex_units import (
    BILLION_PER_L,
    CELLS_PER_CUBIC_MM,
    MG_PER_DL,
    MG_PER_L,
    MM_PER_H,
    PERCENT,
)

log = logging.getLogger(__name__)


# =============================================================================
#  Erythrocyte sedimentation rate (ESR)
# =============================================================================

class Esr(SimpleNumericalResultParser):
    """Erythrocyte sedimentation rate (ESR)."""
    ESR = r"""
        (?: {WORD_BOUNDARY}
            (?: (?: Erythrocyte [\s]+ sed(?:\.|imentation)? [\s]+ rate)
                | (?:ESR) )
        {WORD_BOUNDARY} )
    """.format(WORD_BOUNDARY=WORD_BOUNDARY)
    REGEX = r"""
        ( {ESR} )                           # group for "ESR" or equivalent
        {OPTIONAL_RESULTS_IGNORABLES}
        ( {TENSE_INDICATOR} )?              # optional group for tense indicator
        {OPTIONAL_RESULTS_IGNORABLES}
        ( {RELATION} )?                     # optional group for relation
        {OPTIONAL_RESULTS_IGNORABLES}
        ( {SIGNED_FLOAT} )                  # group for value
        {OPTIONAL_RESULTS_IGNORABLES}
        (                                   # optional group for units
            {MM_PER_H}                          # good
            | {MG_PER_DL}                       # bad
            | {MG_PER_L}                        # bad
        )?
    """.format(
        ESR=ESR,
        OPTIONAL_RESULTS_IGNORABLES=OPTIONAL_RESULTS_IGNORABLES,
        TENSE_INDICATOR=TENSE_INDICATOR,
        RELATION=RELATION,
        SIGNED_FLOAT=SIGNED_FLOAT,
        MM_PER_H=MM_PER_H,
        MG_PER_DL=MG_PER_DL,
        MG_PER_L=MG_PER_L,
    )
    NAME = "ESR"
    PREFERRED_UNIT_COLUMN = "value_mm_h"
    UNIT_MAPPING = {
        MM_PER_H: 1,       # preferred unit
        # not MG_PER_DL, MG_PER_L
    }

    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(
            nlpdef=nlpdef,
            cfgsection=cfgsection,
            regex_str=self.REGEX,
            variable=self.NAME,
            target_unit=self.PREFERRED_UNIT_COLUMN,
            units_to_factor=self.UNIT_MAPPING,
            commit=commit,
            take_absolute=True
        )

    def test(self, verbose: bool = False) -> None:
        self.test_numerical_parser([
            ("ESR (should fail)", []),  # should fail; no values
            ("ESR 6 (should succeed)", [6]),
            ("ESR = 6", [6]),
            ("ESR 6 mm/h", [6]),
            ("ESR <10", [10]),
            ("ESR <10 mm/hr", [10]),
            ("ESR >100", [100]),
            ("ESR >100 mm/hour", [100]),
            ("ESR was 62", [62]),
            ("ESR was 62 mm/h", [62]),
            ("ESR was 62 (H) mm/h", [62]),
            ("ESR was 62 mg/dl (should fail, wrong units)", []),
            ("Erythrocyte sed. rate was 19", [19]),
            ("his erythrocyte sedimentation rate was 19", [19]),
            ("erythrocyte sedimentation rate was 19", [19]),
            ("ESR 1.9 mg/L", []),  # wrong units
            ("ESR 1.9 (H) mg/L", []),  # wrong units
            ("ESR        |       1.9 (H)      | mg/L", []),
            ("my ESR was 15, but his ESR was 89!", [15, 89]),
            ("ESR-18", [18]),
        ], verbose=verbose)


class EsrValidator(ValidatorBase):
    """Validator for Esr (see ValidatorBase for explanation)."""
    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         regex_str_list=[Esr.ESR],
                         validated_variable=Esr.NAME,
                         commit=commit)


# =============================================================================
#  White blood cell count and differential
# =============================================================================
# Do NOT accept my handwritten abbreviations with slashed zeros, e.g.
#       L0 lymphocytes
#       N0 neutrophils
#       M0 monocytes
#       B0 basophils
#       E0 eosinophils
# ... too likely that these are interpreted in wrong contexts, particularly
# if we are not allowing units, like "M0 3": macrophages 3 x 10^9/L, or part
# of "T2 N0 M0 ..." cancer staging?

class WbcBase(SimpleNumericalResultParser):
    """DO NOT USE DIRECTLY. White cell count base class."""
    PREFERRED_UNIT_COLUMN = "value_billion_per_l"
    UNIT_MAPPING = {
        BILLION_PER_L: 1,     # preferred unit: 10^9 / L
        CELLS_PER_CUBIC_MM: 0.001,  # 1000 cells/mm^3 -> 1 x 10^9 / L
        # but NOT percent (too hard to interpret relative differentials
        # reliably)
    }

    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 cell_type_regex_text: str,
                 variable: str,
                 commit: bool = False) -> None:
        super().__init__(
            nlpdef=nlpdef,
            cfgsection=cfgsection,
            regex_str=self.make_wbc_regex(cell_type_regex_text),
            variable=variable,
            target_unit=self.PREFERRED_UNIT_COLUMN,
            units_to_factor=self.UNIT_MAPPING,
            commit=commit,
            take_absolute=True
        )

    @staticmethod
    def make_wbc_regex(cell_type_regex_text: str) -> typing.re.Pattern:
        return r"""
            ({CELL_TYPE})                   # group for cell type name
            {OPTIONAL_RESULTS_IGNORABLES}
            ({TENSE_INDICATOR})?            # optional group for tense indicator
            {OPTIONAL_RESULTS_IGNORABLES}
            ({RELATION})?                   # optional group for relation
            {OPTIONAL_RESULTS_IGNORABLES}
            ({SIGNED_FLOAT})                # group for value
            {OPTIONAL_RESULTS_IGNORABLES}
            (                               # optional units, good and bad
                {BILLION_PER_L}                 # good
                | {CELLS_PER_CUBIC_MM}          # good
                | {PERCENT}                     # bad, so we can ignore it
            )?
        """.format(
            CELL_TYPE=cell_type_regex_text,
            OPTIONAL_RESULTS_IGNORABLES=OPTIONAL_RESULTS_IGNORABLES,
            TENSE_INDICATOR=TENSE_INDICATOR,
            RELATION=RELATION,
            SIGNED_FLOAT=SIGNED_FLOAT,
            BILLION_PER_L=BILLION_PER_L,
            CELLS_PER_CUBIC_MM=CELLS_PER_CUBIC_MM,
            PERCENT=PERCENT,
        )


# -----------------------------------------------------------------------------
# WBC
# -----------------------------------------------------------------------------

class Wbc(WbcBase):
    """White cell count (WBC, WCC)."""
    WBC = r"""
        (?: \b (?:
            (?:                 # White blood cells, white cell count, etc.
                White\b [\s]* (?:\bblood\b)? [\s]* \bcell[s]?\b
                [\s]* (?:\bcount\b)? [\s]*
                (?:     # optional suffix WBC, (WBC), (WBCC), (WCC), etc.
                    [\(]? (?: WBC | WBCC | WCC) [\)]?
                )?
            )
            | (?:               # just WBC(s), WBCC, WCC
                (?: WBC[s]? | WBCC | WCC )
            )
        ) \b )
    """
    NAME = "WBC"

    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         commit=commit,
                         cell_type_regex_text=self.WBC,
                         variable=self.NAME)

    def test(self, verbose: bool = False) -> None:
        self.test_numerical_parser([
            ("WBC (should fail)", []),  # should fail; no values
            ("WBC 6", [6]),
            ("WBC = 6", [6]),
            ("WBC 6 x 10^9/L", [6]),
            ("WBC 6 x 10 ^ 9 / L", [6]),
            ("WCC 6.2", [6.2]),
            ("white cells 6.2", [6.2]),
            ("white cells 6.2", [6.2]),
            ("white cells 9800/mm3", [9.8]),
            ("white cells 9800 cell/mm3", [9.8]),
            ("white cells 9800 cells/mm3", [9.8]),
            ("white cells 9800 per cubic mm", [9.8]),
            ("white cells 17,600/mm3", [17.6]),
            ("WBC – 6", [6]),  # en dash
            ("WBC—6", [6]),  # em dash
            ("WBC -- 6", [6]),  # double hyphen used as dash
            ("WBC - 6", [6]),
            ("WBC-6.5", [6.5]),
        ], verbose=verbose)


class WbcValidator(ValidatorBase):
    """Validator for Wbc (see ValidatorBase for explanation)."""
    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         regex_str_list=[Wbc.WBC],
                         validated_variable=Wbc.NAME,
                         commit=commit)


# -----------------------------------------------------------------------------
#  Neutrophils
# -----------------------------------------------------------------------------

class Neutrophils(WbcBase):
    """Neutrophil count (absolute)."""
    NEUTROPHILS = r"""
        (?:
            (?: \b absolute \s* )?
            \b (?: Neut(?:r(?:o(?:phil)?)?)?s? | N0 ) \b
            (?: \s* count \b )?
        )
    """
    NAME = "neutrophils"

    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         commit=commit,
                         cell_type_regex_text=self.NEUTROPHILS,
                         variable=self.NAME)

    def test(self, verbose: bool = False) -> None:
        self.test_numerical_parser([
            ("neutrophils (should fail)", []),  # should fail; no values
            ("absolute neutrophil count 6", [6]),
            ("neuts = 6", [6]),
            ("N0 6 x 10^9/L", [6]),
            ("neutrophil count 6 x 10 ^ 9 / L", [6]),
            ("neutrs 6.2", [6.2]),
            ("neutrophil 6.2", [6.2]),
            ("neutrophils 6.2", [6.2]),
            ("n0 9800/mm3", [9.8]),
            ("absolute neutrophils 9800 cell/mm3", [9.8]),
            ("neutrophils count 9800 cells/mm3", [9.8]),
            ("n0 9800 per cubic mm", [9.8]),
            ("n0 17,600/mm3", [17.6]),
            ("neuts-17", [17]),
        ], verbose=verbose)


class NeutrophilsValidator(ValidatorBase):
    """Validator for Neutrophils (see ValidatorBase for explanation)."""
    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         regex_str_list=[Neutrophils.NEUTROPHILS],
                         validated_variable=Neutrophils.NAME,
                         commit=commit)


# -----------------------------------------------------------------------------
#  Lymphocytes
# -----------------------------------------------------------------------------

class Lymphocytes(WbcBase):
    """Lymphocyte count (absolute)."""
    LYMPHOCYTES = r"""
        (?:
            (?: \b absolute \s* )?
            \b Lymph(?:o(?:cyte)?)?s? \b
            (?: \s* count \b )?
        )
    """
    NAME = "lymphocytes"

    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         commit=commit,
                         cell_type_regex_text=self.LYMPHOCYTES,
                         variable=self.NAME)

    def test(self, verbose: bool = False) -> None:
        self.test_numerical_parser([
            ("lymphocytes (should fail)", []),  # should fail; no values
            ("absolute lymphocyte count 6", [6]),
            ("lymphs = 6", [6]),
            ("L0 6 x 10^9/L (should fail)", []),
            ("lymphocyte count 6 x 10 ^ 9 / L", [6]),
            ("lymphs 6.2", [6.2]),
            ("lymph 6.2", [6.2]),
            ("lympho 6.2", [6.2]),
            ("lymphos 9800/mm3", [9.8]),
            ("absolute lymphocytes 9800 cell/mm3", [9.8]),
            ("lymphocytes count 9800 cells/mm3", [9.8]),
            ("l0 9800 per cubic mm (should fail)", []),
            ("l0 17,600/mm3 (should fail)", []),
            ("lymphs-6.3", [6.3]),
        ], verbose=verbose)


class LymphocytesValidator(ValidatorBase):
    """Validator for Lymphocytes (see ValidatorBase for explanation)."""
    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         regex_str_list=[Lymphocytes.LYMPHOCYTES],
                         validated_variable=Lymphocytes.NAME,
                         commit=commit)


# -----------------------------------------------------------------------------
#  Monocytes
# -----------------------------------------------------------------------------

class Monocytes(WbcBase):
    """Monocyte count (absolute)."""
    MONOCYTES = r"""
        (?:
            (?: \b absolute \s* )?
            \b Mono(?:cyte)?s? \b
            (?: \s* count \b )?
        )
    """
    NAME = "monocytes"

    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         commit=commit,
                         cell_type_regex_text=self.MONOCYTES,
                         variable=self.NAME)

    def test(self, verbose: bool = False) -> None:
        self.test_numerical_parser([
            ("monocytes (should fail)", []),  # should fail; no values
            ("absolute monocyte count 6", [6]),
            ("monos = 6", [6]),
            ("M0 6 x 10^9/L (should fail)", []),
            ("monocyte count 6 x 10 ^ 9 / L", [6]),
            ("monos 6.2", [6.2]),
            ("mono 6.2", [6.2]),
            ("monos 9800/mm3", [9.8]),
            ("absolute mono 9800 cell/mm3", [9.8]),
            ("monocytes count 9800 cells/mm3", [9.8]),
            ("m0 9800 per cubic mm (should fail)", []),
            ("m0 17,600/mm3 (should fail)", []),
            ("monocytes-5.2", [5.2]),
        ], verbose=verbose)


class MonocytesValidator(ValidatorBase):
    """Validator for Monocytes (see ValidatorBase for explanation)."""
    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         regex_str_list=[Monocytes.MONOCYTES],
                         validated_variable=Monocytes.NAME,
                         commit=commit)


# -----------------------------------------------------------------------------
#  Basophils
# -----------------------------------------------------------------------------

class Basophils(WbcBase):
    """Basophil count (absolute)."""
    BASOPHILS = r"""
        (?:
            (?: \b absolute \s* )?
            \b Baso(?:phil)?s? \b
            (?: \s* count \b )?
        )
    """
    NAME = "basophils"

    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         commit=commit,
                         cell_type_regex_text=self.BASOPHILS,
                         variable=self.NAME)

    def test(self, verbose=False) -> None:
        self.test_numerical_parser([
            ("basophils (should fail)", []),  # should fail; no values
            ("absolute basophil count 6", [6]),
            ("basos = 6", [6]),
            ("B0 6 x 10^9/L (should fail)", []),
            ("basophil count 6 x 10 ^ 9 / L", [6]),
            ("basos 6.2", [6.2]),
            ("baso 6.2", [6.2]),
            ("basos 9800/mm3", [9.8]),
            ("absolute basophil 9800 cell/mm3", [9.8]),
            ("basophils count 9800 cells/mm3", [9.8]),
            ("b0 9800 per cubic mm (should fail)", []),
            ("b0 17,600/mm3 (should fail)", []),
            ("basophils-5.2", [5.2]),
        ], verbose=verbose)


class BasophilsValidator(ValidatorBase):
    """Validator for Basophils (see ValidatorBase for explanation)."""
    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         regex_str_list=[Basophils.BASOPHILS],
                         validated_variable=Basophils.NAME,
                         commit=commit)


# -----------------------------------------------------------------------------
#  Eosinophils
# -----------------------------------------------------------------------------

class Eosinophils(WbcBase):
    """Eosinophil count (absolute)."""
    EOSINOPHILS = r"""
        (?:
            (?: \b absolute \s* )?
            \b Eo(?:sin(?:o(?:phil)?)?)?s? \b
            (?: \s* count \b )?
        )
    """
    NAME = "eosinophils"

    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         commit=commit,
                         cell_type_regex_text=self.EOSINOPHILS,
                         variable=self.NAME)

    def test(self, verbose: bool = False) -> None:
        self.test_numerical_parser([
            ("eosinophils (should fail)", []),  # should fail; no values
            ("absolute eosinophil count 6", [6]),
            ("eos = 6", [6]),
            ("E0 6 x 10^9/L (should fail)", []),
            ("eosinophil count 6 x 10 ^ 9 / L", [6]),
            ("eosins 6.2", [6.2]),
            ("eosino 6.2", [6.2]),
            ("eosinos 9800/mm3", [9.8]),
            ("absolute eosinophil 9800 cell/mm3", [9.8]),
            ("eosinophils count 9800 cells/mm3", [9.8]),
            ("e0 9800 per cubic mm (should fail)", []),
            ("e0 17,600/mm3 (should fail)", []),
            ("eosinophils-5.3", [5.3]),
        ], verbose=verbose)


class EosinophilsValidator(ValidatorBase):
    """Validator for Eosinophils (see ValidatorBase for explanation)."""
    def __init__(self,
                 nlpdef: Optional[NlpDefinition],
                 cfgsection: Optional[str],
                 commit: bool = False) -> None:
        super().__init__(nlpdef=nlpdef,
                         cfgsection=cfgsection,
                         regex_str_list=[Eosinophils.EOSINOPHILS],
                         validated_variable=Eosinophils.NAME,
                         commit=commit)


# =============================================================================
#  Command-line entry point
# =============================================================================

def test_all(verbose: bool = False) -> None:
    # ESR
    esr = Esr(None, None)
    esr.test(verbose=verbose)

    # WBC and differential
    wbc = Wbc(None, None)
    wbc.test(verbose=verbose)
    n0 = Neutrophils(None, None)
    n0.test(verbose=verbose)
    l0 = Lymphocytes(None, None)
    l0.test(verbose=verbose)
    m0 = Monocytes(None, None)
    m0.test(verbose=verbose)
    b0 = Basophils(None, None)
    b0.test(verbose=verbose)
    e0 = Eosinophils(None, None)
    e0.test(verbose=verbose)


if __name__ == '__main__':
    test_all(verbose=True)
