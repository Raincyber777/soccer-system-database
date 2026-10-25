"""
演示种子数据：python manage.py seed_demo

幂等：检测到 admin001 账号已存在则跳过。灌入内容与前端演示 mock 同口径：
- 5 个演示账号（密码均 123456，与登录页一键登录对应）
- 21 市州 + 成都区县示例 + 19 所学校（前端 SchoolSelect 数据源）
- 1 个报名中赛事、11 支球队、注册球员、教练
- 对阵 11 场（已发布赛果 5 场，与门户「赛程赛果」页一致）+ 进球/助攻记录
- 新闻 6 条、政策 3 条（与门户「新闻政策」页一致）
- 报名件 4 条（覆盖 待初审/待终审/已驳回 全状态）+ 审核记录
- 轮播图/合作方/精彩瞬间/最佳阵容/图文直播/字典/系统参数
"""
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.common.models import DictItem, Region, School, SystemConfig
from apps.portal.models import (
    Banner, BestLineup, BestLineupPlayer, Coach, GoalRecord, Highlight, LiveStream,
    Match, MatchEvent, MatchResult, News, Partner, Penalty, Player, Policy, Referee,
    Registration, RegistrationPlayer, ReviewLog, SelectionBest, SelectionScore, Team, Tournament,
)

DT = None  # 占位避免误用；统一走 dt()


def dt(date_str: str, time_str: str = '15:00'):
    """演示时间：USE_TZ=False 全链路 naive 本地时间"""
    return datetime.datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')


CITIES = [
    ('510100', '成都市'), ('510300', '自贡市'), ('510400', '攀枝花市'), ('510500', '泸州市'),
    ('510600', '德阳市'), ('510700', '绵阳市'), ('510800', '广元市'), ('510900', '遂宁市'),
    ('511000', '内江市'), ('511100', '乐山市'), ('511300', '南充市'), ('511400', '眉山市'),
    ('511500', '宜宾市'), ('511600', '广安市'), ('511700', '达州市'), ('511800', '雅安市'),
    ('511900', '巴中市'), ('512000', '资阳市'), ('513200', '阿坝州'), ('513300', '甘孜州'),
    ('513400', '凉山州'),
]

CHENGDU_DISTRICTS = [
    ('510104', '锦江区'), ('510105', '青羊区'), ('510106', '金牛区'), ('510107', '武侯区'),
    ('510108', '成华区'), ('510112', '龙泉驿区'), ('510114', '新都区'), ('510115', '温江区'),
    ('510116', '双流区'), ('510117', '郫都区'),
]

SCHOOLS = [
    ('5101050003', '成都市实验小学', '510100', '青羊区', 'primary'),
    ('5101050002', '成都市石室联合中学', '510100', '青羊区', 'middle'),
    ('5101040001', '四川师范大学附属中学', '510100', '锦江区', 'high'),
    ('5101070004', '成都市第七中学', '510100', '武侯区', 'high'),
    ('5101160008', '四川省双流棠湖中学', '510100', '双流区', 'high'),
    ('5101080009', '成都市实验中学', '510100', '成华区', 'middle'),
    ('5101070005', '四川大学', '510100', '武侯区', 'university'),
    ('5101080007', '电子科技大学', '510100', '成华区', 'university'),
    ('5101070006', '成都体育学院', '510100', '武侯区', 'university'),
    ('5107030001', '四川省绵阳中学', '510700', '涪城区', 'high'),
    ('5107030002', '绵阳南山中学', '510700', '涪城区', 'high'),
    ('5107030003', '西南科技大学', '510700', '涪城区', 'university'),
    ('5106030001', '四川省德阳中学', '510600', '旌阳区', 'high'),
    ('5106030002', '德阳市第一小学', '510600', '旌阳区', 'primary'),
    ('5115020001', '宜宾市第一中学校', '511500', '翠屏区', 'high'),
    ('5115020002', '宜宾市人民路小学', '511500', '翠屏区', 'primary'),
    ('5113020001', '四川省南充高级中学', '511300', '顺庆区', 'high'),
    ('5113020002', '西华师范大学', '511300', '顺庆区', 'university'),
    ('5117020001', '达州市第一中学', '511700', '通川区', 'high'),
]

