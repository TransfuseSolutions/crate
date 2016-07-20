#!/usr/bin/env python
# crate_anon/tools/preprocess_rio.py

"""
NOTES

===============================================================================
THINGS TO DO
===============================================================================
*** Imperfectly tested: Audit_Created_Date, Audit_Updated_Date
    ... some data for Audit_Created_Date, but incomplete audit table
*** Similarly, all cross-checks to RCEP output (currently limited by data
    availability)
*** Test RiO ddgen
*** CRATE docs: piccy, and overview of stages

===============================================================================
Primary keys
===============================================================================
In RCEP, Document_ID is VARCHAR(MAX), and is often:
    'global_table_id_9_or_10_digits' + '_' + 'pk_int_as_string'

HOWEVER, the last part is not always unique; e.g. Care_Plan_Interventions.

-   Care_Plan_Interventions has massive tranches of ENTIRELY identical rows,
    including a column called, ironically, "Unique_Key".
-   Therefore, we could either ditch the key entirely, or just use a non-UNIQUE
    index (and call it "key" not "pk").

-   AND THEN... In Client_Family, we have Document_ID values like
    773577794_1000000_1000001
    ^^^^^^^^^ ^^^^^^^ ^^^^^^^
    table ID  RiO#    Family member's RiO#

    ... there is no unique ID. And we don't need the middle part as we already
    have Client_ID. So this is not very useful. We could mangle out the second
    and subsequent '_' characters to give a unique number here, which would
    meaning having PK as BIGINT not INTEGER.
-   SQL Server's ROW_NUMBER() relates to result sets.
-   However, ADD pkname INT IDENTITY(1, 1) works beautifully and
    autopopulates existing tables.

===============================================================================
How is RiO non-core structured?
===============================================================================

- INDEX TABLES
    AssessmentDates
        associates AssessmentID and ClientID with dates

    AssessmentFormGroupsIndex, e.g.:
        Name               Description          Version    Deleted
        CoreAssess         Core Assessment      16          0
        CoreAssess         Core Assessment      17          0
        CoreAssessNewV1    Core Assessment v1   0           0
        CoreAssessNewV1    Core Assessment v1   1           0
        CoreAssessNewV2    Core Assessment v2   0           0
        CoreAssessNewV2    Core Assessment v2   1           0
        CoreAssessNewV2    Core Assessment v2   2           0
        ^^^                ^^^
        RiO form groups    Nice names

    AssessmentFormGroupsStructure, e.g.:
        name            FormName           AddedDate FormgroupVersion FormOrder
        CoreAssessNewV2	coreasspresprob	    2013-10-30 15:46:00.000	0	0
        CoreAssessNewV2	coreassesspastpsy	2013-10-30 15:46:00.000	0	1
        CoreAssessNewV2	coreassessbackhist	2013-10-30 15:46:00.000	0	2
        CoreAssessNewV2	coreassesmentstate	2013-10-30 15:46:00.000	0	3
        CoreAssessNewV2	coreassescapsafrisk	2013-10-30 15:46:00.000	0	4
        CoreAssessNewV2	coreasssumminitplan	2013-10-30 15:46:00.000	0	5
        CoreAssessNewV2	coreasspresprob	    2014-12-14 19:19:06.410	1	0
        CoreAssessNewV2	coreassesspastpsy	2014-12-14 19:19:06.410	1	1
        CoreAssessNewV2	coreassessbackhist	2014-12-14 19:19:06.413	1	2
        CoreAssessNewV2	coreassesmentstate	2014-12-14 19:19:06.413	1	3
        CoreAssessNewV2	coreassescapsafrisk	2014-12-14 19:19:06.417	1	4
        CoreAssessNewV2	coreasssumminitplan	2014-12-14 19:19:06.417	1	5
        CoreAssessNewV2	coresocial1	        2014-12-14 19:19:06.420	1	6
        CoreAssessNewV2	coreasspresprob	    2014-12-14 19:31:25.377	2	0 } NB
        CoreAssessNewV2	coreassesspastpsy	2014-12-14 19:31:25.377	2	1 }
        CoreAssessNewV2	coreassessbackhist	2014-12-14 19:31:25.380	2	2 }
        CoreAssessNewV2	coreassesmentstate	2014-12-14 19:31:25.380	2	3 }
        CoreAssessNewV2	coreassescapsafrisk	2014-12-14 19:31:25.380	2	4 }
        CoreAssessNewV2	coreasssumminitplan	2014-12-14 19:31:25.383	2	5 }
        CoreAssessNewV2	coresocial1	        2014-12-14 19:31:25.383	2	6 }
        CoreAssessNewV2	kcsahyper	        2014-12-14 19:31:25.387	2	7 }
        ^^^             ^^^
        Form groups     RiO forms; these correspond to UserAssess___ tables.

    AssessmentFormsIndex, e.g.
        Name                InUse Style Deleted    Description  ...
        core_10             1     6     0    Clinical Outcomes in Routine Evaluation Screening Measure-10 (core-10)
        corealcsub          1     6     0    Alcohol and Substance Misuse
        coreassescapsafrisk 1     6     0    Capacity, Safeguarding and Risk
        coreassesmentstate  1     6     0    Mental State
        coreassessbackhist  1     6     0    Background and History
        coreassesspastpsy   1     6     0    Past Psychiatric History and Physical Health
        coreasspresprob     1     6     0    Presenting Problem
        coreasssumminitplan 1     6     0    Summary and Initial Plan
        corecarer           1     6     0    Carers and Cared For
        corediversity       1     6     0    Diversity Needs
        coremedsum          1     6     0    Medication, Allergies and Adverse Reactions
        coremenhis          1     6     0    Mental Health / Psychiatric History
        coremenstate        1     6     0    Mental State and Formulation
        coreperdev          1     6     0    Personal History and Developmental History
        ^^^                                  ^^^
        |||                                  Nice names.
        RiO forms; these correspond to UserAssess___ tables,
        e.g. UserAssesscoreassesmentstate

    AssessmentFormsLocks
        system only; not relevant

    AssessmentFormsTimeout
        system only; not relevant

    AssessmentImageForms
        SequenceID, FormName, ClientID, AssessmentDate, UserID, ImagePath
        ?
        no data

    AssessmentIndex, e.g.
        Name          InUse Version DateBound RequiresClientID  Deleted Description ...
        ConsentShare  1     3       1         0                 1       Consent to Share Information
        CoreAssess    1     1       0         1                 0       Core Assessment
        CoreAssess    1     2       0         1                 0       Core Assessment
        CoreAssess    1     3       0         1                 0       Core Assessment
        CoreAssess    1     4       0         1                 0       Core Assessment
        CoreAssess    1     5       0         1                 0       Core Assessment
        CoreAssess    1     6       0         1                 0       Core Assessment
        CoreAssess    1     7       0         1                 0       Core Assessment
        crhtaaucp     1     1       0         0                 0       CRHTT / AAU Care Plan
        ^^^
        These correspond to AssessmentStructure.Assessment

    AssessmentMasterTableIndex, e.g.
        TableName       TableDescription
        core10          core10
        Corealc1        TAUDIT - Q1
        Corealc2        TAUDIT Q2
        Corealc3        TAUDIT - Q3,4,5,6,7,8
        Corealc4        TAUDIT - Q9,10
        Corealc5        Dependence
        Corealc6        Cocaine Use
        CoreOtherAssess Other Assessments
        crhttcpstat     CRHTT Care Plan Status
        ^^^
        These correspond to UserMaster___ tables.
        ... Find with:
            SELECT * FROM rio_data_raw.information_schema.columns
            WHERE table_name LIKE '%core10%';

    AssessmentPseudoForms, e.g. (all rows):
        Name            Link
        CaseNoteBar     ../Letters/LetterEditableMain.aspx?ClientID
        CaseNoteoview   ../Reports/RioReports.asp?ReportID=15587&ClientID
        kcsahyper       tfkcsa
        physv1hypa      physassess16a&readonlymode=1
        physv1hypb1     physasses16b1&readonlymode=1
        physv1hypb2     physasses16b22&readonlymode=1
        physv1hypbody   testbmap&readonlymode=1
        physv1hypvte    vte&readonlymode=1

    AssessmentReadOnlyFields, e.g.
        Code        CodeDescription       SQLStatementLookup    SQLStatementSearch
        ADCAT       Adminstrative Cat...  SELECT TOP 1 u.Cod... ...
        ADD         Client  Address       SELECT '$LookupVal... ...
        AdmCons     Consultant            SELECT '$LookupVal... ...
        AdmglStat   Status at Admission   SELECT '$LookupVal... ...
        AdmitDate   Admission Date        SELECT '$LookupVal... ...
        AEDEXLI     AED Exceptions...     SELECT TOP 1 ISNUL... ...
        Age         Client Age            SELECT '$LookupVal... ...
        Allergies   Client Allergies      SELECT dbo.LocalCo... ...
        bg          Background (PSOC323)  SELECT TOP 1 ISNUL... ...

        That Allergies one in full:
        - SQLStatementLookup
            SELECT dbo.LocalConfig_GetClientAllergies('$key$') AS Allergies
        - SQLStatementSearch = SQLStatementLookup

        And the bg/Background... one:
        - SQLStatementLookup
            SELECT TOP 1
                ISNULL(Men03,'History of Mental Health Problems / Psychiatric History section of core assessment not filled'),
                ISNULL(Men03,'History of Mental Health Problems / Psychiatric History section of core assessment not filled')
            FROM dbo.view_userassesscoremenhis
              -- ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
              -- view in which data column names renamed 'Men01', 'Men02'...
            WHERE ClientID = '$ClientID$'
            AND dbo.udf_Config_SystemValidationStatus(system_validationData,'Men03','v') = 1
            ORDER BY
                AssessmentDate DESC,
                type12_UpdatedDate DESC
        - SQLStatementSearch = SQLStatementLookup

        - EXEC sp_helptext 'production.rio62camlive.dbo.udf_Config_SystemValidationStatus';
          ... can't view this at present (am on the wrong machine?).

    AssessmentStructure, e.g.:
        FormGroup       Assessment  AssessmentVersion FormGroupVersion FormGroupOrder
        CoreAssessNewV1 CoreAssess    7    1    1
        CoreAssessNewV2 CoreAssess    7    2    0
        CoreAssessNewV2 CoreAssess    6    1    0
        CoreAssessNewV2 CoreAssess    5    0    0
        CoreAssessNewV2 CoreAssess    2    0    1
        CoreAssessNewV2 CoreAssess    3    0    0

        ... FORM GROUP to ASSESSMENT mapping

- MAIN DATA TABLES

    e.g.:
    UserAssesscoreassesmentstate
        ClientID
        system_ValidationData  -- e.g. (with newlines added):
            '<v n="3">
                <MentState s="v" a="<userID>" v="" d="" e="10/11/2013 13:23" o="1" n="3" b="" c="">
                </MentState>
            </v>'
            ... where <userID> was a specific user ID
        NHSNum  -- as VARCHAR
        AssessmentDate
        ServRef
        MentState   -- this contains the text
        type12_NoteID -- PK
        type12_OriginalNoteID  -- can be NULL
        type12_DeletedDate  -- can be NULL
        type12_UpdatedBy
        type12_UpdatedDate
        formref

    UserAssesscoreassesspastpsy
        ClientID
        system_ValidationData
        NHSNum
        AssessmentDate
        ServRef
        PastPsyHist  -- contains text
        PhyHealth    -- contains text
        Allergies    -- contains text
        type12_NoteID
        type12_OriginalNoteID
        type12_DeletedDate
        type12_UpdatedBy
        type12_UpdatedDate
        formref
        frailty  -- numeric; in passing, here's the Rockwood frailty score

- LOOKUP TABLES

    UserMasterfrailty, in full:
        Code CodeDescription            Deleted
        1    1 - Very Fit               0
        2    2 - Well                   0
        3    3 - Managing Well          0
        4    4 - Vulnerable             0
        5    5 - Mildly Frail           0
        7    7 - Severely Frail         0
        6    6 - Moderately Frail       0
        9    9 - Terminally Ill         0
        8    8 - Very Serverely Frail   0

- SO, OVERALL STRUCTURE, APPROXIMATELY:

    RiO front-end example:
        Assessments [on menu]
            -> Core Assessment [menu dropdown]
            -> Core Assessment v2 [LHS, expands to...]
                ->  Presenting Problem [LHS]
                    Past Psychiatric History and Physical Health
                        ->  Service/Team
                            Past Psychiatric History
                            Physical Health / Medical History
                            Allergies
                            Frailty Score
                    Background and History
                    Mental State
                    Capacity, Safeguarding and Risk
                    Summary and Initial Plan
                    Social Circumstances and Employment
                    Keeping Children Safe Assessment

    So, hierarchy at the backend (> forward, < backward keys):

        AssessmentIndex.Name(>) / .Description ('Core Assessment')
            AssessmentStructure.Assessment(<) / .FormGroup(>)
                AssessmentFormGroupsIndex.Name(<) / .Description ('Core Assessment v2')
                AssessmentFormGroupsStructure.name(<) / .FormName(>) ('coreassesspastpsy')
                    AssessmentFormsIndex.Name(<) / .Description ('Past Psychiatric History and Physical Health')
                    UserAssesscoreassesspastpsy = data
                              _________________(<)
                        UserAssesscoreassesspastpsy.frailty(>) [lookup]
                            UserMasterfrailty.Code(<) / .CodeDescription

- Simplifying views (for core and non-core RiO) could be implemented in the
  preprocessor, or after anonymisation.
  Better to do it in the preprocessor, because this knows about RiO.
  The two points of "RiO knowledge" should be:
    - the preprocessor;
        ... PK, RiO number as integer, views
    - the ddgen_* information in the anonymiser config file.
        ... tables to omit
        ... fields to omit
        ... default actions on fields
            ... e.g. exclude if type12_DeletedDate is None
            ... however, we could also do that more efficiently as a view,
                and that suits all use cases so far.

===============================================================================
Scrubbing references to other patients
===============================================================================

There are two ways to do this, in principle.

The first is to reshape the data so that data from "referred-to" patients
appear in fields that can be marked as "third-party". The difficulty is that
the mapping is not 1:1 with any database row. For example, if row A has
fields "MainCarer" and "OtherCarer" that can refer to other patients, then
if the "OtherCarer" field changes, the number of rows to be examined changes.
This prohibits using a real-world PK. (A view that joined according to these
fields would not have an immutable pseudo-PK either.) And that causes
difficulties for a change-detection system. One would have to mark such a view
as something not otherwise read/copied by the anonymiser.

The other method, which is more powerful, is to do this work in the anonymiser
itself, by defining fields that are marked as "third_party_xref_pid", and
building the scrubber recursively with "depth" and "max_depth" parameters;
if depth > 0, the information is taken as third-party.

Well, that sounds achievable.

Done.

===============================================================================
RiO audit trail and change history
===============================================================================

- AuditTrail
    SequenceID -- PK for AuditTrail
    UserNumber -- FK to GenUser.UserNumber
    ActionDateTime
    AuditAction -- 2 = insert, 3 = update
    RowID -- row number -- how does that work?
        ... cheerfully, SQL Server doesn't have an automatic row ID;
        http://stackoverflow.com/questions/909155/equivalent-of-oracles-rowid-in-sql-server  # noqa
        ... so is it the PK we've already identified and called crate_pk?
    TableNumber -- FK to GenTable.Code
    ClientID -- FK to ClientIndex.ClientID
    ...

"""  # noqa

import argparse
from collections import OrderedDict
import logging
import pdb
import sys
import traceback

from sqlalchemy import (
    create_engine,
    MetaData,
)

from crate_anon.anonymise.constants import MYSQL_CHARSET
from crate_anon.common.lang import (
    get_case_insensitive_dict_key,
    merge_two_dicts,
)
from crate_anon.common.logsupport import configure_logger_for_colour
from crate_anon.common.sql import (
    add_columns,
    add_indexes,
    create_view,
    drop_columns,
    drop_indexes,
    drop_view,
    ensure_columns_present,
    execute,
    get_table_names,
    get_view_names,
    get_column_names,
    set_print_not_execute,
    sql_fragment_cast_to_int,
    sql_string_literal,
    ViewMaker,
)

log = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

AUTONUMBER_COLTYPE = "INTEGER IDENTITY(1, 1) NOT NULL"
# ... is specific to SQL Server, which is what RiO uses.
#     MySQL equivalent would be "INTEGER PRIMARY KEY AUTO_INCREMENT" or
#     "INTEGER UNIQUE KEY AUTO_INCREMENT".
#     (MySQL allows only one auto column and it must be a key.)
#     (This also does the indexing.)

# Tables in RiO v6.2 Core:
RIO_TABLE_MASTER_PATIENT = "ClientIndex"
RIO_TABLE_ADDRESS = "ClientAddress"
RIO_TABLE_PROGRESS_NOTES = "PrgProgressNote"
RIO_TABLE_CLINICAL_DOCUMENTS = "ClientDocument"
# Columns in RiO Core:
RIO_COL_PATIENT_ID = "ClientID"  # RiO 6.2: VARCHAR(15)
RIO_COL_NHS_NUMBER = "NNN"  # RiO 6.2: CHAR(10) ("National NHS Number")
RIO_COL_POSTCODE = "PostCode"  # ClientAddress.PostCode
RIO_COL_DEFAULT_PK = "SequenceID"  # INT
RIO_COL_USER_ASSESS_DEFAULT_PK = "type12_NoteID"

# Tables in RiO CRIS Extract Program (RCEP) output database:
RCEP_TABLE_MASTER_PATIENT = "Client_Demographic_Details"
RCEP_TABLE_ADDRESS = "Client_Address_History"
RCEP_TABLE_PROGRESS_NOTES = "Progress_Notes"
# Columns in RCEP extract:
RCEP_COL_PATIENT_ID = "Client_ID"  # RCEP: VARCHAR(15)
RCEP_COL_NHS_NUMBER = "NHS_Number"  # RCEP: CHAR(10)
RCEP_COL_POSTCODE = "Post_Code"  # RCEP: NVARCHAR(10)
# ... general format (empirically): "XX12 3YY" or "XX1 3YY"; "ZZ99" for unknown
# This matches the ONPD "pdcs" format.
RCEP_COL_MANGLED_KEY = "Document_ID"

# CPFT hacks (RiO tables added to RCEP output):
CPFT_RCEP_TABLE_FULL_PROGRESS_NOTES = "Progress_Notes_II"

# Columns in ONS Postcode Database (from CRATE import):
ONSPD_TABLE_POSTCODE = "postcode"
DEFAULT_GEOG_COLS = [
    "pcon", "pct", "nuts", "lea", "statsward", "casward",
    "lsoa01", "msoa01", "ur01ind", "oac01", "lsoa11",
    "msoa11", "parish", "bua11", "buasd11", "ru11ind",
    "oac11", "imd",
]

# Columns added:
CRATE_COL_PK = "crate_pk"
# Do NOT use 'id'; this appears in RiO ClientAlternativeId /
# RCEP Client_Alternative_ID. "pk" is OK for RCEP + RiO, but clarity is good
CRATE_COL_RIO_NUMBER = "crate_rio_number"
# "rio_number" is OK for RCEP + RiO, but clarity is good
CRATE_COL_NHS_NUMBER = "crate_nhs_number_int"
# "nhs_number_int" is OK for RCEP + RiO, but again...
# For RCEP, in SQL Server, check existing columns with:
#   USE database;
#   SELECT column_name, table_name
#       FROM information_schema.columns
#       WHERE column_name = 'something';
# For RiO, for now, check against documented table structure.

# For progress notes:
CRATE_COL_MAX_SUBNUM = "crate_max_subnum_for_notenum"
CRATE_COL_LAST_NOTE = "crate_last_note_in_edit_chain"
# For clinical documents:
CRATE_COL_MAX_DOCVER = "crate_max_docver_for_doc"
CRATE_COL_LAST_DOC = "crate_last_doc_in_chain"

# Indexes added... generic:
CRATE_IDX_PK = "crate_idx_pk"  # for any patient table
CRATE_IDX_RIONUM = "crate_idx_rionum"  # for any patient table
# For progress notes:
CRATE_IDX_RIONUM_NOTENUM = "crate_idx_rionum_notenum"
CRATE_IDX_MAX_SUBNUM = "crate_idx_max_subnum"
CRATE_IDX_LAST_NOTE = "crate_idx_last_note"
# For clinical documents:
CRATE_IDX_RIONUM_SERIALNUM = "crateidx_rionum_serialnum"
CRATE_IDX_MAX_DOCVER = "crate_idx_max_docver"
CRATE_IDX_LAST_DOC = "crate_idx_last_doc"

# Views added:
VIEW_RCEP_CPFT_PROGRESS_NOTES_CURRENT = "progress_notes_current_crate"
VIEW_ADDRESS_WITH_GEOGRAPHY = "client_address_with_geography"

RIO_6_2_ATYPICAL_PKS = {
    # These are table: pk_field mappings for PATIENT tables, i.e. those
    # containing the ClientID field, where that PK is not the default of
    # SequenceID.

    # -------------------------------------------------------------------------
    # RiO Core
    # -------------------------------------------------------------------------

    # Ams*: Appointment Management System
    'AmsAppointmentContactActivity': 'ActivitySequenceID',
    'AmsAppointmentOtherHCP': None,  # non-patient; non-unique SequenceID
    # ... SequenceID is non-unique and the docs also list it as an FK;
    #     ActivitySequenceID this is unique and a PK
    'AmsReferralDatesArchive': 'AMSSequenceID',
    # ... UNVERIFIED as no rows in our data; listed as a PK and an FK
    'AmsReferralListUrgency': None,
    'AmsReferralListWaitingStatus': None,
    'AmsStream': None,  # non-patient; non-unique SequenceID

    'CarePlanIndex': 'CarePlanID',
    'CarePlanProblemOrder': None,

    'ClientAddressMerged': None,  # disused table
    'ClientCareSpell': None,  # CareSpellNum is usually 1 for a given ClientID
    'ClientDocumentAdditionalClient': None,
    'ClientFamily': None,
    'ClientFamilyLink': None,
    'ClientGPMerged': None,
    'ClientHealthCareProvider': None,
    'ClientMerge': None,
    'ClientMerged': None,
    'ClientName': 'ClientNameID',
    'ClientOtherDetail': None,  # not in docs, but looks like Core
    'ClientPhoto': None,
    'ClientPhotoMerged': None,
    'ClientProperty': None,
    'ClientPropertyMerged': None,
    'ClientTelecom': 'ClientTelecomID',
    'ClientUpdatePDSCache': None,

    # Con*: Contracts
    'Contract': 'ContractNumber',
    'ConAdHocAwaitingApproval': 'SequenceNo',
    'ConClientInitialBedRate': None,
    'ConClinicHistory': 'SequenceNo',
    'ConLeaveDiscountHistory': 'SequenceNo',

    # Not documented, but looks like Core
    'Deceased': None,  # or possibly TrustWideID (or just ClientID!)

    'DemClientDeletedDetails': None,

    # EP: E-Prescribing
    # ... with DA: Drug Administration
    # ... with DS: Drug Service
    'EPClientConditions': 'RowID',
    'EPClientPrescription': 'PrescriptionID',
    'EPClientSensitivities': None,  # UNVERIFIED: None? Joint PK on ProdID?
    'EPDiscretionaryDrugClientLink': None,
    'EPVariableDosageDrugLink': 'HistoryID',  # UNVERIFIED
    'EPClientAllergies': 'ReactionID',
    'DAConcurrencyControl': None,
    'DAIPPrescription': 'PrescriptionID',
    'DSBatchPatientGroups': None,
    'DSMedicationBatchContinue': None,
    'DSMedicationBatchLink': None,

    # Ims*: Inpatient Management System
    'ImsEventLeave': 'UniqueSequenceID',  # SequenceID
    'ImsEventMovement': None,
    'ImsEventRefno': None,  # Not in docs but looks like Core.
    'ImsEventRefnoBAKUP': None,  # [Sic.] Not in docs but looks like Core.

    # LR*: Legitimate Relationships
    'LRIdentifiedCache': None,

    # Mes*: messaging
    'MesLettersGenerated': 'Reference',

    # Mnt*: Mental Health module (re MHA detention)
    'MntArtAttendee': None,  # SequenceID being "of person within a meeting"
    'MntArtOutcome': None,  # ditto
    'MntArtPanel': None,  # ditto
    'MntArtRpts': None,  # ditto
    'MntArtRptsReceived': None,  # ditto
    'MntClientEctSection62': None,
    'MntClientMedSection62': None,
    'MntClientSectionDetailCareCoOrdinator': None,
    'MntClientSectionDetailCourtAppearance': None,
    'MntClientSectionDetailFMR': None,
    'MntClientSectionReview': None,

    # NDTMS*: Nation(al?) Drug Treatment Monitoring System

    # SNOMED*: SNOMED
    'SNOMED_Client': 'SC_ID',

    # UserAssess*: user assessment (= non-core?) tables.
    # See other default PK below: type12:

    # -------------------------------------------------------------------------
    # Non-core? No docs available.
    # -------------------------------------------------------------------------
    # Chd*: presumably, child development
    'ChdClientDevCheckBreastFeeding': None,
    # ... guess; DevChkSeqID is probably FK to ChdClientDevCheck.SequenceID

    # ??? But it has q1-q30, qu2-14, home, sch, comm... assessment tool...
    'CYPcurrentviewImport': None,  # not TrustWideID (which is non-unique)

    'GoldmineIfcMapping': None,  # no idea, really, and no data to explore

    'KP90ErrorLog': None,

    'ReportsOutpatientWaitersHashNotSeenReferrals': None,
    'ReportsOutpatientWaitersNotSeenReferrals': None,

    'UserAssesstfkcsa_childprev': 'type12_RowID',  # Keeping Children Safe Assessment subtable  # noqa
    'UserAssesstfkcsa_childs': 'type12_RowID',  # Keeping Children Safe Assessment subtable  # noqa
}

