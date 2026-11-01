"""门户与业务视图：公开读 + 管理端写 + 两级审核流"""
from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.permissions import (
    IsAdminRole,
    IsStaffOrTeamOwner, IsAuthenticatedRole, IsStaffOrReadOnly, IsStaffRole, apply_region_scope,
)
from apps.accounts.models import log_action

from . import services
from .models import (
    Banner, BestLineup, Coach, GoalRecord, Highlight, LiveStream, Match, MatchEvent,
    MatchResult, News, Partner, Penalty, Player, PlayerMatchStat, Policy, Referee,
    Registration, ReviewLog, SelectionBest, SelectionScore, Team, Tournament,
)
from .serializers import (
    BannerSerializer, BestLineupSerializer, BestLineupWriteSerializer, CoachSerializer,
    GoalRecordSerializer, HighlightSerializer, LiveStreamSerializer, MatchEventSerializer,
    MatchResultSerializer, MatchSerializer, NewsSerializer, PartnerSerializer,
    PenaltySerializer, PlayerMatchStatSerializer, PlayerSerializer, PolicySerializer,
    RefereeSerializer, RegistrationListSerializer, RegistrationSerializer,
    RegistrationWriteSerializer, SelectionBestSerializer, SelectionScoreSerializer,
    TeamSerializer, TournamentSerializer,
)


class TournamentViewSet(viewsets.ModelViewSet):
    """赛事：公开读、管理端写"""

    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset().order_by('-created_at')
        p = self.request.query_params
        if group_type := p.get('group_type'):
            qs = qs.filter(group_types__contains=group_type)
        if level := p.get('level'):
            qs = qs.filter(level=level)
        if status := p.get('status'):
            qs = qs.filter(status=status)
        if name := p.get('name'):
            qs = qs.filter(name__icontains=name)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(self.request, f'创建了赛事 {instance.name}')


class TeamViewSet(viewsets.ModelViewSet):
    """球队：公开读；school 管本人球队、city/admin 管本区域"""

    serializer_class = TeamSerializer
    permission_classes = [IsStaffOrTeamOwner]

    def get_queryset(self):
        qs = Team.objects.select_related('school').order_by('-created_at')
        p = self.request.query_params
        # mine=true：仅本人球队（球队负责人管理自己球队用）
        if p.get('mine') == 'true':
            qs = qs.filter(owner=self.request.user)
        if group_type := p.get('group_type'):
            qs = qs.filter(group_type=group_type)
        if city := p.get('city_code'):
            qs = qs.filter(city_code=city)
        if name := p.get('name'):
            qs = qs.filter(name__icontains=name)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        team = serializer.save(owner=user if user.role == 'school' else None)
        log_action(self.request, f'创建了球队 {team.name}')

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == 'school' and serializer.instance.owner_id != user.id:
            raise PermissionDenied('只能修改本人的球队')
        team = serializer.save()
        log_action(self.request, f'更新了球队 {team.name}')

    def perform_destroy(self, instance):
        user = self.request.user
        if user.role == 'school' and instance.owner_id != user.id:
            raise PermissionDenied('只能删除本人的球队')
        log_action(self.request, f'删除了球队 {instance.name}')
        instance.delete()


class PersonViewSetMixin:
    """球员/教练共用的写权限控制：school 管本队，city 管本区域（列表按 query 过滤）"""

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == 'school':
            team = getattr(serializer.instance, 'team', None)
            if not team or team.owner_id != user.id:
                raise PermissionDenied('只能修改本人球队的资料')
        person = serializer.save()
        log_action(self.request, f'更新了 {person.name} 的资料')

    def perform_destroy(self, instance):
        user = self.request.user
        if user.role == 'school':
            team = getattr(instance, 'team', None)
            if not team or team.owner_id != user.id:
                raise PermissionDenied('只能删除本人球队的资料')
        log_action(self.request, f'删除了人员 {instance.name}')
        instance.delete()

    @action(detail=True, methods=['post'], url_path='review')
    def review(self, request, pk=None):
        """审核：approve 置 active / reject 置 rejected（city 本区域、admin 全省）"""
        person = self.get_object()
        result = request.data.get('result')
        if result not in ('approve', 'reject'):
            raise ValidationError({'result': '必须是 approve 或 reject'})
        person.status = 'active' if result == 'approve' else 'rejected'
        person.save(update_fields=['status'])
        label = '通过' if result == 'approve' else '驳回'
        log_action(request, f'{label}了 {type(person).__name__} {person.name} 的注册申请')
        return Response({'detail': f'已{label}', 'status': person.status})


