#!/usr/bin/env python3
# nlp_manager/nlp_manager.py

"""
Manage natural-language processing (NLP) via external tools.

Author: Rudolf Cardinal
Created at: 26 Feb 2015
Last update: see VERSION_DATE below

Copyright/licensing:

    Copyright (C) 2015-2015 Rudolf Cardinal (rudolf@pobox.com).
    Department of Psychiatry, University of Cambridge.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

Speed testing:

    - 8 processes, extracting person, location from a mostly text database
    - commit off during full (non-incremental) processing (much faster)
    - needs lots of RAM; e.g. Java subprocess uses 1.4 Gb per process as an
      average (rises from ~250Mb to ~1.4Gb and falls; steady rise means memory
      leak!); tested on a 16 Gb machine. See also the max_external_prog_uses
      parameter.

from __future__ import division
test_size_mb = 1887
n_person_tags_found =
n_locations_tags_found =
time_s = 10333  # 10333 s for main bit; 10465 including indexing; is 2.9 hours
speed_mb_per_s = test_size_mb / time_s

    ... 0.18 Mb/s
    ... and note that's 1.9 Gb of *text*, not of attachments

    - With incremental option, and nothing to do:
        same run took 18 s
    - During the main run, snapshot CPU usage:
        java about 81% across all processes, everything else close to 0
            (using about 12 Gb RAM total)
        ... or 75-85% * 8 [from top]
        mysqld about 18% [from top]
        nlp_manager.py about 4-5% * 8 [from top]

TO DO:
    - comments for NLP output fields (in table definition, destfields)

"""


# =============================================================================
# Imports
# =============================================================================

# from __future__ import division
# from __future__ import print_function

import argparse
import codecs
import configparser
import logging
import os
import subprocess
import sys

from cardinal_pythonlib.rnc_config import read_config_string_options
from cardinal_pythonlib.rnc_datetime import (
    get_now_utc,
    get_now_utc_notz
)
import cardinal_pythonlib.rnc_db as rnc_db
from cardinal_pythonlib.rnc_db import (
    DatabaseConfig,
    ensure_valid_field_name,
    ensure_valid_table_name,
    is_sqltype_valid
)
from cardinal_pythonlib.rnc_lang import (
    chunks,
    raise_if_attr_blank
)
import cardinal_pythonlib.rnc_log as rnc_log

from crate.anonymise.hash import MD5Hasher
from crate.version import VERSION, VERSION_DATE

log = logging.getLogger(__name__)

# =============================================================================
# Global constants
# =============================================================================

MAX_PID_STR = "9" * 10  # e.g. NHS numbers are 10-digit
ENCRYPTED_OUTPUT_LENGTH = len(MD5Hasher("dummysalt").hash(MAX_PID_STR))
SQLTYPE_ENCRYPTED_PID = "VARCHAR({})".format(ENCRYPTED_OUTPUT_LENGTH)
# ... in practice: VARCHAR(32)

FIELDNAME_LEN = 50
SEP = "=" * 20 + " "

MAX_SQL_FIELD_LEN = 64
# ... http://dev.mysql.com/doc/refman/5.0/en/identifiers.html
SQLTYPE_DB = "VARCHAR({})".format(MAX_SQL_FIELD_LEN)

LOG_FORMAT = '%(asctime)s.%(msecs)03d:%(levelname)s:%(name)s:%(message)s'
LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'

# =============================================================================
# Demo config
# =============================================================================

