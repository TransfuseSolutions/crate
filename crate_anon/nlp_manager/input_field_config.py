##!/usr/bin/env python
# crate_anon/nlp_manager/input_field_config.py

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
# import sys
from typing import Any, Dict, Generator, List, Optional, Tuple

from cardinal_pythonlib.rnc_db import (
    ensure_valid_field_name,
    ensure_valid_table_name,
)
from sqlalchemy import BigInteger, Column, Index, String, Table
from sqlalchemy.sql import and_, column, exists, or_, select, table

from crate_anon.nlp_manager.constants import (
    FN_NLPDEF,
    FN_PK,
    FN_SRCDB,
    FN_SRCTABLE,
    FN_SRCPKFIELD,
    FN_SRCPKVAL,
    FN_SRCPKSTR,
    FN_SRCFIELD,
    MAX_STRING_PK_LENGTH,
)
from crate_anon.common.timing import MultiTimerContext, timer
from crate_anon.common.hash import hash64
from crate_anon.common.parallel import is_my_job_by_hash
from crate_anon.common.sqla import (
    count_star,
    is_sqlatype_integer,
    get_column_type,
    table_exists,
)
from crate_anon.nlp_manager.constants import SqlTypeDbIdentifier
from crate_anon.nlp_manager.models import NlpRecord

# if sys.version_info.major >= 3 and sys.version_info.minor >= 5:
#     from crate_anon.nlp_manager import nlp_definition  # see PEP0484
from crate_anon.nlp_manager.nlp_definition import NlpDefinition

log = logging.getLogger(__name__)

TIMING_GEN_TEXT_SQL_SELECT = "gen_text_sql_select"
TIMING_PROCESS_GEN_TEXT = "process_generated_text"
TIMING_PROGRESS_DB_SELECT = "progress_db_select"
TIMING_PROGRESS_DB_DELETE = "progress_db_delete"


# =============================================================================
# Input field definition
# =============================================================================

