# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-17 00:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('research', '0005_query_sql_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='patientexplorer',
            name='pmq_hash',
            field=models.BigIntegerField(default=0, verbose_name='64-bit non-cryptographic hash of JSON of patient_multiquery'),  # noqa
            preserve_default=False,
        ),
    ]
