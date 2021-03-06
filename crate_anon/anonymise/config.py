#!/usr/bin/env python
# crate_anon/anonymise/config.py

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

Config class for CRATE anonymiser.

Thoughts on configuration method

-   First version used a Config() class, which initializes with blank values.
    The anonymise_cli.py file creates a config singleton and passes it around.
    Then when its set() method is called, it reads a config file and
    instantiates its settings.
    An option exists to print a draft config without ever reading one from
    disk.

    Advantage: easy to start the program without a valid config file (e.g. to
        print one).
    Disadvantage: modules can't be sure that a config is properly instantiated
        before they are loaded, so you can't easily define a class according to
        config settings (you'd have to have a class factory, which gets ugly).

-   The Django method is to have a configuration file (e.g. settings.py, which
    can import from other things) that is read by Django and then becomes
    importable by anything at startup as "django.conf.settings". (I've added
    local settings via an environment variable.) The way Django knows where
    to look is via this in manage.py:

        os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                              "crate_anon.crateweb.config.settings")

    Advantage: setting the config file via an environment variable (read when
        the config file loads) allows guaranteed config existence as other
        modules start.
    Further advantage: config filenames not on command line, therefore not
        visible to ps.
    Disadvantage: how do you override with a command-line (argparse) setting?
        ... though: who cares?
    To print a config using that file: raise an exception on nonexistent
        config, and catch it with a special entry point script.

-   See also
    http://stackoverflow.com/questions/7443366/argument-passing-strategy-environment-variables-vs-command-line  # noqa
