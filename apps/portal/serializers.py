"""序列化器：输出字段名与前端 src/api/types.ts 严格对齐"""
from rest_framework import serializers

from .models import (
    Banner, BestLineup, BestLineupPlayer, Coach, GoalRecord, Highlight, LiveStream,
    Match, MatchEvent, MatchResult, News, Partner, Penalty, Player, Policy, Referee,
    Registration, RegistrationPlayer, ReviewLog, SelectionBest, SelectionScore, Team, Tournament,
)


class TournamentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Tournament
        fields = ['id', 'name', 'group_types', 'organizer', 'sign_start_at', 'sign_end_at',
                  'status', 'status_display', 'created_at', 'updated_at']


class TeamSerializer(serializers.ModelSerializer):
    group_type_display = serializers.CharField(read_only=True)
    school_name = serializers.CharField(read_only=True)
    school_code = serializers.CharField(source='school.code', read_only=True, default='')
    city_name = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source='owner.real_name', read_only=True, default='')

    class Meta:
        model = Team
        fields = ['id', 'name', 'school', 'school_code', 'school_name', 'city_code', 'city_name',
                  'group_type', 'group_type_display', 'founded_at', 'captain', 'intro',
                  'flag_url', 'emblem_url', 'group_photo_url', 'honor_files',
                  'owner', 'owner_name', 'is_active', 'created_at', 'updated_at']

    def get_city_name(self, obj) -> str:
        from apps.common.models import Region
        region = Region.objects.filter(code=obj.city_code).first()
        return region.name if region else ''


class PlayerSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(read_only=True)
    group_type_display = serializers.CharField(read_only=True)
    school_name = serializers.CharField(read_only=True)
    school_code = serializers.CharField(source='school.code', read_only=True, default='')
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = ['id', 'team', 'team_name', 'group_type_display', 'name', 'gender', 'birth_date',
                  'id_card', 'school', 'school_code', 'school_name', 'grade', 'registry_no',
                  'position', 'jersey_number', 'phone', 'photo_url', 'intro',
                  'status', 'status_display', 'is_active', 'created_at', 'updated_at']

    def get_status_display(self, obj) -> str:
        return dict(Player.STATUS_CHOICES).get(obj.status, obj.status)


class CoachSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(read_only=True)
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Coach
        fields = ['id', 'name', 'gender', 'birth_date', 'id_card', 'phone', 'unit_name', 'years',
                  'cert_level', 'category', 'team', 'team_name', 'intro',
                  'status', 'status_display', 'created_at', 'updated_at']

    def get_status_display(self, obj) -> str:
        return dict(Coach.STATUS_CHOICES).get(obj.status, obj.status)


class ReviewLogSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.real_name', read_only=True, default='')

    class Meta:
        model = ReviewLog
        fields = ['id', 'stage', 'result', 'reason', 'operator', 'operator_name', 'created_at']


class RegistrationPlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationPlayer
        fields = ['id', 'name', 'id_card', 'jersey_number', 'position']


class RegistrationListSerializer(serializers.ModelSerializer):
    """列表用：字段与前端 MyRegistrations/初审/终审三页对齐"""

    tournament_name = serializers.CharField(source='tournament.name', read_only=True)
    group_type_display = serializers.CharField(source='get_group_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Registration
        fields = ['id', 'tournament', 'tournament_name', 'team', 'team_name', 'group_type',
                  'group_type_display', 'city_code', 'city_name', 'leader_name', 'phone',
                  'player_count', 'coach_name', 'status', 'status_display', 'submit_time']


class RegistrationSerializer(RegistrationListSerializer):
    """详情用：附球员名单、附件（FileField 原生可写，支持 multipart 上传）与审核记录"""

    review_logs = ReviewLogSerializer(many=True, read_only=True)
    registration_players = RegistrationPlayerSerializer(many=True, read_only=True)

    class Meta(RegistrationListSerializer.Meta):
        fields = RegistrationListSerializer.Meta.fields + [
            'remark', 'player_excel', 'photo_zip', 'stamp_file',
            'review_logs', 'registration_players', 'updated_at',
        ]


class RegistrationWriteSerializer(serializers.ModelSerializer):
    """球队提交/修改报名"""

    class Meta:
        model = Registration
        fields = ['tournament', 'team', 'group_type', 'leader_name', 'phone', 'player_count',
                  'coach_name', 'remark', 'player_excel', 'photo_zip', 'stamp_file']

    def validate(self, attrs):
        team = attrs.get('team')
        if team and not team.group_type:
            raise serializers.ValidationError({'team': '球队未设置组别，请先完善球队信息'})
        return attrs


class MatchResultSerializer(serializers.ModelSerializer):
    winner_team_name = serializers.CharField(read_only=True)

    class Meta:
        model = MatchResult
        fields = ['id', 'match', 'home_score', 'away_score', 'winner_team', 'winner_team_name',
                  'remark', 'is_published', 'published_at']


class MatchSerializer(serializers.ModelSerializer):
    group_type_display = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    home_team_name = serializers.CharField(source='home_team.name', read_only=True)
    away_team_name = serializers.CharField(source='away_team.name', read_only=True)
    result = MatchResultSerializer(read_only=True)
    created_by_name = serializers.CharField(source='created_by.real_name', read_only=True, default='')

    class Meta:
        model = Match
        fields = ['id', 'tournament', 'tournament_name', 'group_type', 'group_type_display',
                  'round_name', 'home_team', 'home_team_name', 'away_team', 'away_team_name',
                  'match_time', 'venue', 'status', 'status_display', 'remark', 'result',
                  'created_by_name', 'created_at', 'updated_at']


class GoalRecordSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source='player.name', read_only=True)
    team_name = serializers.CharField(source='player.team.name', read_only=True, default='')

    class Meta:
        model = GoalRecord
        fields = ['id', 'match', 'player', 'player_name', 'team_name', 'goals', 'assists',
                  'minute', 'note', 'created_at', 'updated_at']


class PenaltySerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source='player.name', read_only=True)

    class Meta:
        model = Penalty
        fields = ['id', 'match', 'player', 'player_name', 'type', 'minute', 'reason', 'created_at']


class RefereeSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = Referee
        fields = ['id', 'match', 'name', 'role', 'role_display', 'cert_level']


class MatchEventSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = MatchEvent
        fields = ['id', 'match', 'minute', 'type', 'type_display', 'content', 'published_at']


class LiveStreamSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    match_display = serializers.CharField(source='__str__', read_only=True)

    class Meta:
        model = LiveStream
        fields = ['id', 'match', 'match_display', 'platform', 'url', 'status', 'status_display', 'created_at']


class NewsSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.real_name', read_only=True, default='')

    class Meta:
        model = News
        fields = ['id', 'title', 'summary', 'cover', 'content', 'source', 'category',
                  'category_display', 'is_top', 'is_published', 'published_at', 'view_count',
                  'created_by_name', 'created_at', 'updated_at']


class PolicySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.real_name', read_only=True, default='')

    class Meta:
        model = Policy
        fields = ['id', 'title', 'summary', 'cover', 'content', 'issuing_org', 'is_published',
                  'published_at', 'created_by_name', 'created_at', 'updated_at']


class BannerSerializer(serializers.ModelSerializer):
    link_news_title = serializers.CharField(source='link_news.title', read_only=True, default='')

    class Meta:
        model = Banner
        fields = ['id', 'title', 'image', 'link_url', 'link_news', 'link_news_title',
                  'sort', 'is_active', 'start_at', 'end_at', 'created_at']


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ['id', 'name', 'logo', 'website_url', 'sort', 'is_active', 'created_at']


class HighlightSerializer(serializers.ModelSerializer):
    match_display = serializers.CharField(source='match.__str__', read_only=True, default='')

    class Meta:
        model = Highlight
        fields = ['id', 'title', 'description', 'image', 'video_url', 'match', 'match_display',
                  'is_published', 'published_at', 'created_at']


class BestLineupPlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BestLineupPlayer
        fields = ['id', 'name', 'team_name', 'position', 'jersey_number', 'avatar', 'sort']


class BestLineupSerializer(serializers.ModelSerializer):
    group_type_display = serializers.CharField(source='get_group_type_display', read_only=True)
    match_display = serializers.CharField(source='match.__str__', read_only=True, default='')
    players = BestLineupPlayerSerializer(many=True, read_only=True, source='lineup_players')

    class Meta:
        model = BestLineup
        fields = ['id', 'title', 'tournament_name', 'group_type', 'group_type_display',
                  'formation', 'match', 'match_display', 'description', 'is_published',
                  'published_at', 'players', 'created_at']


class BestLineupWriteSerializer(serializers.ModelSerializer):
    """发布最佳阵容：players 传数组整体替换明细"""

    players = BestLineupPlayerSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = BestLineup
        fields = ['title', 'tournament_name', 'group_type', 'formation', 'match',
                  'description', 'is_published', 'players']

    def create(self, validated_data):
        players = validated_data.pop('players', [])
        lineup = BestLineup.objects.create(**validated_data)
        self._replace_players(lineup, players)
        return lineup

    def update(self, instance, validated_data):
        players = validated_data.pop('players', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if players is not None:
            self._replace_players(instance, players)
        return instance

    @staticmethod
    def _replace_players(lineup, players):
        lineup.lineup_players.all().delete()
        for index, item in enumerate(players, start=1):
            BestLineupPlayer.objects.create(lineup=lineup, sort=item.get('sort', index), **{
                k: v for k, v in item.items() if k != 'sort'
            })


class SelectionScoreSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(read_only=True)
    player_team = serializers.CharField(source='player.team.name', read_only=True, default='')
    group_type_display = serializers.CharField(source='get_group_type_display', read_only=True)

    class Meta:
        model = SelectionScore
        fields = ['id', 'player', 'player_name', 'player_team', 'group_type', 'group_type_display',
                  'technical', 'physical', 'total', 'status', 'created_at']


class SelectionBestSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(read_only=True)
    team_name = serializers.CharField(read_only=True)
    group_type_display = serializers.CharField(source='get_group_type_display', read_only=True)

    class Meta:
        model = SelectionBest
        fields = ['id', 'group_type', 'group_type_display', 'player', 'player_name',
                  'team_name', 'total', 'status', 'created_at']