class InputFieldConfig(object):
    """
    Class defining configuration for an input field (containing text).
    """

    def __init__(self, nlpdef: NlpDefinition, section: str) -> None:
        """
        Read config from a configparser section.
        """
        def opt_str(option: str) -> str:
            return nlpdef.opt_str(section, option, required=True)

        def opt_strlist(option: str,
                        required: bool = False,
                        lower: bool = True) -> List[str]:
            return nlpdef.opt_strlist(section, option, as_words=False,
                                      lower=lower, required=required)

        def opt_int(option: str, default: Optional[int]) -> Optional[int]:
            return nlpdef.opt_int(section, option, default=default)

        # def opt_bool(option: str, default: bool) -> bool:
        #     return nlpdef.opt_bool(section, option, default=default)

        self._nlpdef = nlpdef

        self._srcdb = opt_str('srcdb')
        self._srctable = opt_str('srctable')
        self._srcpkfield = opt_str('srcpkfield')
        self._srcfield = opt_str('srcfield')
        # Make these case-sensitive to avoid our failure in renaming SQLA
        # Column objects to be lower-case:
        self._copyfields = opt_strlist('copyfields', lower=False)  # fieldnames
        self._indexed_copyfields = opt_strlist('indexed_copyfields',
                                               lower=False)
        self._debug_row_limit = opt_int('debug_row_limit', default=0)
        # self._fetch_sorted = opt_bool('fetch_sorted', default=True)

        ensure_valid_table_name(self._srctable)
        ensure_valid_field_name(self._srcpkfield)
        ensure_valid_field_name(self._srcfield)

        if len(set(self._indexed_copyfields)) != len(self._indexed_copyfields):
            raise ValueError("Redundant indexed_copyfields: {}".format(
                self._indexed_copyfields))

        if len(set(self._copyfields)) != len(self._copyfields):
            raise ValueError("Redundant copyfields: {}".format(
                self._copyfields))

        indexed_not_copied = set(self._indexed_copyfields) - set(
            self._copyfields)
        if indexed_not_copied:
            raise ValueError("Fields in index_copyfields but not in "
                             "copyfields: {}".format(indexed_not_copied))

        # allfields = [self._srcpkfield, self._srcfield] + self._copyfields
        # if len(allfields) != len(set(allfields)):
        #     raise ValueError(
        #         "Field overlap in InputFieldConfig: {}".format(section))
        # RE-THOUGHT: OK to copy source text fields etc. if desired.
        # It's fine in SQL to say SELECT a, a FROM mytable;

        self._db = nlpdef.get_database(self._srcdb)

    def get_srcdb(self) -> str:
        return self._srcdb

    def get_srctable(self) -> str:
        return self._srctable

    def get_srcpkfield(self) -> str:
        return self._srcpkfield

    def get_srcfield(self) -> str:
        return self._srcfield

    def get_source_session(self):
        return self._db.session

    def _get_source_metadata(self):
        return self._db.metadata

    def _get_source_engine(self):
        return self._db.engine

    def _get_progress_session(self):
        return self._nlpdef.get_progdb_session()

    @staticmethod
    def get_core_columns_for_dest() -> List[Column]:
        """Core columns in destination tables, primarily referring to the
        source."""
        return [
            Column(FN_PK, BigInteger, primary_key=True,
                   autoincrement=True,
                   doc="Arbitrary primary key (PK) of output record"),
            Column(FN_NLPDEF, SqlTypeDbIdentifier,
                   doc="Name of the NLP definition producing this row"),
            Column(FN_SRCDB, SqlTypeDbIdentifier,
                   doc="Source database name (from CRATE NLP config)"),
            Column(FN_SRCTABLE, SqlTypeDbIdentifier,
                   doc="Source table name"),
            Column(FN_SRCPKFIELD, SqlTypeDbIdentifier,
                   doc="PK field (column) name in source table"),
            Column(FN_SRCPKVAL, BigInteger,
                   doc="PK of source record (or integer hash of PK if the PK "
                       "is a string)"),
            Column(FN_SRCPKSTR, String(MAX_STRING_PK_LENGTH),
                   doc="NULL if the table has an integer PK, but the PK if "
                       "the PK was a string, to deal with hash collisions. "
                       "Max length: {}".format(MAX_STRING_PK_LENGTH)),
            Column(FN_SRCFIELD, SqlTypeDbIdentifier,
                   doc="Field (column) name of source text"),
        ]

    @staticmethod
    def get_core_indexes_for_dest() -> List[Index]:
        """Indexes for columns, primarily referring to the source."""
        # http://stackoverflow.com/questions/179085/multiple-indexes-vs-multi-column-indexes  # noqa
        return [
            Index('_idx_srcref',
                  # Remember, order matters; more to less specific
                  # See also BaseNlpParser.delete_dest_record
                  FN_SRCPKVAL,
                  FN_NLPDEF,
                  FN_SRCFIELD,
                  FN_SRCTABLE,
                  FN_SRCDB,
                  FN_SRCPKSTR),
            Index('_idx_deletion',
                  # We sometimes delete just using the following; see
                  # BaseNlpParser.delete_where_srcpk_not
                  FN_NLPDEF,
                  FN_SRCFIELD,
                  FN_SRCTABLE,
                  FN_SRCDB),
        ]

    def _require_table_exists(self) -> None:
        if not table_exists(self._get_source_engine(), self._srctable):
            msg = "Missing source table: {}.{}".format(self._srcdb,
                                                       self._srctable)
            log.critical(msg)
            raise ValueError(msg)

    def get_copy_columns(self) -> List[Column]:
        # We read the column type from the source database.
        self._require_table_exists()
        meta = self._get_source_metadata()
        t = Table(self._srctable, meta, autoload=True)
        copy_columns = []  # type: List[Column]
        processed_copy_column_names = []  # type: List[str]
        for c in t.columns:
            # if c.name.lower() in self._copyfields:
            if c.name in self._copyfields:
                copied = c.copy()
                # Force lower case:
                # copied.name = copied.name.lower()
                # copied.name = quoted_name(copied.name.lower(), None)
                # ... this is not working properly. Keep getting an
                # "Unconsumed column names" error with e.g. a source field of
                # "Text".
                # Try making copyfields case-sensitive instead.
                copy_columns.append(copied)
                processed_copy_column_names.append(c.name)
        # Check all requested fields are present:
        missing = set(self._copyfields) - set(processed_copy_column_names)
        if missing:
            raise ValueError(
                "The following fields were requested to be copied but are "
                "absent from the source (NB case-sensitive): {}".format(
                    missing))
        # log.critical(copy_columns)
        return copy_columns

    def get_copy_indexes(self) -> List[Index]:
        self._require_table_exists()
        meta = self._get_source_metadata()
        t = Table(self._srctable, meta, autoload=True)
        copy_indexes = []  # type: List[Index]
        processed_copy_index_col_names = []  # type: List[str]
        for c in t.columns:
            # if c.name.lower() in self._indexed_copyfields:
            if c.name in self._indexed_copyfields:
                copied = c.copy()
                # See above re case.
                idx_name = "idx_{}".format(c.name)
                copy_indexes.append(Index(idx_name, copied))
                processed_copy_index_col_names.append(c.name)
        missing = set(self._indexed_copyfields) - set(
            processed_copy_index_col_names)
        if missing:
            raise ValueError(
                "The following fields were requested to be copied/indexed but "
                "are absent from the source (NB case-sensitive): {}".format(
                    missing))
        return copy_indexes

    def is_pk_integer(self):
        pkcoltype = get_column_type(self._get_source_engine(), self._srctable,
                                    self._srcpkfield)
        if not pkcoltype:
            raise ValueError("Unable to get column type for column "
                             "{}.{}".format(self._srctable, self._srcpkfield))
        pk_is_integer = is_sqlatype_integer(pkcoltype)
        # log.debug("pk_is_integer: {} -> {}".format(repr(pkcoltype),
        #                                            pk_is_integer))
        return pk_is_integer

    def gen_text(self, tasknum: int = 0,
                 ntasks: int = 1) -> Generator[Tuple[str, Dict[str, Any]],
                                               None, None]:
        """
        Generate text strings from the input database.
        Yields tuple of (text, dict), where the dict is a column-to-value
        mapping for all other fields (source reference fields, copy fields).
        """
        if 1 < ntasks <= tasknum:
            raise Exception("Invalid tasknum {}; must be <{}".format(
                tasknum, ntasks))
        base_dict = {
            FN_SRCDB: self._srcdb,
            FN_SRCTABLE: self._srctable,
            FN_SRCPKFIELD: self._srcpkfield,
            FN_SRCFIELD: self._srcfield,
        }
        session = self.get_source_session()
        pkcol = column(self._srcpkfield)
        # ... don't use is_sqlatype_integer with this; it's a column clause,
        # not a full column definition.
        pk_is_integer = self.is_pk_integer()

        selectcols = [pkcol, column(self._srcfield)]
        for extracol in self._copyfields:
            selectcols.append(column(extracol))
        query = select(selectcols).select_from(table(self._srctable))
        # not ordered...
        # if self._fetch_sorted:
        #     query = query.order_by(pkcol)
        distribute_by_hash = False
        if ntasks > 1:
            if pk_is_integer:
                # Integer PK, so we can be efficient and bake the parallel
                # processing work division into the SQL:
                query = query.where(pkcol % ntasks == tasknum)
            else:
                distribute_by_hash = True
        nrows_returned = 0
        hashed_pk = None  # remove warning about reference before assignment
        with MultiTimerContext(timer, TIMING_GEN_TEXT_SQL_SELECT):
            result = session.execute(query)
            for row in result:  # ... a generator itself
                with MultiTimerContext(timer, TIMING_PROCESS_GEN_TEXT):
                    pkval = row[0]
                    if (distribute_by_hash and
                            not is_my_job_by_hash(pkval, tasknum, ntasks)):
                        continue

                    if 0 < self._debug_row_limit <= nrows_returned:
                        log.warning(
                            "Table {}.{}: not fetching more than {} rows (in "
                            "total for this process) due to debugging "
                            "limits".format(self._srcdb, self._srctable,
                                            self._debug_row_limit))
                        result.close()  # http://docs.sqlalchemy.org/en/latest/core/connections.html  # noqa
                        return

                    text = row[1]
                    if not text:
                        continue
                    other_values = dict(zip(self._copyfields, row[2:]))
                    if pk_is_integer:
                        other_values[FN_SRCPKVAL] = pkval
                        other_values[FN_SRCPKSTR] = None
                    else:  # hashed_pk will have been set above
                        other_values[FN_SRCPKVAL] = hashed_pk
                        other_values[FN_SRCPKSTR] = pkval
                    other_values.update(base_dict)
                    yield text, other_values
                    nrows_returned += 1

    def get_count(self) -> int:
        """
        Counts records in the input table for the given InputFieldConfig.
        Used for progress monitoring.
        """
        return count_star(session=self.get_source_session(),
                          tablename=self._srctable)

    def get_progress_record(self,
                            srcpkval: int,
                            srcpkstr: str = None) -> Optional[NlpRecord]:
        """
        Fetch a progress record (NlpRecord) for the given source record, if one
        exists.
        """
        session = self._get_progress_session()
        query = (
            session.query(NlpRecord).
            filter(NlpRecord.srcdb == self._srcdb).
            filter(NlpRecord.srctable == self._srctable).
            filter(NlpRecord.srcpkval == srcpkval).
            filter(NlpRecord.srcfield == self._srcfield).
            filter(NlpRecord.nlpdef == self._nlpdef.get_name())
            # Order not important (though the order of the index certainly
            # is; see NlpRecord.__table_args__).
            # http://stackoverflow.com/questions/11436469/does-order-of-where-clauses-matter-in-sql  # noqa
        )
        if srcpkstr is not None:
            query = query.filter(NlpRecord.srcpkstr == srcpkstr)
        # log.critical(query)
        with MultiTimerContext(timer, TIMING_PROGRESS_DB_SELECT):
            # This was surprisingly slow under SQL Server testing.
            return query.one_or_none()

    def gen_src_pks(self) -> Generator[Tuple[int, Optional[str]], None, None]:
        """
        Generate integer PKs from the source table specified for the
        InputFieldConfig.
        Timing is subsumed under TIMING_DELETE_WHERE_NO_SOURCE.
        """
        session = self.get_source_session()
        query = (
            select([column(self._srcpkfield)]).
            select_from(table(self._srctable))
        )
        result = session.execute(query)
        if self.is_pk_integer():
            for row in result:
                yield row[0], None
        else:
            for row in result:
                pkval = row[0]
                yield hash64(pkval), pkval

    def delete_progress_records_where_srcpk_not(
            self,
            temptable: Optional[Table]) -> None:
        progsession = self._get_progress_session()
        log.debug("delete_progress_records_where_srcpk_not... {}.{} -> "
                  "progressdb".format(self._srcdb, self._srctable))
        prog_deletion_query = (
            progsession.query(NlpRecord).
            filter(NlpRecord.srcdb == self._srcdb).
            filter(NlpRecord.srctable == self._srctable).
            # unnecessary # filter(NlpRecord.srcpkfield == self._srcpkfield).
            filter(NlpRecord.nlpdef == self._nlpdef.get_name())
        )
        if temptable is not None:
            log.debug("... deleting selectively")
            temptable_pkvalcol = temptable.columns[FN_SRCPKVAL]
            temptable_pkstrcol = temptable.columns[FN_SRCPKSTR]
            prog_deletion_query = prog_deletion_query.filter(
                ~exists().where(
                    and_(
                        NlpRecord.srcpkval == temptable_pkvalcol,
                        or_(
                            NlpRecord.srcpkstr == temptable_pkstrcol,
                            and_(
                                NlpRecord.srcpkstr.is_(None),
                                temptable_pkstrcol.is_(None)
                            )
                        )
                    )
                )
            )
        else:
            log.debug("... deleting all")
        with MultiTimerContext(timer, TIMING_PROGRESS_DB_DELETE):
            prog_deletion_query.delete(synchronize_session=False)
            # http://docs.sqlalchemy.org/en/latest/orm/query.html#sqlalchemy.orm.query.Query.delete  # noqa
        self._nlpdef.commit(progsession)

    def delete_all_progress_records(self) -> None:
        progsession = self._get_progress_session()
        prog_deletion_query = (
            progsession.query(NlpRecord).
            filter(NlpRecord.nlpdef == self._nlpdef.get_name())
        )
        log.debug("delete_all_progress_records for NLP definition: {}".format(
            self._nlpdef.get_name()))
        with MultiTimerContext(timer, TIMING_PROGRESS_DB_DELETE):
            prog_deletion_query.delete(synchronize_session=False)
        self._nlpdef.commit(progsession)
