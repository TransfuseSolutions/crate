#!/usr/bin/env python
# crate_anon/anonymise/make_demo_database.py

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

Makes a giant test database for anonymisation testing.

See also:

    http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3751474/
    http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3751474/table/T7/

After anonymisation, check with:

    SELECT * FROM anonymous_output.notes WHERE brcid IN (
        SELECT brcid
        FROM anonymous_mapping.secret_map
        WHERE patient_id < 2
    );
    SELECT * FROM test.patients WHERE patient_id < 2;

"""

import argparse
import datetime
import logging
import os
import random
import subprocess

from sqlalchemy import (
    create_engine,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Text,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import text

from crate_anon.anonymise.constants import (
    CHARSET,
    TABLE_KWARGS,
)
from crate_anon.common.logsupport import configure_logger_for_colour

log = logging.getLogger(__name__)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# =============================================================================
# Constants
# =============================================================================

CONSOLE_ENCODING = 'utf8'
REPORT_EVERY = 50
BASE_DOB = datetime.datetime(day=1, month=10, year=1980)
DT_FORMATS = [
    "%d %b %Y",  # e.g. 24 Jul 2013
    "%d %B %Y",  # e.g. 24 July 2013
    "%a %d %B %Y",  # e.g. Wed 24 July 2013
    "%d %B %Y, %H:%M %z",  # ... e.g. 24 July 2013, 20:04 +0100
    "%a %d %B %Y, %H:%M %z",  # ... e.g. Wed 24 July 2013, 20:04 +0100
    "%a %d %B %Y, %H:%M",  # ... e.g. Wed 24 July 2013, 20:04
    "%a %d %b %Y, %H:%M",  # ... e.g. Wed 24 Jul 2013, 20:04
    "%d %B %Y, %H:%M:%S %z",
    "%d %b %Y, %H:%M %z",
    "%d %b %Y, %H:%M:%S %z",
    "%H:%M",
    "%Y-%m-%dT%H:%M:%S%z",  # e.g. 2013-07-24T20:04:07+0100
    "%Y-%m-%d",  # e.g. 2013-07-24
    "%Y-%m-%dT%H%M",  # e.g. 20130724T2004
    "%Y-%m-%d",  # e.g. 20130724
    "%Y%m%d%H%M%S%z",  # e.g. 20130724200407+0100
    "%Y%m%d",  # e.g. 20130724
    "%Y-%m-%dT%H:%M:%SZ",  # e.g. 2013-07-24T20:03:07Z
    "%d/%m/%Y %H:%M",  # e.g. 01/12/2014 09:45
]

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DOCDIR = os.path.join(CURRENT_DIR, os.pardir, os.pardir,
                              "testdocs_for_text_extraction")
DOCTEST_DOC = os.path.join(DEFAULT_DOCDIR, 'doctest.doc')
DOCTEST_DOCX = os.path.join(DEFAULT_DOCDIR, 'doctest.docx')
DOCTEST_ODT = os.path.join(DEFAULT_DOCDIR, 'doctest.odt')
DOCTEST_PDF = os.path.join(DEFAULT_DOCDIR, 'doctest.pdf')

MAX_EXT_LENGTH_WITH_DOT = 10

# =============================================================================
# BLOB type
# =============================================================================

"""
MySQL: http://dev.mysql.com/doc/refman/5.7/en/storage-requirements.html
    TINYBLOB: up to 2^8 bytes
    BLOB: up to 2^16 bytes = 64 KiB
    MEDIUMBLOB: up to 2^24 bytes = 16 MiB  <-- minimum for docs
    LONGBLOB: up to 2^32 bytes = 4 GiB

    VARBINARY: up to 65535 = 64 KiB

SQL Server: https://msdn.microsoft.com/en-us/library/ms188362.aspx
    BINARY: up to 8000 bytes = 8 KB
    VARBINARY(MAX): up to 2^31 - 1 bytes = 2 GiB <-- minimum for docs
    IMAGE: deprecated; up to 2^31 - 1 bytes = 2 GiB
        https://msdn.microsoft.com/en-us/library/ms187993.aspx

SQL Alchemy:
    _Binary: base class
    LargeBinary: translates to BLOB in MySQL
    VARBINARY, as an SQL base data type
    dialects.mysql.base.LONGBLOB
    dialects.mssql.base.VARBINARY