DEMO_CONFIG = ("""
# Configuration file for nlp_manager.py

# =============================================================================
# Overview
# =============================================================================
# - NOTE THAT THE FOLLOWING FIELDNAMES ARE USED AS STANDARD:
#
#   From nlp_manager.py:
#       _srcdb      {SQLTYPE_DB}     Source database name (*)
#       _srctable   {SQLTYPE_DB}         Source table name (*)
#       _srcpkfield {SQLTYPE_DB}         Source primary key (PK) field name (*)
#       _srcpkval   INT             Source PK value (*)
#       _srcfield   {SQLTYPE_DB}         Source field containing text content
#   (*) Mandatory.
#
#   From CamAnonGatePipeline.java:
#       _type       VARCHAR     Annotation type name
#       _id         INT         Annotation ID
#       _start      INT         Start position in the content
#       _end        INT         End position in the content
#       _content    TEXT        Full content. (You don't have to keep this!)
#
#   The length of the VARCHAR fields is set by the FIELDNAME_LEN constant.
#
#   Then individual GATE annotation systems might add their own fields.
#   For example, the ANNIE example has a "Person" annotation.
#
# - Output type section names MUST be in lower case (and output types will be
#   converted to lower case internally on receipt from the NLP program).

# =============================================================================
# Individual NLP definitions
# - referred to by the nlp_manager.py's command-line arguments
# =============================================================================

[MY_NAME_LOCATION_NLP]

# -----------------------------------------------------------------------------
# Input is from one or more source databases/tables/fields.
# This list refers to config sections that define those fields in more detail.
# -----------------------------------------------------------------------------

inputfielddefs =
    INPUT_FIELD_CLINICAL_DOCUMENTS
    INPUT_FIELD_PROGRESS_NOTES
    ...

# -----------------------------------------------------------------------------
# The output's _type parameter is used to look up possible destination tables
# (in case-insensitive fashion). What follows is a list of pairs: the first
# item is the annotation type coming out of the GATE system, and the second is
# the output type section defined in this file.
# -----------------------------------------------------------------------------

outputtypemap =
    person output_person
    location output_location

# -----------------------------------------------------------------------------
# NLP is done by an external program.
# Here we specify a program and associated arguments. The example shows how to
# use Java to launch a specific Java program (CamAnonGatePipeline), having set
# a path to find other Java classes, and then to pass arguments to the program
# itself.
# -----------------------------------------------------------------------------
# Substitutable parameters:
#   {{X}}         Substitutes variable X from the environment.
#   {{NLPLOGTAG}} Additional environment variable that indicates the process
#               being run; used to label the output from CamAnonGatePipeline.

progenvsection = MY_ENV_SECTION

progargs = java
    -classpath {{NLPPROGDIR}}:{{GATEDIR}}/bin/gate.jar:{{GATEDIR}}/lib/*
    CamAnonGatePipeline
    -g {{GATEDIR}}/plugins/ANNIE/ANNIE_with_defaults.gapp
    -a Person
    -a Location
    -it END_OF_TEXT_FOR_NLP
    -ot END_OF_NLP_OUTPUT_RECORD
    -lt {{NLPLOGTAG}}
    -v -v

# ... to which the text will be passed via stdin
# ... and the result will be expected via stdout, as a set of TSV
#     lines corresponding to the fields in destfields below

# -----------------------------------------------------------------------------
# The external program is slow, because NLP is slow. Therefore, we set up the
# external program and use it repeatedly for a whole bunch of text. Individual
# pieces of text are sent to it (via its stdin). We finish our piece of text
# with a delimiter, which should (a) be specified in the -it parameter above,
# and (b) be set below, TO THE SAME VALUE. The external program should return a
# TSV-delimited set of field/value pairs, like this:
#
#       field1\tvalue1\tfield2\tvalue2...
#       field1\tvalue3\tfield2\tvalue4...
#       ...
#       TERMINATOR
#
# ... where TERMINATOR is something that you (a) specify with the -ot parameter
# above, and (b) set below, TO THE SAME VALUE.
# -----------------------------------------------------------------------------

input_terminator = END_OF_TEXT_FOR_NLP
output_terminator = END_OF_NLP_OUTPUT_RECORD

# -----------------------------------------------------------------------------
# If the external program leaks memory, you may wish to cap the number of uses
# before it's restarted. Specify the max_external_prog_uses option if so.
# Specify 0 or omit the option entirely to ignore this.
# -----------------------------------------------------------------------------

# max_external_prog_uses = 1000

# -----------------------------------------------------------------------------
# To allow incremental updates, information is stored in a progress table.
# -----------------------------------------------------------------------------

progressdb = MY_DESTINATION_DATABASE
progresstable = nlp_progress
hashphrase = doesnotmatter

# =============================================================================
# Environment variable definitions (for external program, and progargs).
# The environment will start by inheriting the parent environment, then add
# variables here. Keys are case-sensitive
# =============================================================================

[MY_ENV_SECTION]

GATEDIR = /home/myuser/GATE_Developer_8.0
NLPPROGDIR = /home/myuser/somewhere/crate/nlp_manager/compiled_nlp_classes

# =============================================================================
# Output types
# =============================================================================

[output_person]

# -----------------------------------------------------------------------------
# The output is defined here. See the list of common fields above.
# Define your table's output fields below. The destfields list contains
# (fieldname, datatype) pairs.
# Anything from the output that matches what's below (in case-insensitive
# fashion) will be kept, and anything else will be discarded.
# -----------------------------------------------------------------------------

destdb = MY_DESTINATION_DATABASE
desttable = PERSON
destfields =
    _srcdb      {SQLTYPE_DB}
    _srctable   {SQLTYPE_DB}
    _srcpkfield {SQLTYPE_DB}
    _srcpkval   INT
    _srcfield   {SQLTYPE_DB}
    _type       {SQLTYPE_DB}
    _id         INT
    _start      INT
    _end        INT
    _content    TEXT
    rule        VARCHAR(100)
    firstname   VARCHAR(100)
    surname     VARCHAR(100)
    gender      VARCHAR(6)
    kind        VARCHAR(100)

indexdefs =
    _idx_srctable _srctable(10)
    _idx_srctable _srcpkfield
    _idx_srcpkval _srcpkval

# ... a set of (indexname, indexdef) pairs

[output_location]

destdb = MY_DESTINATION_DATABASE
desttable = LOCATION
destfields =
    _srcdb      {SQLTYPE_DB}
    _srctable   {SQLTYPE_DB}
    _srcpkfield {SQLTYPE_DB}
    _srcpkval   INT
    _srcfield   {SQLTYPE_DB}
    _type       {SQLTYPE_DB}
    _id         INT
    _start      INT
    _end        INT
    _content    TEXT
    rule        VARCHAR(100)
    loctype     VARCHAR(100)

indexdefs =
    _srctable
    _srcpkfield
    _srcpkval

# =============================================================================
# Input field definitions, referred to within the NLP definition, and cross-
# referencing database definitions
# =============================================================================

[INPUT_FIELD_CLINICAL_DOCUMENTS]

srcdb = MY_SOURCE_DATABASE
srctable = EXTRACTED_CLINICAL_DOCUMENTS
srcpkfield = DOCUMENT_PK
srcfield = DOCUMENT_TEXT

[INPUT_FIELD_PROGRESS_NOTES]

srcdb = MY_SOURCE_DATABASE
srctable = PROGRESS_NOTES
srcpkfield = PN_PK
srcfield = PN_TEXT

# =============================================================================
# Database definitions, each in its own section
# =============================================================================

[MY_SOURCE_DATABASE]

engine = mysql
host = localhost
port = 3306
user = ANONTEST
password = XXX
db = ANONYMOUS_OUTPUT

[MY_DESTINATION_DATABASE]

engine = mysql
host = localhost
port = 3306
user = ANONTEST
password = XXX
db = ANONYMOUS_OUTPUT

""".format(SQLTYPE_DB=SQLTYPE_DB))


