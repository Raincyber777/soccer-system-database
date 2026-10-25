"""统计聚合：射手榜 / 组别统计 / 积分榜（口径：仅统计已发布赛果）"""
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from .models import GoalRecord, Match, Player, Team


def _published_matches(group_type=None):
    qs = Match.objects.filter(result__is_published=True).select_related('result', 'home_team', 'away_team')
    if group_type:
        qs = qs.filter(group_type=group_type)
    return qs


def scorer_ranking(group_type=None, limit=20):
    """射手榜：active 球员按已发布赛果中的进球聚合，助攻同口径"""
    qs = Player.objects.filter(status='active', team__isnull=False, is_active=True)
    if group_type:
        qs = qs.filter(team__group_type=group_type)
    published = Q(goals__match__result__is_published=True)
    qs = (
        qs.annotate(
            total_goals=Coalesce(Sum('goals__goals', filter=published), 0),
            total_assists=Coalesce(Sum('goals__assists', filter=published), 0),
            match_count=Count('goals', filter=published, distinct=True),
        )
        .filter(total_goals__gt=0)
        .order_by('-total_goals', 'name', 'id')[: max(1, min(limit, 100))]
    )
    return [
        {
            'rank': index,
            'player_id': item.id,
            'player_name': item.name,
            'jersey_number': item.jersey_number,
            'position': item.position,
            'team_id': item.team_id,
            'team_name': item.team.name,
            'group_type': item.team.group_type,
            'group_type_display': item.team.get_group_type_display(),
            'total_goals': item.total_goals,
            'assists': item.total_assists,
            'match_count': item.match_count,
        }
        for index, item in enumerate(qs, start=1)
    ]


def group_goals_stats(group_type=None, limit=10):
    """组别进球统计：team_count / player_count / scorer_count / total_goals / top_players"""
    from .models import GroupType

    groups = [group_type] if group_type else list(GroupType.values)
    data = []
    for group in groups:
        display = GroupType(group).label
        teams = Team.objects.filter(group_type=group, is_active=True)
        players = Player.objects.filter(team__group_type=group, status='active', is_active=True)
        goals = GoalRecord.objects.filter(match__group_type=group, match__result__is_published=True)
        top = scorer_ranking(group, limit)
        data.append({
            'group_type': group,
            'group_type_display': display,
            'team_count': teams.count(),
            'player_count': players.count(),
            'scorer_count': goals.values('player').distinct().count(),
            'total_goals': goals.aggregate(total=Coalesce(Sum('goals'), 0))['total'],
            'top_players': top,
        })
    return data


def standings(group_type=None):
    """积分榜：胜 3 平 1 负 0；同分按净胜球 → 进球数 → 球队名"""
    agg: dict = {}
    for match in _published_matches(group_type):
        result = match.result
        group = match.group_type
        display = match.get_group_type_display()

        def entry(team):
            key = (team.id, group)
            if key not in agg:
                agg[key] = {
                    'team_id': team.id, 'team_name': team.name, 'group_type': group,
                    'group_type_display': display,
                    'played': 0, 'win': 0, 'draw': 0, 'loss': 0,
                    'goals_for': 0, 'goals_against': 0, 'points': 0,
                }
            return agg[key]

        home = entry(match.home_team)
        away = entry(match.away_team)
        hs, as_ = result.home_score, result.away_score
        for side, gf, ga in ((home, hs, as_), (away, as_, hs)):
            side['played'] += 1
            side['goals_for'] += gf
            side['goals_against'] += ga
            if gf > ga:
                side['win'] += 1
                side['points'] += 3
            elif gf < ga:
                side['loss'] += 1
            else:
                side['draw'] += 1
                side['points'] += 1

    # 组内排序后重新编号
    rows = list(agg.values())
    rows.sort(key=lambda r: r['team_name'])
    by_group: dict = {}
    for row in rows:
        by_group.setdefault(row['group_type_display'], []).append(row)

    result_rows = []
    for _, group_rows in by_group.items():
        group_rows.sort(key=lambda r: (
            -r['points'],
            -(r['goals_for'] - r['goals_against']),
            -r['goals_for'],
            r['team_name'],
        ))
        for index, row in enumerate(group_rows, start=1):
            row['rank'] = index
            row['goal_diff'] = row['goals_for'] - row['goals_against']
            result_rows.append(row)
    result_rows.sort(key=lambda r: (r['group_type_display'], r['rank']))
    return result_rows