Therefore, we can take the LargeBinary type and modify it:
"""


# http://docs.sqlalchemy.org/en/latest/core/custom_types.html
# noinspection PyUnusedLocal
@compiles(LargeBinary, 'mysql')
def compile_blob_mysql(type_, compiler, **kw):
    return "LONGBLOB"  # would have been "BLOB"


# If this goes wrong for future versions of SQL Server, write another
# specializer to produce "VARBINARY(MAX)" instead of "IMAGE". I haven't done
# that because it may be that SQL Alchemy is reading the SQL Server version
# (it definitely executes "select @@version") and specializing accordingly.


# =============================================================================
# Tables
# =============================================================================

class Patient(Base):
    __tablename__ = 'patient'
    __table_args__ = TABLE_KWARGS

    patient_id = Column(Integer, primary_key=True, autoincrement=False)
    forename = Column(String(50))
    surname = Column(String(50))
    dob = Column(DateTime)
    nullfield = Column(Integer)
    nhsnum = Column(BigInteger)
    phone = Column(String(50))
    postcode = Column(String(50))
    optout = Column(Boolean, default=False)
    related_patient_id = Column(Integer)


class Note(Base):
    __tablename__ = 'note'
    __table_args__ = TABLE_KWARGS

    note_id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patient.patient_id'))
    note = Column(Text)

    patient = relationship("Patient")


class BlobDoc(Base):
    __tablename__ = 'blobdoc'
    __table_args__ = TABLE_KWARGS

    blob_doc_id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patient.patient_id'))
    blob = Column(LargeBinary)  # modified as above!
    extension = Column(String(MAX_EXT_LENGTH_WITH_DOT))

    patient = relationship("Patient")

    def __init__(self, patient: Patient, filename: str) -> None:
        _, extension = os.path.splitext(filename)
        with open(filename, 'rb') as f:
            contents = f.read()  # will be of type 'bytes'
        super().__init__(patient=patient, blob=contents, extension=extension)


class FilenameDoc(Base):
    __tablename__ = 'filenamedoc'
    __table_args__ = TABLE_KWARGS

    filename_doc_id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patient.patient_id'))
    filename = Column(Text)

    patient = relationship("Patient")


# noinspection PyPep8Naming
def main() -> None:
    default_size = 0
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "url",
        help=(
            "SQLAlchemy database URL. Append ?charset=utf8, e.g. "
            "mysql+mysqldb://root:password@127.0.0.1:3306/test?charset=utf8 ."
            " WARNING: If you get the error 'MySQL has gone away', increase "
            "the max_allowed_packet parameter in my.cnf (e.g. to 32M)."))
    parser.add_argument(
        "--size", type=int, default=default_size, choices=[0, 1, 2, 3],
        help="Make tiny (0), small (1), medium (2), or large (3) database "
             "(default={})".format(default_size))
    parser.add_argument('--verbose', '-v', action='store_true',
                        help="Be verbose")
    parser.add_argument("--echo", action="store_true", help="Echo SQL")
    parser.add_argument(
        "--doctest-doc", default=DOCTEST_DOC,
        help="Test file for .DOC (default: {})".format(DOCTEST_DOC))
    parser.add_argument(
        "--doctest-docx", default=DOCTEST_DOCX,
        help="Test file for .DOCX (default: {})".format(DOCTEST_DOCX))
    parser.add_argument(
        "--doctest-odt", default=DOCTEST_ODT,
        help="Test file for .ODT (default: {})".format(DOCTEST_ODT))
    parser.add_argument(
        "--doctest-pdf", default=DOCTEST_PDF,
        help="Test file for .PDF (default: {})".format(DOCTEST_PDF))
    args = parser.parse_args()

    nwords = 10000
    if args.size == 0:
        n_patients = 20
        notes_per_patient = 1
        words_per_note = 100
    elif args.size == 1:
        n_patients = 100
        notes_per_patient = 5
        words_per_note = 100
    elif args.size == 2:
        n_patients = 100
        notes_per_patient = 100
        words_per_note = 1000
    elif args.size == 3:
        # about 1.4 Gb
        n_patients = 1000
        notes_per_patient = 100
        words_per_note = 1000
    else:
        assert False, "Bad size parameter"
    loglevel = logging.DEBUG if args.verbose else logging.INFO
    rootlogger = logging.getLogger()
    configure_logger_for_colour(rootlogger, level=loglevel)

    # 0. Announce intentions

    log.info("n_patients={}, notes_per_patient={}, words_per_note={}".format(
        n_patients, notes_per_patient, words_per_note))

    # 1. Get words

    log.info("Fetching words.")
    words = subprocess.check_output([
        "grep",
        "-v", "'s",
        "-m", str(nwords),
        "/usr/share/dict/words"
    ]).decode(CONSOLE_ENCODING).splitlines()

    # 2. Open database

    log.info("Opening database.")
    log.debug("URL: {}".format(args.url))
    engine = create_engine(args.url, echo=args.echo, encoding=CHARSET)
    session = sessionmaker(bind=engine)()

    # 3. Create tables

    log.info("Creating tables.")
    metadata.drop_all(engine, checkfirst=True)
    metadata.create_all(engine, checkfirst=True)

    # 4. Insert

    log.info("Aiming for a total of {} words in notes.".format(
        n_patients * notes_per_patient * words_per_note))

    log.info("Inserting data.")

    # Special extra patient

    p1 = Patient(
        patient_id=1,
        forename="Ronald Gibbet",
        surname="MacDonald",
        dob=datetime.datetime(day=11, month=11, year=1911),
        nhsnum=123456,
        phone="(01223)-123456",
        postcode="CB2 3EB",
    )
    session.add(p1)
    n1 = Note(
        patient=p1,
        note="""
