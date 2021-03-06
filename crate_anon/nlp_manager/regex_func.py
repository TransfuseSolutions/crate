#!/usr/bin/env python
# crate_anon/nlp_manager/regex_func.py

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

import typing.re
from typing import Any, Dict, Optional, Tuple

import regex
# noinspection PyProtectedMember
from regex import _regex_core

# =============================================================================
#  Core regex functions
# =============================================================================
# - All will use VERBOSE mode for legibility. (No impact on speed: compiled.)
# - Don't forget to use raw strings for all regex definitions!
# - Beware comments inside regexes. The comment parser isn't quite as benign
#   as you might think. Use very plain text only.
# - (?: XXX ) makes XXX into an unnamed group.


REGEX_COMPILE_FLAGS = (regex.IGNORECASE | regex.MULTILINE | regex.VERBOSE |
                       regex.UNICODE)


def at_wb_start_end(regex_str: str) -> str:
    """
    Caution using this. Digits do not end a word, so "mm3" will not match if
    your "mm" group ends in a word boundary.
    """
    return "\b(?: {} )\b".format(regex_str)


def at_start_wb(regex_str: str) -> str:
    """
    With word boundary at start. Beware, though; e.g. "3kg" is reasonable, and
    this does NOT have a word boundary in.
    """
    return "(?: \b (?: {} ) )".format(regex_str)


def compile_regex(regex_str: str) -> typing.re.Pattern:
    try:
        return regex.compile(regex_str, REGEX_COMPILE_FLAGS)
    except _regex_core.error:
        print("FAILING REGEX:\n{}".format(regex_str))
        raise


def compile_regex_dict(regexstr_to_value_dict: Dict[str, Any]) \
        -> Dict[typing.re.Pattern, Any]:
    return {
        compile_regex(k): v
        for k, v in regexstr_to_value_dict.items()
    }


def get_regex_dict_match(text: Optional[str],
                         regex_to_value_dict: Dict[typing.re.Pattern, Any],
                         default: Any = None) \
        -> Tuple[bool, Any]:
    """Returns (matched, result)."""
    if text:
        for r, value in regex_to_value_dict.items():
            if r.match(text):
                return True, value
    return False, default
