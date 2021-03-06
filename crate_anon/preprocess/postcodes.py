#!/usr/bin/env python
# crate_anon/tools/postcodes.py

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

Code-Point Open, CSV, GB
- https://www.ordnancesurvey.co.uk/business-and-government/products/opendata-products.html
- https://www.ordnancesurvey.co.uk/business-and-government/products/code-point-open.html
- https://www.ordnancesurvey.co.uk/opendatadownload/products.html
- http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

Office for National Statistics Postcode Database (ONSPD):
- https://geoportal.statistics.gov.uk/geoportal/catalog/content/filelist.page
- e.g. ONSPD_MAY_2016_csv.zip
- http://www.ons.gov.uk/methodology/geography/licences

Background:
- OA = Output Area
    ... smallest: >=40 households, >=100 people
    ... 181,408 OAs in England & Wales
- LSOA = Lower Layer Super Output Area
    ... 34,753 LSOAs in England & Wales
- MSOA = Middle Layer Super Output Area
    ... 7,201 MSOAs in England & Wales
- WZ = Workplace Zone
    - https://www.ons.gov.uk/methodology/geography/ukgeographies/censusgeography#workplace-zone-wz
- https://www.ons.gov.uk/methodology/geography/ukgeographies/censusgeography#output-area-oa
"""  # noqa

import argparse
import csv
import datetime
import logging
import os
import sys
# import textwrap
from typing import Any, Dict, Generator, Iterable, List, TextIO

import openpyxl
from openpyxl.cell.cell import Cell
import prettytable
from sqlalchemy import (
    Column,
    create_engine,
    Date,
    Integer,
    MetaData,
    Numeric,
    String,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
import xlrd

from cardinal_pythonlib.rnc_extract_text import docx_process_simple_text
from crate_anon.anonymise.constants import CHARSET, TABLE_KWARGS
from crate_anon.common.fileops import find_first
from crate_anon.common.lang import rename_kwarg
from crate_anon.common.logsupport import configure_logger_for_colour

log = logging.getLogger(__name__)
metadata = MetaData()

DEFAULT_ONSPD_DIR = os.path.join(os.path.expanduser("~"), "dev", "onspd")
DEFAULT_REPORT_EVERY = 1000
DEFAULT_COMMIT_EVERY = 10000
YEAR_MONTH_FMT = "%Y%m"

CODE_LEN = 9  # many ONSPD codes have this length
NAME_LEN = 80  # seems about right; a bit more than the length of many


# =============================================================================
# Ancillary functions
# =============================================================================

def convert_date(kwargs: Dict[str, Any], field: str) -> None:
    if field not in kwargs:
        return
    value = kwargs[field]
    if value:
        kwargs[field] = datetime.datetime.strptime(value,
                                                   YEAR_MONTH_FMT)
    else:
        kwargs[field] = None


def convert_int(kwargs: Dict[str, Any], field: str) -> None:
    if field not in kwargs:
        return
    value = kwargs[field]
    if value is None or (isinstance(value, str) and not value.strip()):
        kwargs[field] = None
    else:
        kwargs[field] = int(value)


def convert_float(kwargs: Dict[str, Any], field: str) -> None:
    if field not in kwargs:
        return
    value = kwargs[field]
    if value is None or (isinstance(value, str) and not value.strip()):
        kwargs[field] = None
    else:
        kwargs[field] = float(value)


def values_from_row(row: Iterable[Cell]) -> List[Any]:
    """For openpyxl interface to XLSX files."""
    values = []
    for cell in row:
        values.append(cell.value)
    return values


def commit_and_announce(session: Session) -> None:
    log.info("COMMIT")
    session.commit()


# =============================================================================
# Extend SQLAlchemy Base class
# http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/mixins.html
# =============================================================================

class ExtendedBase(object):
    __table_args__ = TABLE_KWARGS


Base = declarative_base(metadata=metadata, cls=ExtendedBase)


# =============================================================================
# Models: all postcodes
# =============================================================================

class Postcode(Base):
    """Maps individual postcodes to... lots of things. Large table."""
    __tablename__ = 'postcode'

    pcd_nospace = Column(String(8), primary_key=True,
                         doc="Postcode (no spaces)")
    # ... not in original, but simplifies indexing
    pcd = Column(String(7), index=True, unique=True,
                 doc="Unit postcode (7 characters): 2-4 char outward code, "
                     "left-aligned; 3-char inward code, right-aligned")
    pcd2 = Column(String(8), index=True, unique=True,
                  doc="Unit postcode (8 characters): 2-4 char outward code, "
                      "left-aligned; space; 3-char inward code, right-aligned")
    pcds = Column(String(8), index=True, unique=True,
                  doc="Unit postcode (variable length): 2-4 char outward "
                      "code; space; 3-char inward code")
    dointr = Column(Date, doc="Date of introduction (original format YYYYMM)")
    doterm = Column(Date,
                    doc="Date of termination (original format YYYYMM) or NULL")
    oscty = Column(String(CODE_LEN),
                   doc="County code [FK to county_england_2010.county_code]")
    oslaua = Column(String(CODE_LEN),
                    doc="Local authority district (LUA), unitary  authority "
                        "(UA), metropolitan district (MD), London borough (LB),"
                        " council area (CA), or district council area (DCA) "
                        "[FK to lad_local_authority_district_2016.lad_code]")
    osward = Column(String(CODE_LEN),
                    doc="Electoral ward/division "
                        "[FK e.g. to electoral_ward_2016.ward_code]")
    usertype = Column(Integer, doc="Small (0) or large (1) postcode user")
    oseast1m = Column(Integer,
                      doc="National grid reference Easting, 1m resolution")
    osnrth1m = Column(Integer,
                      doc="National grid reference Northing, 1m resolution")
    osgrdind = Column(Integer,
                      doc="Grid reference positional quality indicator")
    oshlthau = Column(
        String(CODE_LEN),
        doc="Former (up to 2013) Strategic Health Authority (SHA), Local "
            "Health Board (LHB), Health Board (HB), Health Authority (HA), or "
            "Health & Social Care Board (HSCB) [FK to one of: "
            "sha_strategic_health_authority_england_2010.sha_code or "
            "sha_strategic_health_authority_england_2004.sha_code; "
            "hb_health_board_n_ireland_2003.hb_code; "
            "hb_health_board_scotland_2014.hb_code; "
            "hscb_health_social_care_board_n_ireland_2010.hscb_code; "
            "lhb_local_health_board_wales_2014.lhb_code or "
            "lhb_local_health_board_wales_2006.lhb_code]")
    hro = Column(String(CODE_LEN),
                 doc="Pan SHA [FK to "
                     "psha_pan_strategic_health_authority_aka_hro_england_2010"
                     ".psha_code]")
    ctry = Column(String(CODE_LEN),
                  doc="Country of the UK [England, Scotland, Wales, "
                      "Northern Ireland] [FK to country_2012.country_code]")
    gor = Column(String(CODE_LEN),
                 doc="Region (former GOR) [GOR = Government Office Regions] "
                     "[FK to gor_govt_office_region_england_2010.gor_code]")
    streg = Column(Integer, doc="Standard (Statistical) Region (SSR) [FK to "
                                "ssr_standard_statistical_region_england_1995."
                                "ssr_code]")
    pcon = Column(String(CODE_LEN),
                  doc="Westminster parliamentary constituency [FK to "
                      "pcon_westminster_parliamentary_constituency_2014."
                      "pcon_code]")
    eer = Column(String(CODE_LEN),
                 doc="European Electoral Region (EER) [FK to "
                     "eer_european_electoral_region_2010.eer_code]")
    teclec = Column(
        String(CODE_LEN),
        doc="Local Learning and Skills Council (LLSC) / Dept. of Children, "
            "Education, Lifelong Learning and Skills (DCELLS) / Enterprise "
            "Region (ER) [PROBABLY FK to one of: "
            "dcells_dept_children_wales_2010.dcells_code; "
            "er_enterprise_region_scotland_2010.er_code; "
            "llsc_local_learning_skills_council_england_2010.llsc_code]")
    ttwa = Column(String(CODE_LEN),
                  doc="Travel to Work Area (TTWA) [FK to "
                      "ttwa_travel_to_work_area_2011.ttwa_code]")
    pct = Column(
        String(CODE_LEN),
        doc="Primary Care Trust (PCT) / Care Trust / Care Trust Plus (CT) / "
            "Local Health Board (LHB) / Community Health Partnership (CHP) / "
            "Local Commissioning Group (LCG) / Primary Healthcare Directorate "
            "(PHD) [FK to one of: "
            "pct_primary_care_trust_organization_england_2011.pct_code; "
            "chp_community_health_partnership_scotland_2012.chp_code; "
            "lcg_local_commissioning_group_n_ireland_2010.lcg_code; "
            "lhb_local_health_board_wales_2014.lhb_code]")
    nuts = Column(String(10),
                  doc="LAU2 areas [European Union spatial regions; Local "
                      "Adminstrative Unit, level 2] / Nomenclature of Units "
                      "for Territorial Statistics (NUTS) [FK to "
                      "lau_eu_local_administrative_unit_2015.lau2_code]")
    psed = Column(String(8),
                  doc="1991 Census Enumeration District (ED) (as OGSS code) "
                      "[POSSIBLY FK to district_england_wales_1991."
                      "district_code_ogss]")
    cened = Column(String(8),
                   doc="1991 Census Enumeration District (ED) (as Census code)"
                       " [POSSIBLY FK to district_england_wales_1991."
                       "district_code_census]")
    edind = Column(Integer, doc="ED positional quality indicator (PQI)")
    oshaprev = Column(
        String(3),
        doc="Previous Strategic Health Authority (SHA) / Health Board (HB) / "
            "Health Authority (HA) / Health and Social Services Board (HSSB) "
            "[FK to one of: "
            "sha_strategic_health_authority_england_2010.sha_code or "
            "sha_strategic_health_authority_england_2004.sha_code]")
    lea = Column(String(3),
                 doc="Previous Local Education Authority (LEA) / Education "
                     "and Library Board (ELB) [PROBABLY FK to "
                     "lea_local_education_authority_2009.lea_code]")
    oldha = Column(String(3),
                   doc="Old-style health authority (prior to 2002 "
                       "England, 2003 Wales [FK to "
                       "ha_health_authority_2001.ha_code]")
    wardc91 = Column(String(6),
                     doc="1991 administrative and electoral area (as Census "
                         "code) [FK to electoral_ward_1991.ward_code_census]")
    wardo91 = Column(String(6),
                     doc="1991 administrative and electoral area (as OGSS "
                         "code) [FK to electoral_ward_1991.ward_code_ogss]")
    ward98 = Column(String(6),
                    doc="1998 administrative and electoral area [FK to "
                        "electoral_ward_1998.ward_code]")
    statsward = Column(String(6),
                       doc="2005 'statistical' ward [?FK to "
                           "electoral_ward_2005.ward_code]")
    oa01 = Column(String(10), doc="2001 Census Output Area (OA). (There are "
                                  "about 222,000, so ~300 population?)")
    casward = Column(String(6),
                     doc="Census Area Statistics (CAS) ward [PROBABLY FK to "
                         "cas_ward_2003.cas_ward_code]")
    park = Column(String(CODE_LEN), doc="National park [FK to "
                                        "park_national_park_2010.park_code]")
    lsoa01 = Column(
        String(CODE_LEN),
        doc="2001 Census Lower Layer Super Output Area (LSOA) [England & "
            "Wales, ~1,500 population] / Data Zone (DZ) [Scotland] / Super "
            "Output Area (SOA) [FK to one of: "
            "lsoa_lower_layer_super_output_area_england_wales_2004.lsoa_code; "
            "lsoa_lower_layer_super_output_area_n_ireland_2005.lsoa_code]")
    msoa01 = Column(
        String(CODE_LEN),
        doc="2001 Census Middle Layer Super Output Area (MSOA) [England & "
            "Wales, ~7,200 population] / Intermediate Zone (IZ) [Scotland] "
            "[FK to one of: "
            "msoa_middle_layer_super_output_area_england_wales_2004.msoa_code;"
            " iz_intermediate_zone_scotland_2005.iz_code]")
    ur01ind = Column(String(1),
                     doc="2001 Census urban/rural indicator [numeric in "
                         "England/Wales/Scotland; letters in N. Ireland]")
    oac01 = Column(String(3),
                   doc="2001 Census Output Area classification (OAC)"
                       "[POSSIBLY FK to output_area_classification_2011."
                       "subgroup_code]")
    oldpct = Column(
        String(5),
        doc="Old (pre-Oct 2006) Primary Care Trust (PCT) / Local Health Board "
            "(LHB) / Care Trust (CT) [FK to one of: "
            "pct_primary_care_trust_organization_england_2005.pct_code]")
    oa11 = Column(String(CODE_LEN),
                  doc="2011 Census Output Area (OA) [England, Wales, Scotland;"
                      " ~100-625 population] / Small Area (SA) [N. Ireland]")
    lsoa11 = Column(
        String(CODE_LEN),
        doc="2011 Census Lower Layer Super Output Area (LSOA) [England & "
            "Wales, ~1,500 population] / Data Zone (DZ) [Scotland] / Super "
            "Output Area (SOA) [FK to one of: "
            "lsoa_lower_layer_super_output_area_england_wales_2011.lsoa_code;"
            " dz_datazone_scotland_2011.dz_code]")
    msoa11 = Column(
        String(CODE_LEN),
        doc="2011 Census Middle Layer Super Output Area (MSOA) [England & "
            "Wales, ~7,200 population] / Intermediate Zone (IZ) [Scotland] "
            "[FK to one of: "
            "msoa_middle_layer_super_output_area_england_wales_2011.msoa_code;"
            " iz_intermediate_zone_scotland_2011.iz_code]")
    parish = Column(String(CODE_LEN),
                    doc="Parish/community [FK to "
                        "parish_lad_england_wales_2014.parish_code; "
                        "ncp_non_civil_parish_2014.ncp_code]")
    wz11 = Column(String(CODE_LEN), doc="2011 Census Workplace Zone (WZ)")
    ccg = Column(
        String(CODE_LEN),
        doc="Clinical Commissioning Group (CCG) / Local Health Board (LHB) / "
            "Community Health Partnership (CHP) / Local Commissioning Group "
            "(LCG) / Primary Healthcare Directorate (PHD) [FK to one of: "
            "ccg_clinical_commissioning_group_england_2015."
            "ccg_ons_code, lhb_local_health_board_wales_2014.lhb_code]")
    bua11 = Column(String(CODE_LEN),
                   doc="Built-up Area (BUA) [FK to "
                       "bua_built_up_area_england_wales_2013.bua_code]")
    buasd11 = Column(
        String(CODE_LEN),
        doc="Built-up Area Sub-division (BUASD) [FK to "
            "buasd_built_up_area_subdivision_england_wales_2013.buas_code]")
    ru11ind = Column(String(2), doc="2011 Census rural-urban classification")
    oac11 = Column(String(3),
                   doc="2011 Census Output Area classification (OAC) [FK to "
                       "output_area_classification_2011.subgroup_code]")
    lat = Column(Numeric(precision=9, scale=6),
                 doc="Latitude (degrees, 6dp)")
    long = Column(Numeric(precision=9, scale=6),
                  doc="Longitude (degrees, 6dp)")
    lep1 = Column(
        String(CODE_LEN),
        doc="Local Enterprise Partnership (LEP) - first instance [FK to "
            "lep_local_enterprise_partnership_england_2013.lep1_code]")
    lep2 = Column(
        String(CODE_LEN),
        doc="Local Enterprise Partnership (LEP) - second instance [FK to "
            "lep_local_enterprise_partnership_england_2013.lep1_code]")
    pfa = Column(String(CODE_LEN),
                 doc="Police Force Area (PFA) [FK to "
                     "pfa_police_force_area_2015.pfa_code]")
    imd = Column(
        Integer,
        doc="Index of Multiple Deprivation (IMD) [rank of LSOA/DZ, where 1 is "
            "the most deprived, within each country] [FK to one of: "
            "imd_index_multiple_deprivation_england_2015.imd_rank; "
            "imd_index_multiple_deprivation_n_ireland_2010.imd_rank; "
            "imd_index_multiple_deprivation_scotland_2012.imd_rank; "
            "imd_index_multiple_deprivation_wales_2014.imd_rank]")

    def __init__(self, **kwargs: Any) -> None:
        convert_date(kwargs, 'dointr')
        convert_date(kwargs, 'doterm')
        convert_int(kwargs, 'usertype')
        convert_int(kwargs, 'oseast1m')
        convert_int(kwargs, 'osnrth1m')
        convert_int(kwargs, 'osgrdind')
        convert_int(kwargs, 'streg')
        convert_int(kwargs, 'edind')
        convert_int(kwargs, 'imd')
        kwargs['pcd_nospace'] = kwargs['pcd'].replace(" ", "")
        super().__init__(**kwargs)


# =============================================================================
# Models: core lookup tables
# =============================================================================

class OAClassification(Base):
    __filename__ = "2011 Census Output Area Classification Names and Codes " \
                   "UK.xlsx"
    __tablename__ = "output_area_classification_2011"

    supergroup_code = Column(String(1))
    supergroup_desc = Column(String(35))
    group_desc = Column(String(40))
    group_code = Column(String(2))
    subgroup_desc = Column(String(60))
    subgroup_code = Column(String(3), primary_key=True)

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'Supergroup', 'supergroup_desc')
        rename_kwarg(kwargs, 'Group', 'group_desc')
        rename_kwarg(kwargs, 'Subgroup', 'subgroup_desc')
        kwargs['supergroup_code'] = kwargs['supergroup_desc'][0:1]
        kwargs['group_code'] = kwargs['group_desc'][0:2]
        kwargs['subgroup_code'] = kwargs['subgroup_desc'][0:3]
        super().__init__(**kwargs)


class BUA(Base):
    __filename__ = "BUA_names and codes EW as at 12_13.xlsx"
    __tablename__ = "bua_built_up_area_england_wales_2013"

    bua_code = Column(String(CODE_LEN), primary_key=True)
    bua_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'BUA13CD', 'bua_code')
        rename_kwarg(kwargs, 'BUA13NM', 'bua_name')
        super().__init__(**kwargs)


class BUASD(Base):
    __filename__ = "BUASD_names and codes EW as at 12_13.xlsx"
    __tablename__ = "buasd_built_up_area_subdivision_england_wales_2013"

    buasd_code = Column(String(CODE_LEN), primary_key=True)
    buasd_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'BUASD13CD', 'buasd_code')
        rename_kwarg(kwargs, 'BUASD13NM', 'buasd_name')
        super().__init__(**kwargs)


class CASWard(Base):
    __filename__ = "CAS ward names and codes UK as at 01_03.xlsx"
    __tablename__ = "cas_ward_2003"

    cas_ward_code = Column(String(CODE_LEN), primary_key=True)
    cas_ward_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'WDCAS03CD', 'cas_ward_code')
        rename_kwarg(kwargs, 'WDCAS03NM', 'cas_ward_name')
        super().__init__(**kwargs)


class CCG(Base):
    __filename__ = "CCG names and codes EN as at 07_15.xlsx"
    __tablename__ = "ccg_clinical_commissioning_group_england_2015"

    ccg_ons_code = Column(String(CODE_LEN), primary_key=True)
    ccg_ccg_code = Column(String(3))
    ccg_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'CCG15CD', 'ccg_ons_code')
        rename_kwarg(kwargs, 'CCG15CDH', 'ccg_ccg_code')
        rename_kwarg(kwargs, 'CCG15NM', 'ccg_name')
        super().__init__(**kwargs)


class CHP(Base):
    __filename__ = "CHP names and codes SC as at 04_12.xlsx"
    __tablename__ = "chp_community_health_partnership_scotland_2012"

    chp_code = Column(String(CODE_LEN), primary_key=True)
    chp_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'CHP12CD', 'chp_code')
        rename_kwarg(kwargs, 'CHP12NM', 'chp_name')
        super().__init__(**kwargs)


class Country(Base):
    __filename__ = "Country names and codes UK as at 08_12.xls"
    __tablename__ = "country_2012"

    country_code = Column(String(CODE_LEN), primary_key=True)
    country_name = Column(String(NAME_LEN))
    country_name_welsh = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'CTRY12CD', 'country_code')
        rename_kwarg(kwargs, 'CTRY12NM', 'country_name')
        rename_kwarg(kwargs, 'CTRY12NMW', 'country_name_welsh')
        super().__init__(**kwargs)


class County1991(Base):
    __filename__ = "County names and codes EW as at 21_04_91.xls"
    __tablename__ = "county_england_wales_1991"
    __headings__ = ["county_code_census", "county_code_ogss",
                    "county_code_ons", "county_name"]
    # __debug_content__ = True

    county_code_census = Column(String(2))
    county_code_ogss = Column(String(2))
    county_code_ons = Column(String(2))
    county_name = Column(String(NAME_LEN), primary_key=True)
    # ... no code type is present for all counties

    def __init__(self, **kwargs: Any) -> None:
        # The "00" codes are stored in the spreadsheet as a numeric 0 with
        # leading zero formatting.
        def process_00(field):
            value = kwargs[field]
            if value == '':
                kwargs[field] = None
            else:
                kwargs[field] = "{:0>2}".format(int(value))

        process_00('county_code_census')
        process_00('county_code_ogss')
        process_00('county_code_ons')
        super().__init__(**kwargs)


class County2010(Base):
    __filename__ = "County names and codes EN as at 12_10.xls"
    __tablename__ = "county_england_2010"

    county_code = Column(String(CODE_LEN), primary_key=True)
    county_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'CTY10CD', 'county_code')
        rename_kwarg(kwargs, 'CTY10NM', 'county_name')
        super().__init__(**kwargs)


class Datazone(Base):
    __filename__ = "Datazone (2011) names and codes SC as at 11_14.xlsx"
    __tablename__ = "dz_datazone_scotland_2011"

    dz_code = Column(String(CODE_LEN), primary_key=True)
    dz_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'DZ11CD', 'dz_code')
        rename_kwarg(kwargs, 'DZ11NM', 'dz_name')
        super().__init__(**kwargs)


class DCELLS(Base):
    __filename__ = "DCELLS names and codes WA as at 12_10.xls"
    __tablename__ = "dcells_dept_children_wales_2010"

    dcells_code = Column(String(CODE_LEN), primary_key=True)
    dcells_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'DCELL10CD', 'dcells_code')
        rename_kwarg(kwargs, 'DCELL10NM', 'dcells_name')
        super().__init__(**kwargs)
        

class District(Base):
    __filename__ = "District names and codes EW as at 21_4_91.xls"
    __headings__ = ["district_name", "district_code_census",
                    "district_code_ogss", "district_code_ons"]
    __tablename__ = "district_england_wales_1991"

    district_name = Column(String(NAME_LEN))
    district_code_census = Column(String(4))
    district_code_ogss = Column(String(4))
    district_code_ons = Column(String(4), primary_key=True)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


class EER(Base):
    __filename__ = "EER names and codes UK as at 12_10.xls"
    __tablename__ = "eer_european_electoral_region_2010"

    eer_code = Column(String(CODE_LEN), primary_key=True)
    eer_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'EER10CD', 'eer_code')
        rename_kwarg(kwargs, 'EER10NM', 'eer_name')
        super().__init__(**kwargs)


class EnterpriseRegion(Base):
    __filename__ = "Enterprise Region names and codes SC as at 12_10.xls"
    __tablename__ = "er_enterprise_region_scotland_2010"

    er_code = Column(String(CODE_LEN), primary_key=True)
    er_code_old = Column(String(3))
    er_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'ER10CD', 'er_code')
        rename_kwarg(kwargs, 'ER10CDO', 'er_code_old')
        rename_kwarg(kwargs, 'ER10NM', 'er_name')
        super().__init__(**kwargs)


class HealthAuthority(Base):
    __filename__ = "Health Authority & Health Board names and codes GB as " \
                   "at 12_01.xls"
    __tablename__ = "ha_health_authority_2001"

    ha_code = Column(String(3), primary_key=True)
    ha_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'HA01CD', 'ha_code')
        rename_kwarg(kwargs, 'HA01NM', 'ha_name')
        super().__init__(**kwargs)


class HealthBoardNI(Base):
    __filename__ = "Health Board names and codes NI as at 2003.xls"
    __tablename__ = "hb_health_board_n_ireland_2003"

    hb_code = Column(String(CODE_LEN), primary_key=True)
    hb_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'HA03CD', 'hb_code')
        rename_kwarg(kwargs, 'HA03NM', 'hb_name')
        super().__init__(**kwargs)


class HealthBoardSC(Base):
    __filename__ = "Health Board names and codes SC as at 12_14.xlsx"
    __tablename__ = "hb_health_board_scotland_2014"

    hb_code = Column(String(CODE_LEN), primary_key=True)
    hb_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'HB14CD', 'hb_code')
        rename_kwarg(kwargs, 'HB14NM', 'hb_name')
        super().__init__(**kwargs)


class HSCBNI(Base):
    __filename__ = "HSCB name and code NI as at 12_10.xls"
    __tablename__ = "hscb_health_social_care_board_n_ireland_2010"

    hscb_code = Column(String(5), primary_key=True)
    hscb_code_2 = Column(String(5))
    hscb_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'HSCB10CDO', 'hscb_code')
        rename_kwarg(kwargs, 'HSCB10CD', 'hscb_code_2')
        rename_kwarg(kwargs, 'HSCB10NM', 'hscb_name')
        super().__init__(**kwargs)


class IMDLookupEN(Base):
    __filename__ = "IMD lookup EN as at 12_15.xlsx"
    __tablename__ = "imd_index_multiple_deprivation_england_2015"

    lsoa_code = Column(String(CODE_LEN), primary_key=True)
    lsoa_name = Column(String(NAME_LEN))
    imd_rank = Column(Integer)

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LSOA11CD', 'lsoa_code')
        rename_kwarg(kwargs, 'LSOA11NM', 'lsoa_name')
        rename_kwarg(kwargs, 'IMD15', 'imd_rank')
        convert_int(kwargs, 'imd_rank')
        super().__init__(**kwargs)


class IMDLookupNI(Base):
    __filename__ = "IMD lookup NI as at 12_10.xlsx"
    __tablename__ = "imd_index_multiple_deprivation_n_ireland_2010"

    oa_code = Column(String(10), primary_key=True)
    imd_rank = Column(Integer)

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'OA01CD', 'oa_code')
        rename_kwarg(kwargs, 'IMD10', 'imd_rank')
        convert_int(kwargs, 'imd_rank')
        super().__init__(**kwargs)


class IMDLookupSC(Base):
    __filename__ = "IMD lookup SC as at 12_12.xlsx"
    __tablename__ = "imd_index_multiple_deprivation_scotland_2012"

    dz_code = Column(String(CODE_LEN), primary_key=True)
    imd_rank = Column(Integer)

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'DZ01CD', 'dz_code')
        rename_kwarg(kwargs, 'IMD12', 'imd_rank')
        convert_int(kwargs, 'imd_rank')
        super().__init__(**kwargs)


class IMDLookupWA(Base):
    __filename__ = "IMD lookup WA as at 12_14.xlsx"
    __tablename__ = "imd_index_multiple_deprivation_wales_2014"

    lsoa_code = Column(String(CODE_LEN), primary_key=True)
    lsoa_name = Column(String(NAME_LEN))
    imd_rank = Column(Integer)

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LSOA11CD', 'lsoa_code')
        rename_kwarg(kwargs, 'LSOA11NM', 'lsoa_name')
        rename_kwarg(kwargs, 'IMD14', 'imd_rank')
        convert_int(kwargs, 'imd_rank')
        super().__init__(**kwargs)


class IZ2005(Base):
    __filename__ = "IZ (2001) names and codes SC as at 11_11.xls"
    # definitely 2005, from metadata
    __tablename__ = "iz_intermediate_zone_scotland_2005"

    iz_code = Column(String(CODE_LEN), primary_key=True)
    iz_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'IZ05CD', 'iz_code')
        rename_kwarg(kwargs, 'IZ05NM', 'iz_name')
        super().__init__(**kwargs)


class IZ2011(Base):
    __filename__ = "IZ (2011) names and codes SC as at 11_14.xlsx"
    __tablename__ = "iz_intermediate_zone_scotland_2011"

    iz_code = Column(String(CODE_LEN), primary_key=True)
    iz_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'IZ11CD', 'iz_code')
        rename_kwarg(kwargs, 'IZ11NM', 'iz_name')
        super().__init__(**kwargs)


class LAU(Base):
    __filename__ = "LAU215_LAU115_NUTS315_NUTS215_NUTS115_UK_LUv2.xlsx"
    __tablename__ = "lau_eu_local_administrative_unit_2015"

    lau2_code = Column(String(10), primary_key=True)
    lau2_name = Column(String(NAME_LEN))
    lau1_code = Column(String(CODE_LEN))
    lau1_name = Column(String(NAME_LEN))
    nuts3_code = Column(String(5))
    nuts3_name = Column(String(NAME_LEN))
    nuts2_code = Column(String(4))
    nuts2_name = Column(String(NAME_LEN))
    nuts1_code = Column(String(3))
    nuts1_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LAU215CD', 'lau2_code')
        rename_kwarg(kwargs, 'LAU215NM', 'lau2_name')
        rename_kwarg(kwargs, 'LAU115CD', 'lau1_code')
        rename_kwarg(kwargs, 'LAU115NM', 'lau1_name')
        rename_kwarg(kwargs, 'NUTS315CD', 'nuts3_code')
        rename_kwarg(kwargs, 'NUTS315NM', 'nuts3_name')
        rename_kwarg(kwargs, 'NUTS215CD', 'nuts2_code')
        rename_kwarg(kwargs, 'NUTS215NM', 'nuts2_name')
        rename_kwarg(kwargs, 'NUTS115CD', 'nuts1_code')
        rename_kwarg(kwargs, 'NUTS115NM', 'nuts1_name')
        super().__init__(**kwargs)


class LAD(Base):
    __filename__ = "LA_UA names and codes UK as at 02_16.xlsx"
    __tablename__ = "lad_local_authority_district_2016"

    lad_code = Column(String(CODE_LEN), primary_key=True)
    lad_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LAD16CD', 'lad_code')
        rename_kwarg(kwargs, 'LAD16NM', 'lad_name')
        super().__init__(**kwargs)


class LCG(Base):
    __filename__ = "LCG names and codes NI as at 12_10.xls"
    __tablename__ = "lcg_local_commissioning_group_n_ireland_2010"

    lcg_code = Column(String(CODE_LEN))
    lcg_code_old = Column(String(5), primary_key=True)
    lcg_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LCG10CD', 'lcg_code')
        rename_kwarg(kwargs, 'LCG10CDO', 'lcg_code_old')
        rename_kwarg(kwargs, 'LCG10NM', 'lcg_name')
        super().__init__(**kwargs)


class LEA(Base):
    __filename__ = "LEA and ELB names and codes UK as at 04_09.xls"
    __tablename__ = "lea_local_education_authority_2009"
    # __debug_content__ = True

    lea_code = Column(String(3), primary_key=True)
    lea_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'EDUC09CD', 'lea_code')
        rename_kwarg(kwargs, 'EDUC09NM', 'lea_name')
        super().__init__(**kwargs)


class LEP(Base):
    __filename__ = "LEP names and codes EN as at 12_13.xlsx"
    __tablename__ = "lep_local_enterprise_partnership_england_2013"
    # __debug_content__ = True

    lep1_code = Column(String(CODE_LEN), primary_key=True)
    lep1_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LEP13CD1', 'lep1_code')
        rename_kwarg(kwargs, 'LEP13NM1', 'lep1_name')
        super().__init__(**kwargs)


class LHB2014(Base):
    __filename__ = "LHB names and codes WA as at 12_14.xlsx"
    __tablename__ = "lhb_local_health_board_wales_2014"
    # __debug_content__ = True

    lhb_code = Column(String(CODE_LEN), primary_key=True)
    lhb_name = Column(String(NAME_LEN))
    lhb_name_welsh = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LHB14CD', 'lhb_code')
        rename_kwarg(kwargs, 'LHB14NM', 'lhb_name')
        rename_kwarg(kwargs, 'LHB14NMW', 'lhb_name_welsh')
        super().__init__(**kwargs)


class LHB2006(Base):
    __filename__ = "Local Health Boards names and codes WA as at 06_06.xls"
    __tablename__ = "lhb_local_health_board_wales_2006"

    lhb_code = Column(String(3), primary_key=True)
    lhb_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LHB06CD', 'lhb_code')
        rename_kwarg(kwargs, 'LHB06NM', 'lhb_name')
        super().__init__(**kwargs)


class LLSC(Base):
    __filename__ = "LLSC names and codes EN as at 12_10.xls"
    __tablename__ = "llsc_local_learning_skills_council_england_2010"

    llsc_code = Column(String(CODE_LEN), primary_key=True)
    llsc_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LLSC10CD', 'llsc_code')
        rename_kwarg(kwargs, 'LLSC10NM', 'llsc_name')
        super().__init__(**kwargs)


class LSOAEW2004(Base):
    __filename__ = "LSOA (2001) names and codes EW as at 02_04.xls"
    __tablename__ = "lsoa_lower_layer_super_output_area_england_wales_2004"

    lsoa_code = Column(String(CODE_LEN), primary_key=True)
    lsoa_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LSOA04CD', 'lsoa_code')
        rename_kwarg(kwargs, 'LSOA04NM', 'lsoa_name')
        super().__init__(**kwargs)


class LSOANI2005(Base):
    __filename__ = "LSOA (2001) names and codes NI as at 02_05.xls"
    __tablename__ = "lsoa_lower_layer_super_output_area_n_ireland_2005"

    lsoa_code = Column(String(8), primary_key=True)
    lsoa_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LSOAN05CD', 'lsoa_code')
        rename_kwarg(kwargs, 'LSOAN05NM', 'lsoa_name')
        super().__init__(**kwargs)


class LSOAEW2011(Base):
    __filename__ = "LSOA (2011) names and codes EW as at 12_12.xlsx"
    __tablename__ = "lsoa_lower_layer_super_output_area_england_wales_2011"

    lsoa_code = Column(String(CODE_LEN), primary_key=True)
    lsoa_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LSOA11CD', 'lsoa_code')
        rename_kwarg(kwargs, 'LSOA11NM', 'lsoa_name')
        super().__init__(**kwargs)


class MSOAEW2004(Base):
    __filename__ = "MSOA (2001) names and codes EW as at 08_04.xls"
    __tablename__ = "msoa_middle_layer_super_output_area_england_wales_2004"

    msoa_code = Column(String(CODE_LEN), primary_key=True)
    msoa_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'MSOA04CD', 'msoa_code')
        rename_kwarg(kwargs, 'MSOA04NM', 'msoa_name')
        super().__init__(**kwargs)


class MSOAEW2011(Base):
    __filename__ = "MSOA (2011) names and codes EW as at 12_12.xlsx"
    __tablename__ = "msoa_middle_layer_super_output_area_england_wales_2011"

    msoa_code = Column(String(CODE_LEN), primary_key=True)
    msoa_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'MSOA11CD', 'msoa_code')
        rename_kwarg(kwargs, 'MSOA11NM', 'msoa_name')
        super().__init__(**kwargs)


class NationalPark(Base):
    __filename__ = "National Park names and codes GB as at 10_10.xls"
    __tablename__ = "park_national_park_2010"

    park_code = Column(String(CODE_LEN), primary_key=True)
    park_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'NPARK10CD', 'park_code')
        rename_kwarg(kwargs, 'NPARK10NM', 'park_name')
        super().__init__(**kwargs)


class PanSHA(Base):
    __filename__ = "Pan SHA names and codes EN as at 12_10.xls"
    __tablename__ = "psha_pan_strategic_health_authority_aka_hro_england_2010"

    psha_code = Column(String(CODE_LEN), primary_key=True)
    psha_code_old = Column(String(3))
    psha_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'PSHA10CD', 'psha_code')
        rename_kwarg(kwargs, 'PSHA10CDO', 'psha_code_old')
        rename_kwarg(kwargs, 'PSHA10NM', 'psha_name')
        super().__init__(**kwargs)


class Parish(Base):
    __filename__ = "Parish LAD names and codes EW as at 12_14.xlsx"
    __tablename__ = "parish_lad_england_wales_2014"

    parish_code = Column(String(CODE_LEN), primary_key=True)
    parish_name = Column(String(NAME_LEN))
    district_code = Column(String(CODE_LEN))
    district_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'PAR14CD', 'parish_code')
        rename_kwarg(kwargs, 'PAR14NM', 'parish_name')
        rename_kwarg(kwargs, 'LAD14CD', 'district_code')
        rename_kwarg(kwargs, 'LAD14NM', 'district_name')
        super().__init__(**kwargs)


class PCT2011(Base):
    __filename__ = "PCO names and codes EN as at 04_11.xls"
    __tablename__ = "pct_primary_care_trust_organization_england_2011"

    pct_code = Column(String(CODE_LEN), primary_key=True)
    pct_code_old = Column(String(3))
    pct_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'PCO11CD', 'pct_code')
        rename_kwarg(kwargs, 'PCO11CDO', 'pct_code_old')
        rename_kwarg(kwargs, 'PCO11NM', 'pct_name')
        super().__init__(**kwargs)


class PCT2005(Base):
    __filename__ = "PCO names and codes EN as at 10_05.xls"
    __tablename__ = "pct_primary_care_trust_organization_england_2005"

    pct_code = Column(String(3), primary_key=True)
    pct_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'PCO05CD', 'pct_code')
        rename_kwarg(kwargs, 'PCO05NM', 'pct_name')
        super().__init__(**kwargs)


class PFA(Base):
    __filename__ = "PFA names and codes GB as at 12_15.xlsx"
    __tablename__ = "pfa_police_force_area_2015"

    pfa_code = Column(String(CODE_LEN), primary_key=True)
    pfa_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'PFA15CD', 'pfa_code')
        rename_kwarg(kwargs, 'PFA15NM', 'pfa_name')
        super().__init__(**kwargs)


class GOR(Base):
    __filename__ = "Region (GOR) names and codes EN as at 12_10.xls"
    __tablename__ = "gor_govt_office_region_england_2010"

    gor_code = Column(String(CODE_LEN), primary_key=True)
    gor_name = Column(String(NAME_LEN))
    gor_name_welsh = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'GOR10CD', 'gor_code')
        rename_kwarg(kwargs, 'GOR10NM', 'gor_name')
        rename_kwarg(kwargs, 'GOR10NMW', 'gor_name')
        super().__init__(**kwargs)


class SHA2004(Base):
    __filename__ = "SHA names and codes EN as at 09_02_04.xls"
    __tablename__ = "sha_strategic_health_authority_england_2004"

    sha_code = Column(String(3), primary_key=True)
    sha_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'SHA04CD', 'sha_code')
        rename_kwarg(kwargs, 'SHA04NM', 'sha_name')
        super().__init__(**kwargs)


class SHA2010(Base):
    __filename__ = "SHA names and codes EN as at 12_10.xls"
    __tablename__ = "sha_strategic_health_authority_england_2010"

    sha_code = Column(String(CODE_LEN), primary_key=True)
    sha_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'SHA10CD', 'sha_code')
        rename_kwarg(kwargs, 'SHA10NM', 'sha_name')
        super().__init__(**kwargs)


class SSR(Base):
    __filename__ = "SSR names and codes EN as at 12_05.xls"
    __tablename__ = "ssr_standard_statistical_region_england_1995"

    ssr_code = Column(Integer, primary_key=True)
    ssr_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'SSR95CD', 'ssr_code')
        rename_kwarg(kwargs, 'SSR95NM', 'ssr_name')
        convert_int(kwargs, 'ssr_code')
        super().__init__(**kwargs)


class Ward1991(Base):
    __filename__ = "Ward names and codes UK as at 21_04_91.xls"
    __tablename__ = "electoral_ward_1991"

    ward_code_ons = Column(String(6), primary_key=True)
    ward_code_census = Column(String(6))
    ward_code_ogss = Column(String(6))
    ward_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'WD91CD', 'ward_code_ons')
        rename_kwarg(kwargs, 'WD91CDC', 'ward_code_census')
        rename_kwarg(kwargs, 'WD91CDO', 'ward_code_ogss')
        rename_kwarg(kwargs, 'WD91NM', 'ward_name')
        super().__init__(**kwargs)


class Ward1998(Base):
    __filename__ = "Ward names and codes UK as at 12_98.xls"
    __tablename__ = "electoral_ward_1998"

    ward_code = Column(String(6), primary_key=True)
    ward_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'WD98CD', 'ward_code')
        rename_kwarg(kwargs, 'WD98NM', 'ward_name')
        super().__init__(**kwargs)


class Ward2005(Base):
    __filename__ = "Statistical ward names and codes UK as at 2005.xls"
    __tablename__ = "electoral_ward_2005"

    ward_code = Column(String(6), primary_key=True)
    ward_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'WDSTL05CD', 'ward_code')
        rename_kwarg(kwargs, 'WDSTL05NM', 'ward_name')
        super().__init__(**kwargs)


class Ward2016(Base):
    __filename__ = "Ward names and codes UK as at 05_16.xlsx"
    __tablename__ = "electoral_ward_2016"

    ward_code = Column(String(CODE_LEN), primary_key=True)
    ward_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'WD16CD', 'ward_code')
        rename_kwarg(kwargs, 'WD16NM', 'ward_name')
        super().__init__(**kwargs)


class TTWA(Base):
    __filename__ = "TTWA names and codes UK as at 12_11 v5.xlsx"
    __tablename__ = "ttwa_travel_to_work_area_2011"

    ttwa_code = Column(String(CODE_LEN), primary_key=True)
    ttwa_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'TTWA11CD', 'ttwa_code')
        rename_kwarg(kwargs, 'TTWA11NM', 'ttwa_name')
        super().__init__(**kwargs)


class NCP(Base):
    __filename__ = "Unparished areas names and codes EN as at 12_14.xlsx"
    __tablename__ = "ncp_non_civil_parish_2014"

    ncp_code = Column(String(CODE_LEN), primary_key=True)
    ncp_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'NCP14CD', 'ncp_code')
        rename_kwarg(kwargs, 'NCP14NM', 'ncp_name')
        super().__init__(**kwargs)


class WestminsterConstituency(Base):
    __filename__ = "Westminster Parliamentary Constituency names and codes " \
                   "UK as at 12_14.xlsx"
    __tablename__ = "pcon_westminster_parliamentary_constituency_2014"

    pcon_code = Column(String(CODE_LEN), primary_key=True)
    pcon_name = Column(String(NAME_LEN))

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'PCON14CD', 'pcon_code')
        rename_kwarg(kwargs, 'PCON14NM', 'pcon_name')
        super().__init__(**kwargs)


# =============================================================================
# Models: centroids
# =============================================================================
# http://webarchive.nationalarchives.gov.uk/20160105160709/http://www.ons.gov.uk/ons/guide-method/geography/products/census/spatial/centroids/index.html
#
# Looking at lower_layer_super_output_areas_(e+w)_2011_population_weighted_centroids_v2.zip : # noqa
# - LSOA_2011_EW_PWC.shp -- probably a Shape file;
#   ... yes
#   ... https://en.wikipedia.org/wiki/Shapefile
#   ... ... describes most of the other files
# - LSOA_2011_EW_PWC_COORD_V2.CSV  -- LSOA to centroid coordinates

class PopWeightedCentroidsLsoa2011(Base):
    __filename__ = "LSOA_2011_EW_PWC_COORD_V2.CSV"
    __tablename__ = "pop_weighted_centroids_lsoa_2011"
    # __debug_content__ = True

    lsoa_code = Column(String(CODE_LEN), primary_key=True)
    lsoa_name = Column(String(NAME_LEN))
    bng_north = Column(Integer, doc="British National Grid, North (m)")
    bng_east = Column(Integer, doc="British National Grid, East (m)")
    # https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid#All-numeric_grid_references  # noqa
    latitude = Column(Numeric(precision=13, scale=10),
                      doc="Latitude (degrees, 10dp)")
    longitude = Column(Numeric(precision=13, scale=10),
                       doc="Longitude (degrees, 10dp)")
    # ... there are some with 10dp, e.g. 0.0000570995
    # ... (precision - scale) = number of digits before '.'
    # ... which can't be more than 3 for any latitude/longitude

    def __init__(self, **kwargs: Any) -> None:
        rename_kwarg(kwargs, 'LSOA11CD', 'lsoa_code')
        rename_kwarg(kwargs, 'LSOA11NM', 'lsoa_name')
        rename_kwarg(kwargs, 'BNGNORTH', 'bng_north')
        rename_kwarg(kwargs, 'BNGEAST', 'bng_east')
        rename_kwarg(kwargs, 'LONGITUDE', 'longitude')
        rename_kwarg(kwargs, 'LATITUDE', 'latitude')
        # MySQL doesn't care if you pass a string to a numeric field, but
        # SQL server does. So:
        convert_int(kwargs, 'bng_north')
        convert_int(kwargs, 'bng_east')
        convert_float(kwargs, 'longitude')
        convert_float(kwargs, 'latitude')
        super().__init__(**kwargs)
        if not self.lsoa_code:
            raise ValueError("Can't have a blank lsoa_code")


# =============================================================================
# Files -> table data
# =============================================================================

def populate_postcode_table(filename: str,
                            session: Session,
                            args: Any,
                            commit: bool = True) -> None:
    tablename = Postcode.__tablename__
    table = Postcode.__table__
    if not args.replace:
        engine = session.bind
        if engine.has_table(tablename):
            log.info("Table {} exists; skipping".format(tablename))
            return
    log.info("Dropping/recreating table: {}".format(tablename))
    table.drop(checkfirst=True)
    table.create(checkfirst=True)
    log.info("Using ONSPD data file: {}".format(filename))
    n = 0
    n_inserted = 0
    extra_fields = []
    db_fields = sorted(k for k in Postcode.__table__.columns.keys()
                       if k != 'pcd_nospace')
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            n += 1
            if n % args.reportevery == 0:
                log.info("Processing row {}: {} ({} inserted)".format(
                    n, row['pcds'], n_inserted))
                # log.debug(row)
            if n == 1:
                file_fields = sorted(row.keys())
                missing_fields = sorted(set(db_fields) - set(file_fields))
                extra_fields = sorted(set(file_fields) - set(db_fields))
                if missing_fields:
                    log.warning("Fields in database but not file: {}".format
                                (missing_fields))
                if extra_fields:
                    log.warning("Fields in file but not database : {}".format(
                        extra_fields))
            for k in extra_fields:
                del row[k]
            if args.startswith:
                ok = False
                for s in args.startswith:
                    if row['pcd'].startswith(s):
                        ok = True
                        break
                if not ok:
                    continue
            obj = Postcode(**row)
            session.add(obj)
            n_inserted += 1
            if commit and n % args.commitevery == 0:
                commit_and_announce(session)
    if commit:
        commit_and_announce(session)


# BASETYPE = TypeVar('BASETYPE', bound=Base)
# http://mypy.readthedocs.io/en/latest/kinds_of_types.html
# https://docs.python.org/3/library/typing.html


def populate_generic_lookup_table(sa_class: Any,  # Type[Base], Type[BASETYPE] fail on methods  # noqa
                                  datadir: str,
                                  session: Session,
                                  args: Any,
                                  commit: bool = True) -> None:
    """
    The .TXT files look at first glance like tab-separated values files,
    but in some cases have inconsistent numbers of tabs (e.g. "2011 Census
    Output Area Classification Names and Codes UK.txt"). So we'll use the
    .XLSX files.

    If the headings parameter is passed, those headings are used. Otherwise,
    the first row is used for headings.
    """
    tablename = sa_class.__tablename__
    filename = find_first(sa_class.__filename__, datadir)
    headings = getattr(sa_class, '__headings__', [])
    debug = getattr(sa_class, '__debug_content__', False)
    n = 0

    if not args.replace:
        engine = session.bind
        if engine.has_table(tablename):
            log.info("Table {} exists; skipping".format(tablename))
            return

    log.info("Dropping/recreating table: {}".format(tablename))
    sa_class.__table__.drop(checkfirst=True)
    sa_class.__table__.create(checkfirst=True)

    log.info('Processing file "{}" -> table "{}"'.format(filename, tablename))
    ext = os.path.splitext(filename)[1].lower()
    type_xlsx = ext in ['.xlsx']
    type_csv = ext in ['.csv']
    file = None  # type: TextIO

    def dict_from_rows(row_iterator: Iterable[List]) \
            -> Generator[Dict, None, None]:
        local_headings = headings
        first_row = True
        for row in row_iterator:
            values = values_from_row(row)
            if first_row and not local_headings:
                local_headings = values
            else:
                yield dict(zip(local_headings, values))
            first_row = False

    if type_xlsx:
        workbook = openpyxl.load_workbook(filename)  # read_only=True
        # openpyxl BUG: with read_only=True, cells can have None as their value
        # when they're fine if opened in non-read-only mode.
        # May be related to this:
        # https://bitbucket.org/openpyxl/openpyxl/issues/601/read_only-cell-row-column-attributes-are  # noqa
        sheet = workbook.active
        dict_iterator = dict_from_rows(sheet.iter_rows())
    elif type_csv:
        file = open(filename, 'r')
        csv_reader = csv.DictReader(file)
        dict_iterator = csv_reader
    else:
        workbook = xlrd.open_workbook(filename)
        sheet = workbook.sheet_by_index(0)
        dict_iterator = dict_from_rows(sheet.get_rows())
    for datadict in dict_iterator:
        n += 1
        if debug:
            log.critical("{}: {}".format(n, datadict))
        # filter out blanks:
        datadict = {k: v for k, v in datadict.items() if k}
        obj = sa_class(**datadict)
        session.add(obj)
        if commit and n % args.commitevery == 0:
            commit_and_announce(session)
    if commit:
        commit_and_announce(session)
    log.info("... inserted {} rows".format(n))

    if file:
        file.close()


# =============================================================================
# Docs
# =============================================================================

def show_docs() -> None:
    columns = sorted(Postcode.__table__.columns.keys())
    pt = prettytable.PrettyTable(
        ["postcode field", "Description"],
        # header=False,
        border=True,
        hrules=prettytable.ALL,
        vrules=prettytable.NONE,
    )
    pt.align = 'l'
    pt.valign = 't'
    pt.max_width = 80
    for col in columns:
        doc = getattr(Postcode, col).doc
        doc = docx_process_simple_text(doc, width=70)
        ptrow = [col, doc]
        pt.add_row(ptrow)
    print(pt.get_string())


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=
        r"""
-   This program reads data from the UK Office of National Statistics Postcode
    Database (ONSPD) and inserts it into a database.

-   You will need to download the ONSPD from
        https://geoportal.statistics.gov.uk/geoportal/catalog/content/filelist.page
    e.g. ONSPD_MAY_2016_csv.zip (79 Mb), and unzip it (>1.4 Gb) to a directory.
    Tell this program which directory you used.

-   Specify your database as an SQLAlchemy connection URL: see
        http://docs.sqlalchemy.org/en/latest/core/engines.html
    The general format is:
        dialect[+driver]://username:password@host[:port]/database[?key=value...]

-   If you get an error like:
        UnicodeEncodeError: 'latin-1' codec can't encode character '\u2019' in
        position 33: ordinal not in range(256)
    then try appending "?charset=utf8" to the connection URL.

-   ONS POSTCODE DATABASE LICENSE.
    Output using this program must add the following attribution statements:

    Contains OS data © Crown copyright and database right [year]
    Contains Royal Mail data © Royal Mail copyright and database right [year]
    Contains National Statistics data © Crown copyright and database right [year]

    See http://www.ons.gov.uk/methodology/geography/licences
    """)  # noqa
    parser.add_argument(
        "--dir", default=DEFAULT_ONSPD_DIR,
        help="Root directory of unzipped ONSPD download (default: {})".format(
            DEFAULT_ONSPD_DIR))
    parser.add_argument(
        "--url", help="SQLAlchemy database URL")
    parser.add_argument(
        "--echo", action="store_true", help="Echo SQL")
    parser.add_argument(
        "--reportevery", type=int, default=DEFAULT_REPORT_EVERY,
        help="Report every n rows (default: {})".format(DEFAULT_REPORT_EVERY))
    parser.add_argument(
        "--commitevery", type=int, default=DEFAULT_COMMIT_EVERY,
        help=(
            "Commit every n rows (default: {}). If you make this too large "
            "(relative e.g. to your MySQL max_allowed_packet setting, you may"
            " get crashes with errors like 'MySQL has gone away'.".format(
                DEFAULT_COMMIT_EVERY)))
    parser.add_argument(
        "--startswith", nargs="+",
        help="Restrict to postcodes that start with one of these strings")
    parser.add_argument(
        "--replace", action="store_true",
        help="Replace tables even if they exist (default: skip existing "
             "tables)")
    parser.add_argument(
        "--skiplookup", action="store_true",
        help="Skip generation of code lookup tables")
    parser.add_argument(
        "--specific_lookup_tables", nargs="*",
        help="Within the lookup tables, process only specific named tables")
    parser.add_argument(
        "--list_lookup_tables", action="store_true",
        help="List all possible lookup tables, then stop")
    parser.add_argument(
        "--skippostcodes", action="store_true",
        help="Skip generation of main (large) postcode table")
    parser.add_argument(
        "--docsonly", action="store_true",
        help="Show help for postcode table then stop")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose")
    args = parser.parse_args()
    rootlogger = logging.getLogger()
    configure_logger_for_colour(
        rootlogger, level=logging.DEBUG if args.verbose else logging.INFO)
    log.debug("args = {}".format(repr(args)))

    if args.docsonly:
        show_docs()
        sys.exit(0)

    classlist = [
        # Core lookup tables:
        # In alphabetical order of filename:
        OAClassification,
        BUA,
        BUASD,
        CASWard,
        CCG,
        CHP,
        Country,
        County2010,
        County1991,
        Datazone,
        DCELLS,
        District,
        EER,
        EnterpriseRegion,
        HealthAuthority,
        HealthBoardNI,
        HealthBoardSC,
        HSCBNI,
        IMDLookupEN,
        IMDLookupNI,
        IMDLookupSC,
        IMDLookupWA,
        IZ2005,
        IZ2011,
        LAU,
        LAD,
        LCG,
        LEA,
        LEP,
        LHB2006,
        LLSC,
        LHB2014,
        LSOAEW2004,
        LSOANI2005,
        LSOAEW2011,
        MSOAEW2004,
        MSOAEW2011,
        NationalPark,
        PanSHA,
        Parish,
        PCT2011,
        PCT2005,
        PFA,
        GOR,
        SHA2004,
        SHA2010,
        SSR,
        Ward2005,
        TTWA,
        NCP,
        Ward2016,
        Ward1998,
        Ward1991,
        WestminsterConstituency,
        # Centroids:
        PopWeightedCentroidsLsoa2011,
    ]

    if args.list_lookup_tables:
        tables_files = []
        for sa_class in classlist:
            tables_files.append((sa_class.__tablename__,
                                 sa_class.__filename__))
        tables_files.sort(key=lambda x: x[0])
        for table, file in tables_files:
            print("Table {} from file {}".format(table, repr(file)))
        return

    if not args.url:
        print("Must specify URL")
        return

    engine = create_engine(args.url, echo=args.echo, encoding=CHARSET)
    metadata.bind = engine
    session = sessionmaker(bind=engine)()

    log.info("Using directory: {}".format(args.dir))
    # lookupdir = os.path.join(args.dir, "Documents")
    lookupdir = args.dir
    # datadir = os.path.join(args.dir, "Data")
    datadir = args.dir

    if not args.skiplookup:
        for sa_class in classlist:
            if (args.specific_lookup_tables and
                    sa_class.__tablename__ not in args.specific_lookup_tables):
                continue
            if (sa_class.__tablename__ ==
                    "ccg_clinical_commissioning_group_england_2015"):
                log.warning("Ignore warning 'Discarded range with reserved "
                            "name' below; it works regardless")
            populate_generic_lookup_table(sa_class, lookupdir, session, args)
    if not args.skippostcodes:
        populate_postcode_table(find_first("ONSPD_*.csv", datadir),
                                session, args)


if __name__ == '__main__':
    main()