Ronald MacDonald lived on a farm and kept a gibbet for scaring off
small animals. He was born on 11 Nov 1911 and was very proud of this.
His cat’s name was Flitterwick. It did not like the gibbets.
Ronalds other passion was blimping.
A typo might be RonaldMacDonald.
His phone number was 0122-312-3456, or 01223-123456, or (01223) 123456,
or 01223 123 456, or 01223 123456.
His NHS number was 123.456 or possibly 12 34 56.
His postcode was CB2 3EB, or possible CB23EB, or CB2, or 3EB.

Some HTML encoding is &amp; and &lt;.
An HTML tag is <a href="http://somewhere">this link</a>.
Start aspirin 75mg od. Remains on Lipitor 40mg nocte.
For haloperidol 2mg po prn max qds.
Start amoxicillin 500 mg b.i.d. for 7 days.

Some numerical results:
His CRP is 10. His previous CRP was <13 mg/dl.
Sodium 140.
TSH 3.5; urea normal.
Height 1.82m, weight 75kg, BMI 22.6. BP 135/82.
MMSE 28/30. ACE-R 72, ACE-II 73, ACE 73.
ESR 16 (H) mm/h.
WBC 9.2; neutrophils 4.3; lymphocytes 2.6; eosinophils 0.4; monocytes 1.2;
basophils 0.6.
        """
    )
    session.add(n1)
    for filename in (DOCTEST_DOC, DOCTEST_DOCX, DOCTEST_ODT, DOCTEST_PDF):
        bd = BlobDoc(patient=p1, filename=filename)
        session.add(bd)
        fd = FilenameDoc(patient=p1, filename=filename)
        session.add(fd)

    p2 = Patient(
        patient_id=2,
        forename="Bob D'Souza",
        surname="",
        dob=datetime.datetime(day=11, month=11, year=1911),
        nhsnum=234567,
        phone="(01223)-234567",
        postcode="CB2 3EB",
        related_patient_id=1,
    )
    session.add(p2)
    n2 = Note(
        patient=p2,
        note="""
Bob D'Souza, also known as Bob, or Mr DSouza, or sometimes Mr D Souza,
or the D'Souza bloke down the road, or BobDSouza or BobD'Souza.
His phone number was 0122-312-3456, or 01223-123456, or (01223) 123456,
or 01223 123 456, or 01223 123456.
His NHS number was 123.456 or possibly 12 34 56 or 123456, perhaps.
His postcode was CB2 3EB, or possible CB23EB, or CB2, or 3EB.
Bob Hope visited Seattle.
Bob took venlafaxine 375 M/R od, and is due to start clozapine 75mg bd.
        """
    )
    session.add(n2)

    # A bunch of patients
    random.seed(1)
    prev_forename = ''
    prev_surname = ''
    for p in range(n_patients):
        if p % REPORT_EVERY == 0:
            log.info("patient {}".format(p))
        forename = words[(p + 1) % nwords] + " " + words[(p + 10) % nwords]
        surname = words[(p + 2) % nwords]
        dob = BASE_DOB + datetime.timedelta(days=p)
        ok_date = dob + datetime.timedelta(days=1)
        nhsnum = random.randint(1, 9999999999)
        patient = Patient(
            patient_id=p + 3,
            forename=forename,
            surname=surname,
            dob=dob,
            nhsnum=nhsnum,
            phone="123456",
            postcode="CB2 3EB",
            related_patient_id=p + 2,  # one back from patient_id
        )
        session.add(patient)
        patient_id = patient.patient_id
        dates = "DATES: " + (
            " ".join([dob.strftime(fmt) for fmt in DT_FORMATS]) +
            " ".join([ok_date.strftime(fmt) for fmt in DT_FORMATS])
        ) + ". "
        fname = "FORENAME: " + forename + ". "
        sname = "SURNAME: " + surname + ". "
        rname = "RELATIVE: " + prev_forename + " " + prev_surname + ". "
        numbers = "NUMBERS: {}, {}, {}. ".format(patient_id, patient_id + 1,
                                                 nhsnum)
        for n in range(notes_per_patient):
            wstr = " ".join(words[p % nwords:(p + words_per_note) % nwords])
            note = Note(
                patient=patient,
                note=fname + sname + rname + numbers + dates + wstr,
            )
            session.add(note)
        prev_forename = forename
        prev_surname = surname

    # 5. Commit

    log.info("Committing...")
    session.commit()
    log.info("Done.")

    # 6. Report size

    if engine.dialect.name == 'mysql':
        log.info("Done. Database size:")
        sql = """
            SELECT
                table_schema,
                table_name,
                table_rows,
                data_length,
                index_length,
                ROUND(((data_length + index_length) / (1024 * 1024)), 2)
                  AS "Size_MB"
            FROM
                information_schema.tables
            WHERE table_schema = DATABASE()
        """
        rows = session.execute(text(sql))
        for r in rows:
            print(
                "schema={}, table={}, rows={}, data_length={}, "
                "index_length={}, size_MB={}".format(*r)
            )


if __name__ == '__main__':
    main()