RIO_6_2_ATYPICAL_PATIENT_ID_COLS = {
    'SNOMED_Client': 'SC_ClientID',
}


# =============================================================================
# Generic table processors
# =============================================================================

def table_is_rio_type(tablename, progargs):
    if progargs.rio:
        return True
    if not progargs.cpft:
        return False
    # RCEP + CPFT modifications: there's one RiO table in the mix
    return tablename == progargs.full_prognotes_table


def get_rio_pk_col_patient_table(table):
    if table.name.startswith('UserAssess'):
        default = RIO_COL_USER_ASSESS_DEFAULT_PK
    else:
        default = RIO_COL_DEFAULT_PK
    pkcol = RIO_6_2_ATYPICAL_PKS.get(table.name, default)
    # log.debug("get_rio_pk_col: {} -> {}".format(table.name, pkcol))
    return pkcol


def get_rio_patient_id_col(table):
    patient_id_col = RIO_6_2_ATYPICAL_PATIENT_ID_COLS.get(table.name,
                                                          RIO_COL_PATIENT_ID)
    # log.debug("get_rio_patient_id_col: {} -> {}".format(table.name,
    #                                                     patient_id_col))
    return patient_id_col


def get_rio_pk_col_nonpatient_table(table):
    if RIO_COL_DEFAULT_PK in table.columns.keys():
        default = RIO_COL_DEFAULT_PK
    else:
        default = None
    return RIO_6_2_ATYPICAL_PKS.get(table.name, default)


def process_patient_table(table, engine, progargs):
    log.info("Patient table: '{}'".format(table.name))
    rio_type = table_is_rio_type(table.name, progargs)
    if rio_type:
        rio_pk = get_rio_pk_col_patient_table(table)
        string_pt_id = get_rio_patient_id_col(table)
        required_cols = [string_pt_id]
    else:  # RCEP type
        rio_pk = None
        required_cols = [RCEP_COL_PATIENT_ID]
        string_pt_id = RCEP_COL_PATIENT_ID
    if not progargs.print:
        required_cols.extend([CRATE_COL_PK, CRATE_COL_RIO_NUMBER])
    # -------------------------------------------------------------------------
    # Add pk and rio_number columns, if not present
    # -------------------------------------------------------------------------
    if rio_type and rio_pk is not None:
        crate_pk_type = 'INTEGER'  # can't do NOT NULL; need to populate it
        required_cols.append(rio_pk)
    else:  # RCEP type, or no PK in RiO
        crate_pk_type = AUTONUMBER_COLTYPE  # autopopulates
    add_columns(engine, table, {
        CRATE_COL_PK: crate_pk_type,
        CRATE_COL_RIO_NUMBER: 'INTEGER',
    })

    # -------------------------------------------------------------------------
    # Update pk and rio_number values, if not NULL
    # -------------------------------------------------------------------------
    ensure_columns_present(engine, table=table, column_names=required_cols)
    log.info("Table '{}': updating columns '{}' and '{}'".format(
        table.name, CRATE_COL_PK, CRATE_COL_RIO_NUMBER))
    cast_id_to_int = sql_fragment_cast_to_int(string_pt_id)
    if rio_type and rio_pk:
        execute(engine, """
            UPDATE {tablename} SET
                {crate_pk} = {rio_pk},
                {crate_rio_number} = {cast_id_to_int}
            WHERE
                {crate_pk} IS NULL
                OR {crate_rio_number} IS NULL
        """.format(
            tablename=table.name,
            crate_pk=CRATE_COL_PK,
            rio_pk=rio_pk,
            crate_rio_number=CRATE_COL_RIO_NUMBER,
            cast_id_to_int=cast_id_to_int,
        ))
    else:
        # RCEP format, or RiO with no PK
        # crate_pk is autogenerated as an INT IDENTITY field
        execute(engine, """
            UPDATE {tablename} SET
                {crate_rio_number} = {cast_id_to_int}
            WHERE
                {crate_rio_number} IS NULL
        """.format(  # noqa
            tablename=table.name,
            crate_rio_number=CRATE_COL_RIO_NUMBER,
            cast_id_to_int=cast_id_to_int,
        ))
    """
    Chucked:
        ensure_columns_present(... RCEP_COL_MANGLED_KEY...)

        {pk} = CAST(
            SUBSTRING(
                {rcep_mangled_pk},
                CHARINDEX('_', {rcep_mangled_pk}) + 1,
                LEN({rcep_mangled_pk}) - CHARINDEX('_', {rcep_mangled_pk})
            ) AS INTEGER
        ),

        # pk=CRATE_COL_PK,
        # rcep_mangled_pk=RCEP_COL_MANGLED_KEY,
    """
    # -------------------------------------------------------------------------
    # Add indexes, if absent
    # -------------------------------------------------------------------------
    # Note that the indexes are unlikely to speed up the WHERE NOT NULL search
    # above, so it doesn't matter that we add these last. Their use is for
    # the subsequent CRATE anonymisation table scans.
    add_indexes(engine, table, [
        {
            'index_name': CRATE_IDX_PK,
            'column': CRATE_COL_PK,
            'unique': True,
        },
        {
            'index_name': CRATE_IDX_RIONUM,
            'column': CRATE_COL_RIO_NUMBER,
        },
    ])


def drop_for_patient_table(table, engine):
    drop_indexes(engine, table, [CRATE_IDX_PK, CRATE_IDX_RIONUM])
    drop_columns(engine, table, [CRATE_COL_PK, CRATE_COL_RIO_NUMBER])


def process_nonpatient_table(table, engine, progargs):
    if progargs.rcep:
        return
    pk_col = get_rio_pk_col_nonpatient_table(table)
    if pk_col:
        add_columns(engine, table, {CRATE_COL_PK: 'INTEGER'})
    else:
        add_columns(engine, table, {CRATE_COL_PK: AUTONUMBER_COLTYPE})
    if not progargs.print:
        ensure_columns_present(engine, table=table,
                               column_names=[CRATE_COL_PK])
    if pk_col:
        execute(engine, """
            UPDATE {tablename} SET {crate_pk} = {rio_pk}
            WHERE {crate_pk} IS NULL
        """.format(tablename=table.name,
                   crate_pk=CRATE_COL_PK,
                   rio_pk=pk_col))
    add_indexes(engine, table, [{'index_name': CRATE_IDX_PK,
                                 'column': CRATE_COL_PK,
                                 'unique': True}])


def drop_for_nonpatient_table(table, engine):
    drop_indexes(engine, table, [CRATE_IDX_PK])
    drop_columns(engine, table, [CRATE_COL_PK])


# =============================================================================
# Specific table processors
# =============================================================================

def process_master_patient_table(table, engine, progargs):
    add_columns(engine, table, {CRATE_COL_NHS_NUMBER: 'BIGINT'})
    if progargs.rcep:
        nhscol = RCEP_COL_NHS_NUMBER
    else:
        nhscol = RIO_COL_NHS_NUMBER
    log.info("Table '{}': updating column '{}'".format(table.name, nhscol))
    ensure_columns_present(engine, table=table, column_names=[nhscol])
    if not progargs.print:
        ensure_columns_present(engine, table=table, column_names=[
            CRATE_COL_NHS_NUMBER])
    execute(engine, """
        UPDATE {tablename} SET
            {nhs_number_int} = CAST({nhscol} AS BIGINT)
            WHERE {nhs_number_int} IS NULL
    """.format(
        tablename=table.name,
        nhs_number_int=CRATE_COL_NHS_NUMBER,
        nhscol=nhscol,
    ))


def drop_for_master_patient_table(table, engine):
    drop_columns(engine, table, [CRATE_COL_NHS_NUMBER])


def process_progress_notes(table, engine, progargs):
    add_columns(engine, table, {
        CRATE_COL_MAX_SUBNUM: 'INTEGER',
        CRATE_COL_LAST_NOTE: 'INTEGER',
    })
    # We're always in "RiO land", not "RCEP land", for this one.
    add_indexes(engine, table, [
        {  # Joint index, for JOIN in UPDATE statement below
            'index_name': CRATE_IDX_RIONUM_NOTENUM,
            'column': '{rio_number}, NoteNum'.format(
                rio_number=CRATE_COL_RIO_NUMBER),
        },
        {  # Speeds up WHERE below. (Much, much faster for second run.)
            'index_name': CRATE_IDX_MAX_SUBNUM,
            'column': CRATE_COL_MAX_SUBNUM,
        },
        {  # Speeds up WHERE below. (Much, much faster for second run.)
            'index_name': CRATE_IDX_LAST_NOTE,
            'column': CRATE_COL_LAST_NOTE,
        },
    ])

    ensure_columns_present(engine, table=table, column_names=[
        "NoteNum", "SubNum", "EnteredInError", "EnteredInError"])
    if not progargs.print:
        ensure_columns_present(engine, table=table, column_names=[
            CRATE_COL_MAX_SUBNUM, CRATE_COL_LAST_NOTE, CRATE_COL_RIO_NUMBER])

    # Find the maximum SubNum for each note, and store it.
    # Slow query, even with index.
    log.info("Progress notes table '{}': updating '{}'".format(
        table.name, CRATE_COL_MAX_SUBNUM))
    execute(engine, """
        UPDATE p1
        SET p1.{max_subnum_col} = subq.max_subnum
        FROM {tablename} p1 JOIN (
            SELECT {rio_number}, NoteNum, MAX(SubNum) AS max_subnum
            FROM {tablename} p2
            GROUP BY {rio_number}, NoteNum
        ) subq
        ON subq.{rio_number} = p1.{rio_number}
        AND subq.NoteNum = p1.NoteNum
        WHERE p1.{max_subnum_col} IS NULL
    """.format(
        max_subnum_col=CRATE_COL_MAX_SUBNUM,
        tablename=table.name,
        rio_number=CRATE_COL_RIO_NUMBER,
    ))

    # Set a single column accordingly
    log.info("Progress notes table '{}': updating '{}'".format(
        table.name, CRATE_COL_LAST_NOTE))
    execute(engine, """
        UPDATE {tablename} SET
            {last_note_col} =
                CASE
                    WHEN SubNum = {max_subnum_col} THEN 1
                    ELSE 0
                END
        WHERE {last_note_col} IS NULL
    """.format(
        tablename=table.name,
        last_note_col=CRATE_COL_LAST_NOTE,
        max_subnum_col=CRATE_COL_MAX_SUBNUM,
    ))

    # Create a view, if we're on an RCEP database
    if progargs.rcep and progargs.cpft:
        select_sql = """
            SELECT *
            FROM {tablename}
            WHERE
                (EnteredInError <> 1 OR EnteredInError IS NULL)
                AND {last_note_col} = 1
        """.format(
            tablename=table.name,
            last_note_col=CRATE_COL_LAST_NOTE,
        )
        create_view(engine, VIEW_RCEP_CPFT_PROGRESS_NOTES_CURRENT, select_sql)


def drop_for_progress_notes(table, engine):
    drop_view(engine, VIEW_RCEP_CPFT_PROGRESS_NOTES_CURRENT)
    drop_indexes(engine, table, [CRATE_IDX_RIONUM_NOTENUM,
                                 CRATE_IDX_MAX_SUBNUM,
                                 CRATE_IDX_LAST_NOTE])
    drop_columns(engine, table, [CRATE_COL_MAX_SUBNUM,
                                 CRATE_COL_LAST_NOTE])


def process_clindocs_table(table, engine, progargs):
    # For RiO only, not RCEP
    add_columns(engine, table, {
        CRATE_COL_MAX_DOCVER: 'INTEGER',
        CRATE_COL_LAST_DOC: 'INTEGER',
    })
    add_indexes(engine, table, [
        {
            'index_name': CRATE_IDX_RIONUM_SERIALNUM,
            'column': '{rio_number}, SerialNumber'.format(
                rio_number=CRATE_COL_RIO_NUMBER),
        },
        {
            'index_name': CRATE_IDX_MAX_DOCVER,
            'column': CRATE_COL_MAX_DOCVER,
        },
        {
            'index_name': CRATE_IDX_LAST_DOC,
            'column': CRATE_COL_LAST_DOC,
        },
    ])

    required_cols = ["SerialNumber", "RevisionID"]
    if not progargs.print:
        required_cols.extend([CRATE_COL_MAX_DOCVER,
                              CRATE_COL_LAST_DOC,
                              CRATE_COL_RIO_NUMBER])
    ensure_columns_present(engine, table=table, column_names=required_cols)

    # Find the maximum SerialNumber for each note, and store it.
    # Slow query, even with index.
    log.info("Clinical documents table '{}': updating '{}'".format(
        table.name, CRATE_COL_MAX_DOCVER))
    execute(engine, """
        UPDATE p1
        SET p1.{max_docver_col} = subq.max_docver
        FROM {tablename} p1 JOIN (
            SELECT {rio_number}, SerialNumber, MAX(RevisionID) AS max_docver
            FROM {tablename} p2
            GROUP BY {rio_number}, SerialNumber
        ) subq
        ON subq.{rio_number} = p1.{rio_number}
        AND subq.SerialNumber = p1.SerialNumber
        WHERE p1.{max_docver_col} IS NULL
    """.format(
        max_docver_col=CRATE_COL_MAX_DOCVER,
        tablename=table.name,
        rio_number=CRATE_COL_RIO_NUMBER,
    ))

    # Set a single column accordingly
    log.info("Clinical documents table '{}': updating '{}'".format(
        table.name, CRATE_COL_LAST_DOC))
    execute(engine, """
        UPDATE {tablename} SET
            {last_doc_col} =
                CASE
                    WHEN RevisionID = {max_docver_col} THEN 1
                    ELSE 0
                END
        WHERE {last_doc_col} IS NULL
    """.format(
        tablename=table.name,
        last_doc_col=CRATE_COL_LAST_DOC,
        max_docver_col=CRATE_COL_MAX_DOCVER,
    ))


def drop_for_clindocs_table(table, engine):
    drop_indexes(engine, table, [CRATE_IDX_RIONUM_SERIALNUM,
                                 CRATE_IDX_MAX_DOCVER,
                                 CRATE_IDX_LAST_DOC])
    drop_columns(engine, table, [CRATE_COL_MAX_DOCVER,
                                 CRATE_COL_LAST_DOC])


# =============================================================================
# RiO view creators: generic
# =============================================================================

def simple_lookup_join(viewmaker, basecolumn,
                       lookup_table, lookup_pk, lookup_fields_aliases,
                       internal_alias_prefix):
    assert basecolumn, "Missing basecolumn"
    assert lookup_table, "Missing lookup_table"
    assert lookup_pk, "Missing lookup_pk"
    assert lookup_fields_aliases, "lookup_fields_aliases column_prefix"
    assert internal_alias_prefix, "Missing internal_alias_prefix"
    aliased_table = internal_alias_prefix + "_" + lookup_table
    for column, alias in lookup_fields_aliases.items():
        viewmaker.add_select("{aliased_table}.{column} AS {alias}".format(
            aliased_table=aliased_table, column=column, alias=alias))
    viewmaker.add_from(
        "LEFT JOIN {lookup_table} {aliased_table}\n"
        "            ON {aliased_table}.{lookup_pk} = "
        "{basetable}.{basecolumn}".format(
            lookup_table=lookup_table,
            aliased_table=aliased_table,
            lookup_pk=lookup_pk,
            basetable=viewmaker.basetable,
            basecolumn=basecolumn))
    viewmaker.record_lookup_table_keyfield(lookup_table, lookup_pk)


def standard_rio_code_lookup(viewmaker, basecolumn, lookup_table,
                             column_prefix, internal_alias_prefix):
    assert basecolumn, "Missing basecolumn"
    assert lookup_table, "Missing lookup_table"
    assert column_prefix, "Missing column_prefix"
    assert internal_alias_prefix, "Missing internal_alias_prefix"
    aliased_table = internal_alias_prefix + "_" + lookup_table
    viewmaker.add_select("""
        {basetable}.{basecolumn} AS {cp}_Code,
        {aliased_table}.CodeDescription AS {cp}_Description
    """.format(  # noqa
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        cp=column_prefix,
        aliased_table=aliased_table,
    ))
    lookup_pk = 'Code'
    viewmaker.add_from(
        "LEFT JOIN {lookup_table} {aliased_table}\n"
        "            ON {aliased_table}.{lookup_pk} = "
        "{basetable}.{basecolumn}".format(
            lookup_table=lookup_table,
            aliased_table=aliased_table,
            lookup_pk=lookup_pk,
            basetable=viewmaker.basetable,
            basecolumn=basecolumn))
    viewmaker.record_lookup_table_keyfield(lookup_table, lookup_pk)


def standard_rio_code_lookup_with_national_code(
        viewmaker, basecolumn, lookup_table,
        column_prefix, internal_alias_prefix):
    assert basecolumn, "Missing basecolumn"
    assert lookup_table, "Missing lookup_table"
    assert column_prefix, "Missing column_prefix"
    assert internal_alias_prefix, "Missing internal_alias_prefix"
    aliased_table = internal_alias_prefix + "_" + lookup_table
    viewmaker.add_select("""
        {basetable}.{basecolumn} AS {cp}_Code,
        {aliased_table}.CodeDescription AS {cp}_Description,
        {aliased_table}.NationalCode AS {cp}_National_Code
    """.format(  # noqa
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        cp=column_prefix,
        aliased_table=aliased_table,
    ))
    lookup_pk = 'Code'
    viewmaker.add_from(
        "LEFT JOIN {lookup_table} {aliased_table}\n"
        "            ON {aliased_table}.{lookup_pk} = "
        "{basetable}.{basecolumn}".format(
            lookup_table=lookup_table,
            aliased_table=aliased_table,
            lookup_pk=lookup_pk,
            basetable=viewmaker.basetable,
            basecolumn=basecolumn))
    viewmaker.record_lookup_table_keyfield(lookup_table, lookup_pk)


def view_formatting_dict(viewmaker):
    return {
        'basetable': viewmaker.basetable,
    }


def simple_view_expr(viewmaker, expr, alias):
    assert expr, "Missing expr"
    assert alias, "Missing alias"
    vd = view_formatting_dict(viewmaker)
    formatted_expr = expr.format(**vd)
    viewmaker.add_select(formatted_expr + " AS {}".format(alias))


def simple_view_where(viewmaker, where_clause, index_cols=None):
    assert where_clause, "Missing where_clause"
    index_cols = index_cols or []
    viewmaker.add_where(where_clause)
    for col in index_cols:
        viewmaker.record_lookup_table_keyfield(viewmaker.basetable, col)


def get_rio_views(engine, progargs, ddhint,
                  suppress_basetables=True, suppress_lookup=True):
    # ddhint modified
    # Returns dictionary of {viewname: select_sql} pairs.
    views = {}
    all_tables_lower = get_table_names(engine, to_lower=True)
    all_views_lower = get_view_names(engine, to_lower=True)
    all_selectables_lower = list(set(all_tables_lower + all_views_lower))
    for viewname, viewdetails in RIO_VIEWS.items():
        basetable = viewdetails['basetable']
        if basetable.lower() not in all_selectables_lower:
            log.warning("Skipping view {} as base table/view {} not "
                        "present".format(viewname, basetable))
            continue
        suppress_basetable = viewdetails.get('suppress_basetable',
                                             suppress_basetables)
        suppress_other_tables = viewdetails.get('suppress_other_tables', [])
        if suppress_basetable:
            ddhint.suppress_table(basetable)
        ddhint.suppress_tables(suppress_other_tables)
        rename = viewdetails.get('rename', None)
        # noinspection PyTypeChecker
        viewmaker = ViewMaker(engine, basetable,
                              rename=rename, progargs=progargs)
        if 'add' in viewdetails:
            for addition in viewdetails['add']:
                function = addition['function']
                kwargs = addition.get('kwargs', {})
                kwargs['viewmaker'] = viewmaker
                function(**kwargs)  # will alter viewmaker
        if progargs.audit_info:
            rio_add_audit_info(viewmaker)  # will alter viewmaker
        views[viewname] = viewmaker.get_sql()
        if suppress_lookup:
            ddhint.suppress_tables(viewmaker.get_lookup_tables())
        ddhint.add_bulk_source_index_request(
            viewmaker.get_lookup_table_keyfields())
    return views


def create_rio_views(engine, metadata, progargs, ddhint):  # ddhint modified
    rio_views = get_rio_views(engine, progargs, ddhint)
    for viewname, select_sql in rio_views.items():
        create_view(engine, viewname, select_sql)
    ddhint.add_indexes(engine, metadata)


def drop_rio_views(engine, metadata, progargs, ddhint):  # ddhint modified
    rio_views = get_rio_views(engine, progargs, ddhint)
    ddhint.drop_indexes(engine, metadata)
    for viewname, _ in rio_views.items():
        drop_view(engine, viewname)


# =============================================================================
# RiO view creators: specific
# =============================================================================

