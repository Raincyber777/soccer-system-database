from django.contrib import admin

from .models import (
    Banner,
    BestLineup,
    BestLineupPlayer,
    Coach,
    GoalRecord,
    Highlight,
    LiveStream,
    Match,
    MatchEvent,
    MatchResult,
    News,
    Partner,
    Penalty,
    Player,
    Policy,
    Referee,
    Registration,
    RegistrationPlayer,
    ReviewLog,
    SelectionBest,
    SelectionScore,
    Team,
    Tournament,
)

# Django 后台（/django-admin/）：赛事业务数据可视化维护


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'organizer', 'status', 'sign_start_at', 'sign_end_at')
    list_filter = ('status',)
    search_fields = ('name', 'organizer')


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'school', 'city_code', 'group_type', 'captain', 'is_active')
    list_filter = ('group_type', 'is_active')
    search_fields = ('name', 'captain')


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'gender', 'team', 'grade', 'position', 'jersey_number',
                    'status', 'is_active')
    list_filter = ('status', 'gender', 'is_active')
    search_fields = ('name', 'id_card', 'team__name')


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'gender', 'unit_name', 'cert_level', 'phone', 'team', 'status')
    list_filter = ('status',)
    search_fields = ('name', 'id_card', 'unit_name')


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'tournament', 'team_name', 'group_type', 'city_name', 'leader_name',
                    'coach_name', 'player_count', 'status', 'submit_time')
    list_filter = ('status', 'group_type')
    search_fields = ('team_name', 'leader_name', 'coach_name')
    date_hierarchy = 'submit_time'


@admin.register(RegistrationPlayer)
class RegistrationPlayerAdmin(admin.ModelAdmin):
    list_display = ('id', 'registration', 'name', 'id_card', 'jersey_number', 'position')
    search_fields = ('name',)


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'registration', 'stage', 'result', 'operator', 'created_at')
    list_filter = ('stage', 'result')


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'tournament_name', 'group_type', 'round_name', 'home_team',
                    'away_team', 'match_time', 'venue', 'status')
    list_filter = ('status', 'group_type')
    search_fields = ('home_team__name', 'away_team__name', 'tournament_name')


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'match', 'home_score', 'away_score', 'winner_team',
                    'is_published', 'published_at')
    list_filter = ('is_published',)


@admin.register(GoalRecord)
class GoalRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'match', 'player', 'goals', 'assists', 'minute', 'note')
    search_fields = ('player__name',)


@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ('id', 'match', 'player', 'type', 'minute', 'reason')
    list_filter = ('type',)


@admin.register(Referee)
class RefereeAdmin(admin.ModelAdmin):
    list_display = ('id', 'match', 'name', 'role', 'cert_level')
    list_filter = ('role',)


@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'match', 'minute', 'type', 'content', 'published_at')
    list_filter = ('type',)


@admin.register(LiveStream)
class LiveStreamAdmin(admin.ModelAdmin):
    list_display = ('id', 'match', 'platform', 'url', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'source', 'is_top', 'is_published',
                    'published_at', 'view_count')
    list_filter = ('category', 'is_published', 'is_top')
    search_fields = ('title', 'source')


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'issuing_org', 'is_published', 'published_at')
    list_filter = ('is_published',)
    search_fields = ('title',)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'image', 'link_url', 'sort', 'is_active', 'start_at', 'end_at')
    list_filter = ('is_active',)


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'website_url', 'sort', 'is_active')
    list_filter = ('is_active',)


@admin.register(Highlight)
class HighlightAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'match', 'is_published', 'published_at')
    list_filter = ('is_published',)
    search_fields = ('title',)


@admin.register(BestLineup)
class BestLineupAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'tournament_name', 'group_type', 'formation',
                    'is_published', 'published_at')
    list_filter = ('group_type', 'is_published')
    search_fields = ('title',)


@admin.register(BestLineupPlayer)
class BestLineupPlayerAdmin(admin.ModelAdmin):
    list_display = ('id', 'lineup', 'name', 'team_name', 'position', 'jersey_number', 'sort')
    search_fields = ('name',)


@admin.register(SelectionScore)
class SelectionScoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'player', 'group_type', 'technical', 'physical', 'total', 'status')
    list_filter = ('group_type', 'status')


@admin.register(SelectionBest)
class SelectionBestAdmin(admin.ModelAdmin):
    list_display = ('id', 'group_type', 'player', 'total', 'status')
    list_filter = ('group_type', 'status')


# 后台站点标题
admin.site.site_header = '绿茵汇 · 省级中小学足球系统管理后台'
admin.site.site_title = '绿茵汇后台'
admin.site.index_title = '数据管理'