# =============================================================================
# Classes for various bits of config
# =============================================================================

class OutputTypeConfig(object):
    """
    Class defining configuration for the output of a given GATE app.
    """

    def __init__(self, parser, section):
        """
        Read config from a configparser section.
        """
        read_config_string_options(
            self,
            parser,
            section,
            [
                "destdb",
                "desttable",
                "destfields",
                "indexdefs",
            ],
            enforce_str=True)
        raise_if_attr_blank(self, [
            "destdb",
            "desttable",
            "destfields",
        ])
        self.destfields = [x for x in self.destfields.lower().strip().split()]
        self.indexnames = []

        if self.indexdefs:
            self.indexdefs = [x for x in self.indexdefs.strip().split()]
            indexdefs = []
            for c in chunks(self.indexdefs, 2):
                n = c[0]
                idxdef = c[1]
                self.indexnames.append(n)
                indexdefs.append(idxdef)
            self.indexdefs = indexdefs

        df = []
        self.dest_datatypes = []
        for c in chunks(self.destfields, 2):
            field = c[0]
            datatype = c[1].upper()
            ensure_valid_field_name(field)
            if not is_sqltype_valid(datatype):
                raise Exception(
                    "Invalid datatype for {}: {}".format(field, datatype))
            df.append(field)
            self.dest_datatypes.append(datatype)
        self.destfields = df

        MANDATORY_FIELDS = ["_srcdb", "_srctable", "_srcpkfield", "_srcpkval"]
        for mandatory in MANDATORY_FIELDS:
            if mandatory not in self.destfields:
                raise Exception(
                    "For section {}, mandatory destfield {} missing".format(
                        section,
                        mandatory,
                    )
                )

        ensure_valid_table_name(self.desttable)


class InputFieldConfig(object):
    """
    Class defining configuration for an input field (containing text).
    """

    def __init__(self, parser, section):
        """
        Read config from a configparser section.
        """
        read_config_string_options(
            self,
            parser,
            section,
            [
                "srcdb",
                "srctable",
                "srcpkfield",
                "srcfield",
            ],
            enforce_str=True)
        raise_if_attr_blank(self, [
            "srcdb",
            "srctable",
            "srcpkfield",
            "srcfield",
        ])
        ensure_valid_table_name(self.srctable)
        ensure_valid_field_name(self.srcpkfield)
        ensure_valid_field_name(self.srcfield)


# =============================================================================
# Config class
# =============================================================================