def rio_add_user_lookup(viewmaker, basecolumn,
                        column_prefix=None, internal_alias_prefix=None):
    # NOT VERIFIED IN FULL - insufficient data with just top 1000 rows for
    # each table (2016-07-12).
    assert basecolumn, "Missing basecolumn"
    column_prefix = column_prefix or basecolumn
    internal_alias_prefix = internal_alias_prefix or "t_" + column_prefix
    # ... table alias
    viewmaker.add_select("""
        {basetable}.{basecolumn} AS {cp}_Code,

        {ap}_genhcp.ConsultantFlag AS {cp}_Consultant_Flag,

        {ap}_genperson.Email AS {cp}_Email,
        {ap}_genperson.Title AS {cp}_Title,
        {ap}_genperson.FirstName AS {cp}_First_Name,
        {ap}_genperson.Surname AS {cp}_Surname,

        {ap}_prof.Code AS {cp}_Responsible_Clinician_Profession_Code,
        {ap}_prof.CodeDescription AS {cp}_Responsible_Clinician_Profession_Description,

        {ap}_serviceteam.Code AS {cp}_Primary_Team_Code,
        {ap}_serviceteam.CodeDescription AS {cp}_Primary_Team_Description,

        {ap}_genspec.Code AS {cp}_Main_Specialty_Code,
        {ap}_genspec.CodeDescription AS {cp}_Main_Specialty_Description,
        {ap}_genspec.NationalCode AS {cp}_main_specialty_national_code,

        {ap}_profgroup.Code AS {cp}_Professional_Group_Code,
        {ap}_profgroup.CodeDescription AS {cp}_Professional_Group_Description,

        {ap}_genorg.Code AS {cp}_Organisation_Type_Code,
        {ap}_genorg.CodeDescription AS {cp}_Organisation_Type_Description
    """.format(  # noqa
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        cp=column_prefix,
        ap=internal_alias_prefix,
    ))
    # - RECP had "speciality" / "specialty" inconsistency.
    # - {cp}_location... ?? Presumably from GenLocation, but via what? Seems
    #   meaningless. In our snapshut, all are NULL anyway.
    # - User codes are keyed to GenUser.GenUserID, but also to several other
    #   tables, e.g. GenHCP.GenHCPCode; GenPerson.GenPersonID
    # - We use unique table aliases here, so that overall we can make >1 sets
    #   of different "user" joins simultaneously.
    viewmaker.add_from("""
        LEFT JOIN (
            GenUser {ap}_genuser
            LEFT JOIN GenPerson {ap}_genperson
                ON {ap}_genperson.GenPersonID = {ap}_genuser.GenUserID
            LEFT JOIN GenHCP {ap}_genhcp
                ON {ap}_genhcp.GenHCPCode = {ap}_genuser.GenUserID
            LEFT JOIN GenHCPRCProfession {ap}_prof
                ON {ap}_prof.Code = {ap}_genhcp.RCProfession
            LEFT JOIN GenServiceTeam {ap}_serviceteam
                ON {ap}_serviceteam.Code = {ap}_genhcp.PrimaryTeam
            LEFT JOIN GenSpecialty {ap}_genspec
                ON {ap}_genspec.Code = {ap}_genhcp.MainGenSpecialtyCode
            LEFT JOIN GenStaffProfessionalGroup {ap}_profgroup
                ON {ap}_profgroup.Code = {ap}_genhcp.StaffProfessionalGroup
            LEFT JOIN GenOrganisationType {ap}_genorg
                ON {ap}_genorg.Code = {ap}_genuser.OrganisationType
        ) ON {ap}_genuser.GenUserID = {basetable}.{basecolumn}
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        ap=internal_alias_prefix,
    ))
    # OTHER THINGS:
    # - GenHCP.Occupation is listed in the RiO docs but doesn't actually seem
    #   to exist. (Perhaps explaining why it's not linked in the RCEP output.)
    #   I had tried to link it to CareCoordinatorOccupation.Code.
    #   If you use:
    #       SELECT *
    #       FROM information_schema.columns
    #       WHERE column_name LIKE '%Occup%'
    #   you only get Client_Demographic_Details.Occupation and
    #   Client_Demographic_Details.Partner_Occupation
    viewmaker.record_lookup_table_keyfields([
        ('GenHCP', 'GenHCPCode'),
        ('GenUser', 'GenUserID'),
        ('GenPerson', 'GenPersonID'),
        ('GenHCPRCProfession', 'Code'),
        ('GenServiceTeam', 'Code'),
        ('GenSpecialty', 'Code'),
        ('GenStaffProfessionalGroup', 'Code'),
        ('GenOrganisationType', 'Code'),
    ])


def rio_add_consultant_lookup(viewmaker, basecolumn,
                              column_prefix=None, internal_alias_prefix=None):
    assert basecolumn, "Missing basecolumn"
    column_prefix = column_prefix or basecolumn
    internal_alias_prefix = internal_alias_prefix or "t_" + column_prefix
    viewmaker.add_select("""
        {basetable}.{basecolumn} AS {cp}_ID,
        {ap}_cons.Firstname AS {cp}_First_Name,
        {ap}_cons.Surname AS {cp}_Surname,
        {ap}_cons.SpecialtyID AS {cp}_Specialty_Code,
        {ap}_spec.CodeDescription AS {cp}_Specialty_Description
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        cp=column_prefix,
        ap=internal_alias_prefix,
    ))
    viewmaker.add_from("""
        LEFT JOIN (
            GenHospitalConsultant {ap}_cons
            LEFT JOIN GenSpecialty {ap}_spec
                ON {ap}_spec.Code = {ap}_cons.SpecialtyID
        ) ON {ap}_cons.ConsultantID = {basetable}.{basecolumn}
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        ap=internal_alias_prefix,
    ))
    viewmaker.record_lookup_table_keyfields([
        ('GenHospitalConsultant', 'ConsultantID'),
        ('GenSpecialty', 'Code'),
    ])


def rio_add_team_lookup(viewmaker, basecolumn,
                        column_prefix=None, internal_alias_prefix=None):
    assert basecolumn, "Missing basecolumn"
    column_prefix = column_prefix or basecolumn
    internal_alias_prefix = internal_alias_prefix or "t_" + column_prefix
    viewmaker.add_select("""
        {basetable}.{basecolumn} AS {cp}_Code,
        {ap}_team.CodeDescription AS {cp}_Description,
        {ap}_classif.Code AS {cp}_Classification_Group_Code,
        {ap}_classif.CodeDescription AS {cp}_Classification_Group_Description
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        cp=column_prefix,
        ap=internal_alias_prefix,
    ))
    viewmaker.add_from("""
        LEFT JOIN (
            GenServiceTeam {ap}_team
            INNER JOIN GenServiceTeamClassification {ap}_classif
                ON {ap}_classif.Code = {ap}_team.ClassificationGroup
        ) ON {basetable}.{basecolumn} = {ap}_team.Code
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        ap=internal_alias_prefix,
    ))
    viewmaker.record_lookup_table_keyfields([
        ('GenServiceTeam', 'Code'),
        ('GenServiceTeamClassification', 'Code'),
    ])


def rio_add_carespell_lookup(viewmaker, basecolumn,
                             column_prefix=None, internal_alias_prefix=None):
    assert basecolumn, "Missing basecolumn"
    column_prefix = column_prefix or basecolumn
    internal_alias_prefix = internal_alias_prefix or "t_" + column_prefix
    viewmaker.add_select("""
        {basetable}.{basecolumn} AS {cp}_Number,
        {ap}_spell.StartDate AS {cp}_Start_Date,
        {ap}_spell.EndDate AS {cp}_End_Date,
        {ap}_spell.MentalHealth AS {cp}_Mental_Health,
        {ap}_spell.GenSpecialtyCode AS {cp}_Specialty_Code,
        {ap}_spec.CodeDescription AS {cp}_Specialty_Description,
        {ap}_spec.NationalCode AS {cp}_Specialty_National_Code
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        cp=column_prefix,
        ap=internal_alias_prefix,
    ))
    viewmaker.add_from("""
        LEFT JOIN (
            ClientCareSpell {ap}_spell
            INNER JOIN GenSpecialty {ap}_spec
                ON {ap}_spec.Code = {ap}_spell.GenSpecialtyCode
        ) ON {basetable}.{basecolumn} = {ap}_spell.CareSpellNum
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        ap=internal_alias_prefix,
    ))
    viewmaker.record_lookup_table_keyfields([
        ('ClientCareSpell', 'CareSpellNum'),
        ('GenSpecialty', 'Code'),
    ])


def rio_add_diagnosis_lookup(viewmaker,
                             basecolumn_scheme, basecolumn_code,
                             alias_scheme, alias_code, alias_description,
                             internal_alias_prefix=None):
    # Can't use simple_lookup_join as we have to join on two fields,
    # diagnostic scheme and diagnostic code.
    assert basecolumn_scheme, "Missing basecolumn_scheme"
    assert basecolumn_code, "Missing basecolumn_code"
    assert alias_scheme, "Missing alias_scheme"
    assert alias_code, "Missing alias_code"
    assert alias_description, "Missing alias_description"
    assert internal_alias_prefix, "Missing internal_alias_prefix"
    internal_alias_prefix = internal_alias_prefix or "t"
    viewmaker.add_select("""
        {basetable}.{basecolumn_scheme} AS {alias_scheme},
        {basetable}.{basecolumn_code} AS {alias_code},
        {ap}_diag.CodeDescription AS {alias_description}
    """.format(
        basetable=viewmaker.basetable,
        basecolumn_scheme=basecolumn_scheme,
        alias_scheme=alias_scheme,
        basecolumn_code=basecolumn_code,
        alias_code=alias_code,
        ap=internal_alias_prefix,
        alias_description=alias_description,
    ))
    # - RECP had "speciality" / "specialty" inconsistency.
    # - {cp}_location... ?? Presumably from GenLocation, but via what? Seems
    #   meaningless. In our snapshut, all are NULL anyway.
    # - User codes are keyed to GenUser.GenUserID, but also to several other
    #   tables, e.g. GenHCP.GenHCPCode; GenPerson.GenPersonID
    # - We use unique table aliases here, so that overall we can make >1 sets
    #   of different "user" joins simultaneously.
    viewmaker.add_from("""
        LEFT JOIN DiagnosisCode {ap}_diag
            ON {ap}_diag.CodingScheme = {basetable}.{basecolumn_scheme}
            AND {ap}_diag.Code = {basetable}.{basecolumn_code}
    """.format(
        basetable=viewmaker.basetable,
        basecolumn_scheme=basecolumn_scheme,
        basecolumn_code=basecolumn_code,
        ap=internal_alias_prefix,
    ))
    viewmaker.record_lookup_table_keyfield('DiagnosisCode', ['CodingScheme',
                                                             'Code'])


def rio_add_ims_event_lookup(viewmaker, basecolumn_event_num,
                             column_prefix, internal_alias_prefix):
    # There is a twin key: ClientID and EventNumber
    # However, we have made crate_rio_number, so we'll use that instead.
    # Key to the TABLE, not the VIEW.
    assert basecolumn_event_num, "Missing basecolumn_event_num"
    assert column_prefix, "Missing column_prefix"
    assert internal_alias_prefix, "Missing internal_alias_prefix"
    viewmaker.add_select("""
        {basetable}.{basecolumn_event_num} AS {cp}_Event_Number,
        {ap}_evt.{CRATE_COL_PK} AS {cp}_Inpatient_Stay_PK
    """.format(
        basetable=viewmaker.basetable,
        basecolumn_event_num=basecolumn_event_num,
        cp=column_prefix,
        ap=internal_alias_prefix,
        CRATE_COL_PK=CRATE_COL_PK,
    ))
    viewmaker.add_from("""
        LEFT JOIN ImsEvent {ap}_evt
            ON {ap}_evt.{CRATE_COL_RIO_NUMBER} = {basetable}.{CRATE_COL_RIO_NUMBER}
            AND {ap}_evt.EventNumber = {basetable}.{basecolumn_event_num}
    """.format(  # noqa
        basetable=viewmaker.basetable,
        ap=internal_alias_prefix,
        CRATE_COL_RIO_NUMBER=CRATE_COL_RIO_NUMBER,
        basecolumn_event_num=basecolumn_event_num,
    ))
    viewmaker.record_lookup_table_keyfield('ImsEvent', [CRATE_COL_RIO_NUMBER,
                                                        'EventNumber'])


def rio_add_gp_lookup(viewmaker, basecolumn,
                      column_prefix, internal_alias_prefix):
    assert basecolumn, "Missing basecolumn"
    assert column_prefix, "Missing column_prefix"
    assert internal_alias_prefix, "Missing internal_alias_prefix"
    viewmaker.add_select("""
        {basetable}.{basecolumn} AS {cp}_Code,
        {ap}_gp.CodeDescription AS {cp}_Description,
        {ap}_gp.NationalCode AS {cp}_National_Code,
        {ap}_gp.Title AS {cp}_Title,
        {ap}_gp.Forename AS {cp}_Forename,
        {ap}_gp.Surname AS {cp}_Surname
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        cp=column_prefix,
        ap=internal_alias_prefix,
    ))
    viewmaker.add_from("""
        LEFT JOIN GenGP {ap}_gp
            ON {ap}_gp.Code = {basetable}.{basecolumn}
    """.format(
        ap=internal_alias_prefix,
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
    ))
    viewmaker.record_lookup_table_keyfield('GenGP', 'Code')


def rio_add_gp_practice_lookup(viewmaker, basecolumn,
                               column_prefix, internal_alias_prefix):
    assert basecolumn, "Missing basecolumn"
    assert column_prefix, "Missing column_prefix"
    assert internal_alias_prefix, "Missing internal_alias_prefix"
    viewmaker.add_select("""
        {basetable}.{basecolumn} AS {cp}_Code,
        {ap}_prac.CodeDescription AS {cp}_Description,
        {ap}_prac.AddressLine1 AS {cp}_Address_Line_1,
        {ap}_prac.AddressLine2 AS {cp}_Address_Line_2,
        {ap}_prac.AddressLine3 AS {cp}_Address_Line_3,
        {ap}_prac.AddressLine4 AS {cp}_Address_Line_4,
        {ap}_prac.AddressLine5 AS {cp}_Address_Line_5,
        {ap}_prac.PostCode AS {cp}_Post_Code,
        {ap}_prac.NationalCode AS {cp}_National_Code
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        cp=column_prefix,
        ap=internal_alias_prefix,
    ))
    viewmaker.add_from("""
        LEFT JOIN GenGPPractice {ap}_prac
            ON {ap}_prac.Code = {basetable}.{basecolumn}
    """.format(
        ap=internal_alias_prefix,
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
    ))
    viewmaker.record_lookup_table_keyfield('GenGPPractice', 'Code')


def rio_add_gp_lookup_with_practice(viewmaker, basecolumn,
                                    column_prefix, internal_alias_prefix):
    assert basecolumn, "Missing basecolumn"
    assert internal_alias_prefix, "Missing internal_alias_prefix"
    if column_prefix:
        column_prefix += '_'
    viewmaker.add_select("""
        {basetable}.{basecolumn} AS {cp}GP_Code,
        {ap}_gp.CodeDescription AS {cp}GP_Description,
        {ap}_gp.NationalCode AS {cp}GP_National_Code,
        {ap}_gp.Title AS {cp}GP_Title,
        {ap}_gp.Forename AS {cp}GP_Forename,
        {ap}_gp.Surname AS {cp}GP_Surname,
        {ap}_prac.Code AS {cp}Practice_Code,
        {ap}_prac.CodeDescription AS {cp}Practice_Description,
        {ap}_prac.AddressLine1 AS {cp}Practice_Address_Line_1,
        {ap}_prac.AddressLine2 AS {cp}Practice_Address_Line_2,
        {ap}_prac.AddressLine3 AS {cp}Practice_Address_Line_3,
        {ap}_prac.AddressLine4 AS {cp}Practice_Address_Line_4,
        {ap}_prac.AddressLine5 AS {cp}Practice_Address_Line_5,
        {ap}_prac.PostCode AS {cp}Practice_Post_Code,
        {ap}_prac.NationalCode AS {cp}Practice_National_Code
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        cp=column_prefix,
        ap=internal_alias_prefix,
    ))
    viewmaker.add_from("""
        LEFT JOIN (
            GenGP {ap}_gp
            INNER JOIN GenGPGPPractice  -- linking table
                ON GenGPPractice.GenGPCode = {ap}_gp.Code
            INNER JOIN GenGPPractice {ap}_prac
                ON {ap}_prac.Code = GenGPPractice.GenPracticeCode
        ) ON {ap}_gp.Code = {basetable}.{basecolumn}
    """.format(
        ap=internal_alias_prefix,
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
    ))
    viewmaker.record_lookup_table_keyfields([
        ('GenGP', 'Code'),
        ('GenGPPractice', 'Code'),
        ('GenGPGPPractice', 'GenGPCode'),
    ])


def where_prognotes_current(viewmaker):
    if not viewmaker.progargs.prognotes_current_only:
        return
    viewmaker.add_where(
        "(EnteredInError <> 1 OR EnteredInError IS NULL) "
        "AND {last_note_col} = 1".format(last_note_col=CRATE_COL_LAST_NOTE))
    viewmaker.record_lookup_table_keyfield(viewmaker.basetable,
                                           'EnteredInError')
    # CRATE_COL_LAST_NOTE already indexed


def where_clindocs_current(viewmaker):
    if not viewmaker.progargs.clindocs_current_only:
        return
    viewmaker.add_where("{last_doc_col} = 1 AND DeletedDate IS NULL".format(
        last_doc_col=CRATE_COL_LAST_DOC))
    viewmaker.record_lookup_table_keyfield(viewmaker.basetable, 'DeletedDate')
    # CRATE_COL_LAST_DOC already indexed


def where_allergies_current(viewmaker):
    if not viewmaker.progargs.allergies_current_only:
        return
    viewmaker.add_where("Deleted = 0 OR Deleted IS NULL")
    viewmaker.record_lookup_table_keyfield(viewmaker.basetable, 'Deleted')


def where_not_deleted_flag(viewmaker, basecolumn):
    assert basecolumn, "Missing basecolumn"
    viewmaker.add_where(
        "({table}.{col} IS NULL OR {table}.{col} = 0)".format(
            table=viewmaker.basetable, col=basecolumn))
    viewmaker.record_lookup_table_keyfield(viewmaker.basetable, basecolumn)


def rio_add_bay_lookup(viewmaker, basecolumn_ward, basecolumn_bay,
                       column_prefix, internal_alias_prefix):
    assert basecolumn_ward, "Missing basecolumn_ward"
    assert basecolumn_bay, "Missing basecolumn_bay"
    assert internal_alias_prefix, "Missing internal_alias_prefix"
    if column_prefix:
        column_prefix += '_'
    viewmaker.add_select("""
        {basetable}.{basecolumn_ward} AS {cp}Ward_Code,
        {ap}_ward.WardDescription AS {cp}Ward_Description,
        {basetable}.{basecolumn_bay} AS {cp}Bay_Code,
        {ap}_bay.BayDescription AS {cp}Bay_Description
    """.format(
        basetable=viewmaker.basetable,
        basecolumn_ward=basecolumn_ward,
        basecolumn_bay=basecolumn_bay,
        cp=column_prefix,
        ap=internal_alias_prefix,
    ))
    viewmaker.add_from("""
        LEFT JOIN (
            ImsBay {ap}_bay
            INNER JOIN ImsWard {ap}_ward
                ON {ap}_ward.WardCode = {ap}_bay.WardCode
        ) ON {ap}_bay.WardCode = {basetable}.{basecolumn_ward}
            AND {ap}_bay.BayCode = {basetable}.{basecolumn_bay}
    """.format(
        ap=internal_alias_prefix,
        basetable=viewmaker.basetable,
        basecolumn_ward=basecolumn_ward,
        basecolumn_bay=basecolumn_bay,
    ))
    viewmaker.record_lookup_table_keyfield('ImsBay', ['WardCode', 'BayCode'])
    viewmaker.record_lookup_table_keyfield('ImsWard', ['WardCode'])


