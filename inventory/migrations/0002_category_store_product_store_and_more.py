# Generated by Django 5.1.7 on 2025-03-19 07:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='store',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='categories', to='accounts.store', verbose_name='매장'),
        ),
        migrations.AddField(
            model_name='product',
            name='store',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='products', to='accounts.store', verbose_name='매장'),
        ),
        migrations.AlterUniqueTogether(
            name='category',
            unique_together={('name', 'store')},
        ),
    ]