class PlayerViewSet(PersonViewSetMixin, viewsets.ModelViewSet):
    serializer_class = PlayerSerializer
    permission_classes = [IsStaffOrTeamOwner]

    def get_queryset(self):
        qs = Player.objects.select_related('team', 'school').order_by('id')
        p = self.request.query_params
        if team := p.get('team'):
            qs = qs.filter(team_id=team)
        if group_type := p.get('group_type'):
            qs = qs.filter(team__group_type=group_type)
        if name := p.get('name'):
            qs = qs.filter(name__icontains=name)
        if id_card := p.get('id_card'):
            qs = qs.filter(id_card__icontains=id_card)
        if player_status := p.get('status'):
            qs = qs.filter(status=player_status)
        if p.get('is_active') == 'true':
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        team = serializer.validated_data.get('team')
        if user.role == 'school' and team and team.owner_id != user.id:
            raise PermissionDenied('只能为本人的球队报送球员')
        player = serializer.save()
        log_action(self.request, f'报送了球员 {player.name}')


class CoachViewSet(PersonViewSetMixin, viewsets.ModelViewSet):
    serializer_class = CoachSerializer
    permission_classes = [IsStaffOrTeamOwner]

    def get_queryset(self):
        qs = Coach.objects.select_related('team').order_by('id')
        p = self.request.query_params
        if team := p.get('team'):
            qs = qs.filter(team_id=team)
        if name := p.get('name'):
            qs = qs.filter(name__icontains=name)
        if status := p.get('status'):
            qs = qs.filter(status=status)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        team = serializer.validated_data.get('team')
        if user.role == 'school' and team and team.owner_id != user.id:
            raise PermissionDenied('只能为本人的球队报送教练')
        coach = serializer.save()
        log_action(self.request, f'报送了教练 {coach.name}')


class PublishedOrStaffMixin:
    """公开仅见已发布，管理端可见草稿"""

    published_field = 'is_published'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.role in ('admin', 'city'):
            return qs
        return qs.filter(**{self.published_field: True})


