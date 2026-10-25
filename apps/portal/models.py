"""赛事业务模型：赛事/球队/球员/教练/报名审核/对阵赛果/内容/直播/遴选"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class GroupType(models.TextChoices):
    PRIMARY = 'primary', '小学组'
    MIDDLE = 'middle', '中学组'
    HIGH = 'high', '高中组'
    UNIVERSITY = 'university', '高校组'


class Tournament(models.Model):
    """赛事主表（报名的挂靠对象）"""

    class Status(models.TextChoices):
        PENDING = 'pending', '未开始'
        SIGNING = 'signing', '报名中'
        ONGOING = 'ongoing', '进行中'
        FINISHED = 'finished', '已结束'

    name = models.CharField('赛事名称', max_length=100)
    group_types = models.JSONField('设组', default=list)  # ["primary","middle",...]
    organizer = models.CharField('主办单位', max_length=100, blank=True, default='')
    sign_start_at = models.DateTimeField('报名开始', null=True, blank=True)
    sign_end_at = models.DateTimeField('报名截止', null=True, blank=True)
    status = models.CharField('状态', max_length=20, choices=Status.choices, default='pending')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='创建人',
                                   on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'portal_tournament'
        verbose_name = '赛事'

    def __str__(self):
        return self.name


class Team(models.Model):
    """球队：以学校标识码绑定学校，组别随学校学段"""

    name = models.CharField('球队名称', max_length=100)
    school = models.ForeignKey('common.School', verbose_name='所属学校', on_delete=models.PROTECT,
                               null=True, blank=True)
    city_code = models.CharField('所属市州', max_length=6, blank=True, default='', db_index=True)
    group_type = models.CharField('参赛组别', max_length=20, choices=GroupType.choices, blank=True, default='')
    founded_at = models.DateField('成立时间', null=True, blank=True)
    captain = models.CharField('队长', max_length=30, blank=True, default='')
    intro = models.TextField('球队简介', blank=True, default='')
    flag_url = models.CharField('队旗', max_length=255, blank=True, default='')
    emblem_url = models.CharField('队徽', max_length=255, blank=True, default='')
    group_photo_url = models.CharField('合照', max_length=255, blank=True, default='')
    honor_files = models.JSONField('荣誉证书', default=list)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='负责人', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='teams')
    is_active = models.BooleanField('启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'portal_team'
        verbose_name = '球队'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # 学校决定市州与组别，避免不一致
        if self.school_id and self.school:
            self.city_code = self.school.city_code
            stage_to_group = {'primary': 'primary', 'middle': 'middle', 'high': 'high', 'university': 'university'}
            self.group_type = stage_to_group.get(self.school.stage, self.group_type)
        super().save(*args, **kwargs)

    @property
    def school_name(self) -> str:
        return self.school.name if self.school else ''

    @property
    def group_type_display(self) -> str:
        return self.get_group_type_display()


class PersonStatusModel(models.Model):
    """player/coach 共用的申报-审核状态基类"""
    status = models.CharField('状态', max_length=20, default='pending', db_index=True)

    class Meta:
        abstract = True

    STATUS_CHOICES = (
        ('pending', '待审核'),
        ('active', '已生效'),
        ('rejected', '已驳回'),
    )


class Player(PersonStatusModel):
    """注册运动员：身份证唯一，学籍绑定学校，active 才公示/可参赛"""

    team = models.ForeignKey(Team, verbose_name='所属球队', on_delete=models.CASCADE,
                             null=True, blank=True, related_name='players')
    name = models.CharField('姓名', max_length=30)
    gender = models.CharField('性别', max_length=2, blank=True, default='男')
    birth_date = models.DateField('出生日期', null=True, blank=True)
    id_card = models.CharField('身份证号', max_length=18, unique=True)
    school = models.ForeignKey('common.School', verbose_name='学籍学校', on_delete=models.PROTECT,
                               null=True, blank=True)
    grade = models.CharField('年级', max_length=20, blank=True, default='')
    registry_no = models.CharField('学籍号', max_length=30, blank=True, default='', db_index=True)
    position = models.CharField('场上位置', max_length=20, blank=True, default='前锋')
    jersey_number = models.IntegerField('球衣号码', null=True, blank=True)
    phone = models.CharField('联系电话', max_length=20, blank=True, default='')
    photo_url = models.CharField('照片', max_length=255, blank=True, default='')
    intro = models.TextField('个人简介', blank=True, default='')
    is_active = models.BooleanField('启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'portal_player'
        verbose_name = '运动员'
        ordering = ['id']

    def __str__(self):
        return self.name

    @property
    def team_name(self) -> str:
        return self.team.name if self.team else ''

    @property
    def group_type_display(self) -> str:
        return self.team.get_group_type_display() if self.team else ''

    @property
    def school_name(self) -> str:
        return self.school.name if self.school else ''


class Coach(PersonStatusModel):
    """教练员"""

    name = models.CharField('姓名', max_length=30)
    gender = models.CharField('性别', max_length=2, blank=True, default='男')
    birth_date = models.DateField('出生日期', null=True, blank=True)
    id_card = models.CharField('身份证号', max_length=18, unique=True)
    phone = models.CharField('联系电话', max_length=20, blank=True, default='')
    unit_name = models.CharField('执教单位', max_length=100, blank=True, default='')
    years = models.IntegerField('执教年限', null=True, blank=True)
    cert_level = models.CharField('教练员等级', max_length=50, blank=True, default='')
    category = models.CharField('人员类别', max_length=30, blank=True, default='')
    team = models.ForeignKey(Team, verbose_name='执教球队', on_delete=models.SET_NULL,
                             null=True, blank=True, related_name='coaches')
    intro = models.TextField('个人简介', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'portal_coach'
        verbose_name = '教练员'
        ordering = ['id']

    def __str__(self):
        return self.name

    @property
    def team_name(self) -> str:
        return self.team.name if self.team else ''


class Registration(models.Model):
    """报名件：球队提交 → 市州初审 → 省级终审 → 公示"""

    class Status(models.TextChoices):
        PENDING_CITY = 'pending_city_review', '待初审'
        PENDING_PROVINCE = 'pending_province_review', '待终审'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已驳回'

    tournament = models.ForeignKey(Tournament, verbose_name='报名赛事', on_delete=models.PROTECT,
                                   related_name='registrations')
    team = models.ForeignKey(Team, verbose_name='球队', on_delete=models.CASCADE, related_name='registrations')
    team_name = models.CharField('球队名称快照', max_length=100, blank=True, default='')
    group_type = models.CharField('组别', max_length=20, choices=GroupType.choices)
    city_code = models.CharField('报名市州', max_length=6, blank=True, default='', db_index=True)
    city_name = models.CharField('市州名', max_length=30, blank=True, default='')
    leader_name = models.CharField('领队', max_length=30)
    phone = models.CharField('联系电话', max_length=20, blank=True, default='')
    player_count = models.IntegerField('参赛队员数', default=0)
    coach_name = models.CharField('带队教练', max_length=30, blank=True, default='')
    remark = models.TextField('备注', blank=True, default='')
    player_excel = models.FileField('球员信息Excel', upload_to='registrations/excel/', blank=True)
    photo_zip = models.FileField('球员照片包', upload_to='registrations/photos/', blank=True)
    stamp_file = models.FileField('盖章扫描件', upload_to='registrations/stamps/', blank=True)
    status = models.CharField('审核状态', max_length=30, choices=Status.choices,
                              default='pending_city_review', db_index=True)
    submit_time = models.DateTimeField('提交时间', default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='提交人',
                                   on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'portal_registration'
        verbose_name = '报名件'
        ordering = ['-submit_time']

    def __str__(self):
        return f'{self.team_name} · {self.tournament.name}'

    def save(self, *args, **kwargs):
        if self.team_id and not self.team_name:
            self.team_name = self.team.name
            self.city_code = self.team.city_code
        super().save(*args, **kwargs)


class RegistrationPlayer(models.Model):
    """报名球员名单快照（Excel 导入解析或前端报送）"""

    registration = models.ForeignKey(Registration, verbose_name='报名件', on_delete=models.CASCADE,
                                     related_name='registration_players')
    name = models.CharField('姓名', max_length=30)
    id_card = models.CharField('身份证号', max_length=18, blank=True, default='')
    jersey_number = models.IntegerField('球衣号码', null=True, blank=True)
    position = models.CharField('场上位置', max_length=20, blank=True, default='')

    class Meta:
        db_table = 'portal_registration_player'
        verbose_name = '报名球员'

    def __str__(self):
        return self.name


class ReviewLog(models.Model):
    """审核记录（前端审核时间线）"""

    registration = models.ForeignKey(Registration, verbose_name='报名件', on_delete=models.CASCADE,
                                     related_name='review_logs')
    stage = models.CharField('审核层级', max_length=10)  # city / province
    result = models.CharField('结论', max_length=10)  # approve / reject
    reason = models.TextField('原因', blank=True, default='')
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='操作人',
                                 on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('时间', auto_now_add=True)

    class Meta:
        db_table = 'portal_review_log'
        verbose_name = '审核记录'
        ordering = ['created_at']


class Match(models.Model):
    """对阵"""

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', '未开始'
        ONGOING = 'ongoing', '进行中'
        FINISHED = 'finished', '已结束'
        POSTPONED = 'postponed', '已延期'

    tournament = models.ForeignKey(Tournament, verbose_name='赛事', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='matches')
    tournament_name = models.CharField('赛事名称快照', max_length=100, blank=True, default='')
    group_type = models.CharField('组别', max_length=20, choices=GroupType.choices)
    round_name = models.CharField('轮次', max_length=30, blank=True, default='')
    home_team = models.ForeignKey(Team, verbose_name='主队', on_delete=models.PROTECT, related_name='home_matches')
    away_team = models.ForeignKey(Team, verbose_name='客队', on_delete=models.PROTECT, related_name='away_matches')
    match_time = models.DateTimeField('比赛时间')
    venue = models.CharField('场地', max_length=100, blank=True, default='')
    status = models.CharField('状态', max_length=20, choices=Status.choices, default='scheduled')
    remark = models.TextField('备注', blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='录入人',
                                   on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'portal_match'
        verbose_name = '对阵'
        ordering = ['match_time']

    def __str__(self):
        return f'{self.home_team} vs {self.away_team}'

    @property
    def group_type_display(self) -> str:
        return self.get_group_type_display()


class MatchResult(models.Model):
    """赛果（一场一结果）；公开接口仅暴露 is_published 的结果"""

    match = models.OneToOneField(Match, verbose_name='对阵', on_delete=models.CASCADE, related_name='result')
    home_score = models.IntegerField('主队得分')
    away_score = models.IntegerField('客队得分')
    winner_team = models.ForeignKey(Team, verbose_name='获胜方', on_delete=models.SET_NULL,
                                    null=True, blank=True)
    remark = models.CharField('备注', max_length=200, blank=True, default='')
    is_published = models.BooleanField('已发布', default=True, db_index=True)
    published_at = models.DateTimeField('发布时间', default=timezone.now)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'portal_match_result'
        verbose_name = '赛果'

    def __str__(self):
        return f'{self.home_score}:{self.away_score}'

    def save(self, *args, **kwargs):
        # 发布赛果自动把对阵置为已结束；未填获胜方时按比分推断
        if self.match_id:
            if self.is_published:
                Match.objects.filter(pk=self.match_id).update(status=Match.Status.FINISHED)
            if self.winner_team_id is None:
                if self.home_score > self.away_score:
                    self.winner_team_id = self.match.home_team_id
                elif self.away_score > self.home_score:
                    self.winner_team_id = self.match.away_team_id
        super().save(*args, **kwargs)

    @property
    def winner_team_name(self) -> str:
        return self.winner_team.name if self.winner_team else ''


class GoalRecord(models.Model):
    """进球记录（射手榜数据源）；一场一球员一条"""

    match = models.ForeignKey(Match, verbose_name='对阵', on_delete=models.CASCADE, related_name='goals')
    player = models.ForeignKey(Player, verbose_name='球员', on_delete=models.CASCADE, related_name='goals')
    goals = models.IntegerField('进球数', default=0)
    assists = models.IntegerField('助攻数', default=0)
    minute = models.IntegerField('进球分钟', null=True, blank=True)
    note = models.CharField('备注', max_length=200, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'portal_goal_record'
        verbose_name = '进球记录'
        unique_together = [('match', 'player')]

    def __str__(self):
        return f'{self.player} {self.goals}球'


class Penalty(models.Model):
    """判罚"""

    match = models.ForeignKey(Match, verbose_name='对阵', on_delete=models.CASCADE, related_name='penalties')
    player = models.ForeignKey(Player, verbose_name='球员', on_delete=models.CASCADE)
    type = models.CharField('类型', max_length=10, choices=[('yellow', '黄牌'), ('red', '红牌')])
    minute = models.IntegerField('分钟', null=True, blank=True)
    reason = models.CharField('原因', max_length=200, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'portal_penalty'
        verbose_name = '判罚'

    def __str__(self):
        return f'{self.get_type_display()} {self.player}'


class Referee(models.Model):
    """裁判（一场多条）"""

    ROLE_CHOICES = [('main', '主裁判'), ('linesman', '边裁'), ('fourth', '第四官员')]
    match = models.ForeignKey(Match, verbose_name='对阵', on_delete=models.CASCADE, related_name='referees')
    name = models.CharField('姓名', max_length=30)
    role = models.CharField('执裁角色', max_length=10, choices=ROLE_CHOICES, default='main')
    cert_level = models.CharField('等级', max_length=50, blank=True, default='')

    class Meta:
        db_table = 'portal_referee'
        verbose_name = '裁判'

    def __str__(self):
        return f'{self.name}({self.get_role_display()})'


class MatchEvent(models.Model):
    """图文直播条目"""

    class Type(models.TextChoices):
        GOAL = 'goal', '进球'
        SUBSTITUTION = 'substitution', '换人'
        CARD = 'card', '红黄牌'
        TEXT = 'text', '文字播报'

    match = models.ForeignKey(Match, verbose_name='对阵', on_delete=models.CASCADE, related_name='events')
    minute = models.IntegerField('分钟', null=True, blank=True)
    type = models.CharField('类型', max_length=20, choices=Type.choices, default='text')
    content = models.CharField('播报内容', max_length=255)
    published_at = models.DateTimeField('发布时间', default=timezone.now)

    class Meta:
        db_table = 'portal_match_event'
        verbose_name = '图文直播'
        ordering = ['published_at']

    def __str__(self):
        return self.content


class LiveStream(models.Model):
    """视频直播链接"""

    class Status(models.TextChoices):
        PENDING = 'pending', '未开始'
        LIVE = 'live', '直播中'
        ENDED = 'ended', '已结束'

    match = models.ForeignKey(Match, verbose_name='关联场次', on_delete=models.CASCADE, related_name='streams')
    platform = models.CharField('直播平台', max_length=50, blank=True, default='')
    url = models.CharField('直播链接', max_length=255)
    status = models.CharField('状态', max_length=10, choices=Status.choices, default='pending')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'portal_live_stream'
        verbose_name = '视频直播'

    def __str__(self):
        return f'{self.match} · {self.platform}'


class News(models.Model):
    """赛事新闻（门户展示）"""

    class Category(models.TextChoices):
        NEWS = 'news', '赛事动态'
        REPORT = 'report', '战报'
        ANNOUNCEMENT = 'announcement', '通知公告'

    title = models.CharField('标题', max_length=200)
    summary = models.CharField('摘要', max_length=500, blank=True, default='')
    content = models.TextField('正文 HTML')
    source = models.CharField('来源', max_length=100, blank=True, default='')
    category = models.CharField('类别', max_length=20, choices=Category.choices, default='news')
    cover = models.CharField('封面图', max_length=255, blank=True, default='')
    is_top = models.BooleanField('置顶', default=False)
    is_published = models.BooleanField('已发布', default=True, db_index=True)
    published_at = models.DateTimeField('发布时间', default=timezone.now)
    view_count = models.IntegerField('浏览量', default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='发布人',
                                   on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'portal_news'
        verbose_name = '赛事新闻'
        ordering = ['-is_top', '-published_at']

    def __str__(self):
        return self.title

    @property
    def category_display(self) -> str:
        return self.get_category_display()


class Policy(models.Model):
    """赛事政策"""

    title = models.CharField('标题', max_length=200)
    summary = models.CharField('摘要', max_length=500, blank=True, default='')
    content = models.TextField('正文 HTML')
    issuing_org = models.CharField('发布单位', max_length=100, blank=True, default='')
    cover = models.CharField('封面图', max_length=255, blank=True, default='')
    is_published = models.BooleanField('已发布', default=True, db_index=True)
    published_at = models.DateTimeField('发布时间', default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='发布人',
                                   on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'portal_policy'
        verbose_name = '赛事政策'
        ordering = ['-published_at']

    def __str__(self):
        return self.title


class Banner(models.Model):
    """门户轮播图"""

    title = models.CharField('标题', max_length=100, blank=True, default='')
    image = models.CharField('图片', max_length=255)
    link_url = models.CharField('外链', max_length=255, blank=True, default='')
    link_news = models.ForeignKey(News, verbose_name='跳转新闻', on_delete=models.SET_NULL,
                                  null=True, blank=True)
    sort = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('启用', default=True)
    start_at = models.DateTimeField('生效起', null=True, blank=True)
    end_at = models.DateTimeField('生效止', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'portal_banner'
        verbose_name = '轮播图'
        ordering = ['sort']

    def __str__(self):
        return self.title


class Partner(models.Model):
    """合作方"""

    name = models.CharField('名称', max_length=100)
    logo = models.CharField('Logo', max_length=255, blank=True, default='')
    website_url = models.CharField('官网', max_length=255, blank=True, default='')
    sort = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'portal_partner'
        verbose_name = '合作方'
        ordering = ['sort']

    def __str__(self):
        return self.name


class Highlight(models.Model):
    """精彩瞬间"""

    title = models.CharField('标题', max_length=100)
    description = models.CharField('说明', max_length=300, blank=True, default='')
    image = models.CharField('图片', max_length=255, blank=True, default='')
    video_url = models.CharField('视频', max_length=255, blank=True, default='')
    match = models.ForeignKey(Match, verbose_name='所属比赛', on_delete=models.SET_NULL,
                              null=True, blank=True)
    is_published = models.BooleanField('已发布', default=True, db_index=True)
    published_at = models.DateTimeField('发布时间', default=timezone.now)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'portal_highlight'
        verbose_name = '精彩瞬间'
        ordering = ['-published_at']

    def __str__(self):
        return self.title


class BestLineup(models.Model):
    """最佳阵容（含球员明细）"""

    title = models.CharField('标题', max_length=100)
    tournament_name = models.CharField('赛事名称', max_length=100, blank=True, default='')
    group_type = models.CharField('组别', max_length=20, choices=GroupType.choices, blank=True, default='')
    formation = models.CharField('阵型', max_length=20, blank=True, default='')
    match = models.ForeignKey(Match, verbose_name='关联比赛', on_delete=models.SET_NULL,
                              null=True, blank=True)
    description = models.CharField('说明', max_length=300, blank=True, default='')
    is_published = models.BooleanField('已发布', default=True, db_index=True)
    published_at = models.DateTimeField('发布时间', default=timezone.now)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'portal_best_lineup'
        verbose_name = '最佳阵容'
        ordering = ['-published_at']

    def __str__(self):
        return self.title


class BestLineupPlayer(models.Model):
    """最佳阵容明细"""

    lineup = models.ForeignKey(BestLineup, verbose_name='阵容', on_delete=models.CASCADE,
                               related_name='lineup_players')
    name = models.CharField('姓名', max_length=30)
    team_name = models.CharField('所属球队', max_length=100, blank=True, default='')
    position = models.CharField('位置', max_length=20, blank=True, default='')
    jersey_number = models.IntegerField('号码', null=True, blank=True)
    avatar = models.CharField('头像', max_length=255, blank=True, default='')
    sort = models.IntegerField('排序', default=0)

    class Meta:
        db_table = 'portal_best_lineup_player'
        verbose_name = '阵容球员'
        ordering = ['sort']


class SelectionScore(models.Model):
    """遴选评分：技评 + 体能"""

    player = models.ForeignKey(Player, verbose_name='球员', on_delete=models.CASCADE)
    group_type = models.CharField('组别', max_length=20, choices=GroupType.choices)
    technical = models.DecimalField('技评得分', max_digits=5, decimal_places=1, default=0)
    physical = models.DecimalField('体能得分', max_digits=5, decimal_places=1, default=0)
    total = models.DecimalField('总分', max_digits=5, decimal_places=1, default=0)
    status = models.CharField('状态', max_length=20, default='pending')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'portal_selection_score'
        verbose_name = '遴选评分'

    def save(self, *args, **kwargs):
        self.total = self.technical + self.physical
        super().save(*args, **kwargs)

    @property
    def player_name(self) -> str:
        return self.player.name


class SelectionBest(models.Model):
    """最佳球员公示"""

    group_type = models.CharField('组别', max_length=20, choices=GroupType.choices)
    player = models.ForeignKey(Player, verbose_name='球员', on_delete=models.CASCADE)
    total = models.DecimalField('综合得分', max_digits=5, decimal_places=1, default=0)
    status = models.CharField('公示状态', max_length=20, default='pending',
                              choices=[('pending', '待公示'), ('publicized', '已公示')])
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'portal_selection_best'
        verbose_name = '最佳球员'

    @property
    def player_name(self) -> str:
        return self.player.name

    @property
    def team_name(self) -> str:
        return self.player.team.name if self.player.team else ''
