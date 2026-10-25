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
    MatchResult, News, Partner, Penalty, Player, Policy, Referee, Registration, ReviewLog,
    SelectionBest, SelectionScore, Team, Tournament,
)
from .serializers import (
    BannerSerializer, BestLineupSerializer, BestLineupWriteSerializer, CoachSerializer,
    GoalRecordSerializer, HighlightSerializer, LiveStreamSerializer, MatchEventSerializer,
    MatchResultSerializer, MatchSerializer, NewsSerializer, PartnerSerializer,
    PenaltySerializer, PlayerSerializer, PolicySerializer, RefereeSerializer,
    RegistrationListSerializer, RegistrationSerializer, RegistrationWriteSerializer,
    SelectionBestSerializer, SelectionScoreSerializer, TeamSerializer, TournamentSerializer,
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
        log_action(self.request, f'发布了赛果 {result.match} {result.home_score}:{result.away_score}')


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

        # 数据域校验：city 只能审本区域
        if stage == 'city' and request.user.role == 'city':
            if registration.city_code and registration.city_code != request.user.region_code:
                raise PermissionDenied('仅能审核本区域的报名件')

        if stage == 'city':
            new_status = (Registration.Status.PENDING_PROVINCE if result == 'approve'
                          else Registration.Status.REJECTED)
        else:
            new_status = Registration.Status.APPROVED if result == 'approve' else Registration.Status.REJECTED

        registration.status = new_status
        registration.save(update_fields=['status', 'updated_at'])
        ReviewLog.objects.create(
            registration=registration, stage=stage, result=result, reason=reason,
            operator=request.user,
        )
        label = '通过初审' if stage == 'city' else '终审'
        verb = '通过' if result == 'approve' else '驳回'
        log_action(request, f'{verb}了报名件（{label}）：{registration.team_name}')
        return Response(RegistrationSerializer(registration, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='first-review')
    def first_review(self, request, pk=None):
        """市州初审：通过自动提交省级终审"""
        if request.user.role not in ('city', 'admin'):
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
    """运动员公示（仅 active）"""
    from apps.common.pagination import EnvelopePagination
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
    """教练员公示（仅 active）"""
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
