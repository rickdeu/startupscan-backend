from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptionplan',
            name='price_eur',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Preço (EUR)'),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='price_aoa',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Preço (AOA)'),
        ),
    ]