class Config(object):
    """
    Class representing configuration as read from config file.
    """

    def __init__(self, filename, nlpname, logtag=""):
        """
        Read config from file.
        """

        self.config_filename = filename
        parser = configparser.RawConfigParser()
        parser.optionxform = str  # make it case-sensitive
        parser.read_file(codecs.open(filename, "r", "utf8"))

        # nlpname
        read_config_string_options(
            self,
            parser,
            nlpname,
            [
                "inputfielddefs",
                "outputtypemap",
                "progenvsection",
                "progargs",
                "input_terminator",
                "output_terminator",
                "max_external_prog_uses",
                "progressdb",
                "progresstable",
                "hashphrase",
            ],
            enforce_str=True)
        raise_if_attr_blank(self, [
            "inputfielddefs",
            "outputtypemap",
            "progargs",
            "input_terminator",
            "output_terminator",
            "progressdb",
            "progresstable",
            "hashphrase",
        ])

        self.inputfieldmap = {}
        self.databases = {}

        # inputfielddefs, inputfieldmap, databases
        self.inputfielddefs = [x for x in self.inputfielddefs.split()]
        for x in self.inputfielddefs:
            if x in self.inputfieldmap.keys():
                continue
            c = InputFieldConfig(parser, x)
            self.inputfieldmap[x] = c
            dbname = c.srcdb
            if dbname not in self.databases.keys():
                self.databases[dbname] = self.get_database(dbname)

        # outputtypemap, databases
        typepairs = self.outputtypemap.split()
        self.outputtypemap = {}
        for c in chunks(typepairs, 2):
            annottype = c[0]
            section = c[1]
            if annottype != annottype.lower():
                raise Exception(
                    "Section {}: annotation types in outputtypemap must be in "
                    "lower case: change {}".format(section, annottype))
            c = OutputTypeConfig(parser, section)
            self.outputtypemap[annottype] = c
            dbname = c.destdb
            if dbname not in self.databases.keys():
                self.databases[dbname] = self.get_database(dbname)

        # progenvsection, env, progargs, logtag
        self.env = os.environ.copy()
        if self.progenvsection:
            newitems = [(str(k), str(v))
                        for k, v in parser.items(self.progenvsection)]
            self.env = dict(list(self.env.items()) + newitems)
        if not logtag:
            logtag = "."
            # because passing a "-lt" switch with no parameter will make
            # CamAnonGatePipeline.java complain and stop
        self.env["NLPLOGTAG"] = logtag
        self.progargs = self.progargs.format(**self.env)
        self.progargs = [
            x for x in str(self.progargs).split()
        ]

        # max_external_prog_uses
        if self.max_external_prog_uses is None:
            self.max_external_prog_uses = 0
        else:
            self.max_external_prog_uses = int(self.max_external_prog_uses)

        # progressdb, progresstable, hashphrase
        self.progdb = self.get_database(self.progressdb)
        ensure_valid_field_name(self.progresstable)
        self.hasher = MD5Hasher(self.hashphrase)

        # other
        self.now = get_now_utc_notz()

    def get_database(self, section):
        """
        Return an rnc_db database object from a config file section.
        """
        parser = configparser.RawConfigParser()
        parser.read_file(codecs.open(self.config_filename, "r", "utf8"))
        try:  # guard this bit to prevent any password leakage
            dbc = DatabaseConfig(parser, section)
            db = dbc.get_database()
            return db
        except:
            raise rnc_db.NoDatabaseError(
                "Problem opening or reading from database {}; details "
                "concealed for security reasons".format(section))
        finally:
            dbc = None

    def hash(self, text):
        # Needs to handle Unicode
        return self.hasher.hash(text.encode("utf8"))


# =============================================================================
# Input support methods
# =============================================================================

def tsv_pairs_to_dict(line, key_lower=True):
    """
    Converts a TSV line into sequential key/value pairs as a dictionary.
    """
    items = line.split("\t")
    d = {}
    for chunk in chunks(items, 2):
        key = chunk[0]
        value = unescape_tabs_newlines(chunk[1])
        if key_lower:
            key = key.lower()
        d[key] = value
    return d


def escape_tabs_newlines(s):
    """
    Escapes CR, LF, tab, and backslashes. (Here just for testing; mirrors the
    equivalent function in the Java code.)
    """
    if not s:
        return s
    s = s.replace("\\", r"\\")  # replace \ with \\
    s = s.replace("\n", r"\n")  # escape \n; note ord("\n") == 10
    s = s.replace("\r", r"\r")  # escape \r; note ord("\r") == 13
    s = s.replace("\t", r"\t")  # escape \t; note ord("\t") == 9
    return s


def unescape_tabs_newlines(s):
    """
    Reverses escape_tabs_newlines.
    """
    # See also http://stackoverflow.com/questions/4020539
    if not s:
        return s
    d = ""  # the destination string
    in_escape = False
    for i in range(len(s)):
        c = s[i]  # the character being processed
        if in_escape:
            if c == "r":
                d += "\r"
            elif c == "n":
                d += "\n"
            elif c == "t":
                d += "\t"
            else:
                d += c
            in_escape = False
        else:
            if c == "\\":
                in_escape = True
            else:
                d += c
    return d


# =============================================================================
# Process handling
# =============================================================================
# Have Python host the client process, communicating with stdin/stdout?
#   http://eyalarubas.com/python-subproc-nonblock.html
#   http://stackoverflow.com/questions/2715847/python-read-streaming-input-from-subprocess-communicate  # noqa
# Java process could be a network server.
#   http://docs.oracle.com/javase/tutorial/networking/sockets/clientServer.html
#   http://www.tutorialspoint.com/java/java_networking.htm
# OK, first one works; that's easier.