class NewsViewSet(PublishedOrStaffMixin, viewsets.ModelViewSet):
    queryset = News.objects.all()
    serializer_class = NewsSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset().order_by('-is_top', '-published_at')
        p = self.request.query_params
        if category := p.get('category'):
            qs = qs.filter(category=category)
        if tournament := p.get('tournament'):
            qs = qs.filter(tournament_id=tournament)
        if p.get('is_top') == 'true':
            qs = qs.filter(is_top=True)
        if keyword := p.get('search'):
            qs = qs.filter(title__icontains=keyword) | qs.filter(summary__icontains=keyword)
        return qs

    def perform_create(self, serializer):
        news = serializer.save(created_by=self.request.user)
        log_action(self.request, f'发布了新闻「{news.title}」')

    def perform_update(self, serializer):
        news = serializer.save()
        log_action(self.request, f'更新了新闻「{news.title}」')

    def perform_destroy(self, instance):
        log_action(self.request, f'删除了新闻「{instance.title}」')

    @action(detail=False, methods=['post'], url_path='generate-report')
    def generate_report(self, request):
        """AI 比赛报告：汇总单场赛果/进球/判罚/技术统计生成报告新闻并自动关联赛事与对阵。
        同一场比赛只生成一份，重复调用返回已有报告。当前为规则引擎版，
        外部 AI 模型接入后替换 _compose_ai_report 的实现即可，接口形态不变。"""
        match = Match.objects.filter(id=request.data.get('match')).select_related(
            'home_team', 'away_team', 'tournament').first()
        if match is None:
            raise ValidationError({'match': '对阵不存在'})
        existed = News.objects.filter(match=match, category=News.Category.AI_REPORT).first()
        if existed:
            return Response({'news': self.get_serializer(existed).data, 'existed': True})
        result = getattr(match, 'result', None)
        if result is None or not result.is_published:
            raise ValidationError({'match': '该对阵尚未发布赛果，请先在赛果管理中发布后再生成报告'})
        news = self._compose_ai_report(match, result)
        log_action(request, f'生成了比赛报告「{news.title}」')
        return Response({'news': self.get_serializer(news).data, 'existed': False},
                        status=status.HTTP_201_CREATED)

    def _compose_ai_report(self, match, result):
        """规则引擎版报告：结构化汇总比赛数据拼装 HTML。
        TODO 接入外部 AI 模型：本方法替换为模型 API 调用（输入比赛数据、输出报告文本）。"""
        m = match
        home, away = m.home_team, m.away_team
        score_part = f'{result.home_score}:{result.away_score}'
        if result.home_score > result.away_score:
            outcome = f'，{home.name} 获胜'
        elif result.home_score < result.away_score:
            outcome = f'，{away.name} 获胜'
        else:
            outcome = '，双方战平'
        title = f'比赛报告：{home.name} {score_part} {away.name}'
        summary = (f'{m.tournament_name or "本届赛事"}{m.round_name or ""}复盘：'
                   f'最终比分 {score_part}{outcome}，含进球记录、纪律情况与技术统计对比。')
        lines = [
            '<h3>比赛概况</h3>',
            f'<p>{m.tournament_name or "本届赛事"}（{m.get_group_type_display()}）{m.round_name or ""}，'
            f'{m.match_time.strftime("%Y-%m-%d %H:%M")}于 {m.venue or "—"} 举行，'
            f'{home.name} 对阵 {away.name}，最终比分 {score_part}{outcome}。</p>',
        ]
        goals = GoalRecord.objects.filter(match=m).select_related('player', 'player__team')
        if goals:
            rows = ''.join(
                f'<tr><td>{g.player.name}</td><td>{g.player.team.name if g.player.team else "—"}</td>'
                f'<td>{g.goals}</td><td>{g.assists}</td>'
                f'<td>{g.minute if g.minute is not None else "—"}</td></tr>'
                for g in goals
            )
            lines.append('<h3>进球记录</h3>'
                         '<table><thead><tr><th>球员</th><th>球队</th><th>进球</th><th>助攻</th><th>分钟</th></tr></thead>'
                         f'<tbody>{rows}</tbody></table>')
        else:
            lines.append('<h3>进球记录</h3><p>本场暂无进球记录。</p>')
        penalties = Penalty.objects.filter(match=m).select_related('player', 'player__team')
        if penalties:
            rows = ''.join(
                f'<tr><td>{p.player.name}</td><td>{p.player.team.name if p.player.team else "—"}</td>'
                f'<td>{p.get_type_display()}</td><td>{p.minute if p.minute is not None else "—"}</td>'
                f'<td>{p.reason or "—"}</td></tr>'
                for p in penalties
            )
            lines.append('<h3>纪律情况</h3>'
                         '<table><thead><tr><th>球员</th><th>球队</th><th>类型</th><th>分钟</th><th>原因</th></tr></thead>'
                         f'<tbody>{rows}</tbody></table>')
        stats = PlayerMatchStat.objects.filter(match=m).select_related('player', 'team')
        if stats:
            def totals(team):
                qs = stats.filter(team=team)
                return {k: sum(getattr(s, k) or 0 for s in qs)
                        for k in ('goals', 'assists', 'yellow_cards', 'red_cards', 'fouls')}
            ht, at = totals(home), totals(away)
            rows = ''.join(
                f'<tr><th>{label}</th><td>{ht[k]}</td><td>{at[k]}</td></tr>'
                for k, label in (('goals', '进球'), ('assists', '助攻'), ('yellow_cards', '黄牌'),
                                 ('red_cards', '红牌'), ('fouls', '犯规'))
            )
            lines.append(f'<h3>技术统计对比</h3>'
                         f'<table><thead><tr><th>指标</th><th>{home.name}</th><th>{away.name}</th></tr></thead>'
                         f'<tbody>{rows}</tbody></table>')
        lines.append('<p class="ai-note">本报告由系统基于比赛数据自动生成；AI 模型接入后将提供深度战术分析。</p>')
        return News.objects.create(
            title=title[:200], summary=summary[:500], content=''.join(lines),
            category=News.Category.AI_REPORT, source='AI 生成',
            ai_generated=True, is_published=True,
            tournament=m.tournament, match=m, created_by=self.request.user,
        )
        instance.delete()


class PolicyViewSet(PublishedOrStaffMixin, viewsets.ModelViewSet):
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset().order_by('-published_at')
        if keyword := self.request.query_params.get('search'):
            qs = qs.filter(title__icontains=keyword)
        return qs

    def perform_create(self, serializer):
        policy = serializer.save(created_by=self.request.user)
        log_action(self.request, f'发布了政策「{policy.title}」')