ACCOUNTS = [
    ('user001', 'school', '李负责人', None, '', '实验中学'),
    ('student001', 'athlete', '王小磊', None, '', '实验中学'),
    ('coach001', 'coach', '张建国', None, '', '实验中学'),
    ('admin001', 'city', '市州管理员', '510100', '成都市', '成都市教育局'),
    ('super001', 'admin', '省级管理员', None, '省本级', '四川省教育厅'),
]

NEWS = [
    ('赛事动态', '小学组第二轮本周开打，实小少年队冲击两连胜', '赛事组委会', '2026-10-23',
     '小学组第二轮实小少年队对阵朝阳小学的比赛今日 14:00 在市体育中心副场进行，图文直播同步开启。',
     ['首轮 5:2 大胜城关小学的实小少年队将于今日 14:00 迎来小组第二个对手朝阳小学。若能取胜，实小少年队将以两连胜提前占据小组出线主动权。',
      '本场比赛在市体育中心副场进行，赛事组委会将在「赛事图文直播」中提供逐分钟文字直播，欢迎各校师生关注。']),
    ('通知公告', '2026 省青少年校园足球联赛（秋季）开赛公告', '四川省足球协会', '2026-10-15',
     '省级总决赛定于 10 月 12 日在省青少年足球基地拉开帷幕，各组别报名球队经市州初审、省级终审后正式参赛。',
     ['2026 年四川省青少年校园足球联赛（秋季）省级总决赛已于 10 月 12 日正式开赛。本届联赛设小学组、中学组、高中组、高校组四个组别，全省 21 个市州共 128 支球队报名参赛。',
      '所有报名球队均经过市州管理员初审与省级终审两级审核，审核通过的球队名单与参赛信息已在平台公示，可登录用户端「信息公示」查看。',
      '比赛将持续至 11 月下旬，赛程对阵与比赛结果将在本平台「赛程赛果」页面实时更新。']),
    ('战报', '第三轮战报：实验中学 3:1 市二中', '赛事组委会', '2026-10-22',
     '王小磊梅开二度、李泽宇锦上添花，实验中学足球队 3:1 战胜市二中，豪取三连胜领跑中学组积分榜。',
     ['中学组第三轮焦点战中，实验中学足球队凭借王小磊的梅开二度与李泽宇的进球，以 3:1 战胜市二中足球队，开赛以来三战全胜，继续领跑中学组积分榜。',
      '市二中由周子豪在下半场扳回一球。第四轮实验中学将客场挑战师大附中，比赛定于 10 月 25 日 15:00 在省青少年足球基地 1 号场进行。']),
    ('通知公告', '关于开展 2026 年四川省中小学足球运动员注册工作的通知', '四川省教育厅', '2026-10-08',
     '全省中小学足球运动员实行统一注册管理，学籍信息与学校标识码绑定，注册信息审核通过后方可参赛。',
     ['为规范校园足球赛事管理，全省中小学足球运动员实行统一注册。运动员注册须绑定学籍信息与教育部学校（机构）标识码，由所在学校统一组织申报。',
      '注册信息经市州管理员审核通过后生效，未生效的注册信息不参与参赛资格校验。各学校请于 11 月 10 日前完成本校运动员注册申报。']),
    ('新闻动态', '成都市校园足球特色校建设成果巡礼', '成都市教育局', '2026-10-06',
     '全市已建成校园足球特色学校 187 所，常态化班级联赛覆盖率达 92%，为省级联赛输送球员 400 余人。',
     ['近年来成都市持续推进校园足球特色学校建设，目前已建成特色学校 187 所，班级联赛常态化开展率达 92%。',
      '依托「教学 + 训练 + 竞赛」一体化体系，成都市为省级联赛输送优秀球员 400 余名，实验中学、成都七中等学校在历届省级赛事中均取得优异成绩。']),
    ('新闻动态', '川师大队首次出征省级联赛高校组', '四川师范大学', '2026-09-28',
     '川师大队以校园组冠军身份首次晋级省级联赛高校组，首轮 0:2 惜败四川大学队，积累经验再出发。',
     ['四川师范大学足球队今年以校内联赛冠军身份首次晋级省级联赛高校组。首轮比赛中 0:2 不敌传统强队四川大学队。',
      '主教练张建国表示，球队将认真总结首轮经验，在 10 月 26 日对阵西南交通大学队的第二轮比赛中全力争胜。']),
]