class NlpController(object):
    """
    Class controlling the external process.
    """

    # -------------------------------------------------------------------------
    # Interprocess comms
    # -------------------------------------------------------------------------
    def __init__(self, config, commit=False, encoding='utf8'):
        """
        Initializes from the config.
        """
        self.config = config
        self.commit = commit
        self.input_terminator = self.config.input_terminator
        self.output_terminator = self.config.output_terminator
        self.starting_fields_values = {}
        self.n_uses = 0
        self.encoding = encoding

    def start(self):
        """
        Launch the external process.
        """
        args = self.config.progargs
        log.info("launching command: " + " ".join(args))
        self.p = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            shell=False,
            bufsize=1
        )
        # ... don't ask for stderr to be piped if you don't want it; firstly,
        # there's a risk that if you don't consume it, something hangs, and
        # secondly if you don't consume it, you see it on the console, which is
        # helpful.

    def _encode_to_subproc_stdin(self, text):
        log.debug("SENDING: " + text)
        bytes_ = text.encode(self.encoding)
        self.p.stdin.write(bytes_)

    def _flush_subproc_stdin(self):
        self.p.stdin.flush()

    def _decode_from_subproc_stdout(self):
        bytes_ = self.p.stdout.readline()
        text = bytes_.decode(self.encoding)
        log.debug("RECEIVING: " + text)
        return text

    def send(self, text, starting_fields_values=None):
        """
        Send text to the external process and receive the result.
        """
        if starting_fields_values is None:
            starting_fields_values = {}
        self.starting_fields_values = starting_fields_values
        # Send
        log.debug("writing: " + text)
        self._encode_to_subproc_stdin(text)
        self._encode_to_subproc_stdin("\n")
        self._encode_to_subproc_stdin(self.input_terminator + "\n")
        self._flush_subproc_stdin()  # required in the Python 3 system
        # Receive
        for line in iter(self._decode_from_subproc_stdout,
                         self.output_terminator + "\n"):
            # ... iterate until the sentinel output_terminator is received
            line = line.rstrip()  # remove trailing newline
            log.debug("stdout received: " + line)
            self.receive(line)
        self.n_uses += 1
        # Restart subprocess?
        if 0 < self.config.max_external_prog_uses <= self.n_uses:
            log.info("relaunching app after {} uses".format(self.n_uses))
            self.finish()
            self.start()
            self.n_uses = 0

    def finish(self):
        """
        Close down the external process.
        """
        self.p.communicate()  # close p.stdout, wait for the subprocess to exit

    # -------------------------------------------------------------------------
    # Input processing
    # -------------------------------------------------------------------------

    def receive(self, line):
        """
        Receive a line from the external process and send the results to our
        database.
        """
        d = tsv_pairs_to_dict(line)
        log.debug("dictionary received: {}".format(d))
        # Merge dictionaries so EXISTING FIELDS/VALUES (starting_fields_values)
        # HAVE PRIORITY.
        # http://stackoverflow.com/questions/38987
        # Python 2: one method was:
        #   d = dict(d.items() + self.starting_fields_values.items())
        # Python 3, for this situation -- would also work in Python 2!:
        d.update(self.starting_fields_values)
        log.debug("dictionary now: {}".format(d))

        # Now process it.
        if "_type" not in d.keys():
            raise Exception("_type information not in data received")
        annottype = d["_type"].lower()
        if annottype not in self.config.outputtypemap.keys():
            log.warning(
                "Unknown annotation type, skipping: {}".format(annottype))
            return
        ot = self.config.outputtypemap[annottype]
        # Restrict to fields we know about
        d = dict((k, d[k]) for k in ot.destfields if k in d)
        db = self.config.databases[ot.destdb]
        table = ot.desttable
        db.insert_record_by_dict(table, d)
        if self.commit:
            db.commit()  # or we get deadlocks

    # -------------------------------------------------------------------------
    # Test
    # -------------------------------------------------------------------------

    def _test(self):
        """
        Test the send function.
        """
        datalist = [
            "Bob Hope visited Seattle.",
            "James Joyce wrote Ulysses."
        ]
        for i in range(len(datalist)):
            self.send(datalist[i], {"_item_number": i})


# =============================================================================
# Database queries
# =============================================================================

def pk_of_record_in_progressdb(config, ifconfig, srcpkval, srchash=None):
    """
    Find the PK of a source record in the progress database.

    Inputs of None cause that field to be skipped in the check.
    With srchash=None, checks for record existence.
    With srchash, checks for matching hash too.
    """
    sql = """
        SELECT pk
        FROM {table}
        WHERE srcdb = ?
        AND srctable = ?
        AND srcpkfield = ?
        AND srcpkval = ?
        AND srcfield = ?
    """.format(
        table=config.progresstable,
    )
    args = [ifconfig.srcdb, ifconfig.srctable, ifconfig.srcpkfield, srcpkval,
            ifconfig.srcfield]
    if srchash is not None:
        sql += " AND srchash = ?"
        args.append(srchash)
    return config.progdb.fetchvalue(sql, *args)


# =============================================================================
# Database operations
# =============================================================================