class BannerViewSet(PublishedOrStaffMixin, viewsets.ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    permission_classes = [IsStaffOrReadOnly]
    # Banner 的上架字段是 is_active（无 is_published），匿名列表过滤靠它
    published_field = 'is_active'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.role in ('admin', 'city'):
            return qs.order_by('sort')
        # 公开仅启用且在生效时间内
        from django.utils import timezone
        now = timezone.now()
        return qs.filter(is_active=True).filter(
            Q(start_at__isnull=True) | Q(start_at__lte=now)
        ).filter(Q(end_at__isnull=True) | Q(end_at__gte=now)).order_by('sort')


class PartnerViewSet(PublishedOrStaffMixin, viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    permission_classes = [IsStaffOrReadOnly]
    published_field = 'is_active'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_authenticated and self.request.user.role in ('admin', 'city'):
            return qs.order_by('sort')
        return qs.order_by('sort')


class HighlightViewSet(PublishedOrStaffMixin, viewsets.ModelViewSet):
    queryset = Highlight.objects.all()
    serializer_class = HighlightSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        if group_type := self.request.query_params.get('group_type'):
            qs = qs.filter(match__group_type=group_type)
        if match := self.request.query_params.get('match'):
            qs = qs.filter(match_id=match)
        return qs


class BestLineupViewSet(PublishedOrStaffMixin, viewsets.ModelViewSet):
    queryset = BestLineup.objects.all()
    permission_classes = [IsStaffOrReadOnly]

    def get_serializer_class(self):
        request = self.request
        if request.method in ('POST', 'PUT', 'PATCH'):
            return BestLineupWriteSerializer
        return BestLineupSerializer

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related('lineup_players')
        if group_type := self.request.query_params.get('group_type'):
            qs = qs.filter(group_type=group_type)
        if name := self.request.query_params.get('tournament_name'):
            qs = qs.filter(tournament_name__icontains=name)
        return qs

    def create(self, request, *args, **kwargs):
        """写入用 WriteSerializer（players 数组整体替换），响应用读序列化器（含 id 与明细）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        log_action(request, f'创建了最佳阵容：{instance.title}')
        return Response(BestLineupSerializer(instance, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(BestLineupSerializer(instance, context={'request': request}).data)


class MatchViewSet(viewsets.ModelViewSet):
    """对阵：公开读、管理端写；支持组别/状态/球队/赛事/关键词筛选"""

    serializer_class = MatchSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = Match.objects.select_related('home_team', 'away_team', 'result').order_by('match_time')
        p = self.request.query_params
        if status := p.get('status'):
            qs = qs.filter(status=status)
        if group_type := p.get('group_type'):
            qs = qs.filter(group_type=group_type)
        if team_id := p.get('team_id'):
            qs = qs.filter(Q(home_team_id=team_id) | Q(away_team_id=team_id))
        if team_name := p.get('team_name'):
            qs = qs.filter(Q(home_team__name__icontains=team_name) | Q(away_team__name__icontains=team_name))
        if tournament := p.get('tournament_name'):
            qs = qs.filter(tournament_name__icontains=tournament)
        if search := p.get('search'):
            qs = qs.filter(
                Q(home_team__name__icontains=search)
                | Q(away_team__name__icontains=search)
                | Q(tournament_name__icontains=search)
            )
        ordering = p.get('ordering')
        if ordering in ('match_time', '-match_time', 'id', '-id'):
            qs = qs.order_by(ordering)
        return qs

    def perform_create(self, serializer):
        match = serializer.save(created_by=self.request.user,
                                tournament_name=serializer.validated_data.get('tournament_name', ''))
        if match.tournament:
            Match.objects.filter(pk=match.pk).update(tournament_name=match.tournament.name)
        log_action(self.request, f'录入了对阵 {match}')

    def perform_destroy(self, instance):
        log_action(self.request, f'删除了对阵 {instance}')
        instance.delete()


class MatchResultViewSet(viewsets.ModelViewSet):
    """赛果：公开仅见已发布；创建时校验一场一结果，发布自动完赛"""

    serializer_class = MatchResultSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = MatchResult.objects.select_related('match', 'winner_team').order_by('-published_at')
        user = self.request.user
        if not (user.is_authenticated and user.role in ('admin', 'city')):
            qs = qs.filter(is_published=True)
        p = self.request.query_params
        if match := p.get('match'):
            qs = qs.filter(match_id=match)
        if group_type := p.get('group_type'):
            qs = qs.filter(match__group_type=group_type)
        if team_name := p.get('team_name'):
            qs = qs.filter(
                Q(match__home_team__name__icontains=team_name)
                | Q(match__away_team__name__icontains=team_name)
            )
        if p.get('is_published') == 'true':
            qs = qs.filter(is_published=True)
        return qs

    def perform_create(self, serializer):
        match = serializer.validated_data['match']
        if MatchResult.objects.filter(match=match).exists():
            raise ValidationError({'match': '该比赛已有赛果，不能重复发布'})
        result = serializer.save()
        self._auto_report(result)
        log_action(self.request, f'发布了赛果 {result.match} {result.home_score}:{result.away_score}')

    def _auto_report(self, result: MatchResult):
        """赛事内容自动关联/自动发送：赛果发布即自动生成战报新闻并关联赛事与对阵（一场一次）"""
        match = result.match
        if News.objects.filter(match=match, category=News.Category.REPORT).exists():
            return
        m = match
        score_part = f'{result.home_score}:{result.away_score}'
        round_part = f'{m.round_name} ' if m.round_name else ''
        title = f'{round_part}战报：{m.home_team.name} {score_part} {m.away_team.name}'.strip()
        summary = f'{m.home_team.name} {score_part} {m.away_team.name}' + (f'（{m.round_name}）' if m.round_name else '')
        lines = [
            f'<p>{m.tournament_name or "本届赛事"}（{m.get_group_type_display()}）{m.round_name or ""}，'
            f'{m.home_team.name} 与 {m.away_team.name} 的比赛已结束，最终比分 {score_part}。</p>',
        ]
        goals = GoalRecord.objects.filter(match=match).select_related('player', 'player__team')
        if goals:
            items = ''.join(
                f'<li>{g.player.name}（{g.player.team.name if g.player.team else "—"}）'
                f'进球 {g.goals}' + (f'／助攻 {g.assists}' if g.assists else '') + '</li>'
                for g in goals
            )
            lines.append(f'<p>本场进球记录：</p><ul>{items}</ul>')
        else:
            lines.append('<p>本场暂无进球记录。</p>')
        lines.append('<p>技术统计与精彩瞬间将持续更新，可在赛程赛果页查看详情。</p>')
        News.objects.create(
            title=title[:200], summary=summary[:500], content=''.join(lines),
            category=News.Category.REPORT, source='系统自动生成',
            is_published=True, tournament=m.tournament, match=match,
            created_by=self.request.user,
        )


class GoalRecordViewSet(viewsets.ModelViewSet):
    """进球记录：仅管理端（榜单数据源）"""

    serializer_class = GoalRecordSerializer
    permission_classes = [IsStaffRole]

    def get_queryset(self):
        qs = GoalRecord.objects.select_related('player', 'player__team', 'match').order_by('-id')
        p = self.request.query_params
        if match := p.get('match'):
            qs = qs.filter(match_id=match)
        if player := p.get('player'):
            qs = qs.filter(player_id=player)
        if team := p.get('team_id'):
            qs = qs.filter(player__team_id=team)
        if group_type := p.get('group_type'):
            qs = qs.filter(match__group_type=group_type)
        return qs

    def perform_create(self, serializer):
        record = serializer.save()
        log_action(self.request, f'登记了进球：{record.player.name} ×{record.goals}')


class PenaltyViewSet(viewsets.ModelViewSet):
    queryset = Penalty.objects.all()
    serializer_class = PenaltySerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset().select_related('player').order_by('-id')
        if match := self.request.query_params.get('match'):
            qs = qs.filter(match_id=match)
        return qs


class RefereeViewSet(viewsets.ModelViewSet):
    queryset = Referee.objects.all()
    serializer_class = RefereeSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset().order_by('id')
        if match := self.request.query_params.get('match'):
            qs = qs.filter(match_id=match)
        return qs


class MatchEventViewSet(viewsets.ModelViewSet):
    """图文直播条目"""

    queryset = MatchEvent.objects.all()
    serializer_class = MatchEventSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset().order_by('published_at')
        if match := self.request.query_params.get('match'):
            qs = qs.filter(match_id=match)
        return qs


class LiveStreamViewSet(viewsets.ModelViewSet):
    queryset = LiveStream.objects.all()
    serializer_class = LiveStreamSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset().order_by('-created_at')
        if match := self.request.query_params.get('match'):
            qs = qs.filter(match_id=match)
        if stream_status := self.request.query_params.get('status'):
            qs = qs.filter(status=stream_status)
        return qs


class RegistrationViewSet(viewsets.ModelViewSet):
    """报名与两级审核：
    提交(school 本队) → 初审(city 本区域) → 终审(admin) → approved 自动进入公示
    列表按角色数据域过滤；school 仅可改/删 待初审 或 已驳回 的报名件
    """

    permission_classes = [IsAuthenticatedRole]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            qs = Registration.objects.all()
        elif user.role == 'city':
            qs = Registration.objects.filter(city_code=user.region_code)
        else:
            qs = Registration.objects.filter(team__owner=user)
        qs = qs.select_related('tournament', 'team')
        p = self.request.query_params
        if team_name := p.get('team_name'):
            qs = qs.filter(team_name__icontains=team_name)
        if group_type := p.get('group_type'):
            qs = qs.filter(group_type=group_type)
        if status := p.get('status'):
            qs = qs.filter(status=status)
        if tournament := p.get('tournament'):
            qs = qs.filter(tournament_id=tournament)
        return qs.order_by('-submit_time')

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RegistrationWriteSerializer
        if self.action == 'list':
            return RegistrationListSerializer
        return RegistrationSerializer

    def perform_create(self, serializer):
        user = self.request.user
        team = serializer.validated_data.get('team')
        if user.role == 'school' and team and team.owner_id != user.id:
            raise PermissionDenied('只能为本人的球队提交报名')
        # 报名时间窗校验
        tournament = serializer.validated_data.get('tournament')
        if tournament and tournament.sign_end_at:
            from django.utils import timezone
            if timezone.now() > tournament.sign_end_at:
                raise ValidationError({'tournament': '已过该赛事报名截止时间'})
        # 报名前置校验：球队需先完善球员与教练信息（各至少 1 人）方可报名
        if team is not None and (team.players.count() < 1 or team.coaches.count() < 1):
            raise ValidationError({'team': '球队需先完善球员与教练信息（各至少 1 人）后方可报名'})
        reg = serializer.save(created_by=user, status=Registration.Status.PENDING_CITY)
        log_action(self.request, f'提交了报名：{reg.team_name} → {tournament.name if tournament else ""}')

    def create(self, request, *args, **kwargs):
        """提交报名：响应用详情 serializer（含 status/team_name），前端直接进入登录态展示"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(RegistrationSerializer(serializer.instance, context={'request': request}).data)

    def _ensure_editable(self, instance):
        if self.request.user.role == 'school' and instance.status not in (
            Registration.Status.PENDING_CITY, Registration.Status.REJECTED
        ):
            raise ValidationError({'status': '当前审核状态下不可修改或删除'})

    def perform_update(self, serializer):
        self._ensure_editable(serializer.instance)
        reg = serializer.save(status=Registration.Status.PENDING_CITY)  # 重新提交回到待初审
        log_action(self.request, f'修改并重新提交了报名：{reg.team_name}')

    def perform_destroy(self, instance):
        self._ensure_editable(instance)
        log_action(self.request, f'删除了报名：{instance.team_name}')
        instance.delete()

    @action(detail=True, methods=['post'], url_path='upload')
    def upload_file(self, request, pk=None):
        """上传报名附件（multipart：field ∈ player_excel/photo_zip/stamp_file + file）。
        独立 action：不改审核状态（school 补传盖章件不应把已通过的报名打回重审）"""
        registration = self.get_object()
        user = request.user
        if user.role == 'school':
            team = registration.team
            if team is None or team.owner_id != user.id:
                raise PermissionDenied('只能为本人的球队上传报名附件')
        field = request.data.get('field')
        if field not in ('player_excel', 'photo_zip', 'stamp_file'):
            raise ValidationError({'field': '必须是 player_excel / photo_zip / stamp_file'})
        file = request.FILES.get('file')
        if not file:
            raise ValidationError({'file': '缺少文件 file'})
        if file.size > 20 * 1024 * 1024:
            raise ValidationError({'file': '文件超过 20MB 上限'})
        setattr(registration, field, file)
        registration.save(update_fields=[field])
        log_action(request, f'上传了报名附件 {field}：{registration.team_name}')
        return Response(RegistrationSerializer(registration, context={'request': request}).data)

    def _review(self, request, stage: str):
        registration = self.get_object()
        result = request.data.get('result')
        reason = request.data.get('reason', '')
        if result not in ('approve', 'reject'):
            raise ValidationError({'result': '必须是 approve 或 reject'})
        if result == 'reject' and not reason:
            raise ValidationError({'reason': '驳回必须填写原因'})

        # 状态机校验：初审仅待初审件、终审仅待终审件，防止重复/跨级审核打乱状态
        expected = Registration.Status.PENDING_CITY if stage == 'city' else Registration.Status.PENDING_PROVINCE
        if registration.status != expected:
            raise ValidationError({'status': '该报名件当前状态不允许此审核操作'})

        # 数据域校验：city 只能审本区域
        if stage == 'city' and request.user.role == 'city':
            if registration.city_code and registration.city_code != request.user.region_code:
                raise PermissionDenied('仅能审核本区域的报名件')

        if stage == 'city':
            if result == 'approve':
                # 校级赛事为一级审核：市州审核通过即正式通过；市州级/省级赛事提交省级终审
                new_status = (Registration.Status.APPROVED
                              if registration.tournament.level == Tournament.Level.SCHOOL
                              else Registration.Status.PENDING_PROVINCE)
            else:
                new_status = Registration.Status.REJECTED
        else:
            new_status = Registration.Status.APPROVED if result == 'approve' else Registration.Status.REJECTED

        registration.status = new_status
        registration.save(update_fields=['status', 'updated_at'])
        ReviewLog.objects.create(
            registration=registration, stage=stage, result=result, reason=reason,
            operator=request.user,
        )
        if stage == 'city':
            label = '审核通过' if registration.tournament.level == Tournament.Level.SCHOOL else '通过初审'
        else:
            label = '终审'
        verb = '通过' if result == 'approve' else '驳回'
        log_action(request, f'{verb}了报名件（{label}）：{registration.team_name}')
        return Response(RegistrationSerializer(registration, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='first-review')
    def first_review(self, request, pk=None):
        """市州初审：通过自动提交省级终审（两级审核制衡：初审仅市州管理员，省级只做终审）"""
        if request.user.role != 'city':
            raise PermissionDenied('仅市州管理员可执行初审')
        return self._review(request, stage='city')

    @action(detail=True, methods=['post'], url_path='final-review')
    def final_review(self, request, pk=None):
        """省级终审：通过即 approved 并进入公示"""
        if not request.user.role == 'admin':
            raise PermissionDenied('仅省级管理员可执行终审')
        return self._review(request, stage='province')

    @action(detail=True, methods=['get'], url_path='review-logs')
    def review_logs(self, request, pk=None):
        registration = self.get_object()
        from .serializers import ReviewLogSerializer
        logs = registration.review_logs.all()
        return Response(ReviewLogSerializer(logs, many=True).data)

    @action(detail=True, methods=['get'], url_path='download/word')
    def download_word(self, request, pk=None):
        """下载球员报名信息表（简化：输出 CSV，Excel/WPS 可直接打开）"""
        import csv
        from django.http import HttpResponse
        registration = self.get_object()
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename=registration-{registration.pk}.csv'
        writer = csv.writer(response)
        writer.writerow(['姓名', '身份证号', '球衣号码', '场上位置'])
        for item in registration.registration_players.all():
            writer.writerow([item.name, item.id_card, item.jersey_number or '', item.position])
        return response


class SelectionScoreViewSet(viewsets.ModelViewSet):
    queryset = SelectionScore.objects.all()
    serializer_class = SelectionScoreSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset().select_related('player').order_by('-total')
        if group_type := self.request.query_params.get('group_type'):
            qs = qs.filter(group_type=group_type)
        return qs


class SelectionBestViewSet(viewsets.ModelViewSet):
    queryset = SelectionBest.objects.all()
    serializer_class = SelectionBestSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset().select_related('player', 'player__team').order_by('-total')
        if group_type := self.request.query_params.get('group_type'):
            qs = qs.filter(group_type=group_type)
        return qs


# ===== 函数式视图：公示 / 统计 / 核验 =====

@api_view(['GET'])
@permission_classes([AllowAny])
def publicity_players(request):
    """运动员公示（仅 active；系统参数 publicity_enabled 关闭时返回空）"""
    from apps.common.models import SystemConfig
    from apps.common.pagination import EnvelopePagination
    if not SystemConfig.objects.filter(key='publicity_enabled', value='true').exists():
        return Response([])
    qs = Player.objects.filter(status='active', is_active=True).select_related('team')
    if name := request.query_params.get('name'):
        qs = qs.filter(name__icontains=name)
    if group_type := request.query_params.get('group_type'):
        qs = qs.filter(team__group_type=group_type)
    page = EnvelopePagination().paginate_queryset(qs.order_by('id'), request)
    return Response(PlayerSerializer(page, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def publicity_coaches(request):
    """教练员公示（仅 active；系统参数 publicity_enabled 关闭时返回空）"""
    from apps.common.models import SystemConfig
    if not SystemConfig.objects.filter(key='publicity_enabled', value='true').exists():
        return Response([])
    qs = Coach.objects.filter(status='active').select_related('team')
    if name := request.query_params.get('name'):
        qs = qs.filter(name__icontains=name)
    return Response(CoachSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def stats_ranking(request):
    """射手榜：?group_type=&limit="""
    group_type = request.query_params.get('group_type') or None
    limit = int(request.query_params.get('limit', 20))
    return Response({'group_type': group_type, 'results': services.scorer_ranking(group_type, limit)})


@api_view(['GET'])
@permission_classes([AllowAny])
def stats_standings(request):
    """积分榜（后端聚合）：?group_type="""
    group_type = request.query_params.get('group_type') or None
    return Response({'group_type': group_type, 'results': services.standings(group_type)})


@api_view(['GET'])
@permission_classes([AllowAny])
def stats_group_goals(request):
    """组别进球统计：?group_type=&limit="""
    group_type = request.query_params.get('group_type') or None
    limit = int(request.query_params.get('limit', 10))
    return Response({'groups': services.group_goals_stats(group_type, limit)})


@api_view(['GET'])
@permission_classes([IsStaffRole])
def verify_athlete(request):
    """参赛身份核验：注册已生效 + 球队报名已通过 → 核验通过"""
    id_card = request.query_params.get('id_card', '')
    match_id = request.query_params.get('match')
    player = Player.objects.filter(id_card=id_card).select_related('team').first()
    if not player:
        return Response({'verify_result': 'fail', 'verify_result_display': '未找到该身份证号的注册球员'})

    team = player.team
    registration = None
    if team:
        reg_qs = Registration.objects.filter(team=team, status=Registration.Status.APPROVED)
        if match_id and (match := Match.objects.filter(pk=match_id).first()):
            if match.tournament:
                reg_qs = reg_qs.filter(tournament=match.tournament)
        registration = reg_qs.first()

    passed = player.status == 'active' and registration is not None
    return Response({
        'name': player.name,
        'id_card': player.id_card,
        'team_name': team.name if team else '',
        'player_status': player.status,
        'registration_status': registration.status if registration else None,
        'verify_result': 'pass' if passed else 'fail',
        'verify_result_display': '核验通过' if passed else '核验不通过（注册未生效或报名未通过）',
    })

# ---------- 球员比赛技术统计：全量红黄牌/犯规/进球数据 + 多主体查询 ----------

class PlayerMatchStatViewSet(viewsets.ModelViewSet):
    """球员比赛技术统计：管理端录入（红黄牌/犯规/进球/出场时间），个人/球队/区域按权限查询"""

    queryset = PlayerMatchStat.objects.select_related(
        'match', 'player', 'team', 'match__home_team', 'match__away_team', 'match__tournament',
    )
    serializer_class = PlayerMatchStatSerializer

    def get_permissions(self):
        # 读取类（列表/详情/个人/汇总）登录即可，数据域在 get_queryset 里按角色收窄
        if self.action in ('list', 'retrieve', 'mine', 'summary'):
            return [IsAuthenticatedRole()]
        return [IsStaffRole()]

    def get_queryset(self):
        qs = super().get_queryset().order_by('-match__match_time')
        p = self.request.query_params
        user = self.request.user
        # 数据域：市州看本市、球队负责人看本队、运动员/教练看本人（按实名身份证匹配）
        if user.role == 'city':
            qs = qs.filter(Q(match__home_team__city_code=user.region_code)
                           | Q(match__away_team__city_code=user.region_code))
        elif user.role == 'school':
            qs = qs.filter(team__owner=user)
        elif user.role in ('athlete', 'coach'):
            qs = qs.filter(player__id_card=user.id_card) if user.id_card else qs.none()
        if match := p.get('match'):
            qs = qs.filter(match_id=match)
        if player := p.get('player'):
            qs = qs.filter(player_id=player)
        if team := p.get('team'):
            qs = qs.filter(team_id=team)
        if days := p.get('days'):
            from datetime import timedelta
            from django.utils import timezone
            try:
                qs = qs.filter(match__match_time__gte=timezone.now() - timedelta(days=int(days)))
            except ValueError:
                pass
        return qs

    def _bind_team(self, serializer):
        # team 冗余自球员归属，录入时自动带出，不信任前端传值
        player = serializer.validated_data.get('player')
        if player and player.team_id:
            serializer.validated_data['team'] = player.team

    def perform_create(self, serializer):
        self._bind_team(serializer)
        stat = serializer.save()
        log_action(self.request, f'录入了比赛技术统计：{stat.player.name} @ {stat.match}')

    def perform_update(self, serializer):
        self._bind_team(serializer)
        stat = serializer.save()
        log_action(self.request, f'更新了比赛技术统计：{stat.player.name} @ {stat.match}')

    def perform_destroy(self, instance):
        label = f'{instance.player.name} @ {instance.match}'
        instance.delete()
        log_action(self.request, f'删除了比赛技术统计：{label}')

    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request):
        """我的参赛数据：当前账号按实名身份证匹配注册球员，逐场返回技术统计"""
        user = request.user
        player = Player.objects.filter(id_card=user.id_card).select_related('team').first() if user.id_card else None
        if not player:
            return Response({
                'player': None, 'items': [], 'summary': self._aggregate(self.get_queryset()),
                'hint': '请先在个人中心填写身份证号完成实名认证，认证后即可查看个人参赛数据',
            })
        qs = self.get_queryset().filter(player=player)
        return Response({
            'player': {'id': player.id, 'name': player.name,
                       'team': player.team.name if player.team else '—'},
            'items': PlayerMatchStatSerializer(qs, many=True).data,
            'summary': self._aggregate(qs),
        })

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """统计汇总：?player_id= 单球员全量 / ?team_id= 球队汇总 / ?days=7|30 时间筛选"""
        user = request.user
        qs = self.get_queryset()
        player_id = request.query_params.get('player_id')
        team_id = request.query_params.get('team_id')
        # 显式指定球员/球队时的越权防护：非省市级角色须在自身数据域内
        if player_id and user.role not in ('city', 'admin') and not qs.filter(player_id=player_id).exists():
            raise PermissionDenied('无权查看该球员的统计数据')
        if team_id and user.role not in ('city', 'admin', 'school') and not qs.filter(team_id=team_id).exists():
            raise PermissionDenied('无权查看该球队的统计数据')
        return Response(self._aggregate(qs))

    @staticmethod
    def _aggregate(qs) -> dict:
        from django.db.models import Count, Sum
        row = qs.aggregate(matches=Count('id'), goals=Sum('goals'), assists=Sum('assists'),
                           yellow=Sum('yellow_cards'), red=Sum('red_cards'), fouls=Sum('fouls'),
                           minutes=Sum('minutes'))
        return {
            'matches': row['matches'] or 0,
            'goals': row['goals'] or 0,
            'assists': row['assists'] or 0,
            'yellow_cards': row['yellow'] or 0,
            'red_cards': row['red'] or 0,
            'fouls': row['fouls'] or 0,
            'minutes': row['minutes'] or 0,
        }
