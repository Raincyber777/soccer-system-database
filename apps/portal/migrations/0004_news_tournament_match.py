import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0003_playermatchstat'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='match',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='auto_news', to='portal.match',
                                    verbose_name='关联对阵（自动战报）'),
        ),
        migrations.AddField(
            model_name='news',
            name='tournament',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='news', to='portal.tournament', verbose_name='关联赛事'),
        ),
    ]
