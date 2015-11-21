# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import extra.fields
import django.core.files.storage
from django.conf import settings
import consent.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CharityPaymentRecord',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='When created')),
                ('payee', models.CharField(max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=8)),
            ],
        ),
        migrations.CreateModel(
            name='ClinicianResponse',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='When created')),
                ('token', models.CharField(max_length=20)),
                ('responded', models.BooleanField(default=False, verbose_name='Responded?')),
                ('responded_at', models.DateTimeField(null=True, verbose_name='When responded')),
                ('response_route', models.CharField(max_length=1, choices=[('e', 'E-mail'), ('w', 'Web')])),
                ('response', models.CharField(max_length=1, choices=[('R', 'R: Clinician asks RDBM to pass request to patient'), ('A', 'A: Clinician will pass the request to the patient'), ('B', 'B: Clinician vetoes on clinical grounds'), ('C', 'C: Patient is definitely ineligible'), ('D', 'D: Patient is dead/discharged or details are defunct')])),
                ('veto_reason', models.TextField(blank=True, verbose_name='Reason for clinical veto')),
                ('ineligible_reason', models.TextField(blank=True, verbose_name='Reason patient is ineligible')),
                ('pt_uncontactable_reason', models.TextField(blank=True, verbose_name='Reason patient is not contactable')),
                ('clinician_confirm_name', models.CharField(max_length=255, verbose_name='Type your name to confirm')),
                ('charity_amount_due', models.DecimalField(decimal_places=2, default=1.0, max_digits=8)),
            ],
        ),
        migrations.CreateModel(
            name='ConsentMode',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('decision_signed_by_patient', models.BooleanField(verbose_name='Request signed by patient?')),
                ('decision_under16_signed_by_parent', models.BooleanField(verbose_name='Patient under 16 and request countersigned by parent?')),
                ('decision_under16_signed_by_clinician', models.BooleanField(verbose_name='Patient under 16 and request countersigned by clinician?')),
                ('decision_lack_capacity_signed_by_representative', models.BooleanField(verbose_name='Patient lacked capacity and request signed by authorized representative?')),
                ('decision_lack_capacity_signed_by_clinician', models.BooleanField(verbose_name='Patient lacked capacity and request countersigned by clinician?')),
                ('nhs_number', models.BigIntegerField(verbose_name='NHS number')),
                ('current', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='When was this record created?')),
                ('exclude_entirely', models.BooleanField(verbose_name='Exclude patient from Research Database entirely?')),
                ('consent_mode', models.CharField(default='', max_length=10, choices=[('red', 'red'), ('yellow', 'yellow'), ('green', 'green')], verbose_name="Consent mode ('red', 'yellow', 'green')")),
                ('consent_after_discharge', models.BooleanField(verbose_name='Consent given to contact patient after discharge?')),
                ('max_approaches_per_year', models.PositiveSmallIntegerField(default=0, verbose_name='Maximum number of approaches permissible per year (0 = no limit)')),
                ('other_requests', models.TextField(blank=True, verbose_name='Other special requests by patient')),
                ('prefers_email', models.BooleanField(verbose_name='Patient prefers e-mail contact?')),
                ('changed_by_clinician_override', models.BooleanField(verbose_name="Consent mode changed by clinician's override?")),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ContactRequest',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='When created')),
                ('request_direct_approach', models.BooleanField(verbose_name='Request direct contact with patient if available (not contact with clinician first)')),
                ('lookup_nhs_number', models.BigIntegerField(null=True, verbose_name='NHS number used for lookup')),
                ('lookup_rid', models.CharField(null=True, max_length=128, verbose_name='Research ID used for lookup')),
                ('lookup_mrid', models.CharField(null=True, max_length=128, verbose_name='Master research ID used for lookup')),
                ('nhs_number', models.BigIntegerField(null=True, verbose_name='NHS number')),
                ('approaches_in_past_year', models.PositiveIntegerField()),
                ('decisions', models.TextField(blank=True, verbose_name='Decisions made')),
                ('decided_no_action', models.BooleanField(default=False)),
                ('decided_send_to_researcher', models.BooleanField(default=False)),
                ('decided_send_to_clinician', models.BooleanField(default=False)),
                ('clinician_involvement', models.PositiveSmallIntegerField(null=True, choices=[(0, 'No clinician involvement required or requested'), (1, 'Clinician involvement requested by researchers'), (2, 'Clinician involvement required by YELLOW consent mode'), (3, 'Clinician involvement required by UNKNOWN consent mode')])),
                ('consent_mode', models.ForeignKey(to='consent.ConsentMode')),
            ],
        ),
        migrations.CreateModel(
            name='DummyPatientSourceInfo',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('pt_local_id_description', models.CharField(blank=True, max_length=100, verbose_name='Description of database-specific ID')),
                ('pt_local_id_number', models.BigIntegerField(blank=True, null=True, verbose_name='Database-specific ID')),
                ('pt_dob', models.DateField(blank=True, null=True, verbose_name='Patient date of birth')),
                ('pt_dod', models.DateField(blank=True, null=True, verbose_name='Patient date of death (NULL if alive)')),
                ('pt_dead', models.BooleanField(verbose_name='Patient is dead')),
                ('pt_discharged', models.NullBooleanField(verbose_name='Patient discharged')),
                ('pt_sex', models.CharField(blank=True, max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('X', 'Inderminate/intersex'), ('?', 'Unknown')], verbose_name='Patient sex')),
                ('pt_title', models.CharField(blank=True, max_length=20, verbose_name='Patient title')),
                ('pt_first_name', models.CharField(blank=True, max_length=100, verbose_name='Patient first name')),
                ('pt_last_name', models.CharField(blank=True, max_length=100, verbose_name='Patient last name')),
                ('pt_address_1', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 1')),
                ('pt_address_2', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 2')),
                ('pt_address_3', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 3')),
                ('pt_address_4', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 4')),
                ('pt_address_5', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 5 (county)')),
                ('pt_address_6', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 6 (postcode)')),
                ('pt_address_7', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 7 (country)')),
                ('pt_telephone', models.CharField(blank=True, max_length=20, verbose_name='Patient telephone')),
                ('pt_email', models.EmailField(blank=True, max_length=254, verbose_name='Patient email')),
                ('gp_title', models.CharField(blank=True, max_length=20, verbose_name='GP title')),
                ('gp_first_name', models.CharField(blank=True, max_length=100, verbose_name='GP first name')),
                ('gp_last_name', models.CharField(blank=True, max_length=100, verbose_name='GP last name')),
                ('gp_address_1', models.CharField(blank=True, max_length=100, verbose_name='GP address line 1')),
                ('gp_address_2', models.CharField(blank=True, max_length=100, verbose_name='GP address line 2')),
                ('gp_address_3', models.CharField(blank=True, max_length=100, verbose_name='GP address line 3')),
                ('gp_address_4', models.CharField(blank=True, max_length=100, verbose_name='GP address line 4')),
                ('gp_address_5', models.CharField(blank=True, max_length=100, verbose_name='GP address line 5 (county)')),
                ('gp_address_6', models.CharField(blank=True, max_length=100, verbose_name='GP address line 6 (postcode)')),
                ('gp_address_7', models.CharField(blank=True, max_length=100, verbose_name='GP address line 7 (country)')),
                ('gp_telephone', models.CharField(blank=True, max_length=20, verbose_name='GP telephone')),
                ('gp_email', models.EmailField(blank=True, max_length=254, verbose_name='GP email')),
                ('clinician_title', models.CharField(blank=True, max_length=20, verbose_name='Clinician title')),
                ('clinician_first_name', models.CharField(blank=True, max_length=100, verbose_name='Clinician first name')),
                ('clinician_last_name', models.CharField(blank=True, max_length=100, verbose_name='Clinician last name')),
                ('clinician_address_1', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 1')),
                ('clinician_address_2', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 2')),
                ('clinician_address_3', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 3')),
                ('clinician_address_4', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 4')),
                ('clinician_address_5', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 5 (county)')),
                ('clinician_address_6', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 6 (postcode)')),
                ('clinician_address_7', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 7 (country)')),
                ('clinician_telephone', models.CharField(blank=True, max_length=20, verbose_name='Clinician telephone')),
                ('clinician_email', models.EmailField(blank=True, max_length=254, verbose_name='Clinician email')),
                ('clinician_is_consultant', models.BooleanField(default=False, verbose_name='Clinician is a consultant')),
                ('clinician_signatory_title', models.CharField(blank=True, max_length=100, verbose_name="Clinician's title for signature")),
                ('nhs_number', models.BigIntegerField(unique=True, verbose_name='NHS number')),
            ],
            options={
                'verbose_name_plural': 'Dummy patient source information',
            },
        ),
        migrations.CreateModel(
            name='Email',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='When created')),
                ('sender', models.CharField(default='CPFT Research Database - DO NOT REPLY <noreply@cpft.nhs.uk>', max_length=255)),
                ('recipient', models.CharField(max_length=255)),
                ('subject', models.CharField(max_length=255)),
                ('msg_text', models.TextField()),
                ('msg_html', models.TextField()),
                ('sent', models.BooleanField(default=False)),
                ('sent_at', models.DateTimeField(null=True, verbose_name='When sent')),
                ('failure_reason', models.TextField(verbose_name='Reason sending failed')),
                ('to_clinician', models.BooleanField(default=False)),
                ('to_researcher', models.BooleanField(default=False)),
                ('to_patient', models.BooleanField(default=False)),
                ('contact_request', models.ForeignKey(null=True, to='consent.ContactRequest')),
            ],
        ),
        migrations.CreateModel(
            name='EmailAttachment',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('file', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url='/download_privatestorage', location='/home/rudolf/Documents/code/crate/working/crateweb/crate_filestorage'), upload_to='')),
                ('sent_filename', models.CharField(null=True, max_length=255)),
                ('content_type', models.CharField(null=True, max_length=255)),
                ('owns_file', models.BooleanField(default=False)),
                ('email', models.ForeignKey(to='consent.Email')),
            ],
        ),
        migrations.CreateModel(
            name='Leaflet',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(unique=True, max_length=50, choices=[('cpft_tpir', 'CPFT: Taking part in research'), ('nihr_yhrsl', 'NIHR: Your health records save lives'), ('cpft_trafficlight_choice', 'CPFT: traffic-light choice'), ('cpft_clinres', 'CPFT: clinical research')], verbose_name='leaflet name')),
                ('pdf', extra.fields.ContentTypeRestrictedFileField(blank=True, upload_to=consent.models.leaflet_upload_to, storage=django.core.files.storage.FileSystemStorage(base_url='/download_privatestorage', location='/home/rudolf/Documents/code/crate/working/crateweb/crate_filestorage'))),
            ],
        ),
        migrations.CreateModel(
            name='Letter',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='When created')),
                ('pdf', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url='/download_privatestorage', location='/home/rudolf/Documents/code/crate/working/crateweb/crate_filestorage'), upload_to='')),
                ('to_clinician', models.BooleanField(default=False)),
                ('to_researcher', models.BooleanField(default=False)),
                ('to_patient', models.BooleanField(default=False)),
                ('sent_manually_at', models.DateTimeField(null=True)),
                ('contact_request', models.ForeignKey(null=True, to='consent.ContactRequest')),
                ('email', models.ForeignKey(null=True, to='consent.Email')),
            ],
        ),
        migrations.CreateModel(
            name='PatientLookup',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('pt_local_id_description', models.CharField(blank=True, max_length=100, verbose_name='Description of database-specific ID')),
                ('pt_local_id_number', models.BigIntegerField(blank=True, null=True, verbose_name='Database-specific ID')),
                ('pt_dob', models.DateField(blank=True, null=True, verbose_name='Patient date of birth')),
                ('pt_dod', models.DateField(blank=True, null=True, verbose_name='Patient date of death (NULL if alive)')),
                ('pt_dead', models.BooleanField(verbose_name='Patient is dead')),
                ('pt_discharged', models.NullBooleanField(verbose_name='Patient discharged')),
                ('pt_sex', models.CharField(blank=True, max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('X', 'Inderminate/intersex'), ('?', 'Unknown')], verbose_name='Patient sex')),
                ('pt_title', models.CharField(blank=True, max_length=20, verbose_name='Patient title')),
                ('pt_first_name', models.CharField(blank=True, max_length=100, verbose_name='Patient first name')),
                ('pt_last_name', models.CharField(blank=True, max_length=100, verbose_name='Patient last name')),
                ('pt_address_1', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 1')),
                ('pt_address_2', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 2')),
                ('pt_address_3', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 3')),
                ('pt_address_4', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 4')),
                ('pt_address_5', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 5 (county)')),
                ('pt_address_6', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 6 (postcode)')),
                ('pt_address_7', models.CharField(blank=True, max_length=100, verbose_name='Patient address line 7 (country)')),
                ('pt_telephone', models.CharField(blank=True, max_length=20, verbose_name='Patient telephone')),
                ('pt_email', models.EmailField(blank=True, max_length=254, verbose_name='Patient email')),
                ('gp_title', models.CharField(blank=True, max_length=20, verbose_name='GP title')),
                ('gp_first_name', models.CharField(blank=True, max_length=100, verbose_name='GP first name')),
                ('gp_last_name', models.CharField(blank=True, max_length=100, verbose_name='GP last name')),
                ('gp_address_1', models.CharField(blank=True, max_length=100, verbose_name='GP address line 1')),
                ('gp_address_2', models.CharField(blank=True, max_length=100, verbose_name='GP address line 2')),
                ('gp_address_3', models.CharField(blank=True, max_length=100, verbose_name='GP address line 3')),
                ('gp_address_4', models.CharField(blank=True, max_length=100, verbose_name='GP address line 4')),
                ('gp_address_5', models.CharField(blank=True, max_length=100, verbose_name='GP address line 5 (county)')),
                ('gp_address_6', models.CharField(blank=True, max_length=100, verbose_name='GP address line 6 (postcode)')),
                ('gp_address_7', models.CharField(blank=True, max_length=100, verbose_name='GP address line 7 (country)')),
                ('gp_telephone', models.CharField(blank=True, max_length=20, verbose_name='GP telephone')),
                ('gp_email', models.EmailField(blank=True, max_length=254, verbose_name='GP email')),
                ('clinician_title', models.CharField(blank=True, max_length=20, verbose_name='Clinician title')),
                ('clinician_first_name', models.CharField(blank=True, max_length=100, verbose_name='Clinician first name')),
                ('clinician_last_name', models.CharField(blank=True, max_length=100, verbose_name='Clinician last name')),
                ('clinician_address_1', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 1')),
                ('clinician_address_2', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 2')),
                ('clinician_address_3', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 3')),
                ('clinician_address_4', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 4')),
                ('clinician_address_5', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 5 (county)')),
                ('clinician_address_6', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 6 (postcode)')),
                ('clinician_address_7', models.CharField(blank=True, max_length=100, verbose_name='Clinician address line 7 (country)')),
                ('clinician_telephone', models.CharField(blank=True, max_length=20, verbose_name='Clinician telephone')),
                ('clinician_email', models.EmailField(blank=True, max_length=254, verbose_name='Clinician email')),
                ('clinician_is_consultant', models.BooleanField(default=False, verbose_name='Clinician is a consultant')),
                ('clinician_signatory_title', models.CharField(blank=True, max_length=100, verbose_name="Clinician's title for signature")),
                ('nhs_number', models.BigIntegerField(verbose_name='NHS number used for lookup')),
                ('lookup_at', models.DateTimeField(auto_now_add=True, verbose_name='When fetched from clinical database')),
                ('source_db', models.CharField(max_length=20, choices=[('dummy_clinical', 'Dummy clinical database for testing'), ('cpft_crs', 'CPFT Care Records System (CRS) 2005-2012'), ('cpft_rio', 'CPFT RiO 2013-')], verbose_name='Source database used for lookup')),
                ('decisions', models.TextField(blank=True, verbose_name='Decisions made during lookup')),
                ('secret_decisions', models.TextField(blank=True, verbose_name='Secret (identifying) decisions made during lookup')),
                ('pt_found', models.BooleanField(default=False, verbose_name='Patient found')),
                ('gp_found', models.BooleanField(default=False, verbose_name='GP found')),
                ('clinician_found', models.BooleanField(default=False, verbose_name='Clinician found')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PatientResponse',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('decision_signed_by_patient', models.BooleanField(verbose_name='Request signed by patient?')),
                ('decision_under16_signed_by_parent', models.BooleanField(verbose_name='Patient under 16 and request countersigned by parent?')),
                ('decision_under16_signed_by_clinician', models.BooleanField(verbose_name='Patient under 16 and request countersigned by clinician?')),
                ('decision_lack_capacity_signed_by_representative', models.BooleanField(verbose_name='Patient lacked capacity and request signed by authorized representative?')),
                ('decision_lack_capacity_signed_by_clinician', models.BooleanField(verbose_name='Patient lacked capacity and request countersigned by clinician?')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='When created')),
                ('contact_request', models.OneToOneField(to='consent.ContactRequest')),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Study',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('institutional_id', models.PositiveIntegerField(unique=True, verbose_name='Institutional (e.g. NHS Trust) study number')),
                ('title', models.CharField(max_length=255, verbose_name='Study title')),
                ('registered_at', models.DateTimeField(blank=True, null=True, verbose_name='When was the study registered?')),
                ('summary', models.TextField(verbose_name='Summary of study')),
                ('search_methods_planned', models.TextField(blank=True, verbose_name='Search methods planned')),
                ('patient_contact', models.BooleanField(verbose_name='Involves patient contact?')),
                ('include_under_16s', models.BooleanField(verbose_name='Include patients under 16?')),
                ('include_lack_capacity', models.BooleanField(verbose_name='Include patients lacking capacity?')),
                ('clinical_trial', models.BooleanField(verbose_name='Clinical trial (CTIMP)?')),
                ('include_discharged', models.BooleanField(verbose_name='Include discharged patients?')),
                ('request_direct_approach', models.BooleanField(verbose_name='Researchers request direct approach to patients?')),
                ('approved_by_rec', models.BooleanField(verbose_name='Approved by REC?')),
                ('rec_reference', models.CharField(blank=True, max_length=50, verbose_name='Research Ethics Committee reference')),
                ('approved_locally', models.BooleanField(verbose_name='Approved by local institution?')),
                ('local_approval_at', models.DateTimeField(blank=True, null=True, verbose_name='When approved by local institution?')),
                ('study_details_pdf', extra.fields.ContentTypeRestrictedFileField(blank=True, upload_to=consent.models.study_details_upload_to, storage=django.core.files.storage.FileSystemStorage(base_url='/download_privatestorage', location='/home/rudolf/Documents/code/crate/working/crateweb/crate_filestorage'))),
                ('subject_form_template_pdf', extra.fields.ContentTypeRestrictedFileField(blank=True, upload_to=consent.models.study_form_upload_to, storage=django.core.files.storage.FileSystemStorage(base_url='/download_privatestorage', location='/home/rudolf/Documents/code/crate/working/crateweb/crate_filestorage'))),
                ('lead_researcher', models.ForeignKey(related_name='studies_as_lead', to=settings.AUTH_USER_MODEL)),
                ('researchers', models.ManyToManyField(related_name='studies_as_researcher', blank=True, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'studies',
            },
        ),
        migrations.CreateModel(
            name='TeamRep',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('team', models.CharField(unique=True, max_length=100, choices=[('dummy_team_one', 'dummy_team_one'), ('dummy_team_two', 'dummy_team_two'), ('dummy_team_three', 'dummy_team_three')], verbose_name='Team description')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'clinical team representative',
                'verbose_name_plural': 'clinical team representatives',
            },
        ),
        migrations.AddField(
            model_name='letter',
            name='study',
            field=models.ForeignKey(null=True, to='consent.Study'),
        ),
        migrations.AddField(
            model_name='email',
            name='study',
            field=models.ForeignKey(null=True, to='consent.Study'),
        ),
        migrations.AddField(
            model_name='contactrequest',
            name='patient_lookup',
            field=models.ForeignKey(to='consent.PatientLookup'),
        ),
        migrations.AddField(
            model_name='contactrequest',
            name='request_by',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='contactrequest',
            name='study',
            field=models.ForeignKey(to='consent.Study'),
        ),
        migrations.AddField(
            model_name='clinicianresponse',
            name='contact_request',
            field=models.OneToOneField(related_name='clinician_response', to='consent.ContactRequest'),
        ),
    ]
