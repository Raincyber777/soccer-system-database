"""portal 路由：/api/portal/* 业务资源 + /api/registrations 报名"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.register('portal/tournaments', views.TournamentViewSet, basename='tournament')
router.register('portal/teams', views.TeamViewSet, basename='team')
router.register('portal/players', views.PlayerViewSet, basename='player')
router.register('portal/coaches', views.CoachViewSet, basename='coach')
router.register('portal/news', views.NewsViewSet, basename='news')
router.register('portal/policy', views.PolicyViewSet, basename='policy')
router.register('portal/banners', views.BannerViewSet, basename='banner')
router.register('portal/partners', views.PartnerViewSet, basename='partner')
router.register('portal/highlights', views.HighlightViewSet, basename='highlight')
router.register('portal/best-lineups', views.BestLineupViewSet, basename='best-lineup')
router.register('portal/matches', views.MatchViewSet, basename='match')
router.register('portal/results', views.MatchResultViewSet, basename='result')
router.register('portal/goals', views.GoalRecordViewSet, basename='goal')
router.register('portal/penalties', views.PenaltyViewSet, basename='penalty')
router.register('portal/referees', views.RefereeViewSet, basename='referee')
router.register('portal/match-events', views.MatchEventViewSet, basename='match-event')
router.register('portal/live-streams', views.LiveStreamViewSet, basename='live-stream')
router.register('portal/selection-scores', views.SelectionScoreViewSet, basename='selection-score')
router.register('portal/selection-best', views.SelectionBestViewSet, basename='selection-best')
router.register('registrations', views.RegistrationViewSet, basename='registration')

urlpatterns = [
    path('', include(router.urls)),
    path('portal/publicity/players/', views.publicity_players, name='publicity-players'),
    path('portal/publicity/coaches/', views.publicity_coaches, name='publicity-coaches'),
    path('portal/stats/ranking/', views.stats_ranking, name='stats-ranking'),
    path('portal/stats/standings/', views.stats_standings, name='stats-standings'),
    path('portal/stats/group-goals/', views.stats_group_goals, name='stats-group-goals'),
    path('portal/verify/', views.verify_athlete, name='verify'),
]