def insert_into_progress_db(config, ifconfig, srcpkval, srchash, commit=False):
    """
    Make a note in the progress database that we've processed a source record.
    """
    pk = pk_of_record_in_progressdb(config, ifconfig, srcpkval, srchash=None)
    args = [
        ifconfig.srcdb,
        ifconfig.srctable,
        ifconfig.srcpkfield,
        srcpkval,
        ifconfig.srcfield,
        config.now,
        srchash
    ]
    if pk is not None:
        sql = """
            UPDATE {table}
            SET srcdb = ?,
                srctable = ?,
                srcpkfield = ?,
                srcpkval = ?,
                srcfield = ?,
                whenprocessedutc = ?,
                srchash = ?
            WHERE pk = ?
        """.format(
            table=config.progresstable,
        )
        args.append(pk)
    else:
        sql = """
            INSERT INTO {table} (
                srcdb, srctable, srcpkfield, srcpkval, srcfield,
                whenprocessedutc, srchash
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?
            )
        """.format(
            table=config.progresstable,
        )
    config.progdb.db_exec(sql, *args)
    if commit:
        config.progdb.commit()
    # Commit immediately, because other processes may need this table promptly.


def delete_where_no_source(config, ifconfig):
    """
    Delete destination records where source records no longer exist.

    - Can't do this in a single SQL command, since the engine can't necessarily
      see both databases.
    - Can't do this in a multiprocess way, because we're trying to do a
      DELETE WHERE NOT IN.
    """

    # 1. Progress database
    log.debug(
        "delete_where_no_source... {}.{} -> progressdb".format(
            ifconfig.srcdb,
            ifconfig.srctable,
        ))
    srcdb = config.databases[ifconfig.srcdb]
    sql = "SELECT {srcpkfield} FROM {srctable}".format(
        srcpkfield=ifconfig.srcpkfield,
        srctable=ifconfig.srctable,
    )
    pks = srcdb.fetchallfirstvalues(sql)
    sql = """
        DELETE FROM {progresstable}
        WHERE srcdb = ?
        AND srctable = ?
        AND srcpkfield = ?
    """.format(
        progresstable=config.progresstable,
    )
    args = [ifconfig.srcdb, ifconfig.srctable, ifconfig.srcpkfield]
    if not pks:
        log.debug("... deleting all")
    else:
        log.debug("... deleting selectively")
        value_string = ','.join(['?'] * len(pks))
        sql += " AND srcpkval NOT IN ({})".format(value_string)
        args += pks
    config.progdb.db_exec(sql, *args)

    # 2. Others. Combine in the same function as we re-use the source PKs.
    for otconfig in config.outputtypemap.values():
        log.debug(
            "delete_where_no_source... {}.{} -> {}.{}".format(
                ifconfig.srcdb,
                ifconfig.srctable,
                otconfig.destdb,
                otconfig.desttable,
            ))
        destdb = config.databases[otconfig.destdb]
        sql = """
            DELETE FROM {desttable}
            WHERE _srcdb = ?
            AND _srctable = ?
            AND _srcpkfield = ?
        """.format(
            desttable=otconfig.desttable,
        )
        # args will already be correct, from above
        if not pks:
            log.debug("... deleting all")
        else:
            log.debug("... deleting selectively")
            # value_string already set
            # noinspection PyUnboundLocalVariable
            sql += " AND _srcpkval NOT IN ({})".format(value_string)
        destdb.db_exec(sql, *args)


def delete_from_dest_dbs(config, ifconfig, srcpkval, commit=False):
    """
    For when a record has been updated; wipe older entries for it.
    """
    for otconfig in config.outputtypemap.values():
        log.debug(
            "delete_from_dest_dbs... {}.{} -> {}.{}".format(
                ifconfig.srcdb,
                ifconfig.srctable,
                otconfig.destdb,
                otconfig.desttable,
            ))
        destdb = config.databases[otconfig.destdb]
        sql = """
            DELETE FROM {desttable}
            WHERE _srcdb = ?
            AND _srctable = ?
            AND _srcpkfield = ?
            AND _srcpkval = ?
        """.format(
            desttable=otconfig.desttable,
        )
        args = [ifconfig.srcdb, ifconfig.srctable, ifconfig.srcpkfield,
                srcpkval]
        destdb.db_exec(sql, *args)
        if commit:
            destdb.commit()
        # ... or we get deadlocks
        # http://dev.mysql.com/doc/refman/5.5/en/innodb-deadlocks.html


def commit_all(config):
    """
    Execute a COMMIT on all databases.
    """
    config.progdb.commit()
    for db in config.databases.values():
        db.commit()


# =============================================================================
# Generators
# =============================================================================