POLICIES = [
    ('四川省青少年校园足球联赛竞赛规程（2026 秋季修订版）', '四川省教育厅 · 四川省足球协会', '2026-09-30',
     '明确本届联赛组别设置、报名资格、竞赛办法、名次评定与纪律要求。',
     ['第一章 总则：联赛由四川省教育厅、四川省足球协会联合主办，设小学组、中学组、高中组、高校组，实行赛会制与主客场相结合的竞赛办法。',
      '第二章 报名资格：参赛运动员须为在籍在校学生，注册信息审核通过并与学校标识码绑定；每队报名运动员 18-22 人，教练员须持有效等级证书。',
      '第三章 竞赛办法与名次评定：小组单循环 + 淘汰赛；积分相同时依次按相互间胜负、净胜球、进球数排定名次。']),
    ('四川省中小学足球运动员注册管理办法（试行）', '四川省教育厅', '2026-09-18',
     '规范运动员注册流程：学籍绑定、学校标识码校验、市州审核与注册有效期管理。',
     ['第一条 全省中小学足球运动员实行统一注册管理，注册信息包括学籍信息、身份信息与运动履历。',
      '第二条 注册须绑定教育部学校（机构）标识码，系统校验学校存在且启用、与所属市州一致后方可提交。',
      '第三条 注册信息由市州管理员审核，审核通过后生效并公示；未生效的注册信息不参与参赛资格校验。']),
    ('校园足球特色学校建设与评价指南', '四川省教育厅', '2026-09-05',
     '从课程教学、训练竞赛、师资配备、场地设施等维度提出特色学校建设标准与评价指标。',
     ['特色学校应保证每周不少于 1 次足球课，常态化开展班级联赛，并按标准配齐足球场地与器材设施。',
      '评价体系包含课程教学（30 分）、训练竞赛（30 分）、师资队伍（20 分）、场地设施（10 分）、文化建设（10 分），总分 90 分以上可申报示范校。']),
]


def html(paragraphs: list[str]) -> str:
    return ''.join(f'<p>{p}</p>' for p in paragraphs)