def rio_add_location_lookup(viewmaker, basecolumn,
                            column_prefix, internal_alias_prefix):
    assert basecolumn, "Missing basecolumn"
    assert column_prefix, "Missing column_prefix"
    assert internal_alias_prefix, "Missing internal_alias_prefix"
    viewmaker.add_select("""
        {basetable}.{basecolumn} AS {cp}_Code,
        {ap}_loc.CodeDescription AS {cp}_Description,
        {ap}_loc.NationalCode AS {cp}_National_Code,
        {ap}_loc.AddressLine1 as {cp}_Address_1,
        {ap}_loc.AddressLine2 as {cp}_Address_2,
        {ap}_loc.AddressLine3 as {cp}_Address_3,
        {ap}_loc.AddressLine4 as {cp}_Address_4,
        {ap}_loc.AddressLine5 as {cp}_Address_5,
        {ap}_loc.Postcode as {cp}_Post_Code,
        {ap}_loc.LocationType as {cp}_Type_Code,
        {ap}_loctype.CodeDescription as {cp}_Type_Description,
        {ap}_loctype.NationalCode as {cp}_Type_National_Code
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        cp=column_prefix,
        ap=internal_alias_prefix,
    ))
    viewmaker.add_from("""
        LEFT JOIN (
            GenLocation {ap}_loc
            INNER JOIN GenLocationType {ap}_loctype
                ON {ap}_loctype.Code = {ap}_loc.LocationType
        ) ON {ap}_loc.Code = {basetable}.{basecolumn}
    """.format(  # noqa
        ap=internal_alias_prefix,
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
    ))
    viewmaker.record_lookup_table_keyfield('GenLocation', ['Code'])
    viewmaker.record_lookup_table_keyfield('GenLocationType', ['Code'])


def rio_add_org_contact_lookup(viewmaker, basecolumn,
                               column_prefix, internal_alias_prefix):
    assert basecolumn, "Missing basecolumn"
    assert column_prefix, "Missing column_prefix"
    viewmaker.add_select("""
        {basetable}.{basecolumn} AS {cp}_ID,
        {ap}_con.ContactType AS {cp}_Contact_Type_Code,
        {ap}_ct.CodeDescription AS {cp}_Contact_Type_Description,
        {ap}_ct.NationalCode AS {cp}_Contact_Type_National_Code,
        {ap}_con.Title AS {cp}_Title,
        {ap}_con.FirstName AS {cp}_First_Name,
        {ap}_con.Surname AS {cp}_Surname,
        {ap}_con.JobTitle AS {cp}_Job_Title,
        {ap}_con.MainPhoneNo AS {cp}_Main_Phone_Number,
        {ap}_con.OtherPhoneNo AS {cp}_Other_Phone_Number,
        {ap}_con.FaxNo AS {cp}_Fax_Number,
        {ap}_con.EmailAddress AS {cp}_Email_Address,
        {ap}_con.Comments AS {cp}_Comments,
        {ap}_con.OrganisationID AS {cp}_Organisation_ID,
        {ap}_org.OrganisationCode AS {cp}_Organisation_Code,
        {ap}_org.OrganisationName AS {cp}_Organisation_Name,
        {ap}_org.OrganisationType AS {cp}_Organisation_Type_Code,
        {ap}_orgtype.CodeDescription AS {cp}_Organisation_Type_Description,
        {ap}_org.DepartmentName AS {cp}_Organisation_Department_Name,
        {ap}_org.MainPhoneNo AS {cp}_Organisation_Main_Phone_Number,
        {ap}_org.OtherPhoneNo AS {cp}_Organisation_Other_Phone_Number,
        {ap}_org.FaxNo AS {cp}_Organisation_Fax_Number,
        {ap}_org.EmailAddress AS {cp}_Organisation_Email_Address,
        {ap}_org.AddressLine1 AS {cp}_Organisation_Address_Line_1,
        {ap}_org.AddressLine2 AS {cp}_Organisation_Address_Line_2,
        {ap}_org.AddressLine3 AS {cp}_Organisation_Address_Line_3,
        {ap}_org.AddressLine4 AS {cp}_Organisation_Address_Line_4,
        {ap}_org.AddressLine5 AS {cp}_Organisation_Address_Line_5,
        {ap}_org.PostCode AS {cp}_Organisation_Post_Code
    """.format(
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
        cp=column_prefix,
        ap=internal_alias_prefix,
    ))
    # Phone/fax/email/comments not in RCEP
    viewmaker.add_from("""
        LEFT JOIN (
            OrgContact {ap}_con
            INNER JOIN OrgContactType {ap}_ct
                ON {ap}_ct.Code = {ap}_con.ContactType
            INNER JOIN OrgOrganisation {ap}_org
                ON {ap}_org.SequenceID = {ap}_con.OrganisationID  -- ?
            INNER JOIN OrgType {ap}_orgtype
                ON {ap}_orgtype.Code = {ap}_org.OrganisationType
        ) ON {ap}_con.OrganisationID = {basetable}.{basecolumn}
    """.format(
        ap=internal_alias_prefix,
        basetable=viewmaker.basetable,
        basecolumn=basecolumn,
    ))
    viewmaker.record_lookup_table_keyfields([
        ('OrgContact', 'OrganisationID'),
        ('OrgContactType', 'Code'),
        ('OrgOrganisation', 'SequenceID'),
        ('OrgType', 'Code'),
    ])


def rio_amend_standard_noncore(viewmaker):
    # Add user:
    rio_add_user_lookup(viewmaker, "type12_UpdatedBy",
                        column_prefix="Updated_By", internal_alias_prefix="ub")
    # Omit deleted:
    viewmaker.add_where("type12_DeletedDate IS NULL")
    viewmaker.record_lookup_table_keyfield(viewmaker.basetable,
                                           'type12_DeletedDate')


def rio_noncore_yn(viewmaker, basecolumn, result_alias):
    # 1 = yes, 2 = no
    # ... clue: "pregnant?" for males, in UserAssesstfkcsa.expectQ
    assert basecolumn, "Missing basecolumn"
    assert result_alias, "Missing result_alias"
    viewmaker.add_select(
        "CASE "
        "WHEN {basetable}.{basecolumn} = 1 THEN 1 "  # 1 = yes
        "WHEN {basetable}.{basecolumn} = 2 THEN 0 "  # 2 = no
        "ELSE NULL "
        "END "
        "AS {result_alias}".format(
            basetable=viewmaker.basetable,
            basecolumn=basecolumn,
            result_alias=result_alias,
        )
    )


def rio_add_audit_info(viewmaker):
    # - In RCEP: lots of tables have Created_Date, Updated_Date with no source
    #   column; likely from audit table.
    # - Here: Audit_Created_Date, Audit_Updated_Date
    ap1 = "_au_cr"
    ap2 = "_au_up"
    viewmaker.add_select("""
        {ap1}_subq.Audit_Created_Date AS Audit_Created_Date,
        {ap2}_subq.Audit_Updated_Date AS Audit_Updated_Date
    """.format(
        ap1=ap1,
        ap2=ap2,
    ))
    viewmaker.add_from("""
        LEFT JOIN (
            SELECT {ap1}_audit.RowID,
                MIN({ap1}_audit.ActionDateTime) AS Audit_Created_Date
            FROM AuditTrail {ap1}_audit
            INNER JOIN GenTable {ap1}_table
                ON {ap1}_table.TableNumber = {ap1}_audit.TableNumber
            WHERE {ap1}_table.GenTableCode = {literal}
                AND {ap1}_audit.AuditAction = 2  -- INSERT
            GROUP BY {ap1}_audit.RowID
        ) {ap1}_subq
            ON {ap1}_subq.RowID = {basetable}.{CRATE_COL_PK}
        LEFT JOIN (
            SELECT {ap2}_audit.RowID,
                MAX({ap2}_audit.ActionDateTime) AS Audit_Updated_Date
            FROM AuditTrail {ap2}_audit
            INNER JOIN GenTable {ap2}_table
                ON {ap2}_table.TableNumber = {ap2}_audit.TableNumber
            WHERE {ap2}_table.GenTableCode = {literal}
                AND {ap2}_audit.AuditAction = 3  -- UPDATE
            GROUP BY {ap2}_audit.RowID
        ) {ap2}_subq
            ON {ap2}_subq.RowID = {basetable}.{CRATE_COL_PK}
    """.format(
        ap1=ap1,
        ap2=ap2,
        basetable=viewmaker.basetable,
        literal=sql_string_literal(viewmaker.basetable),
        CRATE_COL_PK=CRATE_COL_PK,
    ))
    viewmaker.record_lookup_table_keyfields([
        ('AuditTrail', ['AuditAction', 'RowID', 'TableNumber']),
        ('GenTable', 'GenTableCode'),
    ])
    # AuditTrail indexes based on SQL Server recommendations (Query -> Analyze
    # Query in Database Engine Tuning Advisor -> ... -> Recommendations ->
    # Index Recommendations -> Definition). Specifically:
    # CREATE STATISTICS [_dta_stat_1213247377_6_4] ON [dbo].[AuditTrail](
    #     [TableNumber], [AuditAction])
    # CREATE STATISTICS [_dta_stat_1213247377_5_4] ON [dbo].[AuditTrail](
    #     [RowID], [AuditAction])
    # CREATE NONCLUSTERED INDEX [_dta_index_AuditTrail_blahblah]
    #     ON [dbo].[AuditTrail] 
    # (
    # 	[AuditAction] ASC,
    # 	[RowID] ASC,
    # 	[TableNumber] ASC
    # )
    # INCLUDE ( [ActionDateTime]) WITH (SORT_IN_TEMPDB = OFF,
    #     IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF) ON [PRIMARY]


# =============================================================================
# RiO view creators: collection
# =============================================================================

# Quickest way to develop these: open
# 1. RiO information schema
#    SELECT *
#    FROM <databasename>.information_schema.columns
#    -- +/- WHERE column_name NOT LIKE 'crate_%'
#    ORDER BY table_name, ordinal_position
# 2. RiO data model reference guide
# 3. RCEP information schema

DEFAULT_NONCORE_RENAMES = {
    # Identifiers:
    'ClientID': None,  # we have crate_rio_number instead
    'NHSNum': None,  # not needed and would have to scrub

    # System:
    'system_ValidationData': 'system_Validation_Data',
    'ServRef': None,  # e.g. "I6337", "R47800"; ?internal reference
    'formref': None,

    # Relevant:
    'type12_NoteID': 'Note_ID',
    'type12_OriginalNoteID': 'Original_Note_ID',
    'type12_DeletedDate': 'Deleted_Date',  # also filtered on
    'type12_UpdatedBy': None,  # user lookup
    'type12_UpdatedDate': 'Updated_Date',

    # Common to all assessments:
    'AssessmentDate': 'Assessment_Date',

    # For subtables:
    'type12_RowID': 'Row_ID',
    'type12_OriginalRowID': 'Original_Row_ID',
}

RIO_VIEWS = OrderedDict([
    # An OrderedDict in case you wanted to make views from views.
    # But that is a silly idea.

    # -------------------------------------------------------------------------
    # Template
    # -------------------------------------------------------------------------

    # ('XXX', {
    #     'basetable': 'XXX',
    #     'rename': {
    #         'XXX': 'XXX',  #
    #         'XXX': None,  #
    #     },
    #     'add': [
    #         {
    #             'function': simple_view_expr,
    #             'kwargs': {
    #                 'expr': 'XXX',
    #                 'alias': 'XXX',
    #             },
    #         },
    #         {
    #             'function': simple_lookup_join,
    #             'kwargs': {
    #                 'basecolumn': 'XXX',
    #                 'lookup_table': 'XXX',
    #                 'lookup_pk': 'XXX',
    #                 'lookup_fields_aliases': {
    #                     'XXX': 'XXX',
    #                 },
    #                 'internal_alias_prefix': 'XXX',
    #             }
    #         },
    #         {
    #             'function': standard_rio_code_lookup,
    #             'kwargs': {
    #                 'basecolumn': 'XXX',
    #                 'lookup_table': 'XXX',
    #                 'column_prefix': 'XXX',
    #                 'internal_alias_prefix': 'XXX',
    #             },
    #         },
    #         {
    #             'function': standard_rio_code_lookup_with_national_code,
    #             'kwargs': {
    #                 'basecolumn': 'XXX',
    #                 'lookup_table': 'XXX',
    #                 'column_prefix': 'XXX',
    #                 'internal_alias_prefix': 'XXX',
    #             }
    #         },
    #         {
    #             'function': rio_add_user_lookup,
    #             'kwargs': {
    #                 'basecolumn': 'XXX',
    #                 'column_prefix': 'XXX',
    #                 'internal_alias_prefix': 'XXX',
    #             },
    #         },
    #         {
    #             'function': rio_add_consultant_lookup,
    #             'kwargs': {
    #                 'basecolumn': 'XXX',
    #                 'column_prefix': 'XXX',
    #                 'internal_alias_prefix': 'XXX',
    #             },
    #         },
    #         {
    #             'function': rio_add_team_lookup,
    #             'kwargs': {
    #                 'basecolumn': 'XXX',
    #                 'column_prefix': 'XXX',
    #                 'internal_alias_prefix': 'XXX',
    #             },
    #         },
    #         {
    #             'function': rio_add_carespell_lookup,
    #             'kwargs': {
    #                 'basecolumn': 'XXX',
    #                 'column_prefix': 'XXX',
    #                 'internal_alias_prefix': 'XXX',
    #             },
    #         },
    #         {
    #             'function': rio_add_diagnosis_lookup,
    #             'kwargs': {
    #                 'basecolumn_scheme': 'XXX',
    #                 'basecolumn_code': 'XXX',
    #                 'alias_scheme': 'XXX',
    #                 'alias_code': 'XXX',
    #                 'alias_description': 'XXX',
    #                 'internal_alias_prefix': 'XXX',
    #             }
    #         },
    #         {
    #             'function': rio_add_ims_event_lookup,
    #             'kwargs': {
    #                 'basecolumn_event_num': 'XXX',
    #                 'column_prefix': 'XXX',
    #                 'internal_alias_prefix': 'XXX',
    #             },
    #         },
    #         {
    #             'function': rio_add_gp_lookup,
    #             'kwargs': {
    #                 'basecolumn': 'XXX',
    #                 'column_prefix': 'XXX',
    #                 'internal_alias_prefix': 'XXX',
    #             },
    #         },
    #         {
    #             'function': rio_add_bay_lookup,
    #             'kwargs': {
    #                 'basecolumn_ward': 'XXX',
    #                 'basecolumn_bay': 'XXX',
    #                 'column_prefix': 'XXX',
    #                 'internal_alias_prefix': 'XXX',
    #             },
    #         },
    #         {
    #             'function': rio_add_location_lookup,
    #             'kwargs': {
    #                 'basecolumn': 'XXX',
    #                 'column_prefix': 'XXX',
    #                 'internal_alias_prefix': 'XXX',
    #             },
    #         },
    #         {
    #             'function': simple_view_where,
    #             'kwargs': {
    #                 'where_clause': 'XXX',
    #                 'index_cols': [],
    #             },
    #         },
    #     ],
    #     'suppress_basetable': True,
    #     'suppress_other_tables': [],
    # }),

    # -------------------------------------------------------------------------
    # Core: views provided by RCEP (with some extensions)
    # -------------------------------------------------------------------------

    # 'assessmentsCRISSpec' is RCEP internal for CRIS tree/form/field/... info

    ('Care_Plan_Index', {
        'basetable': 'CarePlanIndex',
        'rename': {
            'CarePlanID': 'Care_Plan_ID',  # RCEP
            'StartDate': 'Start_Date',  # RCEP
            'EndDate': 'End_Date',  # RCEP
            'StartUserID': None,  # user lookup
            'EndUserID': None,  # user lookup
            'EndReason': None,  # "Obsolete field"
            'CarePlanType': None,  # lookup below
        },
        'add': [
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'StartUserID',
                    'column_prefix': 'Start_User',  # RCEP
                    'internal_alias_prefix': 'su',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'EndUserID',
                    'column_prefix': 'End_User',  # RCEP
                    'internal_alias_prefix': 'eu',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'CarePlanType',
                    'lookup_table': 'CarePlanType',
                    'column_prefix': 'Care_Plan_Type',  # RCEP
                    'internal_alias_prefix': 'cpt',
                },
            },
        ],
    }),

    ('Care_Plan_Interventions', {
        'basetable': 'CarePlanInterventions',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'ProblemID': 'Problem_FK_Care_Plan_Problems',  # RCEP: Problem_Key
            'InterventionID': 'Intervention_Key',  # RCEP; non-unique
            'Box1': 'Box_1',  # not in RCEP
            'Box2': 'Box_2',  # not in RCEP
            'Box3': 'Box_3',  # not in RCEP
            'Box4': 'Box_4',  # not in RCEP
            'Box5': 'Box_5',  # not in RCEP
            'Box6': 'Box_6',  # not in RCEP
            'StartDate': 'Start_Date',  # RCEP
            'EndDate': 'End_Date',  # RCEP
            'UserID': None,  # user lookup
            'EntryDate': 'Entry_Date',  # RCEP
            'InterventionType': None,  # lookup below
            'OutCome': None,  # lookup below
            # Comment: unchanged
            'Picklist1Code': 'Picklist_1_Code',  # not in RCEP
            'Picklist1Description': 'Picklist_1_Description',  # not in RCEP
            'Picklist2Code': 'Picklist_2_Code',  # not in RCEP
            'Picklist2Description': 'Picklist_2_Description',  # not in RCEP
            'Picklist3Code': 'Picklist_3_Code',  # not in RCEP
            'Picklist3Description': 'Picklist_3_Description',  # not in RCEP
            'DateField1': 'Date_Field_1',  # not in RCEP
            'DateField2': 'Date_Field_2',  # not in RCEP
            'LibraryID': 'Library_ID',  # not in RCEP
            'LibraryEdited': 'Library_Edited',  # not in RCEP
            'SequenceID': 'Unique_Key',  # RCEP
            'InterventionCategory': None,  # lookup below
            'CheckBox1': 'Check_Box_1',  # not in RCEP
            'CheckBox2': 'Check_Box_2',  # not in RCEP
        },
        'add': [
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'UserID',
                    'column_prefix': 'User',  # RCEP
                    'internal_alias_prefix': 'u',
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'InterventionType',
                    'lookup_table': 'CarePlanInterventionTypes',
                    'column_prefix': 'Intervention_Type',
                    # ... RCEP, except RCEP had InterventionType_Code
                    'internal_alias_prefix': 'it',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'Outcome',
                    'lookup_table': 'CarePlanInterventionOutcomes',
                    'column_prefix': 'Outcome',  # RCEP
                    'internal_alias_prefix': 'od',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'InterventionCategory',
                    'lookup_table': 'CarePlanInterventionCategory',
                    'column_prefix': 'Intervention_Category',  # RCEP
                    'internal_alias_prefix': 'ic',
                },
            },
        ],
    }),

    ('Care_Plan_Problems', {
        'basetable': 'CarePlanProblems',
        'rename': {
            'ProblemID': 'Problem_ID',  # RCEP
            'CarePlanID': 'Care_Plan_ID_FK_Care_Plan_Index',  # RCEP: was Care_Plan_ID  # noqa
            'Text': 'Text',  # RCEP
            'StartDate': 'Start_Date',  # RCEP
            'EndDate': 'End_Date',  # RCEP
            'UserID': None,  # user lookup
            'EntryDate': 'Entry_Date',  # RCEP
            'ProblemType': None,  # lookup below
            'OutCome': None,  # lookup below
            # Comment: unchanged
            'LibraryID': 'Library_ID',  # not in RCEP
            'LibraryEdited': 'Library_Edited',  # not in RCEP
            'SequenceID': 'Unique_Key',  # RCEP
            'ProblemCategory': None,  # lookup below
            'ProblemDate': 'Problem_Date',  # RCEP; not in RiO 6.2 docs
        },
        'add': [
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'UserID',
                    'column_prefix': 'User',  # RCEP
                    'internal_alias_prefix': 'u',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'ProblemType',
                    'lookup_table': 'CarePlanProblemTypes',
                    'column_prefix': 'Problem_Type',  # RCEP
                    'internal_alias_prefix': 'pt',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'OutCome',
                    'lookup_table': 'CarePlanProblemOutcomes',
                    'column_prefix': 'Outcome',  # RCEP
                    'internal_alias_prefix': 'oc',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'ProblemCategory',
                    'lookup_table': 'CarePlanProblemCategory',
                    'column_prefix': 'Problem_Category',  # RCEP
                    'internal_alias_prefix': 'pc',
                },
            },
        ],
    }),

    ('Client_Address_History', {
        'basetable': VIEW_ADDRESS_WITH_GEOGRAPHY,  # original: 'ClientAddress'
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'FromDate': 'Address_From_Date',  # RCEP
            'ToDate': 'Address_To_Date',  # RCEP
            'AddressLine1': 'Address_Line_1',  # RCEP
            'AddressLine2': 'Address_Line_2',  # RCEP
            'AddressLine3': 'Address_Line_3',  # RCEP
            'AddressLine4': 'Address_Line_4',  # RCEP
            'AddressLine5': 'Address_Line_5',  # RCEP
            'PostCode': 'Post_Code',  # RCEP
            'ElectoralWard': None,  # lookup below
            'MailsortCode': 'Mailsort_Code',  # RCEP
            'PrimaryCareGroup': None,  # lookup below
            'HealthAuthority': None,  # lookup below
            'SequenceID': 'Unique_Key',  # RCEP
            'LastUpdated': 'Last_Updated',  # RCEP
            'AddressType': None,  # lookup below
            'AccommodationType': None,  # lookup below
            'AddressGroup': 'Address_Group',  # RCEP; ?nature; RiO docs wrong
            'PAFKey': None,  # NHS Spine interaction field
            'SpineID': None,  # NHS Spine interaction field
        },
        'add': [
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'ElectoralWard',
                    'lookup_table': 'GenElectoralWard',
                    'column_prefix': 'Electoral_Ward',
                    'internal_alias_prefix': 'ew',
                    # ... RCEP: code was Electoral_Ward and description absent
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'PrimaryCareGroup',
                    'lookup_table': 'GenPCG',
                    'column_prefix': 'Primary_Care_Group',
                    # ... RCEP: code was Primary_Care_Group and descr. absent
                    'internal_alias_prefix': 'pcg',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'HealthAuthority',
                    'lookup_table': 'GenHealthAuthority',
                    'column_prefix': 'Health_Authority',
                    # ... RCEP: code was Health_Authority and descr. absent
                    'internal_alias_prefix': 'ha',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'AddressType',
                    'lookup_table': 'GenAddressType',
                    'column_prefix': 'Address_Type',  # RCEP
                    'internal_alias_prefix': 'adt',
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'AccommodationType',
                    'lookup_table': 'GenAccommodationType',
                    'column_prefix': 'Accommodation_Type',
                    # ... RCEP, though National_Code added
                    'internal_alias_prefix': 'act',
                },
            },
        ],
    }),

    ('Client_Alternative_ID', {
        # IDs on other systems
        'basetable': 'ClientAlternativeID',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'SystemID': None,  # lookup below
            'ID': 'ID',  # RCEP; this is the foreign ID
            'SequenceID': 'Unique_Key',  # RCEP
        },
        'add': [
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'SystemID',
                    'lookup_table': 'GenOtherSystem',
                    'column_prefix': 'System',
                    'internal_alias_prefix': 'sys',
                    # RCEP: was SystemID (code), System (description)
                },
            },
        ],
    }),

    ('Client_Allergies', {
        'basetable': 'EPClientAllergies',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'ReactionID': 'Unique_Key',  # RCEP; INT
            'UserID': None,  # user lookup; VARCHAR(15)
            # Substance: unchanged, RCEP; VARCHAR(255)
            'ReactionType': 'Reaction_Type_ID',  # and lookup below; INT
            # Reaction: unchanged, RCEP; VARCHAR(255)
            'ReactionSeverity': 'Reaction_Severity_ID',  # not RCEP; lookup below; INT  # noqa
            'ReportedBy': 'Reported_By_ID',  # and lookup below; INT
            'Name': 'Name',  # RCEP; think this is "reported by" name; VARCHAR(50)  # noqa
            'WitnessingHCP': 'Witnessing_HCP',  # RCEP; VARCHAR(50)
            'YearOfIdentification': 'Year_Of_Identification',  # RCEP; INT
            # Comment: unchanged, RCEP; VARCHAR(500)
            # Deleted: unchanged, RCEP; BIT
            'DeletionReason': 'Deletion_Reason_ID',  # not in RCEP; INT
            'DeletedBy': None,  # user lookup; VARCHAR(15)
            'RemovalDate': 'Removal_Date',  # RCEP; DATETIME
        },
        'add': [
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'UserID',
                    'column_prefix': 'Entered_By',  # RCEP
                    'internal_alias_prefix': 'eb',
                },
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'ReactionType',
                    'lookup_table': 'EPReactionType',
                    'lookup_pk': 'ReactionID',
                    'lookup_fields_aliases': {
                        'Code': 'Reaction_Type_Code',
                        'CodeDescription': 'Reaction_Type_Description',
                        # ... all RCEP
                    },
                    'internal_alias_prefix': 'rt',
                }
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'ReactionSeverity',
                    'lookup_table': 'EPSeverity',
                    'lookup_pk': 'SeverityID',
                    'lookup_fields_aliases': {
                        'Code': 'Reaction_Severity_Code',
                        'CodeDescription': 'Reaction_Severity_Description',
                        # ... all RCEP
                    },
                    'internal_alias_prefix': 'rs',
                }
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'ReportedBy',
                    # RCEP code is Reported_By; NB error in RiO docs AND RCEP;
                    # code is INT ranging from 1-4
                    'lookup_table': 'EPReportedBy',
                    'lookup_pk': 'ReportedID',  # not Code!
                    'lookup_fields_aliases': {
                        'Code': 'Reported_By_Code',
                        'CodeDescription': 'Reported_By_Description',
                    },
                    'internal_alias_prefix': 'rb',
                }
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'DeletionReason',
                    'lookup_table': 'EPClientAllergyRemovalReason',
                    'lookup_pk': 'RemovalID',
                    'lookup_fields_aliases': {
                        'Code': 'Deletion_Reason_Code',  # not in RCEP
                        'Reason': 'Deletion_Reason_Description',  # not in RCEP
                    },
                    'internal_alias_prefix': 'dr',
                }
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'DeletedBy',
                    'column_prefix': 'Deleted_By',  # RCEP
                    'internal_alias_prefix': 'db',
                },
            },
            {
                # Restrict to current allergies only?
                'function': where_allergies_current,
            },
        ],
    }),

    ('Client_Communications_History', {
        'basetable': 'ClientTelecom',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'ClientTelecomID': 'Unique_Key',  # RCEP
            'Detail': 'Contact_Details',  # RCEP; may be phone no. or email addr
            'ContactMethod': None,  # lookup below
            'Context': None,  # lookup below
            'StartDate': 'Valid_From',  # RCEP
            'EndDate': 'Valid_To',  # RCEP
            'SpineID': None,  # omitted in RCEP
        },
        'add': [
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'ContactMethod',
                    'lookup_table': 'GenTelecomContactMethod',
                    'column_prefix': 'Method',  # RCEP
                    'internal_alias_prefix': 'cm',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'Context',
                    'lookup_table': 'GenTelecomContext',
                    'column_prefix': 'Context',  # RCEP
                    'internal_alias_prefix': 'cx',
                },
            },
            # Extras for CRATE anonymisation:
            {
                'function': simple_view_expr,
                'kwargs': {
                    'expr': 'CASE WHEN (ContactMethod = 1 OR ContactMethod = 2'
                            ' OR ContactMethod = 4) THEN Detail ELSE NULL END',
                    # 1 = telephone; 2 = fax; 4 = minicom/textphone
                    'alias': 'crate_telephone',
                },
            },
            {
                'function': simple_view_expr,
                'kwargs': {
                    'expr': 'CASE WHEN ContactMethod = 3 THEN Detail '
                            'ELSE NULL END',
                    'alias': 'crate_email_address',
                },
            },
        ],
    }),

    ('Client_CPA', {
        'basetable': 'CPAClientCPA',
        'rename': {
            'SequenceID': 'Unique_Key',  # RCEP
            'StartDate': 'Start_Date',  # RCEP
            'EndDate': 'End_Date',  # RCEP
            'ChangedBy': None,  # user lookup
            'EndReason': 'End_Reason_Code',  # RCEP
            'NextReviewDate': 'Next_CPA_Review_Date',  # RCEP
            'CPALevel': None,  # lookup below
        },
        'add': [
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'ChangedBy',
                    'column_prefix': 'Changed_By',  # RCEP
                    'internal_alias_prefix': 'cb',
                },
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'EndReason',
                    'lookup_table': 'CPAReviewOutcomes',
                    'lookup_pk': 'Code',
                    'lookup_fields_aliases': {
                        'CodeDescription': 'End_Reason_Description',
                        'NationalCode': 'End_Reason_National_Code',
                        'DischargeFromCPA': 'End_Reason_Is_Discharge',
                        # ... all RCEP
                    },
                    'internal_alias_prefix': 'er',
                }
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'CPALevel',
                    'lookup_table': 'CPALevel',
                    'column_prefix': 'CPA_Level',
                    'internal_alias_prefix': 'lv',
                }
            },
        ],
    }),

    ('Client_Demographic_Details', {
        'basetable': 'ClientIndex',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'NNN': 'NHS_Number',  # RCEP
            # RCEP: Shared_ID = hashed NHS number (CRATE does this); skipped
            'NNNStatus': None,  # lookup below
            'AlternativeID': 'Alternative_RiO_Number',  # may always be NULL
            'Surname': None,  # always NULL; see ClientName instead
            'SurnameSoundex': None,  # always NULL; see ClientName instead
            'Firstname': None,  # always NULL; see ClientName instead
            'FirstnameSoundex': None,  # always NULL; see ClientName instead
            'Title': None,  # always NULL; see ClientName instead
            'Gender': None,  # lookup below
            # RCEP: CAMHS_National_Gender_Code: ?source
            'DateOfBirth': 'Date_Of_Birth',  # RCEP
            # Truncated_Date_of_Birth (RCEP): ignored (CRATE does this)
            'EstimatedDOB': 'Estimated_Date_Of_Birth',  # 0/1 flag
            'DaytimePhone': 'Daytime_Phone',  # not in RCEP
            'EveningPhone': 'Evening_Phone',  # not in RCEP
            'Occupation': 'Occupation',  # RCEP
            'PartnerOccupation': 'Partner_Occupation',  # RCEP
            'MaritalStatus': None,  # lookup below
            'Ethnicity': None,  # lookup below
            'Religion': None,  # lookup below
            'Nationality': None,  # lookup below
            'DateOfDeath': 'Date_Of_Death',  # RCEP
            # RCEP: comment: ?source
            'OtherAddress': None,  # Not in RCEP. Occasional (0.34%) confused mismash e.g. "Temporary Address: 1 Thing Lane, ..."; so unhelpful for anon. but identifying  # noqa
            'MotherLink': None,  # Not in RCEP. ?Always NULL. See ClientFamilyLink instead  # noqa
            'FatherLink': None,  # Not in RCEP. ?Always NULL. See ClientFamilyLink instead  # noqa
            'DateRegistered': 'Date_Registered',  # RCEP
            'EMailAddress': None,  # always NULL; see ClientTelecom instead
            'MobilePhone': None,  # always NULL; see ClientTelecom instead
            'FirstLanguage': None,  # lookup below
            'School': None,  # always NULL; see ClientSchool instead
            'NonClient': 'Non_Client',  # RCEP; 0/1 indicator
            'DiedInHospital': 'Died_In_Hospital',  # RCEP
            'MainCarer': None,  # see CAST below
            'NINumber': 'National_Insurance_Number',  # RCEP
            'DeathFlag': 'Death_Flag',  # RCEP; 0/1 indicator
            'TimeStamps': None,  # RiO internal system record-locking field (!)
            'FirstCareDate': 'Date_Of_First_Mental_Health_Care',  # RCEP
            'NNNLastTape': None,  # Not in RCEP. May refer to tape storage of NHS numbers, i.e. system internal; see NNNTape.  # noqa
            'OtherCarer': None,  # see CAST below
            'LastUpdated': 'Last_Updated',  # RCEP
            'ReportsFile': 'Reports_File',  # RCEP; 0/1 flag
            'SENFile': 'SEN_File',  # RCEP; 0/1 flag
            'Interpreter': 'Interpreter_Required',  # RCEP; 0/1 flag
            'OutPatMedAdminRecord': 'Outpatient_Medical_Admin_Record',  # 0/1 flag; RCEP was OutPatMedAdminRecord  # noqa
            'SpineID': None,  # omitted from RCEP
            'SpineSyncDate': None,  # omitted from RCEP
            'SensitiveFlag': 'Sensitive_Flag',  # RCEP
            'DeathDateNational': 'Death_Date_National',  # RCEP
            'DeathDateStatus': 'Death_Date_Status',  # RCEP
            'SupersedingNNN': 'Superseding_NHS_Number',  # RCEP
            'Deleted': 'Deleted_Flag',  # RCEP
            'PersonRole': None,  # lookup below
            'Exited': 'Exited_NHS_Care',  # RCEP was Exited; 0/1 flag
        },
        'add': [
            {
                'function': simple_view_expr,
                'kwargs': {
                    'expr': sql_fragment_cast_to_int('MainCarer'),
                    'alias': 'Main_Carer',
                    # RCEP; RiO number CROSS-REFERENCE
                },
            },
            {
                'function': simple_view_expr,
                'kwargs': {
                    'expr': sql_fragment_cast_to_int('OtherCarer'),
                    'alias': 'Other_Carer',
                    # RCEP; RiO number CROSS-REFERENCE
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'NNNStatus',
                    'lookup_table': 'NNNStatus',
                    'column_prefix': 'NNN_Status',
                    # ... RCEP except code was NNN_Status
                    'internal_alias_prefix': 'ns',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'Gender',
                    'lookup_table': 'GenGender',
                    'column_prefix': 'Gender',  # RCEP
                    'internal_alias_prefix': 'gd',
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'MaritalStatus',
                    'lookup_table': 'GenMaritalStatus',
                    'column_prefix': 'Marital_Status',
                    # RCEP, except national was National_Marital_Status_Code
                    'internal_alias_prefix': 'ms',
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'Ethnicity',
                    'lookup_table': 'GenEthnicity',
                    'column_prefix': 'Ethnicity',
                    # RCEP, except national was National_Ethnicity_Code
                    'internal_alias_prefix': 'et',
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'Religion',
                    'lookup_table': 'GenReligion',
                    'column_prefix': 'Religion',
                    # RCEP, except national was National_Religion_Code
                    'internal_alias_prefix': 're',
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'Nationality',
                    'lookup_table': 'GenNationality',
                    'column_prefix': 'Nationality',  # RCEP
                    'internal_alias_prefix': 'nt',
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'FirstLanguage',
                    'lookup_table': 'GenLanguage',
                    'column_prefix': 'First_Language',
                    # RCEP, except national was National_Language_Code
                    'internal_alias_prefix': 'la',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'PersonRole',
                    'lookup_table': 'ClientPersonRole',
                    'column_prefix': 'Person_Role',  # RCEP
                    'internal_alias_prefix': 'pr',
                },
            },
        ],
    }),

    # Ignored: ClientFamily, which has a single field (comment), with
    # probably-identifying and hard-to-anonymise-with information.

    ('Client_Family', {
        'basetable': 'ClientFamilyLink',
        'rename': {
            'RelatedClientID': None,  # see CAST below
            'Relationship': None,  # lookup below
            'ParentalResponsibility': None,  # lookup below
            'LegalStatus': None,  # lookup below
            'TempVal': None,  # Temporary_Value in RCEP, but who cares!?
            # RCEP: Comment: ?the comment from ClientFamily -- ignored
        },
        'add': [
            {
                'function': simple_view_expr,
                'kwargs': {
                    'expr': sql_fragment_cast_to_int('RelatedClientID'),
                    'alias': 'Related_Client_ID',
                    # RCEP; RiO number CROSS-REFERENCE
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'Relationship',
                    'lookup_table': 'GenFamilyRelationship',
                    'column_prefix': 'Relationship',  # RCEP
                    'internal_alias_prefix': 'rl',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'ParentalResponsibility',
                    'lookup_table': 'GenFamilyParentalResponsibility',
                    'column_prefix': 'Parental_Responsibility',  # RCEP
                    'internal_alias_prefix': 'pr',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'LegalStatus',
                    'lookup_table': 'GenFamilyLegalStatus',
                    'column_prefix': 'Legal_Status',  # RCEP
                    'internal_alias_prefix': 'ls',
                }
            },
        ],
    }),

    ('Client_GP_History', {
        # Ignored: ClientGPMerged = ?old data
        # RiO docs say ClientHealthCareProvider supersedes ClientGP
        'basetable': 'ClientHealthCareProvider',
        'rename': {
            'GPCode': None,  # lookup below
            'PracticeCode': None,  # lookup below
            'FromDate': 'GP_From_Date',  # RCEP
            'ToDate': 'GP_To_Date',  # RCEP
            # Allocation: RCEP; unchanged - but what is it?
            'PersonHCPProviderID': 'Person_HCP_Provider_ID',  # RCEP
            'LastUpdated': 'Last_Updated',  # RCEP
            # RCEP Care_Group: PCG marked defunct in RiO GenGPPractice
            'HCProviderTypeID': None,  # lookup below
            # HCProviderID: not in RCEP; unchanged
        },
        'add': [
            {
                'function': rio_add_gp_lookup,
                'kwargs': {
                    'basecolumn': 'GPCode',
                    'column_prefix': 'GP',  # RCEP with some modifications
                    'internal_alias_prefix': 'gp',
                },
            },
            {
                'function': rio_add_gp_practice_lookup,
                'kwargs': {
                    'basecolumn': 'PracticeCode',
                    'column_prefix': 'GP_Practice',  # RCEP with extras
                    'internal_alias_prefix': 'prac',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'HCProviderTypeID',
                    'lookup_table': 'GenHealthCareProviderType',
                    'column_prefix': 'Provider_Type',  # RCEP
                    'internal_alias_prefix': 'pt',
                },
            },
        ],
    }),

    ('Client_Medication', {
        # UNTESTED as no data in CPFT
        'basetable': 'EPClientMedication',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'SequenceID': 'Unique_Key',  # RCEP
            'EventNumber': 'Event_Number',  # RCEP
            'EventSequenceID': 'Event_ID',  # RCEP
            'StartDate': 'Start_Date',  # RCEP
            'RoutePrescribed': 'Route_Prescribed',  # RCEP
            'Frequency': 'Frequency_Code',  # RCEP; also lookup below
            'Units': None,  # lookup below
            'DosageComment': 'Dosage_Comment',  # RCEP
            'AdminInstructions': 'Admin_Instructions',  # CEP
            'MedicationType': None,  # lookup below
            'EndDate': 'End_Date',  # RCEP: was EndDate
            # Incomplete: unchanged, in RCEP
            'EndDateCommit': 'End_Date_Commit',  # RCEP: was EndDateCommit; 1/0
            'StartBy': None,  # user lookup
            'EndBy': None,  # user lookup
            'MinDose': 'Min_Dose',  # RCEP
            'MaxDose': 'Max_Dose',  # RCEP
            'AdminTime': 'Admin_Time',  # RCEP
            'AdminNumber': 'Admin_Number',  # RCEP
            'ConfirmText': 'Confirm_Text',  # RCEP
            'HourlyStartTime': 'Hourly_Start_Time',  # RCEP
            'DRCWarning': 'DRC_Warning',  # RCEP
            'DailyFrequency': 'Daily_Frequency_Code',  # RCEP; also lookup
            'ReasonID': 'DRC_Override_Reason_ID',  # INT; not RCEP; also lookup
            'AdministeredInError': 'Administered_In_Error_Flag',  # RCEP
            # Deleted: unchanged, in RCEP
            # Confirmed: unchanged, in RCEP
            'NumOfDays': 'Num_Of_Days',  # in RCEP
            'VTMFormulation': 'VTMFormulation',  # RCEP; VTM = Virtual Therapeutic Moieties  # noqa
        },
        'add': [
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'Frequency',
                    'lookup_table': 'EPMedicationFrequency',
                    'lookup_pk': 'Code',
                    'lookup_fields_aliases': {
                        'CodeDescription': 'Frequency_Description',
                        'Depot': 'Frequency_Is_Depot',
                        'AdminNum': 'Frequency_Admin_Number',
                        'DayInterval': 'Frequency_Day_Interval',
                        # ... all RCEP
                    },
                    'internal_alias_prefix': 'fr',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'Units',
                    'lookup_table': 'EPMedicationBaseUnits',
                    'column_prefix': 'Units',
                    # RiO docs: EPClientMedication.Units is VARCHAR(100) but
                    # also FK to EPMedicationBaseUnits.Code; is 100 a typo for
                    # 10?
                    # RCEP: Units VARCHAR(200) so who knows.
                    'internal_alias_prefix': 'un',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'MedicationType',
                    'lookup_table': 'EPMedicationType',
                    'column_prefix': 'Medication_Type',  # RCEP
                    'internal_alias_prefix': 'mt',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'StartBy',
                    'column_prefix': 'Start_By',  # RCEP
                    'internal_alias_prefix': 'sb',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'EndBy',
                    'column_prefix': 'End_By',  # RCEP
                    'internal_alias_prefix': 'eb',
                },
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'DailyFrequency',
                    'lookup_table': 'EPMedicationDailyFrequency',
                    'lookup_pk': 'Code',
                    'lookup_fields_aliases': {
                        'CodeDescription': 'Daily_Frequency_Description',
                        'AdminNum': 'Daily_Frequency_Admin_Number',
                        'AdvancedMed': 'Daily_Frequency_Advanced_Med_Flag',
                        'HourlyMed': 'Daily_Frequency_Hourly_Med_Flag',
                        'HourlyMedIntervalMinutes': 'Daily_Frequency_Hourly_Med_Interval_Minutes',  # noqa
                        # 'DisplayOrder': 'Daily_Frequency_Display_Order',
                        # ... all RCEP except AdminNum, DisplayOrder not RCEP
                        # DisplayOrder just governs order in picklist
                    },
                    'internal_alias_prefix': 'df',
                }
            },
            {  # DRC = dose range checking [override]
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'ReasonID',
                    'lookup_table': 'EPDRCOverride',  # not EPDRCOverRide
                    'lookup_pk': 'ReasonID',  # not Code (also present)
                    'lookup_fields_aliases': {
                        'Code': 'DRC_Override_Reason_Code',
                        'Reason': 'DRC_Override_Reason_Description',
                        # ... all RCEP
                        # ReasonID is INT; Code is VARCHAR(10)
                    },
                    'internal_alias_prefix': 'drc',
                }
            },
        ],
    }),

    ('Client_Name_History', {
        'basetable': 'ClientName',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'Surname': 'Family_Name',  # RCEP
            'ClientNameID': 'Unique_Key',  # RCEP
            'EffectiveDate': 'Effective_Date',  # RCEP
            'Deleted': 'Deleted_Flag',  # RCEP
            'AliasType': None,  # lookup below
            'EndDate': 'End_Date',  # RCEP: was End_Date_
            'SpineID': None,  # not in RCEP
            'Prefix': 'Title',  # RCEP
            'Suffix': 'Suffix',  # RCEP
            'GivenName1': 'Given_Name_1',  # RCEP
            'GivenName2': 'Given_Name_2',  # RCEP
            'GivenName3': 'Given_Name_3',  # RCEP
            'GivenName4': 'Given_Name_4',  # RCEP
            'GivenName5': 'Given_Name_5',  # RCEP
            'GivenName1Soundex': None,  # not in RCEP
            'GivenName2Soundex': None,  # not in RCEP
            'GivenName3Soundex': None,  # not in RCEP
            'GivenName4Soundex': None,  # not in RCEP
            'GivenName5Soundex': None,  # not in RCEP
            'SurnameSoundex': None,  # not in RCEP
        },
        'add': [
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'AliasType',
                    'lookup_table': 'ClientAliasType',
                    'column_prefix': 'Name_Type',  # RCEP
                    'internal_alias_prefix': 'al',
                },
            },
        ],
    }),

    ('Client_Personal_Contacts', {
        'basetable': 'ClientContact',
        'rename': {
            'SequenceID': 'Unique_Key',  # RCEP
            'ContactType': None,  # lookup below
            'Surname': 'Family_Name',  # RCEP
            'Firstname': 'Given_Name',  # RCEP
            'Title': 'Title',  # RCEP
            'AddressLine1': 'Address_Line_1',  # RCEP
            'AddressLine2': 'Address_Line_2',  # RCEP
            'AddressLine3': 'Address_Line_3',  # RCEP
            'AddressLine4': 'Address_Line_4',  # RCEP
            'AddressLine5': 'Address_Line_5',  # RCEP
            'PostCode': 'Post_Code',  # RCEP
            'MainPhone': 'Main_Phone',  # RCEP
            'OtherPhone': 'Other_Phone',  # RCEP
            'EMailAddress': 'Email_Address',  # RCEP was Email (inconsistent)
            'Relationship': 'Contact_Relationship_Code',  # RCEP + lookup
            'ContactComment': 'Comment',  # RCEP
            'Organisation': 'Organisation',  # VARCHAR(40); SEE NOTE 1.
            'Deleted': 'Deleted_Flag',  # RCEP
            'StartDate': 'Start_Date',  # RCEP
            'EndDate': 'End_Date',  # RCEP
            'LanguageCommunication': None,  # lookup below
            'LanguageProficiencyLevel': None,  # lookup below
            'PreferredContactMethod': None,  # lookup below
            'NHSNumber': 'NHS_Number',  # RCEP
            'SpineID': None,  # not in RCEP; spine interaction field
            'PAFKey': None,  # not in RCEP; spine interaction field [2]
            'PositionNumber': 'Position_Number',  # RCEP
            'MainContactMethod': None,  # lookup below
            'MainContext': None,  # lookup below
            'OtherContactMethod': None,  # lookup below
            'OtherContext': None,  # lookup below
            # [1] RiO's ClientContact.Organisation is VARCHAR(40).
            #   Unclear what it links to.
            #   Typical data: NULL, 'CPFT', 'Independent Living Service',
            #       'Solicitors'  - which makes it look like free text.
            #   RCEP has:
            #       - Organisation_ID VARCHAR(40)  -- looks like the link field
            #       - Organisation_Name VARCHAR(80) } all NULL in our snapshot
            #       - Organisation_Code VARCHAR(20) }
            #   Candidate RiO lookup tables are
            #       - GenOrganisation  -- only content maps RT1 to "Cambrigeshire and Peterborough..."  # noqa
            #       - OrgOrganisation  -- empty for us
            #   So I think they've screwed it up, and it's free text that
            #   RCEP is incorrectly trying to link.
            # [2] PAF Key = PAF address key, postal address file key
            #   = unique ID keyed to Royal Mail PAF Directory
            #   http://systems.hscic.gov.uk/demographics/spineconnect/spineconnectpds.pdf  # noqa
        },
        'add': [
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'ContactType',
                    'lookup_table': 'ClientContactType',
                    'column_prefix': 'Contact_Type',  # RCEP
                    'internal_alias_prefix': 'ct',
                },
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'Relationship',
                    'lookup_table': 'ClientContactRelationship',
                    'lookup_pk': 'Code',
                    'lookup_fields_aliases': {
                        'CodeDescription': 'Contact_Relationship_Description',
                        'NationalCode': 'Contact_Relationship_National_Code',
                        'FamilyRelationship': 'Family_Relationship_Flag',
                        # ... all RCEP except was
                        # National_Contact_Relationship_Code
                    },
                    'internal_alias_prefix': 'cr',
                }
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'LanguageCommunication',
                    'lookup_table': 'GenLanguage',
                    'column_prefix': 'Language',
                    # ... RCEP except was National_Language_Code
                    'internal_alias_prefix': 'la',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'LanguageProficiencyLevel',
                    'lookup_table': 'GenLanguageProficiencyLevel',
                    'column_prefix': 'Language_Proficiency',
                    # ... RCEP: code = Language_Proficiency, desc absent
                    'internal_alias_prefix': 'la',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'PreferredContactMethod',
                    'lookup_table': 'GenPreferredContactMethod',
                    'column_prefix': 'Preferred_Contact_Method',  # RCEP
                    'internal_alias_prefix': 'pcm',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'MainContactMethod',
                    'lookup_table': 'GenTelecomContactMethod',
                    'column_prefix': 'Main_Phone_Method',  # RCEP
                    'internal_alias_prefix': 'mcm',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'MainContext',
                    'lookup_table': 'GenTelecomContext',
                    'column_prefix': 'Main_Phone_Context',  # RCEP
                    'internal_alias_prefix': 'mcx',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'OtherContactMethod',
                    'lookup_table': 'GenTelecomContactMethod',
                    'column_prefix': 'Other_Phone_Method',  # RCEP
                    'internal_alias_prefix': 'ocm',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'OtherContext',
                    'lookup_table': 'GenTelecomContext',
                    'column_prefix': 'Other_Phone_Context',  # RCEP
                    'internal_alias_prefix': 'ocx',
                }
            },
        ],
    }),

    ('Client_Physical_Details', {
        'basetable': 'ClientPhysicalDetail',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            # RCEP: From_Date: ?source
            # RCEP: Last_Updated: ?source
            'Height': 'Height_m',  # RCEP was Height; definitely not cm...
            'Weight': 'Weight_kg',  # RCEP was Weight
            'Comment': 'Extra_Comment',  # RCEP
            'BloodGroup': None,  # lookup below
            'SequenceID': 'Unique_Key',  # RCEP
            'BSA': 'BSA',  # RCEP
            'BMI': 'BMI',  # RCEP
            'HeadCircumference': 'Head_Circumference',  # RCEP: HeadCircumference  # noqa
            'RecordedBy': None,  # user lookup
            'Area': None,  # lookup below
            'DateTaken': 'Date_Taken',  # RCEP
            'DateRecorded': 'Date_Recorded',  # RCEP
            'DateDeleted': 'Date_Deleted',  # RCEP
            'ParentSeqID': 'Preceding_Entry_Key',  # RCEP: ParentSeqID [1]
            'FieldName': 'System_Field_Name',  # RCEP: Field_Name
            'BSAFormulaID': 'BSA_Formula_ID',  # RCEP
            'BSAFormulaAlterationReasonID': 'BSA_Formula_Alteration_Reason_ID',  # RCEP # noqa
            # [1] ParentSeqID a silly name because (a) we've named SequenceID
            #     to UniqueKey, so users won't know what "SeqID" is, and
            #     (b) because "preceding" isn't a "parent" relationship.
        },
        'add': [
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'BloodGroup',
                    'lookup_table': 'GenBloodGroup',
                    'column_prefix': 'Blood_Group',  # RCEP
                    'internal_alias_prefix': 'bg',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'RecordedBy',
                    'column_prefix': 'Recorded_By',
                    # RCEP: Recorded_By_User_Code but rest User_*
                    'internal_alias_prefix': 'rb',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'Area',
                    'lookup_table': 'MasterTableAreaCode',
                    'column_prefix': 'System_Area',
                    # RCEP: code = Area, description absent
                    'internal_alias_prefix': 'bg',
                },
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'BSAFormulaID',
                    'lookup_table': 'EPBSAFormula',
                    'lookup_pk': 'SequenceID',
                    'lookup_fields_aliases': {
                        'Description': 'BSA_Formula_Description',
                        'Formula': 'BSA_Formula',
                        # ... all RCEP
                    },
                    'internal_alias_prefix': 'bsaf',
                }
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'BSAFormulaAlterationReasonID',
                    'lookup_table': 'EPBSAFormulaAlterationReason',
                    # ... documentation error in RiO 6.2 docs
                    'lookup_pk': 'SequenceID',
                    'lookup_fields_aliases': {
                        'Reason': 'BSA_Formula_Alteration_Reason',  # RCEP
                    },
                    'internal_alias_prefix': 'bsaf',
                }
            },
        ],
    }),

    ('Client_Prescription', {
        'basetable': 'EPClientPrescription',
        'rename': {
            'PrescriptionID': 'Unique_Key',  # RCEP
            'IssueDate': 'Issue_Date',  # RCEP
            'CourseStartDate': 'Course_Start_Date',  # RCEP
            'NumberOfDays': 'Number_Of_Days',  # RCEP
            'IssueMethod': 'Issue_Method',  # RCEP [1]
            'IssuedBy': None,  # user lookup
            'ReferralCode': 'ReferralCode',  # RCEP [2]
            'HCPCode': None,  # user lookup
            'NonIssueReason': None,  # lookup below
            'ReprintReason': 'Reprint_Reason',  # RCEP
            # 'Prescriber': None,  # user lookup
            # [1] Looks like it should be an FK, but can't see any link.
            # [2] ? FK to Referral? Unclear and not in docs.
        },
        'add': [
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'IssuedBy',
                    'column_prefix': 'HCP_User',  # RCEP
                    'internal_alias_prefix': 'ib',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'HCPCode',
                    'column_prefix': 'Issued_By',  # RCEP
                    'internal_alias_prefix': 'ihcp',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'NonIssueReason',
                    'lookup_table': 'EPPrescriptionsNonIssueReasons',
                    'column_prefix': 'Non_Issue_Reason',  # RCEP
                    'internal_alias_prefix': 'nir',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'Prescriber',
                    'column_prefix': 'Prescriber',  # RCEP
                    # .. keys to GenPerson and GenUser should be equivalent,
                    # I think
                    'internal_alias_prefix': 'pr',
                },
            },
        ],
    }),

    ('Client_Professional_Contacts', {
        'basetable': 'DemClientOtherContact',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'SequenceID': 'Unique_Key',  # RCEP
            'OrgContactID': None,  # lookup below
            'OrgContactRelationshipID': None,  # lookup below
            'FromDate': 'Effective_From_Date',  # RCEP
            'ToDate': 'Effective_To_Date',  # RCEP
            'Deleted': 'Deleted_Flag',  # RCEP
            'ClosedByDeletion': 'Closed_By_Deletion_Flag',  # RCEP
            'ContactGroup': 'Contact_Group',  # RCEP
        },
        'add': [
            {
                'function': rio_add_org_contact_lookup,
                'kwargs': {
                    'basecolumn': 'OrgContactID',
                    'column_prefix': 'Contact',
                    # ... renamed prefix from RCEP for several
                    'internal_alias_prefix': 'c',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'OrgContactRelationshipID',
                    'lookup_table': 'OrgContactRelationshipType',
                    'column_prefix': 'Relationship_Type',
                    # RCEP except description was Relationship
                    'internal_alias_prefix': 'rt',
                },
            },
        ],
    }),

    ('Client_School', {
        'basetable': 'ClientSchool',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'SequenceID': 'Unique_Key',  # RCEP
            'FromDate': 'School_From_Date',  # RCEP
            'ToDate': 'School_To_Date',  # RCEP
            'SchoolCode': 'School_Code',  # RCEP
            'ChangeReason': 'Change_Reason',  # RCEP
        },
        'add': [
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'SchoolCode',
                    'lookup_table': 'GenSchool',
                    'lookup_pk': 'Code',
                    'lookup_fields_aliases': {
                        'CodeDescription': 'School_Name',
                        'Address': 'School_Address',
                    },
                    'internal_alias_prefix': 'sc',
                }
            },
        ],
    }),

    ('CPA_Care_Coordinator', {  # RCEP: was CPA_CareCoordinator
        'basetable': 'CPACareCoordinator',
        'rename': {
            'CareCoordinatorID': None,  # user lookup below
            'StartDate': 'Start_Date',  # RCEP
            'EndDate': 'End_Date',  # RCEP
            'EndReason': None,  # lookup below
            'CPASequenceID': 'CPA_Key',  # RCEP
            'SequenceID': 'Unique_Key',  # RCEP
        },
        'add': [
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'CareCoordinatorID',
                    'column_prefix': 'Care_Coordinator',
                    'internal_alias_prefix': 'cc',
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'EndReason',
                    'lookup_table': 'CPAReviewCareSpellEnd',
                    'column_prefix': 'End_Reason',  # RCEP
                    'internal_alias_prefix': 'er',
                }
            },
        ],
    }),

    ('CPA_Review', {
        'basetable': 'CPAReviewDate',
        'rename': {
            # Created_Date: RCEP; ?source
            # Updated_Date: RCEP; ?source
            'ReviewDate': 'Review_Date',  # RCEP
            'CurrentFlag': 'Is_Current_Flag',  # RCEP
            'EndReason': None,  # lookup below
            'CPASequenceID': 'CPA_Key',  # RCEP
            'CPAReviewOutcome': 'CPA_Review_Outcome_Code',  # RCEP
            'FullHoNOS': 'Full_HoNOS',  # not in RCEP
            'ReviewType': 'Review_Type',  # RCEP
            'SWInvolved': 'Social_Worker_Involved_Flag',  # RCEP
            'DayCentreInvolved': 'Day_Centre_Involved_Flag',  # RCEP
            'ShelteredWorkInvolved': 'Sheltered_Work_Involved_Flag',  # RCEP
            'NonNHSResAccom': 'Non_NHS_Residential_Accommodation',  # RCEP
            'DomicilCareInvolved': 'Domicile_Care_Involved',  # RCEP
            'ReviewDiagnosis1': 'Review_Diagnosis_1_FK_Diagnosis',  # in RCEP, Review_Diagnosis_1, etc.  # noqa
            'ReviewDiagnosis2': 'Review_Diagnosis_2_FK_Diagnosis',
            'ReviewDiagnosis3': 'Review_Diagnosis_3_FK_Diagnosis',
            'ReviewDiagnosis4': 'Review_Diagnosis_4_FK_Diagnosis',
            'ReviewDiagnosis5': 'Review_Diagnosis_5_FK_Diagnosis',
            'ReviewDiagnosis6': 'Review_Diagnosis_6_FK_Diagnosis',
            'ReviewDiagnosis7': 'Review_Diagnosis_7_FK_Diagnosis',
            'ReviewDiagnosis8': 'Review_Diagnosis_8_FK_Diagnosis',
            'ReviewDiagnosis9': 'Review_Diagnosis_9_FK_Diagnosis',
            'ReviewDiagnosis10': 'Review_Diagnosis_10_FK_Diagnosis',
            'ReviewDiagnosis11': 'Review_Diagnosis_11_FK_Diagnosis',
            'ReviewDiagnosis12': 'Review_Diagnosis_12_FK_Diagnosis',
            'ReviewDiagnosis13': 'Review_Diagnosis_13_FK_Diagnosis',
            'ReviewDiagnosis14': 'Review_Diagnosis_14_FK_Diagnosis',
            'ReviewDiagnosisConfirmed': 'Review_Diagnosis_Confirmed_Date',  # RCEP  # noqa
            'ReviewDiagnosisBy': None,  # user lookup
            'ReferralSource': None,  # lookup below
            'CareSpellEndCode': None,  # lookup below
            'SequenceID': 'Unique_Key',  # RCEP
            'CareTeam': None,  # team lookup below
            'LastReviewDate': 'Last_Review_Date',  # RCEP
            'OtherReviewOutcome': None,  # lookup below
            'ReviewLength': 'Review_Length',  # RCEP was ReviewLength
            'Validated': 'Validated',  # RCEP
            'ThirdPartyInformation': 'Third_Party_Information',  # RCEP: was ThirdPartyInformation  # noqa
            'Text1': 'Notes_Text_1',  # not in RCEP
            'Text2': 'Notes_Text_2',  # not in RCEP
            'Text3': 'Notes_Text_3',  # not in RCEP
            'Text4': 'Notes_Text_4',  # not in RCEP
            'Text5': 'Notes_Text_5',  # not in RCEP
            'Text6': 'Notes_Text_6',  # not in RCEP
            'Text7': 'Notes_Text_7',  # not in RCEP
            'Text8': 'Notes_Text_8',  # not in RCEP
            'Text9': 'Notes_Text_9',  # not in RCEP
            'Text10': 'Notes_Text_10',  # not in RCEP
            'ScheduledRecord': 'Scheduled_Record',  # RCEP was ScheduledRecord
            'LastUpdatedBy': None,  # user lookup
            'LastUpdatedDate': 'Last_Updated_Date',  # RCEP
            'ParentSequenceID': 'Parent_Key',  # RCEP
            'AppointmentSequenceID': 'Appointment_Key',  # RCEP
            'CPAReviewPackFilename': 'CPA_Review_Pack_Filename',  # RCEP
            'LocationDescription': 'Location_Description_Text',  # RCEP
            'Section117StartDate': 'Section117_Start_Date',  # RCEP
            'Section117Continue': 'Section117_Continue',  # RCEP
            'Section117Decision': 'Section117_Decision',  # RCEP
            'ProgSequenceID': 'Progress_Note_Key',  # RCEP: was Progress__Note_Key  # noqa
            'CancellationDateTime': 'Cancellation_Date_Time',  # RCEP
            'CancellationReason': None,  # lookup below
            'CancellationBy': None,  # user lookup
            'EmploymentStatus': None,  # lookup below
            'WeeklyHoursWorked': None,  # lookup below
            'AccommodationStatus': None,  # lookup below
            'SettledAccommodationIndicator': None,  # lookup below
            'Location': None,  # location lookup
            'Section117EndDate': 'Section117_End_Date',  # RCEP
            'Section117Eligibility': 'Section117_Eligibility',  # RCEP
        },
        'add': [
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'EndReason',
                    'lookup_table': 'CPAReviewOutcomes',
                    'column_prefix': 'End_Reason',
                    # ... RCEP code was End_Reason; lookup added
                    'internal_alias_prefix': 'er',
                }
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'CPAReviewOutcome',
                    'lookup_table': 'CPAReviewCareSpellEnd',
                    'lookup_pk': 'Code',
                    'lookup_fields_aliases': {
                        'CodeDescription': 'CPA_Review_Outcome_Description',
                        'NationalCode': 'CPA_Review_Outcome_National_Code',
                        'DischargeFromCPA': 'CPA_Review_Outcome_Is_Discharge',
                        # ... all RCEP
                    },
                    'internal_alias_prefix': 'ro',
                }
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'ReviewDiagnosisBy',
                    'column_prefix': 'Review_Diagnosis_By',
                    'internal_alias_prefix': 'rdb',
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'ReferralSource',
                    'lookup_table': 'AmsReferralSource',
                    'column_prefix': 'Referral_Source',  # RCEP
                    'internal_alias_prefix': 'rs',
                }
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'CareSpellEndCode',
                    'lookup_table': 'CPAReviewCareSpellEnd',
                    'column_prefix': 'Care_Spell_End',  # RCEP
                    'internal_alias_prefix': 'cse',
                }
            },
            {
                'function': rio_add_team_lookup,
                'kwargs': {
                    'basecolumn': 'CareTeam',
                    'column_prefix': 'Care_Team',
                    'internal_alias_prefix': 'tm',
                    # ... all RCEP, except REP has Care_Team_Code and
                    # Team* for others; this has Care_Team_*
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'OtherReviewOutcome',
                    'lookup_table': 'CPAReviewOutcomes',
                    'column_prefix': 'Other_Review_Outcome',  # RCEP
                    'internal_alias_prefix': 'oro',
                }
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'LastUpdatedBy',
                    'column_prefix': 'Last_Updated_By',
                    'internal_alias_prefix': 'lub',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'CancellationReason',
                    # 'lookup_table': 'CPACancellationReasons',
                    # CPACancellationReasons has a single column, Code, which
                    # is a key to GenCancellationReason, thus making it
                    # entirely pointless (except, presumably, as a filter for
                    # data entry).
                    'lookup_table': 'GenCancellationReason',
                    'column_prefix': 'Cancellation_Reason',  # RCEP
                    'internal_alias_prefix': 'cr',
                }
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'CancellationBy',
                    'column_prefix': 'Cancellation_By',
                    'internal_alias_prefix': 'cb',
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'EmploymentStatus',
                    'lookup_table': 'GenEmpStatus',
                    'column_prefix': 'Employment_Status',  # RCEP
                    'internal_alias_prefix': 'es',
                }
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'WeeklyHoursWorked',
                    'lookup_table': 'GenWeeklyHoursWorked',
                    'column_prefix': 'Weekly_Hours_Worked',  # not in RCEP
                    # RCEP code was Weekly_Hours_Worked
                    'internal_alias_prefix': 'whw',
                }
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'AccommodationStatus',
                    'lookup_table': 'GenAccommodationStatus',
                    'column_prefix': 'Accommodation_Status',  # RCEP
                    'internal_alias_prefix': 'as',
                }
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'SettledAccommodationIndicator',
                    'lookup_table': 'GenSettledAccommodation',
                    'column_prefix': 'Settled_Accommodation_Indicator',  # RCEP
                    'internal_alias_prefix': 'sa',
                }
            },
            {
                'function': rio_add_location_lookup,
                'kwargs': {
                    'basecolumn': 'Location',
                    'column_prefix': 'Location',  # RCEP
                    'internal_alias_prefix': 'loc',
                },
            },
        ],
    }),

    ('Diagnosis', {
        'basetable': 'DiagnosisClient',
        'rename': {
            # Comment: unchanged
            # RemovalComment: unchanged
            'CodingScheme': None,  # put back in below
            'Diagnosis': None,  # becomes 'Diagnosis_Code' below
            'DiagnosisEndDate': 'Diagnosis_End_Date',  # RCEP
            'DiagnosisStartDate': 'Diagnosis_Start_Date',  # RCEP
            'EntryBy': None,  # RCEP; is user code
            'EntryDate': 'Entry_Date',
            'RemovalBy': None,  # RCEP; is user code
            'RemovalDate': 'Removal_Date',
            'RemovalReason': None,  # lookup below
        },
        'add': [
            {
                'function': rio_add_diagnosis_lookup,
                'kwargs': {
                    'basecolumn_scheme': 'CodingScheme',
                    'basecolumn_code': 'Diagnosis',
                    'alias_scheme': 'Coding_Scheme',  # RCEP: CodingScheme
                    'alias_code': 'Diagnosis_Code',  # RCEP
                    'alias_description': 'Diagnosis',  # RCEP
                    'internal_alias_prefix': 'd',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'RemovalReason',
                    'lookup_table': 'DiagnosisRemovalReason',
                    'column_prefix': 'Removal_Reason',  # RCEP
                    'internal_alias_prefix': 'rr',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'EntryBy',
                    'column_prefix': 'Entered_By',
                    'internal_alias_prefix': 'eb',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'RemovalBy',
                    'column_prefix': 'Removal_By',
                    'internal_alias_prefix': 'rb',
                },
            },
        ],
    }),

    ('Inpatient_Stay', {
        'basetable': 'ImsEvent',
        'rename': {
            # Created_Date: RCEP; ?source
            # Referrer: unchanged
            # Updated_Date: RCEP; ?source
            'AdministrativeCategory': None,  # lookup below
            'AdmissionAllocation': None,  # lookup below
            'AdmissionDate': 'Admission_Date',  # RCEP
            'AdmissionMethod': None,  # lookup below
            'AdmissionSource': None,  # lookup below
            'ClientClassification': None,  # lookup below
            'DecideToAdmitDate': 'Decide_To_Admit_Date',  # RCEP
            'DischargeAddressLine1': 'Discharge_Address_Line_1',  # RCEP
            'DischargeAddressLine2': 'Discharge_Address_Line_2',  # RCEP
            'DischargeAddressLine3': 'Discharge_Address_Line_3',  # RCEP
            'DischargeAddressLine4': 'Discharge_Address_Line_4',  # RCEP
            'DischargeAddressLine5': 'Discharge_Address_Line_5',  # RCEP
            'DischargeAllocation': None,  # lookup below
            'DischargeAwaitedReason': None,  # lookup below
            'DischargeComment': 'Discharge_Comment',  # RCEP
            'DischargeDate': 'Discharge_Date',  # RCEP
            'DischargeDestination': None,  # lookup below
            'DischargeDiagnosis1': 'Discharge_Diagnosis_1_FK_Diagnosis',  # in RCEP, DischargeDiagnosis1, etc.  # noqa
            'DischargeDiagnosis10': 'Discharge_Diagnosis_10_FK_Diagnosis',
            'DischargeDiagnosis11': 'Discharge_Diagnosis_11_FK_Diagnosis',
            'DischargeDiagnosis12': 'Discharge_Diagnosis_12_FK_Diagnosis',
            'DischargeDiagnosis13': 'Discharge_Diagnosis_13_FK_Diagnosis',
            'DischargeDiagnosis14': 'Discharge_Diagnosis_14_FK_Diagnosis',
            'DischargeDiagnosis2': 'Discharge_Diagnosis_2_FK_Diagnosis',
            'DischargeDiagnosis3': 'Discharge_Diagnosis_3_FK_Diagnosis',
            'DischargeDiagnosis4': 'Discharge_Diagnosis_4_FK_Diagnosis',
            'DischargeDiagnosis5': 'Discharge_Diagnosis_5_FK_Diagnosis',
            'DischargeDiagnosis6': 'Discharge_Diagnosis_6_FK_Diagnosis',
            'DischargeDiagnosis7': 'Discharge_Diagnosis_7_FK_Diagnosis',
            'DischargeDiagnosis8': 'Discharge_Diagnosis_8_FK_Diagnosis',
            'DischargeDiagnosis9': 'Discharge_Diagnosis_9_FK_Diagnosis',
            'DischargeDiagnosisBy': None,  # user lookup
            'DischargeDiagnosisConfirmed': 'Discharge_Diagnosis_Confirmed_Date',  # RCEP  # noqa
            'DischargeMethod': None,  # lookup below
            'DischargePostCode': 'Discharge_Post_Code',  # RCEP
            'DischargeReadyDate': 'Discharge_Ready_Date',  # RCEP
            'EventNumber': 'Event_Number',  # RCEP
            'FirstInSeries': 'First_In_Series',  # RCEP
            'HighSecurityCategory': 'High_Security_Category',  # RCEP
            'IntendedDischargeDate': 'Intended_Discharge_Date',  # RCEP
            'IntendedManagement': None,  # lookup below
            'LegalStatus': None,  # lookup below
            'ReferralID': 'Referral_ID_FK_Referral',  # Referral_ID in RCEP
            'ReferralReason': 'Referral_Reason',  # RCEP
            'ReferralRequest': None,  # present in RCEP but "no longer used" in docs  # noqa
            'ReferralSource': None,  # lookup below
            'ReferringConsultant': None,  # not in RCEP; see lookup below
            'ReferringGP': None,  # see lookup below
            'WaitingStartDateA': 'Waiting_Start_Date_A',  # RCEP
            'WaitingStartDateB': 'Waiting_Start_Date_B',  # RCEP
        },
        'add': [
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'AdmissionMethod',
                    'lookup_table': 'ImsAdmissionMethod',
                    'column_prefix': 'Admission_Method',
                    # ... in RCEP, code absent, desc = Admission_Method
                    'internal_alias_prefix': 'am',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'AdmissionSource',
                    'lookup_table': 'ImsAdmissionSource',
                    'column_prefix': 'Admission_Source',
                    # ... in RCEP, code absent, desc = Admission_Source
                    'internal_alias_prefix': 'as',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'ClientClassification',
                    'lookup_table': 'ImsClientClassification',
                    'column_prefix': 'Client_Classification',
                    # ... in RCEP, code absent, desc = Client_Classification
                    'internal_alias_prefix': 'cc',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'DischargeAwaitedReason',
                    'lookup_table': 'ImsClientClassification',
                    'column_prefix': 'Discharge_Awaited_Reason',
                    # ... in RCEP, code absent, desc = Discharge_Awaited_Reason
                    'internal_alias_prefix': 'dar',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'DischargeDestination',
                    'lookup_table': 'ImsDischargeDestination',
                    'column_prefix': 'Discharge_Destination',
                    # ... in RCEP, code absent, desc = Discharge_Destination
                    'internal_alias_prefix': 'dd',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'DischargeMethod',
                    'lookup_table': 'ImsDischargeMethod',
                    'column_prefix': 'Discharge_Method',
                    # ... in RCEP, code absent, desc = Discharge_Method
                    'internal_alias_prefix': 'dm',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'IntendedManagement',
                    'lookup_table': 'ImsIntendedManagement',
                    'column_prefix': 'Intended_Management',
                    # ... in RCEP, code absent, desc = Intended_Management
                    'internal_alias_prefix': 'im',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'AdministrativeCategory',
                    'lookup_table': 'GenAdministrativeCategory',
                    'column_prefix': 'Administrative_Category',
                    # ... in RCEP, code absent, desc = Administrative_Category
                    'internal_alias_prefix': 'ac',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'ReferralSource',
                    'lookup_table': 'AmsReferralSource',
                    'column_prefix': 'Referral_Source',
                    # ... in RCEP, code absent, desc = Referral_Source
                    'internal_alias_prefix': 'rs',
                },
            },
            {
                'function': rio_add_gp_practice_lookup,
                'kwargs': {
                    'basecolumn': 'ReferringGP',
                    'column_prefix': 'Referring_GP',
                    # RCEP + slight renaming + GP practice extras
                    'internal_alias_prefix': 'rgp',
                },
            },
            # Look up the same field two ways.
            {  # If AmsReferralSource.Behaviour = 'CS'...
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'ReferringConsultant',
                    'column_prefix': 'Referring_Consultant_Cons',
                    'internal_alias_prefix': 'rcc',
                },
            },
            {  # If AmsReferralSource.Behaviour = 'CH'...
                'function': rio_add_consultant_lookup,
                'kwargs': {
                    'basecolumn': 'ReferringConsultant',
                    'column_prefix': 'Referring_Consultant_HCP',
                    'internal_alias_prefix': 'rch',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'AdmissionAllocation',
                    'lookup_table': 'GenPCG',
                    'column_prefix': 'Admission_Allocation_PCT',
                    # ... in RCEP, code = Admission_Allocation, desc absent
                    'internal_alias_prefix': 'aa',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'DischargeAllocation',
                    'lookup_table': 'GenPCG',
                    'column_prefix': 'Discharge_Allocation_PCT',
                    # ... in RCEP, code = Discharge_Allocation, desc absent
                    'internal_alias_prefix': 'da',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'LegalStatus',
                    'lookup_table': 'ImsLegalStatusClassification',
                    'column_prefix': 'Legal_Status',
                    # ... in RCEP, code = Legal_Status, desc absent
                    'internal_alias_prefix': 'ls',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'DischargeDiagnosisBy',
                    'column_prefix': 'Discharge_Diagnosis_By',  # RCEP
                    'internal_alias_prefix': 'eb',
                },
            },
        ],
        'suppress_basetable': True,
        'suppress_other_tables': [],
    }),

    ('Inpatient_Leave', {
        'basetable': 'ImsEventLeave',
        'rename': {
            # Created_Date: RCEP ?source
            # Escorted: unchanged  # RCEP
            # Updated_Date: RCEP ?source
            'AddressLine1': 'Address_Line_1',  # RCEP
            'AddressLine2': 'Address_Line_2',  # RCEP
            'AddressLine3': 'Address_Line_3',  # RCEP
            'AddressLine4': 'Address_Line_4',  # RCEP
            'AddressLine5': 'Address_Line_5',  # RCEP
            'Deleted': 'Deleted_Flag',  # RCEP
            'EndDateTime': 'End_Date_Time',  # RCEP
            'EndedByAWOL': 'Ended_By_AWOL',  # RCEP
            'EventNumber': 'Event_Number',
            # ... RCEP; event number within this admission? Clusters near 1.
            'ExpectedReturnDateTime': 'Expected_Return_Date_Time',  # RCEP
            'LeaveEndReason': None,  # lookup below
            'LeaveType': None,  # lookup below
            'OtherInformation': 'Other_Information',  # RCEP
            'PlannedStartDateTime': 'Planned_Start_Date_Time',  # RCEP
            'PostCode': 'Post_Code',  # RCEP
            'SequenceID': 'Leave_Instance_Number',  # I think... RCEP
            'StartDateTime': 'Start_Date_Time',  # RCEP
            'UniqueSequenceID': 'Unique_Key',
        },
        'add': [
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'LeaveType',
                    'lookup_table': 'ImsLeaveType',
                    'column_prefix': 'Leave_Type',  # RCEP
                    # RCEP except code was LeaveType_Code
                    'internal_alias_prefix': 'lt',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'LeaveEndReason',
                    'lookup_table': 'ImsLeaveEndReason',
                    'column_prefix': 'Leave_End_Reason',  # RCEP
                    'internal_alias_prefix': 'lt',
                },
            },
            {
                'function': where_not_deleted_flag,
                'kwargs': {
                    'basecolumn': 'Deleted',
                },
            },
            {
                'function': rio_add_ims_event_lookup,
                'kwargs': {
                    'basecolumn_event_num': 'EventNumber',
                    'column_prefix': 'Admission',
                    'internal_alias_prefix': 'ad',
                },
            },
        ],
    }),

    ('Inpatient_Movement', {
        'basetable': 'ImsEventMovement',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'EventNumber': 'Event_Number',  # RCEP
            'SequenceID': 'Movement_Key',  # RCEP
            'StartDateTime': 'Start_Date',  # RCEP
            'EndDateTime': 'End_Date',  # RCEP
            'WardCode': None,  # Ward_Code (RCEP) is from bay lookup
            'BayCode': None,  # Bay_Code (RCEP) is from bay lookup
            'BedNumber': 'Bed',  # RCEP
            'IdentitySequenceID': 'Unique_Key',  # RCEP
            'EpisodeType': None,  # lookup below
            'PsychiatricPatientStatus': None,  # lookup below
            'Consultant': None,  # user lookup
            'Specialty': None,  # lookup below
            'OtherConsultant': None,  # user lookup
            'MovementTypeFlag': 'Movement_Type_Flag',  # RCEP
            # RCEP: Initial_Movement_Flag ?source ?extra bit flag in new RiO
            'Diagnosis1': 'Diagnosis_1_FK_Diagnosis',  # in RCEP, DischargeDiagnosis1, etc.  # noqa
            'Diagnosis10': 'Diagnosis_10_FK_Diagnosis',
            'Diagnosis11': 'Diagnosis_11_FK_Diagnosis',
            'Diagnosis12': 'Diagnosis_12_FK_Diagnosis',
            'Diagnosis13': 'Diagnosis_13_FK_Diagnosis',
            'Diagnosis14': 'Diagnosis_14_FK_Diagnosis',
            'Diagnosis2': 'Diagnosis_2_FK_Diagnosis',
            'Diagnosis3': 'Diagnosis_3_FK_Diagnosis',
            'Diagnosis4': 'Diagnosis_4_FK_Diagnosis',
            'Diagnosis5': 'Diagnosis_5_FK_Diagnosis',
            'Diagnosis6': 'Diagnosis_6_FK_Diagnosis',
            'Diagnosis7': 'Diagnosis_7_FK_Diagnosis',
            'Diagnosis8': 'Diagnosis_8_FK_Diagnosis',
            'Diagnosis9': 'Diagnosis_9_FK_Diagnosis',
            'DiagnosisConfirmed': 'Diagnosis_Confirmed_Date_Time',  # RCEP
            'DiagnosisBy': None,  # user lookup
            'Service': None,  # lookup below
            'ServiceChargeRate': 'Service_Charge_Rate',  # RCEP
        },
        'add': [
            {
                'function': rio_add_bay_lookup,
                'kwargs': {
                    'basecolumn_ward': 'WardCode',
                    'basecolumn_bay': 'BayCode',
                    'column_prefix': '',
                    # Ward_Code, Ward_Description,
                    # Bay_Code, Bay_Description as per RCEP
                    'internal_alias_prefix': 'bay',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'EpisodeType',
                    'lookup_table': 'ImsEpisodeType',
                    'column_prefix': 'Episode_Type',
                    # in RCEP, code = Episode_Type, desc absent
                    'internal_alias_prefix': 'et',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'PsychiatricPatientStatus',
                    'lookup_table': 'ImsPsychiatricPatientStatus',
                    'column_prefix': 'Psychiatric_Patient_Status',
                    # in RCEP, code = Psychiatric_Patient_Status, desc absent
                    'internal_alias_prefix': 'pp',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'Consultant',
                    'column_prefix': 'Consultant',  # RCEP
                    'internal_alias_prefix': 'co',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'OtherConsultant',
                    'column_prefix': 'Other_Consultant',  # RCEP
                    'internal_alias_prefix': 'oc',
                },
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'Specialty',
                    'lookup_table': 'GenSpecialty',
                    'column_prefix': 'Specialty',  # RCEP
                    'internal_alias_prefix': 'sp',
                }
            },
            {
                'function': simple_view_expr,
                'kwargs': {
                    # http://stackoverflow.com/questions/7778444
                    'expr': 'CAST((MovementTypeFlag & 1) AS BIT)',
                    'alias': 'Consultant_Change_Flag',
                },
            },
            {
                'function': simple_view_expr,
                'kwargs': {
                    'expr': 'CAST((MovementTypeFlag & 2) AS BIT)',
                    'alias': 'Bed_Change_Flag',
                },
            },
            {
                'function': simple_view_expr,
                'kwargs': {
                    'expr': 'CAST((MovementTypeFlag & 4) AS BIT)',
                    'alias': 'Bay_Change_Flag',
                },
            },
            {
                'function': simple_view_expr,
                'kwargs': {
                    'expr': 'CAST((MovementTypeFlag & 8) AS BIT)',
                    'alias': 'Ward_Change_Flag',
                },
            },
            {
                'function': simple_view_expr,
                'kwargs': {
                    'expr': 'CAST((MovementTypeFlag & 16) AS BIT)',
                    'alias': 'Service_Change_Flag',
                },
            },
            {
                'function': simple_view_expr,
                'kwargs': {
                    'expr': 'CAST((MovementTypeFlag & 32) AS BIT)',
                    'alias': 'Nurse_Change_Flag',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'DiagnosisBy',
                    'column_prefix': 'Diagnosis_Confirmed_By',  # RCEP
                    'internal_alias_prefix': 'dcb',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'Service',
                    'lookup_table': 'GenService',
                    'column_prefix': 'Service',  # RCEP
                    'internal_alias_prefix': 'sv',
                },
            },
        ],
    }),

    ('Inpatient_Named_Nurse', {
        'basetable': 'ImsEventNamedNurse',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'EventNumber': 'Event_Number',  # RCEP
            'GenHCPCode': 'Named_Nurse_User_Code',  # RCEP
            'StartDateTime': 'Start_Date_Time',  # RCEP
            'EndDateTime': 'End_Date_Time',  # RCEP
            'SequenceID': 'Unique_Key',  # RCEP
            'EventMovementID': 'Key_To_Associated_Movement',  # RCEP
            'EndedOnDeath': 'Ended_On_Death_Flag',  # RCEP
        },
        'add': [
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'GenHCPCode',
                    'column_prefix': 'User',
                    # ... RCEP is a bit confused, with
                    #   GenHCPCode -> Named_Nurse_User_Code
                    # and User_* for the other fields.
                    # Still, stick with it for now...
                    'internal_alias_prefix': 'nn',
                },
            },
        ],
    }),

    ('Inpatient_Sleepover', {
        'basetable': 'ImsEventSleepover',
        'rename': {
            # RCEP: Created_Date: see our Audit_Created_Date
            # RCEP: Updated_Date: see our Audit_Updated_Date
            'SequenceID': 'Event_Key',  # RCEP; not sure this one is worthwhile
            'EventID': 'Event_ID',  # RCEP
            'StartDate': 'Start_Date',  # StartDate in RCEP
            'ExpectedEndDate': 'Expected_End_Date',  # RCEP
            'EndDate': 'End_Date',  # RCEP
            'WardCode': None,  # Ward_Code (RCEP) is from bay lookup
            'BayCode': None,  # Bay_Code (RCEP) is from bay lookup
            'BedNumber': 'Bed',  # RCEP
            # Comment: unchanged  # RCEP
            'EndedOnDeath': 'Ended_On_Death_Flag',  # RCEP
        },
        'add': [
            {
                'function': rio_add_bay_lookup,
                'kwargs': {
                    'basecolumn_ward': 'WardCode',
                    'basecolumn_bay': 'BayCode',
                    'column_prefix': '',
                    # Ward_Code, Ward_Description,
                    # Bay_Code, Bay_Description as per RCEP
                    'internal_alias_prefix': 'bay',
                },
            },
        ],
    }),

    # 'LSOA_buffer' is RCEP internal, cf. my ONS PD geography database

    ('Referral', {  # was Main_Referral_Data
        'basetable': 'AmsReferral',
        'rename': {
            # EnquiryNumber: unchanged
            # Referrer: unchanged; not in RCEP; missing?
            # Referral_Reason_National_Code: RCEP; ?source. Only AmsReferralSource.NationalCode  # noqa
            'AdministrativeCategory': None,  # lookup below
            'CABReferral': 'CAB_Referral',  # RCEP
            'ClientCareSpell': None,  # see lookup below
            'DischargeAddressLine1': 'Discharge_Address_Line_1',  # RCEP
            'DischargeAddressLine2': 'Discharge_Address_Line_2',  # RCEP
            'DischargeAddressLine3': 'Discharge_Address_Line_3',  # RCEP
            'DischargeAddressLine4': 'Discharge_Address_Line_4',  # RCEP
            'DischargeAddressLine5': 'Discharge_Address_Line_5',  # RCEP
            'DischargeAllocation': 'Discharge_Allocation',  # RCEP
            'DischargeComment': 'Discharge_Comment',  # RCEP
            'DischargeDateTime': 'Discharge_DateTime',  # not in RCEP; missing?
            'DischargedOnAdmission': 'Discharged_On_Admission',  # RCEP
            'DischargeHCP': None,  # RCEP; user lookup
            'DischargePostCode': 'Discharge_Post_Code',  # RCEP
            'DischargeReason': 'Discharge_Reason',  # not in RCEP; missing?
            'ExternalReferralId': 'External_Referral_Id',
            # ... RCEP (field is not VARCHAR(8000) as docs suggest; 25 in RiO,
            #     50 in RCEP)
            'HCPAllocationDate': 'HCP_Allocation_Date',  # RCEP
            'HCPReferredTo': None,  # not in RCEP; lookup added below
            'IWSComment': 'IWS_Comment',  # RCEP
            'IWSHeld': 'IWS_Held',  # RCEP
            'LikelyFunder': 'Likely_Funder',  # RCEP
            'LikelyLegalStatus': 'Likely_Legal_Status',  # RCEP
            'PatientArea': None,  # lookup below
            'ReferralAcceptedDate': 'Referral_Accepted_Date',  # RCEP
            'ReferralActionDate': 'Referral_ActionDate',  # not in RCEP; missing?  # noqa
            'ReferralAllocation': 'Referral_Allocation',  # RCEP
            'ReferralComment': 'Referral_Comment',  # not in RCEP; missing?
            'ReferralDateTime': 'Referral_DateTime',  # not in RCEP; missing?
            'ReferralNumber': 'Referral_Number',  # RCEP
            'ReferralReason': 'Referral_Reason_Code',  # RCEP, + lookup below
            'ReferralReceivedDate': 'Referral_Received_Date',  # RCEP
            'ReferralSource': 'Referral_Source',  # RCEP
            'ReferredConsultant': None,  # RCEP; user lookup
            'ReferredWard': 'Referred_Ward_Code',  # RCEP
            'ReferrerOther': 'Referrer_Other',  # RCEP
            'ReferringConsultant': None,  # tricky lookup; see below
            'ReferringGP': 'Referring_GP_Code',  # RCEP
            'ReferringGPPracticeCode': 'Referring_GP_Practice_Code',  # RCEP
            'RemovalCode': 'Removal_Code',  # RCEP
            'RemovalDateTime': 'Removal_DateTime',  # RCEP
            'RemovalUser': None,  # RCEP; user lookup
            'RTTCode': 'RTT_Code',  # RCEP; FK to RTTPathwayConfig.RTTCode (ignored)  # noqa
            'ServiceReferredTo': None,  # lookup below
            'SpecialtyReferredTo': None,  # lookup below
            'TeamReferredTo': None,  # not in RCEP; lookup added below
            'Urgency': None,  # lookup below
            'WaitingListID': 'Waiting_List_ID',  # RCEP; FK to WLConfig.WLCode (ignored)  # noqa
        },
        'add': [
            {  # not in RCEP
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'Urgency',
                    'lookup_table': 'GenUrgency',
                    'column_prefix': 'Urgency',
                    # not in RCEP; missing?
                    'internal_alias_prefix': 'ur',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'PatientArea',
                    'lookup_table': 'AmsPatientArea',
                    'column_prefix': 'Patient_Area',  # RCEP
                    # in RCEP, code = Patient_Area
                    'internal_alias_prefix': 'pa',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'AdministrativeCategory',
                    'lookup_table': 'GenAdministrativeCategory',
                    'column_prefix': 'Administrative_Category',
                    # ... RCEP
                    'internal_alias_prefix': 'ac',
                },
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'ReferralReason',
                    'lookup_table': 'GenReferralReason',
                    'lookup_pk': 'Code',
                    'lookup_fields_aliases': {
                        'CodeDescription': 'Referral_Reason_Description',
                        'NationalCode_CIDS': 'Referral_Reason_National_Code_CIDS',  # noqa
                        'NationalCode_CAMHS': 'Referral_Reason_National_Code_CAMHS',  # noqa
                        # ... RCEP, except Referral_Reason_National_Code;
                        # unsure which it refers to! Probably *_CIDS;
                        # http://www.datadictionary.nhs.uk/data_dictionary/messages/clinical_data_sets/data_sets/community_information_data_set_fr.asp?shownav=1  # noqa
                    },
                    'internal_alias_prefix': 'rr',
                }
            },
            {
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'ReferredWard',
                    'lookup_table': 'ImsWard',
                    'lookup_pk': 'WardCode',
                    'lookup_fields_aliases': {
                        'WardDescription': 'Referred_Ward_Description',  # RCEP
                    },
                    'internal_alias_prefix': 'rw',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'DischargeHCP',
                    'column_prefix': 'Discharge_HCP',  # RCEP
                    'internal_alias_prefix': 'dhcp',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'ReferredConsultant',
                    'column_prefix': 'Referred_Consultant',  # RCEP
                    'internal_alias_prefix': 'rc',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'RemovalUser',
                    'column_prefix': 'Removal_User',  # RCEP
                    'internal_alias_prefix': 'ru',
                },
            },
            {
                'function': rio_add_carespell_lookup,
                'kwargs': {
                    'basecolumn': 'ClientCareSpell',
                    'column_prefix': 'Care_Spell',  # RCEP
                    'internal_alias_prefix': 'cs',
                },
            },
            {  # not in RCEP
                'function': rio_add_team_lookup,
                'kwargs': {
                    'basecolumn': 'TeamReferredTo',
                    'column_prefix': 'Team_Referred_To',
                    'internal_alias_prefix': 'trt',
                },
            },
            {  # not in RCEP
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'HCPReferredTo',
                    'column_prefix': 'HCP_Referred_To',
                    'internal_alias_prefix': 'hrt',
                },
            },
            {  # not in RCEP
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'SpecialtyReferredTo',
                    'lookup_table': 'GenSpecialty',
                    'column_prefix': 'Specialty_Referred_To',
                    'internal_alias_prefix': 'sprt',
                }
            },
            {  # not in RCEP
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'ServiceReferredTo',
                    'lookup_table': 'GenService',
                    'column_prefix': 'Service_Referred_To',
                    'internal_alias_prefix': 'sert',
                }
            },
            # Look up the same field two ways.
            {  # If AmsReferralSource.Behaviour = 'CS'...
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'ReferringConsultant',
                    'column_prefix': 'Referring_Consultant_Cons',
                    'internal_alias_prefix': 'rcc',
                },
            },
            {  # If AmsReferralSource.Behaviour = 'CH'...
                'function': rio_add_consultant_lookup,
                'kwargs': {
                    'basecolumn': 'ReferringConsultant',
                    'column_prefix': 'Referring_Consultant_HCP',
                    # ... RCEP: Referring_Consultant_User
                    'internal_alias_prefix': 'rch',
                },
            },
        ],
    }),

    ('Progress_Notes', {
        'basetable': 'PrgProgressNote',
        'rename': {
            # create:
            'DateAndTime': 'Created_Date',  # RCEP; RCEP synonym: 'Date'
            'UserID': None,  # RCEP; user lookup
            # update:
            'EnterDatetime': 'Updated_Date',  # RCEP; later than DateAndTime
            'EnteredBy': None,  # not in RCEP; user lookup
            # verify:
            'VerifyDate': 'Verified_Date',  # RCEP was: Validate_This_Note
            'VerifyUserID': None,  # RCEP; user lookup
            # other:
            # 'HTMLIncludedFlag': None,  # RCEP
            # 'NoteNum': None,  # RCEP
            # 'Significant': 'This_Is_A_Significant_Event',  # RCEP
            # 'SubNum': None,  # RCEP
            'EnteredInError': 'Entered_In_Error',  # RCEP
            'NoteText': 'Text',  # RCEP
            'NoteType': None,  # lookup below
            'Problem': None,  # RCEP; "obsolete"
            'RiskRelated': 'Risk_Related',  # RCEP was: Add_To_Risk_History
            'RiskType': None,  # lookup below
            'SubNoteType': None,  # lookup below
            'ThirdPartyInfo': 'Third_Party_Info',
            # ... RCEP was: This_Note_Contains_Third_Party_Information
            'ClinicalEventType': None,  # lookup below
            'SpecialtyID': None,  # lookup below
        },
        'add': [
            {  # not in RCEP
                'function': simple_view_expr,
                'kwargs': {
                    'expr': 'CASE WHEN {basetable}.VerifyDate IS NULL THEN 0 '
                            'ELSE 1 END',
                    'alias': 'validated',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'NoteType',
                    'lookup_table': 'GenUserPrgNoteType',
                    'column_prefix': 'Note_Type',
                    # in RCEP, code absent, desc = Note_Type
                    'internal_alias_prefix': 'nt',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'SubNoteType',
                    'lookup_table': 'GenUserPrgNoteSubType',
                    'column_prefix': 'Sub_Note_Type',
                    # in RCEP, code absent, desc = Sub_Note_Type
                    'internal_alias_prefix': 'snt',
                }
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'RiskType',
                    'lookup_table': 'RskRiskType',
                    'column_prefix': 'Risk_Type',
                    # in RCEP, code absent, desc = Risk_Type
                    'internal_alias_prefix': 'rt',
                }
            },
            {  # not in RCEP
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'ClinicalEventType',
                    'lookup_table': 'GenClinicalEventType',
                    'column_prefix': 'Clinical_Event_Type',
                    'internal_alias_prefix': 'cet',
                }
            },
            {  # not in RCEP
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'SpecialtyID',
                    'lookup_table': 'GenSpecialty',
                    'column_prefix': 'Specialty',
                    'internal_alias_prefix': 'spec',
                }
            },
            {  # not in RCEP
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'RoleID',
                    'lookup_table': 'GenUserType',
                    'lookup_pk': 'UserTypeID',
                    'lookup_fields_aliases': {
                        'RoleDescription': 'Role_Description',
                    },
                    'internal_alias_prefix': 'rl',
                }
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'UserID',
                    'column_prefix': 'Originating_User',
                    # ... RCEP: was originator_user
                    'internal_alias_prefix': 'ou',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'EnteredBy',
                    'column_prefix': 'Updating_User',  # not in RCEP
                    'internal_alias_prefix': 'uu',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'VerifyUserID',
                    'column_prefix': 'Verifying_User',
                    # ... RCEP: was verified_by_user
                    'internal_alias_prefix': 'vu',
                },
            },
            {
                # Restrict to current progress notes using CRATE extra info?
                'function': where_prognotes_current,
            },
        ],
    }),

    ('Referral_Staff_History', {
        'basetable': 'AmsReferralAllocation',
        'rename': {
            # Comment: unchanged
            'CurrentAtDischarge': 'Current_At_Discharge',
            'EndDate': 'End_Date',  # RCEP
            'HCPCode': None,  # RCEP was HCPCode but this is in user lookup
            'ReferralID': 'Referral_Key',  # RCEP
            'StartDate': 'Start_Date',  # RCEP
            'TransferDate': 'Transfer_Date',  # RCEP
        },
        'add': [
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'HCPCode',
                    'column_prefix': 'HCP_User',  # RCEP
                    'internal_alias_prefix': 'hu',
                },
            },
        ],
        'suppress_basetable': True,
        'suppress_other_tables': [],
    }),

    ('Referral_Team_History', {
        'basetable': 'AmsReferralTeam',
        'rename': {
            # Comment - unchanged
            'CurrentAtDischarge': 'Current_At_Discharge',  # RCEP
            'EndDate': 'End_Date',  # RCEP
            'ReferralID': 'Referral_Key',  # RCEP
            'StartDate': 'Start_Date',  # RCEP
            'TeamCode': None,  # Team_Code (as per RCEP) from lookup below
        },
        'add': [
            {
                'function': rio_add_team_lookup,
                'kwargs': {
                    'basecolumn': 'TeamCode',
                    'column_prefix': 'Team',  # RCEP
                    'internal_alias_prefix': 't',
                },
            },
        ],
    }),

    ('Referral_Waiting_Status_History', {
        'basetable': 'AmsReferralListWaitingStatus',
        'rename': {
            'ChangeBy': None,  # RCEP; user lookup
            'ChangeDateTime': 'Change_Date_Time',  # RCEP
            'EndDate': 'End_Date',  # RCEP
            'ReferralID': 'Referral_Key',  # RCEP
            'StartDate': 'Start_Date',  # RCEP
            'WaitingStatus': None,  # lookup below
        },
        'add': [
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'WaitingStatus',
                    'lookup_table': 'GenReferralWaitingStatus',
                    'column_prefix': 'Waiting_Status',
                    # in RCEP, code absent, desc = Waiting_Status
                    'internal_alias_prefix': 'ws',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'ChangeBy',
                    'column_prefix': 'Changed_By',  # RCEP
                    'internal_alias_prefix': 'cb',
                },
            },
        ],
    }),

    # -------------------------------------------------------------------------
    # Core: important things missed out by RCEP
    # -------------------------------------------------------------------------

    ('Clinical_Documents', {
        'basetable': 'ClientDocument',
        'rename': {
            # ClientID: ignored; CRATE_COL_RIO_NUMBER instead
            # SequenceID: ignored; CRATE_COL_PK instead
            'UserID': None,  # user lookup
            'Type': None,  # lookup below
            'DateCreated': 'Date_Created',
            'SerialNumber': 'Serial_Number',  # can repeat across ClientID
            'Path': 'Path',  # ... no path, just filename (but CONTAINS ID)
            # ... filename format is e.g.:
            #   46-1-20130903-XXXXXXX-OC.pdf
            # where 46 = SerialNumber; 1 = RevisionID; 20130903 = date;
            # XXXXXXX = RiO number; OC = Type
            'Description': 'Description',
            'Title': 'Title',
            'Author': 'Author',
            'DocumentDate': 'Document_Date',
            'InsertedDate': 'Inserted_Date',
            'RevisionID': 'Document_Version',  # starts from 1 for each
            'FinalRevFlag': 'Is_Final_Version',  # 0 (draft) or 1 (final)
            'DeletedDate': 'Deleted_Date',
            'DeletedBy': None,  # user lookup
            'DeletedReason': None,  # lookup below
            'FileSize': 'File_Size',
        },
        'add': [
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'UserID',
                    'column_prefix': 'Storing_User',
                    'internal_alias_prefix': 'su',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'Type',
                    'lookup_table': 'GenDocumentType',
                    'column_prefix': 'Type',
                    'internal_alias_prefix': 'ty',
                },
            },
            {
                'function': rio_add_user_lookup,
                'kwargs': {
                    'basecolumn': 'DeletedBy',
                    'column_prefix': 'Deleting_User',
                    'internal_alias_prefix': 'du',
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'DeletedReason',
                    'lookup_table': 'GenDocumentRemovalReason',
                    'column_prefix': 'Deleted_Reason',
                    'internal_alias_prefix': 'dr',
                },
            },
            {
                # Restrict to current progress notes using CRATE extra info?
                'function': where_clindocs_current,
            },
        ],
    }),


    # -------------------------------------------------------------------------
    # Non-core: CPFT
    # -------------------------------------------------------------------------

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # CPFT Core Assessment v2
    #
    # 1. Getting form and table names (prepend 'UserAssess' to table names):
    #
    #    USE rio_data_raw;
    #
    #    SELECT *
    #    FROM AssessmentFormGroupsIndex afgi
    #    INNER JOIN AssessmentFormGroupsStructure afgs
    #      ON afgs.name = afgi.Name
    #    INNER JOIN AssessmentFormsIndex afi
    #      ON afi.name = afgs.FormName
    #    WHERE afgi.deleted = 0
    #    AND afgi.Description = 'Core Assessment v2'
    #    ORDER BY afgs.FormOrder, afgs.FormName, afgs.FormgroupVersion;
    #
    # 2. Getting field descriptions: explore the front end
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    ('CPFT_Core_Assessment_v2_Presenting_Problem', {
        'basetable': 'UserAssesscoreasspresprob',
        'rename': merge_two_dicts(DEFAULT_NONCORE_RENAMES, {
            'ReasonRef': 'Reasons_For_Referral',
            'HistProb': 'History_Of_Presenting_Problem',
            'CurrInt': 'Current_Interventions_Medication',
        }),
        'add': [
            {'function': rio_amend_standard_noncore},
        ],
    }),

    ('CPFT_Core_Assessment_v2_PPH_PMH_Allergies_Frailty', {
        'basetable': 'UserAssesscoreassesspastpsy',
        'rename': merge_two_dicts(DEFAULT_NONCORE_RENAMES, {
            'PastPsyHist': 'Past_Psychiatric_History',
            'PhyHealth': 'Physical_Health_Medical_History',
            'Allergies': 'Allergies',
        }),
        'add': [
            {
                # Rockwood frailty score
                'function': simple_lookup_join,
                'kwargs': {
                    'basecolumn': 'frailty',
                    'lookup_table': 'UserMasterfrailty',
                    'lookup_pk': 'Code',
                    'lookup_fields_aliases': {
                        'CodeDescription': 'Frailty_Description',
                    },
                    'internal_alias_prefix': 'fr',
                }
            },
            {'function': rio_amend_standard_noncore},
        ],
    }),

    ('CPFT_Core_Assessment_v2_Background_History', {
        'basetable': 'UserAssesscoreassessbackhist',
        'rename': merge_two_dicts(DEFAULT_NONCORE_RENAMES, {
            'FamPersHist': 'Family_Personal_History',
            'ScoHist': 'Social_History',  # sic (Sco not Soc)
            'DruAlc': 'Drugs_Alcohol',
            'ForHist': 'Forensic_History',
        }),
        'add': [
            {'function': rio_amend_standard_noncore},
        ],
    }),

    ('CPFT_Core_Assessment_v2_Mental_State', {
        'basetable': 'UserAssesscoreassesmentstate',
        'rename': merge_two_dicts(DEFAULT_NONCORE_RENAMES, {
            'MentState': 'Mental_State_Examination',
        }),
        'add': [
            {'function': rio_amend_standard_noncore},
        ],
    }),

    ('CPFT_Core_Assessment_v2_Capacity_Safeguarding_Risk', {
        'basetable': 'UserAssesscoreassescapsafrisk',
        'rename': merge_two_dicts(DEFAULT_NONCORE_RENAMES, {
            'CapIssCon': 'Capacity_Issues_Consent',
            'Safeguard': 'Safeguarding',
            # "Please indicate whether any issues were identified..."
            'sovayn': 'Risk_SOVA',
            'childprotyn': 'Risk_Child_Protection',
            'sshyn': 'Risk_Suicide_Self_Harm',
            'violyn': 'Risk_Violence',
            'negvulyn': 'Risk_Neglect_Vulnerability',
            'fallsyn': 'Risk_Falls',
            'CurrDL2': 'Current_Driving_Licence',
            'Riskida': 'Risk_Impaired_Driving',
            'Risk': 'Risk_Screen',
        }),
        'add': [
            {'function': rio_amend_standard_noncore},
        ],
    }),

    ('CPFT_Core_Assessment_v2_Summary_Initial_Plan', {
        'basetable': 'UserAssesscoreasssumminitplan',
        'rename': merge_two_dicts(DEFAULT_NONCORE_RENAMES, {
            'ServStre': 'Service_User_Strengths_Needs_Expectations',
            'CareView': 'Carer_Views_Needs',
            'SummForm': 'Summary_Formulation',
            'Plan1': 'Initial_Plan',
            # PLAN is an SQL Server reserved word:
            # https://msdn.microsoft.com/en-us/library/ms189822.aspx
        }),
        'add': [
            {'function': rio_amend_standard_noncore},
        ],
    }),

    ('CPFT_Core_Assessment_v2_Social_Circumstances_Employment', {
        'basetable': 'UserAssesscoresocial1',
        # no free text
        # bad field names!
        'rename': merge_two_dicts(DEFAULT_NONCORE_RENAMES, {
            'Social06': None,  # lookup below
            'Social07': None,  # lookup below
            'Social16': None,  # lookup below
            'Social17': None,  # lookup below
        }),
        'add': [
            {'function': rio_amend_standard_noncore},
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'Social06',
                    # ... range 1-50, and field order
                    'lookup_table': 'GenAccommodationStatus',
                    'column_prefix': 'Accommodation_Status',  # RCEP
                    'internal_alias_prefix': 'as',
                }
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'Social07',
                    # ... range 1-5, and field order
                    'lookup_table': 'GenSettledAccommodation',
                    'column_prefix': 'Settled_Accommodation_Indicator',  # RCEP
                    'internal_alias_prefix': 'sa',
                }
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'Social16',
                    # ... range 1-12, and field order
                    'lookup_table': 'GenEmpStatus',
                    'column_prefix': 'Employment_Status',  # RCEP
                    'internal_alias_prefix': 'es',
                }
            },
            {
                'function': standard_rio_code_lookup_with_national_code,
                'kwargs': {
                    'basecolumn': 'Social17',
                    # ... by elimination, and field order
                    'lookup_table': 'GenWeeklyHoursWorked',
                    'column_prefix': 'Weekly_Hours_Worked',  # not in RCEP
                    # RCEP code was Weekly_Hours_Worked
                    'internal_alias_prefix': 'whw',
                }
            },
        ],
    }),

    ('CPFT_Core_Assessment_v2_Keeping_Children_Safe_Assessment', {
        # Stem was kcsahyper, so you'd expect the table to be
        # UserAssesskcsahyper; however, that doesn't exist. For '%kcsa%', there
        # are:
        # - UserAssesstfkcsa
        #       ... this is the main one
        # - UserAssesstfkcsa_childs
        #       ... this is the list of children in current household
        # - UserAssesstfkcsa_childprev
        #       ... this is the list of children from prev. relationships
        'basetable': 'UserAssesstfkcsa',
        'rename': merge_two_dicts(DEFAULT_NONCORE_RENAMES, {
            # - Does SU live in household where there are children?
            # - Please specify relationship?
            # - Is SU expecting a baby?
            # - If so, what is the EDD?
            # - Children in household:
            #   - List of: {name of child, date of birth, gender}
            #     (with minimum list size, with child name = "N/A" if none)
            # - Does the SU have contact with children (not living in the same
            #   household) from previous relationships?
            #   - If yes, specify (LIST as above)
            # - Comments
            # - Does the SU have significant contact with other children?
            # - If yes, please specify
            #
            # [FAMILY/ENVIRONMENTAL FACTORS]
            # - Does the SU experience any family and environmental
            #   difficulties that could impact on their ability to care for
            #   children?
            # - Please use this space to support your assessment outcome
            # [PARENTING CAPACITY]
            # - "Consider the outcomes of the adult assessment. Can the service
            #   user demonstrate their ability to care for children or do they
            #   require any additional support with parenting?"
            #   ... Exceptionally bad phrasing! Field is "DemAb"
            # - comments
            # [CHILD DEVELOPMENTAL NEEDS]
            # - Does info suggest there could be... difficulties with child's
            #   developmental needs?
            # - comments
            # [DOMESTIC ABUSE]
            # - Is this person affected by domestic abuse?
            # - comments
            # [SUBSTANCE MISUSE#
            # - Any concerns in relation to substance misuse?
            # - comments
            # [MENTAL HEALTH, DELUSIONAL IDEATION, SUICIDE PLANNING]
            # - does risk profile indicate delusional beliefs involving
            #   children?
            # - does... indicat suicidal ideation and/or suicide plan involving
            #   children?
            # - are there any other MH concerns which may impact on SU's
            #   ability to care for children?
            # - comments
            #
            # - CURRENT RISK/NEED STATUS (1 low to 4 serious+imminent)

            'ChildHous': None,  # transform below
            'Relation': 'Children_In_Household_Relationship',
            'expectQ': None,  # transform below
            'dodv': 'Estimated_Delivery_Date',
            'ChildCon': None,  # transform below
            'commts': 'Comments',
            'SigCon': None,  # transform below
            'SigConSpec': 'Significant_Contact_Other_Children_Specify',
            'EnvDiff': None,  # transform below
            'EnvDiffSpec': 'Family_Environment_Difficulty_Specify',
            'DemAb': None,  # transform below
            'DemAbSpec': 'Demonstrate_Ability_Care_Children_Specify',
            'DevNeeds': None,  # transform below
            'DevNeedsSpec': 'Child_Developmental_Needs_Specify',
            'domab1': None,  # transform below
            'DomAbSpec': 'Domestic_Abuse_Specify',
            'SubMis': None,  # transform below
            'SubMisSpec': 'Substance_Misuse_Specify',
            'Q1': None,  # transform below
            'Q2': None,  # transform below
            'Q3': None,  # transform below
            'QSpec': 'Mental_Health_Specify',
            'CRNS': None,  # lookup below
        }),
        'add': [
            {'function': rio_amend_standard_noncore},
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'ChildHous',
                    'result_alias': 'Children_In_Household',
                },
            },
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'expectQ',
                    'result_alias': 'Pregnant',
                },
            },
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'ChildCon',
                    'result_alias': 'Contact_Children_Prev_Relationship_Other_Household',  # noqa
                },
            },
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'SigCon',
                    'result_alias': 'Significant_Contact_Other_Children',
                },
            },
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'EnvDiff',
                    'result_alias': 'Family_Environment_Difficulty_Concern',
                },
            },
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'DemAb',
                    'result_alias': 'Demonstrate_Ability_Care_Children_Or_Requires_Support',  # noqa
                    #  ... not safe to fail to allude to ambiguity of this
                },
            },
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'DevNeeds',
                    'result_alias': 'Child_Developmental_Needs_Concern',
                },
            },
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'domab1',
                    'result_alias': 'Domestic_Abuse_Concern',
                },
            },
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'SubMis',
                    'result_alias': 'Substance_Misuse_Concern',
                },
            },
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'Q1',
                    'result_alias': 'Mental_Health_Delusional_Beliefs_Re_Children',  # noqa
                },
            },
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'Q2',
                    'result_alias': 'Mental_Health_Suicidal_Or_Suicide_Plan_Re_Children',  # noqa
                },
            },
            {
                'function': rio_noncore_yn,
                'kwargs': {
                    'basecolumn': 'Q3',
                    'result_alias': 'Mental_Health_Other_Concern_Affecting_Child_Care',  # noqa
                },
            },
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'CRNS',
                    'lookup_table': 'UserMasterCRNS',
                    'column_prefix': 'Current_Risk_Need_Status',
                    'internal_alias_prefix': 'crns',
                },
            },
        ],
    }),

    ('CPFT_Core_Assessment_v2_KCSA_Children_In_Household', {
        'basetable': 'UserAssesstfkcsa_childs',
        'rename': merge_two_dicts(DEFAULT_NONCORE_RENAMES, {
            'type12_NoteID': 'KCSA_Note_ID',
            'NOC': 'Child_Name',
            'DOB': 'Child_Date_Of_Birth',
            'Gender': None,  # lookup below
        }),
        'add': [
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'Gender',
                    'lookup_table': 'UserMasterGender',
                    'column_prefix': 'Child_Gender',
                    'internal_alias_prefix': 'cg',
                },
            },
        ],
    }),

    ('CPFT_Core_Assessment_v2_KCSA_Children_Previous_Relationships', {
        'basetable': 'UserAssesstfkcsa_childprev',
        'rename': merge_two_dicts(DEFAULT_NONCORE_RENAMES, {
            'type12_NoteID': 'KCSA_Note_ID',
            'chname': 'Child_Name',
            'chdob': 'Child_Date_Of_Birth',
            'chgend': None,  # lookup below
        }),
        'add': [
            {
                'function': standard_rio_code_lookup,
                'kwargs': {
                    'basecolumn': 'chgend',
                    'lookup_table': 'UserMasterGender',
                    'column_prefix': 'Child_Gender',
                    'internal_alias_prefix': 'cg',
                },
            },
        ],
    }),
])


# =============================================================================
# Geography views
# =============================================================================

def add_postcode_geography_view(engine, progargs, ddhint):  # ddhint modified
    # Re-read column names, as we may have inserted some recently by hand that
    # may not be in the initial metadata.
    if progargs.rio:
        addresstable = RIO_TABLE_ADDRESS
        rio_postcodecol = RIO_COL_POSTCODE
    else:
        addresstable = RCEP_TABLE_ADDRESS
        rio_postcodecol = RCEP_COL_POSTCODE
    orig_column_names = get_column_names(engine, tablename=addresstable,
                                         sort=True)

    # Remove any original column names being overridden by new ones.
    # (Could also do this the other way around!)
    geogcols_lowercase = [x.lower() for x in progargs.geogcols]
    orig_column_names = [x for x in orig_column_names
                         if x.lower() not in geogcols_lowercase]

    orig_column_specs = [
        "{t}.{c}".format(t=addresstable, c=col)
        for col in orig_column_names
    ]
    geog_col_specs = [
        "{db}.{t}.{c}".format(db=progargs.postcodedb,
                              t=ONSPD_TABLE_POSTCODE,
                              c=col)
        for col in sorted(progargs.geogcols, key=lambda x: x.lower())
    ]
    overlap = set(orig_column_names) & set(progargs.geogcols)
    if overlap:
        raise ValueError(
            "Columns overlap: address table contains columns {}; "
            "geogcols = {}; overlap = {}".format(
                orig_column_names, progargs.geogcols, overlap))
    ensure_columns_present(engine, tablename=addresstable, column_names=[
        rio_postcodecol])
    select_sql = """
        SELECT {origcols},
            {geogcols}
        FROM {addresstable}
        LEFT JOIN {pdb}.{pcdtab}
        ON {addresstable}.{rio_postcodecol} = {pdb}.{pcdtab}.pcds
        -- RCEP, and presumably RiO, appear to use the ONS pcds format, of
        -- 2-4 char outward code; space; 3-char inward code.
        -- If this fails, use this slower version:
        -- ON REPLACE({addresstable}.{rio_postcodecol},
        --            ' ',
        --            '') = {pdb}.{pcdtab}.pcd_nospace
    """.format(
        addresstable=addresstable,
        origcols=",\n            ".join(orig_column_specs),
        geogcols=",\n            ".join(geog_col_specs),
        pdb=progargs.postcodedb,
        pcdtab=ONSPD_TABLE_POSTCODE,
        rio_postcodecol=rio_postcodecol,
    )
    create_view(engine, VIEW_ADDRESS_WITH_GEOGRAPHY, select_sql)
    ddhint.suppress_table(addresstable)


# =============================================================================
# Table action selector
# =============================================================================

def process_table(table, engine, progargs):
    tablename = table.name
    column_names = table.columns.keys()
    log.debug("TABLE: '{}'; COLUMNS: {}".format(tablename, column_names))
    if progargs.rio:
        patient_table_indicator_column = get_rio_patient_id_col(table)
    else:  # RCEP:
        patient_table_indicator_column = RCEP_COL_PATIENT_ID

    is_patient_table = (patient_table_indicator_column in column_names or
                        tablename == progargs.full_prognotes_table)
    # ... special for RCEP/CPFT, where a RiO table (with different patient ID
    # column) lives within an RCEP database.
    if progargs.drop_danger_drop:
        # ---------------------------------------------------------------------
        # DROP STUFF! Opposite order to creation (below)
        # ---------------------------------------------------------------------
        # Specific
        if tablename == progargs.master_patient_table:
            drop_for_master_patient_table(table, engine)
        elif tablename == progargs.full_prognotes_table:
            drop_for_progress_notes(table, engine)
        elif progargs.rio and tablename == RIO_TABLE_CLINICAL_DOCUMENTS:
            drop_for_clindocs_table(table, engine)
        # Generic
        if is_patient_table:
            drop_for_patient_table(table, engine)
        else:
            drop_for_nonpatient_table(table, engine)
    else:
        # ---------------------------------------------------------------------
        # CREATE STUFF!
        # ---------------------------------------------------------------------
        # Generic
        if is_patient_table:
            process_patient_table(table, engine, progargs)
        else:
            process_nonpatient_table(table, engine, progargs)
        # Specific
        if tablename == progargs.master_patient_table:
            process_master_patient_table(table, engine, progargs)
        elif progargs.rio and tablename == RIO_TABLE_CLINICAL_DOCUMENTS:
            process_clindocs_table(table, engine, progargs)
        elif tablename == progargs.full_prognotes_table:
            process_progress_notes(table, engine, progargs)


def process_all_tables(engine, metadata, progargs):
    if progargs.debug_skiptables:
        return
    for table in sorted(metadata.tables.values(),
                        key=lambda t: t.name.lower()):
        process_table(table, engine, progargs)


# =============================================================================
# Default settings for CRATE anonymiser "ddgen_*" fields, for RiO
# =============================================================================

class DDHint(object):
    def __init__(self):
        self._suppressed_tables = set()
        self._index_requests = {}  # dict of dicts

    def suppress_table(self, table):
        self._suppressed_tables.add(table)

    def suppress_tables(self, tables):
        for t in tables:
            self.suppress_table(t)

    def get_suppressed_tables(self):
        return sorted(self._suppressed_tables)

    def add_source_index_request(self, table, columns):
        if isinstance(columns, str):
            columns = [columns]
        assert table, "Bad table: {}".format(repr(table))
        assert columns, "Bad columns: {}".format(repr(columns))
        index_name = 'crate_idx_' + '_'.join(columns)
        if table not in self._index_requests:
            self._index_requests[table] = {}
            if index_name not in self._index_requests[table]:
                self._index_requests[table][index_name] = {
                    'index_name': index_name,
                    'column': ', '.join(columns),
                    'unique': False,
                }

    def add_bulk_source_index_request(self, table_columns_list):
        for table, columns in table_columns_list:
            assert table, ("Bad table; table={}, table_columns_list={}".format(
                repr(table), repr(table_columns_list)))
            assert columns, (
                "Bad table; columns={}, table_columns_list={}".format(
                    repr(columns), repr(table_columns_list)))
            self.add_source_index_request(table, columns)

    def add_indexes(self, engine, metadata):
        for tablename, tabledict in self._index_requests.items():
            indexdictlist = []
            for indexname, indexdict in tabledict.items():
                indexdictlist.append(indexdict)
            tablename_casematch = get_case_insensitive_dict_key(
                metadata.tables, tablename)
            if not tablename_casematch:
                log.warning("add_indexes: Skipping index as table {} "
                            "absent".format(tablename))
                continue
            table = metadata.tables[tablename_casematch]
            add_indexes(engine, table, indexdictlist)

    def drop_indexes(self, engine, metadata):
        for tablename, tabledict in self._index_requests.items():
            index_names = list(tabledict.keys())
            tablename_casematch = get_case_insensitive_dict_key(
                metadata.tables, tablename)
            if not tablename_casematch:
                log.warning("add_indexes: Skipping index as table {} "
                            "absent".format(tablename))
                continue
            table = metadata.tables[tablename_casematch]
            drop_indexes(engine, table, index_names)


def report_rio_dd_settings(progargs, ddhint):
    settings_text = """
ddgen_omit_by_default = True

ddgen_omit_fields =

ddgen_include_fields = #
    # -------------------------------------------------------------------------
    # RCEP core views:
    # -------------------------------------------------------------------------
    Care_Plan_Index.*
    Care_Plan_Interventions.*
    Care_Plan_Problems.*
    Client_Address_History.*
    Client_Alternative_ID.*
    Client_Allergies.*
    Client_Communications_History.*
    Client_CPA.*
    Client_Demographic_Details.*
    Client_Family.*
    Client_GP_History.*
    Client_Medication.*
    Client_Name_History.*
    Client_Personal_Contacts.*
    Client_Physical_Details.*
    Client_Prescription.*
    Client_Professional_Contacts.*
    Client_School.*
    CPA_CareCoordinator.*
    CPA_Review.*
    Diagnosis.*
    Inpatient_Stay.*
    Inpatient_Leave.*
    Inpatient_Movement.*
    Inpatient_Named_Nurse.*
    Inpatient_Sleepover.*
    Referral.*
    Progress_Notes.*
    Referral_Staff_History.*
    Referral_Team_History.*
    Referral_Waiting_Status_History.*
    # -------------------------------------------------------------------------
    # Non-core:
    # -------------------------------------------------------------------------
    Core_Assessment_PPH_PMH_Allergies_Frailty.*

ddgen_allow_no_patient_info = False

ddgen_per_table_pid_field = crate_rio_number

ddgen_add_per_table_pids_to_scrubber = False

ddgen_master_pid_fieldname = crate_nhs_number_int

ddgen_table_whitelist = #
    # -------------------------------------------------------------------------
    # Whitelist: Prefixes: groups of tables
    # -------------------------------------------------------------------------
    EPClientAllergy*  # Allergy details within EP module
    # -------------------------------------------------------------------------
    # Whitelist: Suffixes
    # -------------------------------------------------------------------------
    *_crate  # Views added by CRATE
    # -------------------------------------------------------------------------
    # Whitelist: Individual tables
    # -------------------------------------------------------------------------
    EPReactionType  # Allergy reaction type details within EP module

ddgen_table_blacklist = #
    # -------------------------------------------------------------------------
    # Blacklist: Prefixes: groups of tables; individual tables
    # -------------------------------------------------------------------------
    Agresso*  # Agresso [sic] module (comms to social worker systems)
    ADT*  # ?admit/discharge/transfer messages (see codes in ADTMessage)
    Ams*  # Appointment Management System (Ams) module
    Audit*  # RiO Audit Trail
    CDSContract*  # something to do with commissioner contracts
    Chd*  # Child development (interesting, but lots of tables and all empty)
    ClientAddressHistory  # defunct according to RIO 6.2 docs
    ClientAddressMerged  # defunct according to RIO 6.2 docs
    ClientChild*  # child info e.g. birth/immunisation (interesting, but several tables and all empty)
    ClientCommunityDomain # defunct according to RIO 6.2 docs
    ClientFamily  # contains only a comment; see ClientFamilyLink instead
    ClientMerge*  # record of admin events (merging of client records)
    ClientPhoto*  # no use to us or identifiable!
    ClientRestrictedRecord*  # ? but admin
    Con*  # Contracts module
    DA*  # Drug Administration within EP
    DgnDiagnosis  # "Obsolete"; see DiagnosisClient
    DS*  # Drug Service within EP
    EP*  # E-Prescribing (EP) module, which we don't have
    #   ... mostly we don't have it, but we may have EPClientAllergies etc.
    #   ... so see whitelist too
    ESRImport  # user-to-?role map? Small and system.
    ExternalSystem*  # system
    GenChd*  # lookup codes for Chd*
    GenCon*  # lookup codes for Con*
    GenDiagnosis  # "Obsolete"
    GenError*  # system
    GenExtract*  # details of reporting extracts
    GenHCPTemplateDetails  # HCP diary template
    GenIDSeed  # system (counters for different ID types)
    GenLicenseKeys  # system; NB shows what components are licensed!
    GenPrinter*  # printers
    GenToDoList  # user to-do list items/notifications
    KP90ErrorLog  # error log for KP90 report; http://www.hscic.gov.uk/datacollections/kp90
    LR*  # Legitimate Relationships module
    Meeting*  # Meetings module
    Mes*  # messaging
    MonthlyPlanner*  # system
    PSS*  # Prevention, Screening & Surveillance (PSS)
    RioPerformanceTimings  # system
    RR*  # Results Reporting (e.g. laboratories, radiology)
    #   ... would be great, but we don't have it
    RTT*  # RTT* = Referral-to-Treatment (RTT) data collection (see NHS England docs)
    SAF*  # SAF* = system; looks like details of tablet devices
    Scheduler*  # Scheduler* = Scheduler module (for RiO computing)
    Sec*  # Security? Definitely RiO internal stuff.
    SPINE*  # system
    SPRExternalNotification  # system?
    tbl*  # records of changes to tables?
    TeamPlanner*  # system
    Temp*  # system
    umt*  # system
    Wfl*  # workflow
    WL*  # Waiting lists (WL) module
    # -------------------------------------------------------------------------
    # Blacklist: Middle bits, suffixes
    # -------------------------------------------------------------------------
    *Access*  # system access controls
    *Backup  # I'm guessing backups...
    *Cache*  # system
    *Lock*  # system
    *Timeout*  # system
    # -------------------------------------------------------------------------
    # Blacklist: Views supersede
    # Below here, we have other tables suppressed because CRATE's views offer
    # more comprehensive alternatives
    # -------------------------------------------------------------------------
    {suppress_tables}

# USEFUL TABLES (IN CPFT INSTANCE) INCLUDE:
# =========================================
# Assessment* = includes maps of non-core assessments (see e.g. AssessmentIndex)
# CDL_OUTDATEDPATIENTS_TWI = map from TWI (trust-wide identifier) to old CPFT M number
# UserAssess* = non-core assessments themselves
# UserMaster* = lookup tables for non-core assessments

ddgen_field_whitelist =

ddgen_field_blacklist = #
    {RIO_COL_PATIENT_ID}  # replaced by crate_rio_number
    *Soundex  # identifying 4-character code; https://msdn.microsoft.com/en-us/library/ms187384.aspx
    Spine*  # NHS Spine identifying codes

ddgen_pk_fields = crate_pk

ddgen_constant_content = False

ddgen_constant_content_tables =

ddgen_nonconstant_content_tables =

ddgen_addition_only = False

ddgen_addition_only_tables = #
    UserMaster*  # Lookup tables for non-core - addition only?

ddgen_deletion_possible_tables =

ddgen_pid_defining_fieldnames = ClientIndex.crate_rio_number

ddgen_scrubsrc_patient_fields = # several of these:
    # ----------------------------------------------------------------------
    # Original RiO tables (some may be superseded by views; list both here)
    # ----------------------------------------------------------------------
    AmsReferral.DischargeAddressLine*  # superseded by view Referral
    AmsReferral.DischargePostCode  # superseded by view Referral
    ClientAddress.AddressLine*  # superseded by view Client_Address_History
    ClientAddress.PostCode  # superseded by view Client_Address_History
    ClientAlternativeID.ID  # superseded by view Client_Alternative_ID
    ClientIndex.crate_pk  # superseded by view Client_Demographic_Details
    ClientIndex.DateOfBirth  # superseded by view Client_Demographic_Details
    ClientIndex.DaytimePhone  # superseded by view Client_Demographic_Details
    ClientIndex.EMailAddress  # superseded by view Client_Demographic_Details
    ClientIndex.EveningPhone  # superseded by view Client_Demographic_Details
    ClientIndex.Firstname  # superseded by view Client_Demographic_Details
    ClientIndex.MobilePhone  # superseded by view Client_Demographic_Details
    ClientIndex.NINumber  # superseded by view Client_Demographic_Details
    ClientIndex.OtherAddress  # superseded by view Client_Demographic_Details
    ClientIndex.SpineID  # superseded by view Client_Demographic_Details
    ClientIndex.Surname  # superseded by view Client_Demographic_Details
    ClientName.GivenName*  # superseded by view Client_Name_History
    ClientName.Surname  # superseded by view Client_Name_History
    ClientTelecom.Detail  # superseded by view Client_Communications_History
    ImsEvent.DischargeAddressLine*  # superseded by view Inpatient_Stay
    ImsEvent.DischargePostCode*  # superseded by view Inpatient_Stay
    ImsEventLeave.AddressLine*  # superseded by view Inpatient_Leave
    ImsEventLeave.PostCode  # superseded by view Inpatient_Leave
    # ----------------------------------------------------------------------
    # Views
    # ----------------------------------------------------------------------
    Client_Address_History.Address_Line_*
    Client_Address_History.Post_Code
    Client_Alternative_ID.ID
    Client_Communications_History.crate_telephone
    Client_Communications_History.crate_email_address
    Client_Demographic_Details.crate_rio_number
    Client_Demographic_Details.NHS_Number
    Client_Demographic_Details.Firstname
    Client_Demographic_Details.Surname
    Client_Demographic_Details.Date_of_Birth
    Client_Demographic_Details.*Phone
    Client_Demographic_Details.Superseding_NHS_Number
    Client_Name_History.Given_Name_*
    Client_Name_History.Family_Name
    Inpatient_Leave.Address_Line*
    Inpatient_Leave.PostCode
    Inpatient_Stay.Discharge_Address_Line_*
    Inpatient_Stay.Discharge_Post_Code*
    Referral.Discharge_Address_Line_*
    Referral.Discharge_Post_Code*
    {VIEW_ADDRESS_WITH_GEOGRAPHY}.AddressLine*  # superseded by other view Client_Address_History
    {VIEW_ADDRESS_WITH_GEOGRAPHY}.PostCode  # superseded by other view Client_Address_History

ddgen_scrubsrc_thirdparty_fields = # several:
    # ----------------------------------------------------------------------
    # Original RiO tables (some may be superseded by views; list both here)
    # ----------------------------------------------------------------------
    # ClientFamilyLink.RelatedClientID  # superseded by view Client_Family
    ClientContact.Surname  # superseded by view Client_Personal_Contacts
    ClientContact.Firstname  # superseded by view Client_Personal_Contacts
    ClientContact.AddressLine*  # superseded by view Client_Personal_Contacts
    ClientContact.PostCode  # superseded by view Client_Personal_Contacts
    ClientContact.*Phone  # superseded by view Client_Personal_Contacts
    ClientContact.EmailAddress  # superseded by view Client_Personal_Contacts
    ClientContact.NHSNumber  # superseded by view Client_Personal_Contacts
    # ClientIndex.MainCarer  # superseded by view Client_Demographic_Details
    # ClientIndex.OtherCarer  # superseded by view Client_Demographic_Details
    # ----------------------------------------------------------------------
    # Views
    # ----------------------------------------------------------------------
    Client_Personal_Contacts.Family_Name
    Client_Personal_Contacts.Given_Name
    Client_Personal_Contacts.Address_Line_*
    Client_Personal_Contacts.Post_Code
    Client_Personal_Contacts.*Phone
    Client_Personal_Contacts.Email_Address
    Client_Personal_Contacts.NHS_Number

ddgen_scrubsrc_thirdparty_xref_pid_fields = # several:
    # ----------------------------------------------------------------------
    # Original RiO tables (some may be superseded by views; list both here)
    # ----------------------------------------------------------------------
    # none; these are not integer:
    # ClientFamilyLink.RelatedClientID  # superseded by view Client_Family
    # ClientIndex.MainCarer  # superseded by view Client_Demographic_Details
    # ClientIndex.OtherCarer  # superseded by view Client_Demographic_Details
    # ----------------------------------------------------------------------
    # Views
    # ----------------------------------------------------------------------
    Client_Demographic_Details.Main_Carer
    Client_Demographic_Details.Other_Carer
    Client_Family.Related_Client_ID

ddgen_scrubmethod_code_fields = # variants:
    *PostCode*
    *Post_Code*
    NINumber
    National_Insurance_Number
    ClientAlternativeID.ID
    Client_Alternative_ID.ID

ddgen_scrubmethod_date_fields = *Date*

ddgen_scrubmethod_number_fields = #
    *Phone*
    *NNN*
    *NHS_Number*

ddgen_scrubmethod_phrase_fields = *Address*

ddgen_safe_fields_exempt_from_scrubbing =

    # RiO mostly uses string column lengths of 4, 10, 20, 40, 80, 500,
    # unlimited. So what length is the minimum for "free text"?
    # Comments are 500. Lots of 80-length fields are lookup descriptions.
    # (Note that many scrub-SOURCE fields are of length 80, e.g. address
    # fields, but they need different special handling.)
ddgen_min_length_for_scrubbing = 81

ddgen_truncate_date_fields = ClientIndex.DateOfBirth

ddgen_filename_to_text_fields = Clinical_Documents.Path

ddgen_binary_to_text_field_pairs =

ddgen_skip_row_if_extract_text_fails_fields = Clinical_Documents.Path

ddgen_index_fields =

ddgen_allow_fulltext_indexing = True

ddgen_force_lower_case = False

ddgen_convert_odd_chars_to_underscore = True
    """.format(  # noqa
        suppress_tables="\n    ".join(ddhint.get_suppressed_tables()),
        RIO_COL_PATIENT_ID=RIO_COL_PATIENT_ID,
        VIEW_ADDRESS_WITH_GEOGRAPHY=VIEW_ADDRESS_WITH_GEOGRAPHY,
    )
    with open(progargs.settings_filename, 'w') as f:
        print(settings_text, file=f)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=
        r"""
*   Alters a RiO database to be suitable for CRATE.

*   By default, this treats the source database as being a copy of a RiO
    database (slightly later than version 6.2; exact version unclear).
    Use the "--rcep" (+/- "--cpft") switch(es) to treat it as a
    Servelec RiO CRIS Extract Program (RCEP) v2 output database.
    """)  # noqa
    parser.add_argument("--url", required=True, help="SQLAlchemy database URL")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose")
    parser.add_argument(
        "--print", action="store_true",
        help="Print SQL but do not execute it. (You can redirect the printed "
             "output to create an SQL script.")
    parser.add_argument("--echo", action="store_true", help="Echo SQL")

    parser.add_argument(
        "--rcep", action="store_true",
        help="Treat the source database as the product of Servelec's RiO CRIS "
             "Extract Program v2 (instead of raw RiO)")
    parser.add_argument(
        "--drop-danger-drop", action="store_true",
        help="REMOVES new columns and indexes, rather than creating them. "
             "(There's not very much danger; no real information is lost, but "
             "it might take a while to recalculate it.)")
    parser.add_argument(
        "--cpft", action="store_true",
        help="Apply hacks for Cambridgeshire & Peterborough NHS Foundation "
             "Trust (CPFT) RCEP database. Only appicable with --rcep")

    parser.add_argument(
        "--debug-skiptables", action="store_true",
        help="DEBUG-ONLY OPTION. Skip tables (view creation only)")

    parser.add_argument(
        "--prognotes-current-only",
        dest="prognotes_current_only",
        action="store_true",
        help="Progress_Notes view restricted to current versions only "
             "(* default)")
    parser.add_argument(
        "--prognotes-all",
        dest="prognotes_current_only",
        action="store_false",
        help="Progress_Notes view shows old versions too")
    parser.set_defaults(prognotes_current_only=True)

    parser.add_argument(
        "--clindocs-current-only",
        dest="clindocs_current_only",
        action="store_true",
        help="Clinical_Documents view restricted to current versions only (*)")
    parser.add_argument(
        "--clindocs-all",
        dest="clindocs_current_only",
        action="store_false",
        help="Clinical_Documents view shows old versions too")
    parser.set_defaults(clindocs_current_only=True)

    parser.add_argument(
        "--allergies-current-only",
        dest="allergies_current_only",
        action="store_true",
        help="Client_Allergies view restricted to current info only")
    parser.add_argument(
        "--allergies-all",
        dest="allergies_current_only",
        action="store_false",
        help="Client_Allergies view shows deleted allergies too (*)")
    parser.set_defaults(allergies_current_only=False)

    parser.add_argument(
        "--audit-info",
        dest="audit_info",
        action="store_true",
        help="Audit information (creation/update times) added to views")
    parser.add_argument(
        "--no-audit-info",
        dest="audit_info",
        action="store_false",
        help="No audit information added (*)")
    parser.set_defaults(audit_info=False)

    parser.add_argument(
        "--postcodedb",
        help='Specify database (schema) name for ONS Postcode Database (as '
             'imported by CRATE) to link to addresses as a view. With SQL '
             'Server, you will have to specify the schema as well as the '
             'database; e.g. "--postcodedb ONS_PD.dbo"')
    parser.add_argument(
        "--geogcols", nargs="*", default=DEFAULT_GEOG_COLS,
        help="List of geographical information columns to link in from ONS "
             "Postcode Database. BEWARE that you do not specify anything too "
             "identifying. Default: {}".format(' '.join(DEFAULT_GEOG_COLS)))

    parser.add_argument(
        "--settings-filename",
        help="Specify filename to write draft ddgen_* settings to, for use in "
             "a CRATE anonymiser configuration file.")

    progargs = parser.parse_args()

    rootlogger = logging.getLogger()
    configure_logger_for_colour(
        rootlogger, level=logging.DEBUG if progargs.verbose else logging.INFO)

    progargs.rio = not progargs.rcep
    if progargs.rcep:
        # RCEP
        progargs.master_patient_table = RCEP_TABLE_MASTER_PATIENT
        if progargs.cpft:
            progargs.full_prognotes_table = CPFT_RCEP_TABLE_FULL_PROGRESS_NOTES
            # We (CPFT) may have a hacked-in copy of the RiO main progress 
            # notes table added to the RCEP output database. 
        else:
            progargs.full_prognotes_table = None
            # The RCEP does not export sufficient information to distinguish 
            # current and non-current versions of progress notes.
    else:
        # RiO
        progargs.master_patient_table = RIO_TABLE_MASTER_PATIENT
        progargs.full_prognotes_table = RIO_TABLE_PROGRESS_NOTES

    if progargs.postcodedb and not progargs.geogcols:
        raise ValueError(
            "If you specify postcodedb, you must specify some geogcols")

    log.info("CRATE in-place preprocessor for RiO or RiO CRIS Extract Program "
             "(RCEP) databases")
    safeargs = {k: v for k, v in vars(progargs).items() if k != 'url'}
    log.debug("args (except url): {}".format(repr(safeargs)))
    log.info("RiO mode" if progargs.rio else "RCEP mode")

    set_print_not_execute(progargs.print)

    engine = create_engine(progargs.url, echo=progargs.echo,
                           encoding=MYSQL_CHARSET)
    metadata = MetaData()
    metadata.bind = engine
    log.info("Database: {}".format(repr(engine.url)))  # ... repr hides p/w
    log.debug("Dialect: {}".format(engine.dialect.name))

    log.info("Reflecting (inspecting) database...")
    metadata.reflect(engine)
    log.info("... inspection complete")

    ddhint = DDHint()

    if progargs.drop_danger_drop:
        # Drop views (and view-induced table indexes) first
        if progargs.rio:
            drop_rio_views(engine, metadata, progargs, ddhint)
        if progargs.postcodedb:
            drop_view(engine, VIEW_ADDRESS_WITH_GEOGRAPHY)
        process_all_tables(engine, metadata, progargs)
    else:
        # Tables first, then views
        process_all_tables(engine, metadata, progargs)
        if progargs.postcodedb:
            add_postcode_geography_view(engine, progargs, ddhint)
        if progargs.rio:
            create_rio_views(engine, metadata, progargs, ddhint)

    if progargs.settings_filename:
        report_rio_dd_settings(progargs, ddhint)


if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        main()
    except:
        type_, value, tb = sys.exc_info()
        traceback.print_exc()
        pdb.post_mortem(tb)