def gen_text(config, ifconfig, tasknum=0, ntasks=1):
    """
    Generate text strings from the input database.
    """
    if 1 < ntasks <= tasknum:
            raise Exception("Invalid tasknum {}; must be <{}".format(
                tasknum, ntasks))
    threadcondition = ""
    if ntasks > 1:
        threadcondition = """
            WHERE {pkfield} % {ntasks} = {tasknum}
        """.format(
            pkfield=ifconfig.srcpkfield,
            ntasks=ntasks,
            tasknum=tasknum,
        )
    sql = """
        SELECT {pkfield}, {textfield}
        FROM {table}
        {threadcondition}
        ORDER BY {pkfield}
    """.format(
        pkfield=ifconfig.srcpkfield,
        textfield=ifconfig.srcfield,
        table=ifconfig.srctable,
        threadcondition=threadcondition,
    )
    db = config.databases[ifconfig.srcdb]
    cursor = db.cursor()
    db.db_exec_with_cursor(cursor, sql)
    row = cursor.fetchone()
    while row is not None:
        yield row[0], row[1]
        row = cursor.fetchone()


# =============================================================================
# Core functions
# =============================================================================

def process_nlp(config, incremental=False, tasknum=0, ntasks=1):
    """
    Main NLP processing function. Fetch text, send it to the GATE app
    (storing the results), and make a note in the progress database.
    """
    log.info(SEP + "NLP")
    controller = NlpController(config, commit=incremental)
    controller.start()
    for ifconfig in config.inputfieldmap.values():
        for pkval, text in gen_text(config, ifconfig,
                                    tasknum=tasknum, ntasks=ntasks):
            log.info("Processing {}.{}.{}, {}={}".format(
                ifconfig.srcdb, ifconfig.srctable, ifconfig.srcfield,
                ifconfig.srcpkfield, pkval
            ))
            srchash = config.hash(text)
            if (incremental and
                    pk_of_record_in_progressdb(config, ifconfig,
                                               pkval, srchash) is not None):
                log.debug("Record previously processed; skipping")
                continue
            starting_fields_values = {
                "_srcdb": ifconfig.srcdb,
                "_srctable": ifconfig.srctable,
                "_srcpkfield": ifconfig.srcpkfield,
                "_srcpkval": pkval,
                "_srcfield": ifconfig.srcfield,
            }
            if incremental:
                delete_from_dest_dbs(config, ifconfig, pkval,
                                     commit=incremental)
            controller.send(text, starting_fields_values)
            insert_into_progress_db(config, ifconfig, pkval, srchash,
                                    commit=incremental)
    controller.finish()
    commit_all(config)


def drop_remake(config, incremental=False, dynamic=True, compressed=False):
    """
    Drop output tables and recreate them.
    """

    # Not parallel.
    # -------------------------------------------------------------------------
    # 1. Progress database
    # -------------------------------------------------------------------------
    if not incremental:
        log.debug("progressdb: dropping table {}".format(
            config.progresstable))
        config.progdb.drop_table(config.progresstable)
    sql = """
        CREATE TABLE IF NOT EXISTS {t} (
            pk INT PRIMARY KEY AUTO_INCREMENT,
            srcdb {SQLTYPE_DB},
            srctable {SQLTYPE_DB},
            srcpkfield {SQLTYPE_DB},
            srcpkval INT,
            srcfield {SQLTYPE_DB},

            whenprocessedutc DATETIME,
            srchash {SQLTYPE_ENCRYPTED_PID},

            UNIQUE INDEX _idx1 (srcdb, srctable, srcpkfield, srcpkval,
                                srcfield)
        )
    """.format(
        t=config.progresstable,
        SQLTYPE_DB=SQLTYPE_DB,
        SQLTYPE_ENCRYPTED_PID=SQLTYPE_ENCRYPTED_PID,
    )
    # The pk field isn't used.
    log.debug(sql)
    config.progdb.db_exec_literal(sql)

    # -------------------------------------------------------------------------
    # 2. Output database(s)
    # -------------------------------------------------------------------------
    for ot in config.outputtypemap.values():
        db = config.databases[ot.destdb]
        t = ot.desttable
        fancy_ok = db.is_mysql()
        # Drop
        if not incremental:
            log.debug("dropping table {}".format(t))
            db.drop_table(t)
        # Recreate
        fieldspecs = []
        for i in range(len(ot.destfields)):
            f = ot.destfields[i]
            dt = ot.dest_datatypes[i]
            fieldspecs.append(f + " " + dt)
        sql = """
            CREATE TABLE IF NOT EXISTS {table} (
                {fieldspecs}
            )
            {dynamic}
            {compressed}
            CHARACTER SET utf8
            COLLATE utf8_general_ci
        """.format(
            table=t,
            fieldspecs=",".join(fieldspecs),
            dynamic="ROW_FORMAT=DYNAMIC" if dynamic and fancy_ok else "",
            compressed=("ROW_FORMAT=COMPRESSED"
                        if compressed and fancy_ok else ""),
        )
        log.debug(sql)
        db.db_exec_literal(sql)

    # -------------------------------------------------------------------------
    # 3. Delete WHERE NOT IN for incremental
    # -------------------------------------------------------------------------

    if incremental:
        for ifconfig in config.inputfieldmap.values():
            delete_where_no_source(config, ifconfig)

    # -------------------------------------------------------------------------
    # 4. Overall commit
    # -------------------------------------------------------------------------
    commit_all(config)


