import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0005_news_ai_report'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='live_away_score',
            field=models.IntegerField(blank=True, null=True, verbose_name='实时客队比分'),
        ),
        migrations.AddField(
            model_name='match',
            name='live_home_score',
            field=models.IntegerField(blank=True, null=True, verbose_name='实时主队比分'),
        ),
        migrations.AddField(
            model_name='match',
            name='live_phase',
            field=models.CharField(blank=True, choices=[('first_half', '上半场'), ('halftime', '中场休息'),
                                                        ('second_half', '下半场'), ('overtime', '加时赛'),
                                                        ('penalty', '点球大战')],
                                   default='', max_length=20, verbose_name='比赛阶段'),
        ),
        migrations.AddField(
            model_name='match',
            name='live_pushed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='最近推送时间'),
        ),
        migrations.AddField(
            model_name='match',
            name='score_token',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='计分板推送密钥'),
        ),
        migrations.AddField(
            model_name='match',
            name='scoreboard_enabled',
            field=models.BooleanField(default=False, verbose_name='计分板对接'),
        ),
    ]