class Command(BaseCommand):
    help = '灌入演示数据（幂等）'

    def handle(self, *args, **options):
        if User.objects.filter(username='admin001').exists():
            self.stdout.write(self.style.WARNING('演示数据已存在，跳过（重建请删除 db.sqlite3 后重新 migrate + seed）'))
            return

        self._seed_regions_schools()
        self._seed_accounts()
        tournament = self._seed_tournament()
        teams = self._seed_teams()
        players = self._seed_players(teams)
        self._seed_coaches(teams)
        matches = self._seed_matches(teams, tournament)
        self._seed_goals(matches, players)
        self._seed_news_policy()
        self._seed_registrations(teams, tournament)
        self._seed_content(matches)
        self._seed_selection(players)
        self._seed_misc()

        self.stdout.write(self.style.SUCCESS('演示数据灌入完成：演示账号 5 个（密码 123456），门户数据与前端 mock 同口径'))

    # ---------- 基础数据 ----------

    def _seed_regions_schools(self):
        for code, name in CITIES:
            Region.objects.create(code=code, name=name, parent_code=None)
        for code, name in CHENGDU_DISTRICTS:
            Region.objects.create(code=code, name=name, parent_code='510100')
        for code, name, city, district, stage in SCHOOLS:
            School.objects.create(code=code, name=name, city_code=city, district_name=district, stage=stage)

    def _seed_accounts(self):
        for username, role, name, region_code, region_name, unit in ACCOUNTS:
            User.objects.create_user(
                username=username, password='123456', role=role, real_name=name,
                region_code=region_code, region_name=region_name, unit_name=unit,
                email=f'{username}@demo.cn', is_staff=role in ('admin', 'city'),
            )

    def _seed_tournament(self) -> Tournament:
        return Tournament.objects.create(
            name='2026 省青少年校园足球联赛（秋季）',
            group_types=['primary', 'middle', 'high', 'university'],
            organizer='四川省教育厅 · 四川省足球协会',
            sign_start_at=dt('2026-10-15', '00:00'),
            sign_end_at=dt('2026-11-05', '23:59'),
            status='signing',
        )

    def _seed_teams(self) -> dict:
        school = {s.code: s for s in School.objects.all()}
        spec = {
            # key: (名称, 学校code|None, 组别)
            'shiyan': ('实验中学足球队', '5101080009', None),
            'shiyi': ('一中队', None, 'middle'),
            'ershizhong': ('市二中足球队', None, 'middle'),
            'fuzhong': ('师大附中队', '5101040001', None),
            'shixiao': ('实小少年队', '5101050003', None),
            'chengguan': ('城关小学队', None, 'primary'),
            'chaoyang': ('朝阳小学队', None, 'primary'),
            'scu': ('四川大学队', '5101070005', None),
            'csd': ('川师大队', None, 'university'),
            'cdsu': ('成都体育学院队', '5101070006', None),
            'swjtu': ('西南交通大学队', None, 'university'),
            'cdqz': ('成都七中球队', '5101070004', None),
        }
        teams = {}
        for key, (name, school_code, group) in spec.items():
            teams[key] = Team.objects.create(
                name=name,
                school=school.get(school_code),
                group_type=group or '',
                founded_at=datetime.date(2018, 9, 1),
                captain='队长',
                intro=f'{name}，参加 2026 省青少年校园足球联赛。',
            )
        # 演示归属：实验中学足球队挂到 user001（球队负责人），用户端「我的报名」才有数据
        teams['shiyan'].owner = User.objects.get(username='user001')
        teams['shiyan'].save(update_fields=['owner'])
        return teams

    def _seed_players(self, teams) -> dict:
        serial = iter(range(11, 99))

        def player(team, name, birth, position, number, status='active', school=None):
            id_card = f'510104{birth.replace("-", "")}{next(serial):04d}'
            return Player.objects.get_or_create(
                id_card=id_card,
                defaults=dict(
                    team=team, name=name, gender='男', birth_date=birth,
                    school=school, grade='初二', registry_no=f'G510108{birth.replace("-", "")}01',
                    position=position, jersey_number=number, status=status,
                ),
            )[0]

        shiyan = teams['shiyan']
        return {
            'wanglei': player(shiyan, '王小磊', '2011-03-12', '前锋', 9, school=shiyan.school),
            'lizeyu': player(shiyan, '李泽宇', '2011-07-25', '中场', 10, school=shiyan.school),
            'chenhao': player(shiyan, '陈昊', '2010-11-08', '守门员', 1, status='pending', school=shiyan.school),
            'zhouzihao': player(teams['ershizhong'], '周子豪', '2011-05-16', '前锋', 7),
            'zhengkai': player(teams['fuzhong'], '郑凯', '2010-12-30', '后卫', 5),
        }

    def _seed_coaches(self, teams):
        Coach.objects.create(
            name='张建国', gender='男', birth_date='1985-04-02', id_card='510104198504020011',
            phone='13800000001', unit_name='实验中学', years=10, cert_level='亚足联C级',
            category='专职教练', team=teams['shiyan'], status='active',
        )
        Coach.objects.create(
            name='刘洋', gender='男', birth_date='1990-09-15', id_card='510104199009150011',
            phone='13800000002', unit_name='实验中学', years=4, cert_level='中国足协D级',
            category='兼职教练', team=teams['shiyan'], status='pending',
        )

    # ---------- 对阵与进球 ----------

    def _seed_matches(self, teams, tournament) -> dict:
        def match(key, group, round_name, home, away, date, time, venue, status):
            m = Match.objects.create(
                tournament=tournament, tournament_name=tournament.name,
                group_type=group, round_name=round_name,
                home_team=teams[home], away_team=teams[away],
                match_time=dt(date, time), venue=venue, status=status,
            )
            teams.setdefault(f'__match__:{key}', m)
            return m

        base = '省青少年足球基地'
        m = {}
        m['p1'] = match('p1', 'primary', '第 1 轮', 'shixiao', 'chengguan', '2026-10-12', '10:00', '市体育中心副场', 'finished')
        m['u1a'] = match('u1a', 'university', '第 1 轮', 'cdsu', 'swjtu', '2026-10-17', '15:00', '成都体育学院足球场', 'finished')
        m['u1b'] = match('u1b', 'university', '第 1 轮', 'scu', 'csd', '2026-10-18', '15:00', '四川大学足球场', 'finished')
        m['m1'] = match('m1', 'middle', '第 1 轮', 'shiyan', 'shiyi', '2026-10-13', '15:00', f'{base} 2 号场', 'finished')
        m['m3'] = match('m3', 'middle', '第 3 轮', 'shiyan', 'ershizhong', '2026-10-22', '15:00', f'{base} 1 号场', 'finished')
        m['m2'] = match('m2', 'middle', '第 2 轮', 'fuzhong', 'shiyi', '2026-10-19', '16:30', f'{base} 2 号场', 'finished')
        m['m5'] = match('m5', 'middle', '第 4 轮', 'ershizhong', 'shiyi', '2026-10-24', '10:00', f'{base} 2 号场', 'finished')
        m['p2'] = match('p2', 'primary', '第 2 轮', 'shixiao', 'chaoyang', '2026-10-23', '14:00', '市体育中心副场', 'ongoing')
        m['m4'] = match('m4', 'middle', '第 4 轮', 'fuzhong', 'shiyan', '2026-10-25', '15:00', f'{base} 1 号场', 'scheduled')
        m['u2'] = match('u2', 'university', '第 2 轮', 'csd', 'swjtu', '2026-10-26', '15:00', '四川师范大学足球场', 'scheduled')
        m['p3'] = match('p3', 'primary', '第 3 轮', 'chengguan', 'chaoyang', '2026-10-27', '10:00', '市体育中心副场', 'scheduled')

        results = {
            'p1': (5, 2), 'u1a': (1, 0), 'u1b': (2, 0),
            'm1': (2, 0), 'm3': (3, 1), 'm2': (1, 1), 'm5': (2, 1),
        }
        for key, (hs, as_) in results.items():
            MatchResult.objects.create(match=m[key], home_score=hs, away_score=as_, is_published=True)
        return m

    def _seed_goals(self, matches, players):
        # 与战报口径一致：3:1 一役王小磊梅开二度 + 李泽宇一球；2:0 一役王小磊、李泽宇各一球
        GoalRecord.objects.create(match=matches['m1'], player=players['wanglei'], goals=1, assists=1, minute=23)
        GoalRecord.objects.create(match=matches['m1'], player=players['lizeyu'], goals=1, assists=1, minute=67)
        GoalRecord.objects.create(match=matches['m3'], player=players['wanglei'], goals=2, assists=0, minute=38, note='梅开二度')
        GoalRecord.objects.create(match=matches['m3'], player=players['lizeyu'], goals=1, assists=1, minute=80)
        GoalRecord.objects.create(match=matches['m3'], player=players['zhouzihao'], goals=1, assists=0, minute=61)
        GoalRecord.objects.create(match=matches['m2'], player=players['zhengkai'], goals=1, assists=0, minute=45)

    # ---------- 内容 ----------

    def _seed_news_policy(self):
        for tag, title, source, date, summary, body in NEWS:
            News.objects.create(
                title=title, summary=summary, content=html(body), source=source,
                category={'战报': 'report', '通知公告': 'announcement'}.get(tag, 'news'),
                is_published=True, published_at=dt(date, '09:00'),
                view_count=12, created_by=User.objects.filter(username='admin001').first(),
            )
        for title, org, date, summary, body in POLICIES:
            Policy.objects.create(
                title=title, summary=summary, content=html(body), issuing_org=org,
                is_published=True, published_at=dt(date, '09:00'),
                created_by=User.objects.filter(username='super001').first(),
            )

    def _seed_registrations(self, teams, tournament):
        shiyan_user = User.objects.get(username='user001')
        admin = User.objects.get(username='admin001')
        super_user = User.objects.get(username='super001')

        def reg(team, group, leader, count, coach, status='pending_city_review'):
            return Registration.objects.create(
                tournament=tournament, team=team, group_type=group, city_code=team.city_code,
                city_name='成都市', leader_name=leader, phone='13800000000',
                player_count=count, coach_name=coach, status=status,
                created_by=shiyan_user, submit_time=dt('2026-10-16', '14:20'),
            )

        r1 = reg(teams['shiyan'], 'middle', '李负责人', 18, '张建国')
        RegistrationPlayer.objects.create(registration=r1, name='王小磊', id_card='510104201103120011', jersey_number=9, position='前锋')
        RegistrationPlayer.objects.create(registration=r1, name='李泽宇', id_card='510104201107250011', jersey_number=10, position='中场')
        reg(teams['cdqz'], 'high', '王老师', 20, '赵教练')
        r3 = reg(teams['csd'], 'university', '陈领队', 22, '孙教练', status='pending_province_review')
        ReviewLog.objects.create(registration=r3, stage='city', result='approve', reason='', operator=admin)
        r4 = reg(teams['shixiao'], 'primary', '周老师', 12, '吴教练', status='rejected')
        ReviewLog.objects.create(registration=r4, stage='city', result='reject', reason='学籍材料不齐全，请补充后重新提交', operator=admin)
        _ = super_user

    def _seed_content(self, matches):
        Banner.objects.create(title='2026 秋季联赛火热进行中', image='', link_news=News.objects.first(), sort=1)
        Banner.objects.create(title='四川省校园足球特色校巡礼', image='', link_url='', sort=2)
        Partner.objects.create(name='四川省足球协会', website_url='https://www.scfa.org.cn', sort=1)
        Partner.objects.create(name='成都市教育局', website_url='http://edu.chengdu.gov.cn', sort=2)
        Partner.objects.create(name='体坛传媒', website_url='https://example.com', sort=3)
        Highlight.objects.create(title='补时绝杀', description='第 93 分钟头球破门', match=matches['m3'])
        Highlight.objects.create(title='守门员三连扑', description='单场三次神扑力保球门不失', match=matches['u1a'])
        lineup = BestLineup.objects.create(
            title='2026 秋季联赛中学组第 3 轮最佳阵容', tournament_name='2026 省青少年校园足球联赛（秋季）',
            group_type='middle', formation='4-3-3', match=matches['m3'], description='由组委会评选',
        )
        BestLineupPlayer.objects.create(lineup=lineup, name='王小磊', team_name='实验中学足球队', position='前锋', jersey_number=9, sort=1)
        BestLineupPlayer.objects.create(lineup=lineup, name='李泽宇', team_name='实验中学足球队', position='中场', jersey_number=10, sort=2)
        MatchEvent.objects.create(match=matches['p2'], minute=12, type='text', content='比赛开始，实小少年队率先控球')
        MatchEvent.objects.create(match=matches['p2'], minute=21, type='goal', content='实小少年队 10 号远射破门！1:0')
        MatchEvent.objects.create(match=matches['p2'], minute=35, type='text', content='朝阳小学加强中场逼抢，比赛节奏加快')
        LiveStream.objects.create(match=matches['p2'], platform='川观新闻', url='https://live.example.com/1234', status='live')
        Penalty.objects.create(match=matches['m3'], player=Player.objects.filter(name='周子豪').first(), type='yellow', minute=70, reason='战术犯规')
        Referee.objects.create(match=matches['m3'], name='李明', role='main', cert_level='国家级')
        Referee.objects.create(match=matches['m3'], name='王强', role='linesman')

    def _seed_selection(self, players):
        SelectionScore.objects.create(player=players['wanglei'], group_type='middle', technical=85, physical=90, status='passed')
        SelectionScore.objects.create(player=players['lizeyu'], group_type='middle', technical=88, physical=82, status='passed')
        SelectionScore.objects.create(player=players['zhouzihao'], group_type='middle', technical=80, physical=86)
        SelectionBest.objects.create(group_type='middle', player=players['wanglei'], total=92, status='publicized')

    def _seed_misc(self):
        for value, label in [('afc-c', '亚足联C级'), ('cfa-d', '中国足协D级'), ('afc-b', '亚足联B级')]:
            DictItem.objects.create(dict_type='cert_level', value=value, label=label)
        for sort, label in enumerate(['前锋', '中场', '后卫', '守门员'], start=1):
            DictItem.objects.create(dict_type='position', value=label, label=label, sort=sort)
        SystemConfig.objects.create(key='sign_deadline', name='秋季联赛报名截止', description='报名通道关闭时间', value='2026-11-05 23:59:59')
        SystemConfig.objects.create(key='publicity_enabled', name='信息公示开关', description='关闭后门户隐藏公示信息', value='true')
        SystemConfig.objects.create(key='season', name='当前赛季', description='', value='2026 秋季')