"""

# =============================================================================
# Imports
# =============================================================================

import codecs
import fnmatch
import logging
import os
import sys
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import regex
from cardinal_pythonlib.rnc_db import (
    ensure_valid_field_name,
    ensure_valid_table_name,
)
from cardinal_pythonlib.rnc_log import remove_all_logger_handlers
from sqlalchemy import BigInteger, create_engine, String
from sqlalchemy.dialects.mssql.base import dialect as mssql_dialect
from sqlalchemy.dialects.mysql.base import dialect as mysql_dialect
from sqlalchemy.engine import Engine
from sqlalchemy.sql.sqltypes import TypeEngine

from crate_anon.anonymise.constants import (
    CONFIG_ENV_VAR,
    DEFAULT_CHUNKSIZE,
    DEFAULT_REPORT_EVERY,
    DEFAULT_MAX_ROWS_BEFORE_COMMIT,
    DEFAULT_MAX_BYTES_BEFORE_COMMIT,
    SEP,
)
from crate_anon.anonymise.dd import DataDictionary
from crate_anon.anonymise.scrub import (
    NonspecificScrubber,
    WordList,
)
from crate_anon.common.extendedconfigparser import ExtendedConfigParser
from crate_anon.common.formatting import sizeof_fmt
from crate_anon.common.hash import GenericHasher, make_hasher
from crate_anon.common.sql import TransactionSizeLimiter
from crate_anon.common.sqla import (
    hack_in_mssql_xml_type,
    is_sqlatype_integer,
    monkeypatch_TableClause,
)

if TYPE_CHECKING:
    from crate_anon.anonymise.dbholder import DatabaseHolder

log = logging.getLogger(__name__)

# The Config class is loaded very early, via the nasty singleton.
# This is therefore the appropriate moment to make any changes to SQLAlchemy.
monkeypatch_TableClause()
hack_in_mssql_xml_type()  # support XML type under SQL Server


# =============================================================================
# Config/databases
# =============================================================================

class DatabaseSafeConfig(object):
    """Class representing non-sensitive configuration information about a
    source database."""

    def __init__(self, parser: ExtendedConfigParser, section: str) -> None:
        """Read from a configparser section."""
        if not parser.has_section(section):
            raise ValueError("config missing section: " + section)

        def opt_str(option: str) -> str:
            return parser.get(section, option, fallback=None)

        def opt_multiline(option: str, as_words: bool = True) -> List[str]:
            return parser.get_str_list(section, option, as_words=as_words)

        def opt_bool(option: str, default: bool) -> bool:
            return parser.getboolean(section, option, fallback=default)

        def opt_int(option: str, default: Optional[int]) -> Optional[int]:
            return parser.get_int_default_if_failure(section, option, default)

        def opt_multiline_csv_pairs(option: str) -> Dict[str, str]:
            d = {}
            lines = opt_multiline(option, as_words=False)
            for line in lines:
                pair = [item.strip() for item in line.split(",")]
                if len(pair) != 2:
                    raise ValueError("For option {}: specify items as a list "
                                     "of comma-separated pairs".format(option))
                d[pair[0]] = pair[1]
            return d

        self.ddgen_omit_by_default = opt_bool(
            'ddgen_omit_by_default', True)
        self.ddgen_omit_fields = opt_multiline('ddgen_omit_fields')
        self.ddgen_include_fields = opt_multiline('ddgen_include_fields')

        self.ddgen_allow_no_patient_info = opt_bool(
            'ddgen_allow_no_patient_info', False)
        self.ddgen_per_table_pid_field = opt_str('ddgen_per_table_pid_field')
        self.ddgen_add_per_table_pids_to_scrubber = opt_bool(
            'ddgen_add_per_table_pids_to_scrubber', False)
        self.ddgen_master_pid_fieldname = opt_str('ddgen_master_pid_fieldname')
        self.ddgen_table_blacklist = opt_multiline('ddgen_table_blacklist')
        self.ddgen_table_whitelist = opt_multiline('ddgen_table_whitelist')
        self.ddgen_table_require_field_absolute = opt_multiline(
            'ddgen_table_require_field_absolute')
        self.ddgen_table_require_field_conditional = opt_multiline_csv_pairs(
            'ddgen_table_require_field_conditional')
        self.ddgen_field_blacklist = opt_multiline('ddgen_field_blacklist')
        self.ddgen_field_whitelist = opt_multiline('ddgen_field_whitelist')
        self.ddgen_pk_fields = opt_multiline('ddgen_pk_fields')

        self.ddgen_constant_content = opt_bool(
            'ddgen_constant_content', False)
        self.ddgen_constant_content_tables = opt_str(
            'ddgen_constant_content_tables')
        self.ddgen_nonconstant_content_tables = opt_str(
            'ddgen_nonconstant_content_tables')
        self.ddgen_addition_only = opt_bool('ddgen_addition_only', False)
        self.ddgen_addition_only_tables = opt_str('ddgen_addition_only_tables')
        self.ddgen_deletion_possible_tables = opt_str(
            'ddgen_deletion_possible_tables')

        self.ddgen_pid_defining_fieldnames = opt_multiline(
            'ddgen_pid_defining_fieldnames')
        self.ddgen_scrubsrc_patient_fields = opt_multiline(
            'ddgen_scrubsrc_patient_fields')
        self.ddgen_scrubsrc_thirdparty_fields = opt_multiline(
            'ddgen_scrubsrc_thirdparty_fields')
        self.ddgen_scrubsrc_thirdparty_xref_pid_fields = opt_multiline(
            'ddgen_scrubsrc_thirdparty_xref_pid_fields')
        self.ddgen_required_scrubsrc_fields = opt_multiline(
            'ddgen_required_scrubsrc_fields')
        self.ddgen_scrubmethod_code_fields = opt_multiline(
            'ddgen_scrubmethod_code_fields')
        self.ddgen_scrubmethod_date_fields = opt_multiline(
            'ddgen_scrubmethod_date_fields')
        self.ddgen_scrubmethod_number_fields = opt_multiline(
            'ddgen_scrubmethod_number_fields')
        self.ddgen_scrubmethod_phrase_fields = opt_multiline(
            'ddgen_scrubmethod_phrase_fields')
        self.ddgen_safe_fields_exempt_from_scrubbing = opt_multiline(
            'ddgen_safe_fields_exempt_from_scrubbing')
        self.ddgen_min_length_for_scrubbing = opt_int(
            'ddgen_min_length_for_scrubbing', 0)

        self.ddgen_truncate_date_fields = opt_multiline(
            'ddgen_truncate_date_fields')
        self.ddgen_filename_to_text_fields = opt_multiline(
            'ddgen_filename_to_text_fields')

        self.bin2text_dict = opt_multiline_csv_pairs(
            'ddgen_binary_to_text_field_pairs')
        self.ddgen_skip_row_if_extract_text_fails_fields = opt_multiline(
            'ddgen_skip_row_if_extract_text_fails_fields')
        self.ddgen_rename_tables_remove_suffixes = opt_multiline(
            'ddgen_rename_tables_remove_suffixes', as_words=True)

        self.ddgen_index_fields = opt_multiline('ddgen_index_fields')
        self.ddgen_allow_fulltext_indexing = opt_bool(
            'ddgen_allow_fulltext_indexing', True)

        self.ddgen_force_lower_case = opt_bool('ddgen_force_lower_case', True)
        self.ddgen_convert_odd_chars_to_underscore = opt_bool(
            'ddgen_convert_odd_chars_to_underscore', True)

        self.debug_row_limit = opt_int('debug_row_limit', 0)
        self.debug_limited_tables = opt_multiline('debug_limited_tables')

        self.ddgen_patient_opt_out_fields = opt_multiline(
            'ddgen_patient_opt_out_fields')

        self.ddgen_extra_hash_fields = opt_multiline_csv_pairs(
            'ddgen_extra_hash_fields')
        # ... key: fieldspec
        # ... value: hash_config_section_name

        self.PidType = BigInteger
        self.MpidType = BigInteger

    def is_table_blacklisted(self, table: str) -> bool:
        for white in self.ddgen_table_whitelist:
            r = regex.compile(fnmatch.translate(white), regex.IGNORECASE)
            if r.match(table):
                return False
        for black in self.ddgen_table_blacklist:
            r = regex.compile(fnmatch.translate(black), regex.IGNORECASE)
            if r.match(table):
                return True
        return False

    def is_field_blacklisted(self, field: str) -> bool:
        for white in self.ddgen_field_whitelist:
            r = regex.compile(fnmatch.translate(white), regex.IGNORECASE)
            if r.match(field):
                return True
        for black in self.ddgen_field_blacklist:
            r = regex.compile(fnmatch.translate(black), regex.IGNORECASE)
            if r.match(field):
                return True
        return False

    def does_table_fail_minimum_fields(self, colnames: List[str]) -> bool:
        for abs_req in self.ddgen_table_require_field_absolute:
            if abs_req not in colnames:
                return True
        for if_field, then_field in self.ddgen_table_require_field_conditional.items():  # noqa
            if if_field in colnames and then_field not in colnames:
                return True
        return False


# =============================================================================
# ExtraHashconfig
# =============================================================================

def get_extra_hasher(parser: ExtendedConfigParser,
                     section: str) -> GenericHasher:
    """Read from a configparser section."""
    if not parser.has_section(section):
        raise ValueError("config missing section: " + section)

    def opt_str(option: str) -> str:
        return parser.get(section, option, fallback=None)

    hash_method = opt_str("hash_method")
    secret_key = opt_str("secret_key")
    return make_hasher(hash_method, secret_key)


# =============================================================================
# Config
# =============================================================================

class Config(object):
    """Class representing the main configuration."""

    def __init__(self, open_databases: bool = True) -> None:
        """
        Read config from file
        """
        # Get filename
        try:
            self.config_filename = os.environ[CONFIG_ENV_VAR]
            assert self.config_filename
        except (KeyError, AssertionError):
            print(
                "You must set the {} environment variable to point to a CRATE "
                "anonymisation config file, or specify it on the command "
                "line. Run crate_print_demo_anon_config "
                "to see a specimen config.".format(CONFIG_ENV_VAR))
            sys.exit(1)

        # Read config from file.
        parser = ExtendedConfigParser()
        log.info("Reading config file: {}".format(self.config_filename))
        parser.read_file(codecs.open(self.config_filename, "r", "utf8"))
        section = "main"

        def opt_str(option: str) -> str:
            return parser.get(section, option, fallback=None)

        def opt_multiline(option: str) -> List[str]:
            return parser.get_str_list(section, option)

        def opt_multiline_int(option: str,
                              minimum: int = None,
                              maximum: int = None) -> List[int]:
            return parser.get_int_list(section, option, minimum=minimum,
                                       maximum=maximum, suppress_errors=False)

        def opt_bool(option: str, default: bool) -> bool:
            return parser.getboolean(section, option, fallback=default)

        def opt_int(option: str, default: Optional[int]) -> Optional[int]:
            return parser.get_int_default_if_failure(section, option, default)

        def opt_pyvalue_list(option: str, default: Any = None) -> Any:
            return parser.get_pyvalue_list(section, option, default=default)

        def get_database(section_: str,
                         name: str,
                         srccfg_: DatabaseSafeConfig = None,
                         with_session: bool = False,
                         with_conn: bool = True,
                         reflect: bool = True) -> "DatabaseHolder":
            return parser.get_database(section_,
                                       dbname=name,
                                       srccfg=srccfg_,
                                       with_session=with_session,
                                       with_conn=with_conn,
                                       reflect=reflect)

        def get_sqlatype(sqlatype: str, default: TypeEngine) -> TypeEngine:
            if not sqlatype:
                return default
            if sqlatype == "BigInteger":
                return BigInteger
            r = regex.compile(r"String\((\d+)\)")  # e.g. String(50)
            try:
                m = r.match(sqlatype)
                length = int(m.group(1))
                return String(length)
            except (AttributeError, ValueError):
                raise ValueError("Bad SQLAlchemy type specification for "
                                 "PID/MPID columns: {}".format(repr(sqlatype)))

        # ---------------------------------------------------------------------
        # Data dictionary
        # ---------------------------------------------------------------------

        self.data_dictionary_filename = opt_str('data_dictionary_filename')

        # ---------------------------------------------------------------------
        # Critical field types
        # ---------------------------------------------------------------------

        self.PidType = get_sqlatype(opt_str('sqlatype_pid'), BigInteger)
        self.pidtype_is_integer = is_sqlatype_integer(self.PidType)
        self.MpidType = get_sqlatype(opt_str('sqlatype_mpid'), BigInteger)
        self.mpidtype_is_integer = is_sqlatype_integer(self.MpidType)

        # ---------------------------------------------------------------------
        # Encryption phrases/passwords
        # ---------------------------------------------------------------------

        self.hash_method = opt_str('hash_method')
        self.per_table_patient_id_encryption_phrase = opt_str(
            'per_table_patient_id_encryption_phrase')
        self.master_patient_id_encryption_phrase = opt_str(
            'master_patient_id_encryption_phrase')
        self.change_detection_encryption_phrase = opt_str(
            'change_detection_encryption_phrase')
        _extra_hash_config_section_names = opt_multiline(
            "extra_hash_config_sections")

        self.extra_hashers = {}  # type: Dict[str, GenericHasher]
        for hasher_name in _extra_hash_config_section_names:
            self.extra_hashers[hasher_name] = get_extra_hasher(parser,
                                                               hasher_name)
        # Load encryption keys and create hashers
        dummyhash = make_hasher(self.hash_method, "dummysalt")
        encrypted_length = dummyhash.output_length()

        self.SqlTypeEncryptedPid = String(encrypted_length)
        self.sqltype_encrypted_pid_as_sql = str(self.SqlTypeEncryptedPid)
        # ... VARCHAR(32) for MD5; VARCHAR(64) for SHA-256; VARCHAR(128) for
        # SHA-512.

        if not self.per_table_patient_id_encryption_phrase:
            raise ValueError("Missing per_table_patient_id_encryption_phrase")
        self.primary_pid_hasher = make_hasher(
            self.hash_method, self.per_table_patient_id_encryption_phrase)

        if not self.master_patient_id_encryption_phrase:
            raise ValueError("Missing master_patient_id_encryption_phrase")
        self.master_pid_hasher = make_hasher(
            self.hash_method, self.master_patient_id_encryption_phrase)

        if not self.change_detection_encryption_phrase:
            raise ValueError("Missing change_detection_encryption_phrase")
        self.change_detection_hasher = make_hasher(
            self.hash_method, self.change_detection_encryption_phrase)

        # ---------------------------------------------------------------------
        # Text extraction
        # ---------------------------------------------------------------------

        self.extract_text_extensions_case_sensitive = opt_bool(
            'extract_text_extensions_case_sensitive', False)
        self.extract_text_extensions_permitted = opt_multiline(
            'extract_text_extensions_permitted')
        self.extract_text_extensions_prohibited = opt_multiline(
            'extract_text_extensions_prohibited')
        self.extract_text_plain = opt_bool('extract_text_plain', False)
        self.extract_text_width = opt_int('extract_text_width', 80)

        # ---------------------------------------------------------------------
        # Anonymisation
        # ---------------------------------------------------------------------

        self.replace_patient_info_with = opt_str('replace_patient_info_with')
        self.replace_third_party_info_with = opt_str(
            'replace_third_party_info_with')
        self.replace_nonspecific_info_with = opt_str(
            'replace_nonspecific_info_with')
        self.thirdparty_xref_max_depth = opt_int('thirdparty_xref_max_depth',
                                                 1)
        self.string_max_regex_errors = opt_int('string_max_regex_errors', 0)
        self.min_string_length_for_errors = opt_int(
            'min_string_length_for_errors', 1)
        self.min_string_length_to_scrub_with = opt_int(
            'min_string_length_to_scrub_with', 2)
        self.scrub_all_uk_postcodes = opt_bool('scrub_all_uk_postcodes', False)
        self.anonymise_codes_at_word_boundaries_only = opt_bool(
            'anonymise_codes_at_word_boundaries_only', True)
        self.anonymise_dates_at_word_boundaries_only = opt_bool(
            'anonymise_dates_at_word_boundaries_only', True)
        self.anonymise_numbers_at_word_boundaries_only = opt_bool(
            'anonymise_numbers_at_word_boundaries_only', False)
        self.anonymise_numbers_at_numeric_boundaries_only = opt_bool(
            'anonymise_numbers_at_numeric_boundaries_only', True)
        self.anonymise_strings_at_word_boundaries_only = opt_bool(
            'anonymise_strings_at_word_boundaries_only', True)

        self.scrub_string_suffixes = opt_multiline('scrub_string_suffixes')
        self.whitelist_filenames = opt_multiline('whitelist_filenames')
        self.blacklist_filenames = opt_multiline('blacklist_filenames')
        self.scrub_all_numbers_of_n_digits = opt_multiline_int(
            'scrub_all_numbers_of_n_digits', minimum=1)

        if not self.extract_text_extensions_case_sensitive:
            self.extract_text_extensions_permitted = [
                x.upper() for x in self.extract_text_extensions_permitted]
            self.extract_text_extensions_permitted = [
                x.upper() for x in self.extract_text_extensions_permitted]

        # Whitelist, blacklist, nonspecific scrubber
        self.whitelist = WordList(
            filenames=self.whitelist_filenames,
            hasher=self.change_detection_hasher,
        )
        self.blacklist = WordList(
            filenames=self.blacklist_filenames,
            replacement_text=self.replace_nonspecific_info_with,
            hasher=self.change_detection_hasher,
            at_word_boundaries_only=(
                self.anonymise_strings_at_word_boundaries_only),
            max_errors=0,
        )
        self.nonspecific_scrubber = NonspecificScrubber(
            replacement_text=self.replace_nonspecific_info_with,
            hasher=self.change_detection_hasher,
            anonymise_codes_at_word_boundaries_only=(
                self.anonymise_codes_at_word_boundaries_only),
            anonymise_numbers_at_word_boundaries_only=(
                self.anonymise_numbers_at_word_boundaries_only),
            blacklist=self.blacklist,
            scrub_all_numbers_of_n_digits=self.scrub_all_numbers_of_n_digits,
            scrub_all_uk_postcodes=self.scrub_all_uk_postcodes,
        )

        # ---------------------------------------------------------------------
        # Output fields and formatting
        # ---------------------------------------------------------------------

        self.mapping_patient_id_fieldname = opt_str(
            'mapping_patient_id_fieldname')
        self.research_id_fieldname = opt_str('research_id_fieldname')
        self.trid_fieldname = opt_str('trid_fieldname')
        self.mapping_master_id_fieldname = opt_str(
            'mapping_master_id_fieldname')
        self.master_research_id_fieldname = opt_str(
            'master_research_id_fieldname')
        self.source_hash_fieldname = opt_str('source_hash_fieldname')
        self.date_to_text_format = opt_str('date_to_text_format')
        self.datetime_to_text_format = opt_str('datetime_to_text_format')
        self.append_source_info_to_comment = opt_bool(
            'append_source_info_to_comment', True)

        # ---------------------------------------------------------------------
        # Destination database configuration
        # ---------------------------------------------------------------------

        self.max_rows_before_commit = opt_int('max_rows_before_commit',
                                              DEFAULT_MAX_ROWS_BEFORE_COMMIT)
        self.max_bytes_before_commit = opt_int('max_bytes_before_commit',
                                               DEFAULT_MAX_BYTES_BEFORE_COMMIT)
        self.temporary_tablename = opt_str('temporary_tablename')

        # ---------------------------------------------------------------------
        # Databases
        # ---------------------------------------------------------------------

        destination_database_cfg_section = opt_str('destination_database')
        self._destination_database_url = parser.get_str(
            destination_database_cfg_section, 'url', required=True)
        admin_database_cfg_section = opt_str('admin_database')
        if destination_database_cfg_section == admin_database_cfg_section:
            raise ValueError(
                "Destination and admin databases mustn't be the same")
        source_database_cfg_sections = opt_multiline('source_databases')
        self.source_db_names = source_database_cfg_sections
        if destination_database_cfg_section in source_database_cfg_sections:
            raise ValueError("Destination database mustn't be listed as a "
                             "source database")
        if admin_database_cfg_section in source_database_cfg_sections:
            raise ValueError("Admin database mustn't be listed as a "
                             "source database")

        self.destdb = get_database(destination_database_cfg_section,
                                   name=destination_database_cfg_section,
                                   with_session=open_databases,
                                   with_conn=False,
                                   reflect=False)
        if not self.destdb:
            raise ValueError("Destination database misconfigured")
        if open_databases:
            self.dest_dialect = self.destdb.engine.dialect
        else:  # in context of web framework, some sort of default
            self.dest_dialect = mysql_dialect
        self._destdb_transaction_limiter = TransactionSizeLimiter(
            session=self.destdb.session,
            max_bytes_before_commit=self.max_bytes_before_commit,
            max_rows_before_commit=self.max_rows_before_commit
        )

        self.admindb = get_database(admin_database_cfg_section,
                                    name=admin_database_cfg_section,
                                    with_session=open_databases,
                                    with_conn=False,
                                    reflect=open_databases)
        if not self.admindb:
            raise ValueError("Admin database misconfigured")

        self.sources = {}
        self.src_dialects = {}
        for sourcedb_name in source_database_cfg_sections:
            log.info("Adding source database: {}".format(sourcedb_name))
            srccfg = DatabaseSafeConfig(parser, sourcedb_name)
            srcdb = get_database(sourcedb_name,
                                 srccfg_=srccfg,
                                 name=sourcedb_name,
                                 with_session=open_databases,
                                 with_conn=False,
                                 reflect=open_databases)
            if not srcdb:
                raise ValueError("Source database {} misconfigured".format(
                    sourcedb_name))
            self.sources[sourcedb_name] = srcdb
            if open_databases:
                self.src_dialects[sourcedb_name] = srcdb.engine.dialect
            else:  # in context of web framework
                self.src_dialects[sourcedb_name] = mssql_dialect

        # ---------------------------------------------------------------------
        # Processing options
        # ---------------------------------------------------------------------

        self.debug_max_n_patients = opt_int('debug_max_n_patients', 0)
        self.debug_pid_list = opt_multiline('debug_pid_list')

        # ---------------------------------------------------------------------
        # Opting out entirely
        # ---------------------------------------------------------------------

        self.optout_pid_filenames = opt_multiline('optout_pid_filenames')
        self.optout_mpid_filenames = opt_multiline('optout_mpid_filenames')
        self.optout_col_values = opt_pyvalue_list('optout_col_values')

        # ---------------------------------------------------------------------
        # Rest of initialization
        # ---------------------------------------------------------------------

        self.dd = DataDictionary(self)

        self.rows_in_transaction = 0
        self.bytes_in_transaction = 0
        self.rows_inserted_per_table = {}
        self.warned_re_limits = {}

        self.report_every_n_rows = DEFAULT_REPORT_EVERY
        self.chunksize = DEFAULT_CHUNKSIZE
        self.debug_scrubbers = False
        self.save_scrubbers = False
        
        self._src_bytes_read = 0
        self._dest_bytes_written = 0
        self._echo = False

    def get_destdb_engine_outside_transaction(
            self, encoding: str = 'utf-8') -> Engine:
        url = self._destination_database_url
        return create_engine(
            url,
            encoding=encoding,
            echo=self._echo,
            connect_args={'autocommit': True})  # for pyodbc
        # https://github.com/mkleehammer/pyodbc/wiki/Database-Transaction-Management  # noqa

    def overall_progress(self) -> str:
        return "{} read, {} written".format(
            sizeof_fmt(self._src_bytes_read),
            sizeof_fmt(self._dest_bytes_written))

    def load_dd(self, check_against_source_db: bool = True) -> None:
        log.info(SEP + "Loading data dictionary: {}".format(
            self.data_dictionary_filename))
        self.dd.read_from_file(self.data_dictionary_filename)
        self.dd.check_valid(
            prohibited_fieldnames=[self.source_hash_fieldname,
                                   self.trid_fieldname],
            check_against_source_db=check_against_source_db)
        self.init_row_counts()

    def init_row_counts(self) -> None:
        """Initialize row counts for all source tables."""
        self.rows_inserted_per_table = {}
        for db_table_tuple in self.dd.get_src_db_tablepairs():
            self.rows_inserted_per_table[db_table_tuple] = 0
            self.warned_re_limits[db_table_tuple] = False

    def check_valid(self) -> None:
        """Raise exception if config is invalid."""

        # Destination databases
        if not self.destdb:
            raise ValueError("No destination database specified.")
        if not self.admindb:
            raise ValueError("No admin database specified.")

        # Test table names
        if not self.temporary_tablename:
            raise ValueError("No temporary_tablename specified.")
        ensure_valid_table_name(self.temporary_tablename)

        # Test field names
        def validate_fieldattr(name):
            if not getattr(self, name):
                raise ValueError("Blank fieldname: " + name)
            ensure_valid_field_name(getattr(self, name))

        specialfieldlist = [
            "mapping_patient_id_fieldname",
            "research_id_fieldname",
            "trid_fieldname",
            "master_research_id_fieldname",
            "mapping_master_id_fieldname",
            "source_hash_fieldname",
        ]
        fieldset = set()
        for attrname in specialfieldlist:
            validate_fieldattr(attrname)
            fieldset.add(getattr(self, attrname))
        if len(fieldset) != len(specialfieldlist):
            raise ValueError(
                "Config: these must all be DIFFERENT fieldnames: " +
                ",".join(specialfieldlist))

        # Test strings
        if not self.replace_patient_info_with:
            raise ValueError("Blank replace_patient_info_with")
        if not self.replace_third_party_info_with:
            raise ValueError("Blank replace_third_party_info_with")
        if not self.replace_nonspecific_info_with:
            raise ValueError("Blank replace_nonspecific_info_with")
        replacements = list({self.replace_patient_info_with,
                             self.replace_third_party_info_with,
                             self.replace_nonspecific_info_with})
        if len(replacements) != 3:
            raise ValueError(
                "Inadvisable: replace_patient_info_with, "
                "replace_third_party_info_with, and "
                "replace_nonspecific_info_with should all be distinct")

        # Regex
        if self.string_max_regex_errors < 0:
            raise ValueError("string_max_regex_errors < 0, nonsensical")
        if self.min_string_length_for_errors < 1:
            raise ValueError("min_string_length_for_errors < 1, nonsensical")
        if self.min_string_length_to_scrub_with < 1:
            raise ValueError(
                "min_string_length_to_scrub_with < 1, nonsensical")

        # Source databases
        if not self.sources:
            raise ValueError("No source databases specified.")
        for dbname, dbinfo in self.sources.items():
            cfg = dbinfo.srccfg
            if not cfg.ddgen_allow_no_patient_info:
                if not cfg.ddgen_per_table_pid_field:
                    raise ValueError(
                        "Missing ddgen_per_table_pid_field in config for "
                        "database {}".format(dbname))
                ensure_valid_field_name(cfg.ddgen_per_table_pid_field)
                if cfg.ddgen_per_table_pid_field == self.source_hash_fieldname:
                    raise ValueError("Config: ddgen_per_table_pid_field can't "
                                     "be the same as source_hash_fieldname")
            if cfg.ddgen_master_pid_fieldname:
                ensure_valid_field_name(cfg.ddgen_master_pid_fieldname)

        # OK!
        log.debug("Config validated.")

    def encrypt_primary_pid(self, pid: int) -> str:
        """Encrypt a primary PID, producing a RID."""
        if pid is None:  # this is very unlikely!
            raise ValueError("Trying to hash NULL PID!")
            # ... see encrypt_master_pid() below
        return self.primary_pid_hasher.hash(pid)

    def encrypt_master_pid(self, mpid: int) -> Optional[str]:
        """Encrypt a master PID, producing a master RID."""
        if mpid is None:
            return None
            # potentially: risk of revealing the hash
            # and DEFINITELY: two patients, both with no NHS number, must not
            # be equated on the hash (e.g. hash(None) -> hash("None") -> ...)!
        return self.master_pid_hasher.hash(mpid)

    def hash_object(self, l: Any) -> str:
        """
        Hashes a list with Python's built-in hash function.

        We could use Python's build-in hash() function, which produces a 64-bit
        unsigned integer (calculated from: sys.maxint).
        However, there is an outside chance that someone uses a single-field
        table and therefore that this is vulnerable to content discovery via a
        dictionary attack. Thus, we should use a better version.
        """
        return self.change_detection_hasher.hash(repr(l))

    def get_extra_hasher(self, hasher_name: str) -> GenericHasher:
        if hasher_name not in self.extra_hashers.keys():
            raise ValueError(
                "Extra hasher {} requested but doesn't exist; check you have "
                "listed it in 'extra_hash_config_sections' in the config "
                "file".format(hasher_name))
        return self.extra_hashers[hasher_name]

    def get_source_db_names(self) -> List[str]:
        return self.source_db_names

    def set_echo(self, echo: bool) -> None:
        self._echo = echo
        self.admindb.engine.echo = echo
        self.destdb.engine.echo = echo
        for db in self.sources.values():
            db.engine.echo = echo
        # Now, SQLAlchemy will mess things up by adding an additional handler.
        # So, bye-bye:
        for logname in ('sqlalchemy.engine.base.Engine',
                        'sqlalchemy.engine.base.OptionEngine'):
            logger = logging.getLogger(logname)
            # log.critical(logger.__dict__)
            remove_all_logger_handlers(logger)

    def get_src_dialect(self, src_db) -> Any:
        return self.src_dialects[src_db]

    def get_dest_dialect(self) -> Any:
        return self.dest_dialect

    def commit_dest_db(self) -> None:
        self._destdb_transaction_limiter.commit()

    def notify_src_bytes_read(self, n_bytes: int) -> None:
        self._src_bytes_read += n_bytes

    def notify_dest_db_transaction(self, n_rows: int, n_bytes: int) -> None:
        self._destdb_transaction_limiter.notify(n_rows=n_rows, n_bytes=n_bytes)
        # ... may trigger a commit
        self._dest_bytes_written += n_bytes

    def extract_text_extension_permissible(self, extension: str) -> bool:
        if not self.extract_text_extensions_case_sensitive:
            extension = extension.upper()
        if self.extract_text_extensions_permitted:
            return extension in self.extract_text_extensions_permitted
        return extension not in self.extract_text_extensions_prohibited