def create_indexes(config, tasknum=0, ntasks=1):
    """
    Create indexes on destination table(s).
    """
    # Parallelize by table.
    log.info(SEP + "Create indexes")
    outputtypes_list = list(config.outputtypemap.values())
    for i in range(len(outputtypes_list)):
        if i % ntasks != tasknum:
            continue
        ot = outputtypes_list[i]
        if not ot.indexdefs:
            continue
        db = config.databases[ot.destdb]
        t = ot.desttable
        sqlbits = []
        for j in range(len(ot.indexnames)):
            n = ot.indexnames[j]
            d = ot.indexdefs[j]
            s = "ADD INDEX {n} ({d})".format(n=n, d=d)
            if db.index_exists(t, n):
                continue  # because it will crash if you add it again!
            sqlbits.append(s)
        if not sqlbits:
            continue
        sql = "ALTER TABLE {t} {add_indexes}".format(
            t=t,
            add_indexes=", ".join(sqlbits),
        )
        log.debug(sql)
        db.db_exec(sql)


# =============================================================================
# Main
# =============================================================================

def fail():
    """
    Exit with a failure code.
    """
    sys.exit(1)


def main():
    """
    Command-line entry point.
    """
    version = "Version {} ({})".format(VERSION, VERSION_DATE)
    description = """
NLP manager. {version}. By Rudolf Cardinal.""".format(version=version)

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-n", "--version", action="version", version=version)
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help="Be verbose (use twice for extra verbosity)")
    parser.add_argument("configfile", nargs="?",
                        help="Configuration file name")
    parser.add_argument("nlpname", nargs="?",
                        help="NLP definition name (from config file)")
    parser.add_argument("--process", nargs="?", type=int, default=0,
                        help="For multiprocess patient-table mode: specify "
                             "process number")
    parser.add_argument("--nprocesses", nargs="?", type=int, default=1,
                        help="For multiprocess patient-table mode: specify "
                             "total number of processes (launched somehow, of "
                             "which this is to be one)")
    parser.add_argument("--processcluster", default="",
                        help="Process cluster name")
    parser.add_argument("--democonfig", action="store_true",
                        help="Print a demo config file")
    parser.add_argument("--incremental", action="store_true",
                        help="Process only new/changed information, where "
                             "possible")
    parser.add_argument("--dropremake", action="store_true",
                        help="Drop/remake destination tables only")
    parser.add_argument("--nlp", action="store_true",
                        help="Perform NLP processing only")
    parser.add_argument("--index", action="store_true",
                        help="Create indexes only")
    args = parser.parse_args()

    # Demo config?
    if args.democonfig:
        print(DEMO_CONFIG)
        return

    # Validate args
    if not args.configfile:
        parser.print_help()
        fail()
    if not args.nlpname:
        parser.print_help()
        fail()
    if args.nprocesses < 1:
        log.error("--nprocesses must be >=1")
        fail()
    if args.process < 0 or args.process >= args.nprocesses:
        log.error(
            "--process argument must be from 0 to (nprocesses - 1) inclusive")
        fail()

    everything = not any([args.dropremake, args.nlp, args.index])

    # -------------------------------------------------------------------------

    # Verbosity
    mynames = []
    if args.processcluster:
        mynames.append(args.processcluster)
    if args.nprocesses > 1:
        mynames.append("process {}".format(args.process))
    rnc_log.reset_logformat_timestamped(
        log,
        extraname=" ".join(mynames),
        level=logging.DEBUG if args.verbose >= 1 else logging.INFO
    )
    rnc_db.set_loglevel(logging.DEBUG if args.verbose >= 2 else logging.INFO)
    mainloglevel = logging.DEBUG if args.verbose >= 1 else logging.INFO
    logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATEFMT,
                        level=mainloglevel)

    # Report args
    log.debug("arguments: {}".format(args))

    # Load/validate config
    log.info("Loading config")
    config = Config(args.configfile,
                    args.nlpname,
                    logtag="_".join(mynames).replace(" ", "_"))

    # -------------------------------------------------------------------------

    log.info("Starting")
    start = get_now_utc()

    # 1. Drop/remake tables. Single-tasking only.
    if args.dropremake or everything:
        drop_remake(config, incremental=args.incremental)

    # 2. NLP
    if args.nlp or everything:
        process_nlp(config, incremental=args.incremental,
                    tasknum=args.process, ntasks=args.nprocesses)

    # 3. Indexes.
    if args.index or everything:
        create_indexes(config, tasknum=args.process, ntasks=args.nprocesses)

    log.info("Finished")
    end = get_now_utc()
    time_taken = end - start
    log.info("Time taken: {} seconds".format(time_taken.total_seconds()))


# =============================================================================
# Command-line entry point
# =============================================================================

if __name__ == '__main__':
    main()
