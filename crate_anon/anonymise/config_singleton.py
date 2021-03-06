#!/usr/bin/env python
# crate_anon/anonymise/config_singleton.py

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

from crate_anon.anonymise.config import Config


# =============================================================================
# Singleton config
# =============================================================================

config = Config()

# A singleton class here is messy.
# The reason we use it is that class definitions, such as PatientInfo,
# depend on things set in the config, even before instances are created.
