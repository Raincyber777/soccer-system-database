import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0004_news_tournament_match'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='ai_generated',
            field=models.BooleanField(default=False, verbose_name='AI 生成'),
        ),
        migrations.AlterField(
            model_name='news',
            name='category',
            field=models.CharField(choices=[('news', '赛事动态'), ('report', '战报'),
                                           ('announcement', '通知公告'), ('ai_report', '比赛报告')],
                                   default='news', max_length=20, verbose_name='类别'),
        ),
    ]
