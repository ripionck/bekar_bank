# Generated by Django 4.2.7 on 2023-12-30 09:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0003_transaction_receiver_account_number_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='receiver_account_number',
        ),
    ]
