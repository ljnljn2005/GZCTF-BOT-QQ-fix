import requests
import json
import pytz
import re
from datetime import datetime
from nonebot import get_plugin_config
from .config import Config

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG = get_plugin_config(Config).CONFIG
HEADERS = {"Content-Type": "application/json"}
GZCTF_URL = CONFIG["GZCTF_URL"].rstrip('/')
SESSION = requests.Session()
SESSION.headers.update({
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
})
LOGINDATA = "{" + f'"userName": "{CONFIG["GZ_USER"]}", "password": "{CONFIG["GZ_PASS"]}"' + "}"
UTC_TIMEZONE = pytz.timezone('UTC')
UTC_PLUS_8_TIMEZONE = pytz.timezone('Asia/Shanghai')
BAN_DATA = "{\"status\":\"Suspended\"}"


def parseArgs(s):
    """
        解析参数
    """
    results = []
    depth = 0
    start = 0
    in_brackets = False

    for i, char in enumerate(s):
        if char == '[':
            if depth == 0:
                start = i + 1
                in_brackets = True
            depth += 1
        elif char == ']':
            depth -= 1
            if depth == 0 and in_brackets:
                results.append(s[start:i])
                in_brackets = False

    return results


def parseNameOrId(s):
    """
        解析队伍名或队伍ID
    """
    id_pattern = r'^id=([^\s&]+)'
    name_pattern = r'^name=([^\s&]+)'

    id_match = re.search(id_pattern, s)
    name_match = re.search(name_pattern, s)

    if id_match:
        id_value = id_match.group(1)
    else:
        id_value = None

    if name_match:
        name_value = name_match.group(1)
    else:
        name_value = None

    return id_value, name_value


def getGameList(name: str = None):
    global HEADERS, SESSION, GZCTF_URL
    API_GAME_LIST_URL = GZCTF_URL + "/api/game"
    
    print(f"[DEBUG] 获取比赛列表，URL: {API_GAME_LIST_URL}")
    
    if not checkCookieExpired():
        getLogin()
    
    try:
        # 发送请求
        response = SESSION.get(url=API_GAME_LIST_URL, headers=HEADERS, verify=False)
        
        print(f"[DEBUG] API响应状态码: {response.status_code}")
        print(f"[DEBUG] API响应内容: {response.text}")
        
        # 检查响应状态码
        if response.status_code != 200:
            print(f"[ERROR] API请求失败，状态码: {response.status_code}")
            return []
        
        # 解析JSON响应
        game_data = response.json()
        
        print(f"[DEBUG] 解析后的API响应: {game_data}")
        
        # 检查响应结构 - 适配两种可能的格式
        if isinstance(game_data, list):
            # 如果返回的是列表，直接使用
            game_list = game_data
        elif isinstance(game_data, dict) and "data" in game_data:
            # 如果返回的是包含data字段的字典
            game_list = game_data["data"]
        else:
            print(f"[ERROR] API响应格式未知: {type(game_data)}")
            return []
            
        print(f"[DEBUG] 最终比赛列表: {game_list}")
        
    except Exception as e:
        print(f"[ERROR] 获取比赛列表失败: {e}")
        return []
    
    if name:
        Temp_List = []
        for game in game_list:
            # 同时匹配ID和标题
            if str(game.get("id")) == str(name) or game.get("title") == name:
                Temp_List.append(game)
        print(f"[DEBUG] 根据名称 '{name}' 筛选结果: {Temp_List}")
        return Temp_List
    
    return game_list

def getGameInfo(game_id: int):
    """
        获取比赛信息
    """
    global HEADERS, SESSION, GZCTF_URL
    API_GAME_INFO_URL = GZCTF_URL + f"/api/game/{str(game_id)}"
    if not checkCookieExpired():
        getLogin()
    try:
        game_info = SESSION.get(url=API_GAME_INFO_URL, headers=HEADERS, verify=False)
    except Exception as e:
        print(e)
        game_info = {}
    return game_info.json()


def getLogin():
    """
        登录
    """
    global LOGINDATA, HEADERS, SESSION, GZCTF_URL
    API_LOGIN_URL = GZCTF_URL + "/api/account/login"
    login = SESSION.post(url=API_LOGIN_URL, data=LOGINDATA, headers=HEADERS, verify=False)


def checkCookieExpired():
    """
        判断会话的cookie有没有到期
    """
    global SESSION
    for cookie in SESSION.cookies:
        if cookie is not None and cookie.name == "GZCTF_Token":
            headers = {
                "Cookie": f"{cookie.name}={cookie.value}"
            }
            API_CHECK_COOKIE_URL = GZCTF_URL + "/api/admin/config"
            try:
                check = SESSION.get(url=API_CHECK_COOKIE_URL, headers=headers, verify=False)
            except Exception as e:
                print(e)
                return False
            if check.status_code == 200:
                return True
    return False


def checkConfig(config: dict):
    """
        检测CONFIG
    """
    return True if config.get("SEND_LIST") else False


def parseTime(timestamp_ms):
    """
    解析毫秒级时间戳（Unix timestamp in milliseconds）并转换为 UTC+8 时间
    Args:
        timestamp_ms (int/str): 毫秒级时间戳，如 `1716801234000` 或字符串形式的数字
    Returns:
        tuple: (year, month, day, hour, minute, second)
    """
    try:
        # 确保 timestamp_ms 是数字类型
        if isinstance(timestamp_ms, str):
            # 如果是字符串，尝试转换为浮点数
            timestamp_ms = float(timestamp_ms)
        
        # 将毫秒转换为秒（datetime.fromtimestamp 需要秒级时间戳）
        timestamp_sec = timestamp_ms / 1000

        # 转换为 UTC+8 时区的 datetime 对象
        date = datetime.fromtimestamp(timestamp_sec, tz=UTC_PLUS_8_TIMEZONE)

        # 格式化各部分
        year = date.year
        month = f"{date.month:02d}"  # 补零，如 7 → "07"
        day = f"{date.day:02d}"
        hour = f"{date.hour:02d}"
        minute = f"{date.minute:02d}"
        second = f"{date.second:02d}"

        nowTime = (year, month, day, hour, minute, second)
        return nowTime
        
    except Exception as e:
        print(f"[ERROR] 解析时间戳失败: {e}, 原始值: {timestamp_ms}, 类型: {type(timestamp_ms)}")
        # 返回当前时间作为默认值
        current_time = datetime.now(UTC_PLUS_8_TIMEZONE)
        return (
            current_time.year,
            f"{current_time.month:02d}",
            f"{current_time.day:02d}",
            f"{current_time.hour:02d}",
            f"{current_time.minute:02d}",
            f"{current_time.second:02d}"
        )


def getGameNotice(game_id: int):
    """
    获取比赛通知
    """
    global HEADERS, SESSION, GZCTF_URL
    API_GAME_NOTICE_URL = GZCTF_URL + f"/api/game/{str(game_id)}/notices"
    
    print(f"[DEBUG] 获取比赛通知，URL: {API_GAME_NOTICE_URL}")
    
    if not checkCookieExpired():
        getLogin()
    
    try:
        game_notice = SESSION.get(url=API_GAME_NOTICE_URL, headers=HEADERS, verify=False)
        print(f"[DEBUG] 比赛通知响应状态码: {game_notice.status_code}")
        
        if game_notice.status_code != 200:
            print(f"[ERROR] 获取比赛通知失败，状态码: {game_notice.status_code}")
            return []
        
        notices = game_notice.json()
        print(f"[DEBUG] 比赛通知响应内容: {notices}")
        return notices
        
    except Exception as e:
        print(f"[ERROR] 获取比赛通知异常: {e}")
        return []


def getCheatInfo(game_id: int):
    """
    获取作弊信息
    """
    global HEADERS, SESSION, GZCTF_URL
    API_CHEAT_URL = GZCTF_URL + f"/api/game/{str(game_id)}/CheatInfo"
    
    print(f"[DEBUG] 获取作弊信息，URL: {API_CHEAT_URL}")
    
    if not checkCookieExpired():
        getLogin()
    
    try:
        cheat_info = SESSION.get(url=API_CHEAT_URL, headers=HEADERS, verify=False)
        print(f"[DEBUG] 作弊信息响应状态码: {cheat_info.status_code}")
        
        if cheat_info.status_code != 200:
            print(f"[WARNING] 获取作弊信息失败，状态码: {cheat_info.status_code}")
            return [], cheat_info.status_code
        
        cheat_data = cheat_info.json()
        print(f"[DEBUG] 作弊信息响应内容: {cheat_data}")
        return cheat_data, cheat_info.status_code
        
    except Exception as e:
        print(f"[ERROR] 获取作弊信息异常: {e}")
        return {}, 500


def getChallenges(game_id: int):
    """
    获取题目列表
    """
    global HEADERS, SESSION, GZCTF_URL
    API_CHALLENGES_URL = GZCTF_URL + f"/api/edit/games/{str(game_id)}/challenges"
    
    print(f"[DEBUG] 获取题目列表，URL: {API_CHALLENGES_URL}")
    
    if not checkCookieExpired():
        getLogin()
    
    try:
        challenges = SESSION.get(url=API_CHALLENGES_URL, headers=HEADERS, verify=False)
        print(f"[DEBUG] 题目列表响应状态码: {challenges.status_code}")
        
        if challenges.status_code != 200:
            print(f"[ERROR] 获取题目列表失败，状态码: {challenges.status_code}")
            return []
        
        allChallenges = challenges.json()
        print(f"[DEBUG] 题目列表响应内容: {allChallenges}")
        
        allChallenges.sort(key=lambda x: (x["category"], x["isEnabled"]))
        for challenge in allChallenges:
            if 'category' in challenge:
                challenge['tag'] = challenge.pop('category')
        
        print(f"[DEBUG] 处理后的题目列表: {allChallenges}")
        return allChallenges
        
    except Exception as e:
        print(f"[ERROR] 获取题目列表异常: {e}")
        return []


def getChallengesInfo(game_id: int, challenge_id: int):
    """
        获取题目信息
    """
    global HEADERS, SESSION, GZCTF_URL
    API_CHALLENGES_INFO_URL = GZCTF_URL + f"/api/game/{str(game_id)}/challenges/{str(challenge_id)}"
    if not checkCookieExpired():
        getLogin()
    try:
        challenges_info = SESSION.get(url=API_CHALLENGES_INFO_URL, headers=HEADERS, verify=False)
    except Exception as e:
        print(e)
        challenges_info = {}
    challengesInfo = challenges_info.json()
    challengesInfo['tag'] = challengesInfo.pop('category')
    return challengesInfo


def openOrCloseChallenge(game_id: int, challenge_id: int, isEnable: bool):
    """
        开放/关闭题目
    """
    global HEADERS, SESSION, GZCTF_URL
    if not checkCookieExpired():
        getLogin()
    API_OPEN_CHALLENGE_URL = GZCTF_URL + f"/api/edit/games/{str(game_id)}/challenges/{str(challenge_id)}"
    if isEnable:
        data = "{\"isEnabled\":true}"
    else:
        data = "{\"isEnabled\":false}"
    try:
        oc = SESSION.put(url=API_OPEN_CHALLENGE_URL, headers=HEADERS, verify=False, data=data)
        if oc.status_code == 200:
            return True
    except Exception as e:
        print(e)
    return False


def banTeam(teamIds: list):
    """
        封禁队伍
    """
    global HEADERS, SESSION, GZCTF_URL
    if not checkCookieExpired():
        getLogin()
    for team_id in teamIds:
        API_BAN_TEAM_URL = GZCTF_URL + f"/api/admin/participation/{str(team_id)}"
        try:
            a = SESSION.put(url=API_BAN_TEAM_URL, headers=HEADERS, data=BAN_DATA, verify=False)
            print(a.text)
            if a.status_code != 200:
                return False
        except Exception as e:
            print(e)
    return True


def unlockTeam(teamId: int):
    """
        解锁队伍
    """
    global HEADERS, SESSION, GZCTF_URL
    if not checkCookieExpired():
        getLogin()
    API_UNLOCK_TEAM_URL = GZCTF_URL + f"/api/admin/teams/{str(teamId)}"
    data = {"locked": False}
    try:
        unlock = SESSION.put(url=API_UNLOCK_TEAM_URL, headers=HEADERS, verify=False, json=data)
        if unlock.status_code == 200:
            return True
    except Exception as e:
        print(e)
    return False


def getTeamInfoWithName(teamName: str):
    """
        通过队伍名获取队伍ID
    """
    global HEADERS, SESSION, GZCTF_URL
    if not checkCookieExpired():
        getLogin()
    API_TEAM_URL = GZCTF_URL + f"/api/admin/teams/search?hint={teamName}"
    allTeams = []
    try:
        teams = SESSION.post(url=API_TEAM_URL, headers=HEADERS, verify=False)

    except Exception as e:
        print(e)
        teams = {}
    for team in teams.json()['data']:
        if team['name'] == teamName:
            allTeams.append(team)
    return allTeams


def getTeamInfoWithId(teamId: str):
    """
        通过队伍Id获取队伍Info
    """
    global HEADERS, SESSION, GZCTF_URL
    if not checkCookieExpired():
        getLogin()
    API_TEAM_URL = GZCTF_URL + f"/api/admin/teams/search?hint={teamId}"
    allTeams = []
    try:
        teams = SESSION.post(url=API_TEAM_URL, headers=HEADERS, verify=False)
    except Exception as e:
        print(e)
        teams = {}
    for team in teams.json()['data']:
        if team['id'] == int(teamId):
            allTeams.append(team)
    return allTeams


def getTeamInfoWithGameId(game_Id: int):
    """
        通过gameID获取队伍信息
    """
    global HEADERS, SESSION, GZCTF_URL
    if not checkCookieExpired():
        getLogin()
    API_TEAM_URL = GZCTF_URL + f"/api/game/{str(game_Id)}/participations"
    try:
        team = SESSION.get(url=API_TEAM_URL, headers=HEADERS, verify=False)
    except Exception as e:
        print(e)
        team = []
    return team.json()


def getScoreBoard(game_id: int):
    """
        获取排行榜
    """
    global HEADERS, SESSION, GZCTF_URL
    API_RANK_URL = GZCTF_URL + f"/api/game/{str(game_id)}/scoreboard"
    if not checkCookieExpired():
        getLogin()
    try:
        rank = SESSION.get(url=API_RANK_URL, headers=HEADERS, verify=False)
    except Exception as e:
        print(e)
        rank = {}
    return rank.json()


def getRank(game_id: int):
    """
        获取总排行榜
    """
    if 'items' not in getScoreBoard(game_id):
        return getScoreBoard(game_id)
    rank = getScoreBoard(game_id)['items']
    allRank = []
    if not rank:
        return None
    for item in rank:
        Rank = {'teamName': item['name'], 'score': item['score'], 'rank': item['rank']}
        allRank.append(Rank)
    allRank.sort(key=lambda x: x["rank"])
    return allRank


def getRankWithOrg(game_id: int, org: str):
    """
        获取组织排行榜
    """
    rank = getScoreBoard(game_id)['items']
    allOrgRank = []
    for item in rank:
        if item.get('organization') is None:
            return None
        if item['organization'] == org:
            orgRank = {'teamName': item['name'], 'score': item['score'], 'rank': item['organizationRank']}
            allOrgRank.append(orgRank)
    allOrgRank.sort(key=lambda x: x["rank"])
    return allOrgRank


def getRankWithTeamId(game_id: int, team_id: int):
    """
        获取队伍排名
    """
    rank = getScoreBoard(game_id)['items']
    for item in rank:
        if item['id'] == team_id:
            teamRank = {'teamName': item['name'], 'score': item['score'], 'rank': item['rank']}
            if item.get('organizationRank') is not None:
                teamRank['organizationRank'] = item['organizationRank']
            return teamRank
    return None


def getChallengesInfoByName(game_id: int, challenge_name: str):
    """
        通过题目NAME获取题目信息
    """
    global HEADERS, SESSION, GZCTF_URL
    API_CHALLENGES_INFO_URL = GZCTF_URL + f"/api/game/{str(game_id)}/details"
    challenges = getChallenges(game_id)
    if not checkCookieExpired():
        getLogin()
    try:
        challenges_info = SESSION.get(url=API_CHALLENGES_INFO_URL, headers=HEADERS, verify=False)
    except Exception as e:
        print(e)
        challenges_info = {}
    Info = {}
    for challenge in challenges:
        if challenge['title'] == challenge_name:
            Info['title'] = challenge_name
            Info['tag'] = challenge['tag']
            Info['isEnabled'] = challenge['isEnabled']
            Info['score'] = challenge['score']
            findChallenges = challenges_info.json()['challenges'][f"{Info['tag']}"]
            for findChallenge in findChallenges:
                if findChallenge['title'] == challenge_name:
                    Info['solved'] = findChallenge['solved']
                    Info['bloods'] = findChallenge['bloods']
                    return Info
    return None


def getUserWithName(userName: str):
    """
        通过用户名获取用户信息
    """
    global HEADERS, SESSION, GZCTF_URL
    if not checkCookieExpired():
        getLogin()
    API_USER_URL = GZCTF_URL + f"/api/admin/Users/Search?hint={userName}"
    try:
        user = SESSION.post(url=API_USER_URL, headers=HEADERS, verify=False)
    except Exception as e:
        print(e)
        user = {}
    for item in user.json()['data']:
        if item['userName'] == userName:
            return item
    return False


def resetPwd(userName: str):
    """
        重置密码
    """
    global HEADERS, SESSION, GZCTF_URL
    if not checkCookieExpired():
        getLogin()
    if getUserWithName(userName):
        userId = getUserWithName(userName)['id']
    else:
        return False
    API_RESET_PWD_URL = GZCTF_URL + f"/api/admin/Users/{userId}/Password"
    try:
        reset = SESSION.delete(url=API_RESET_PWD_URL, headers=HEADERS, verify=False)
        if reset.status_code == 200:
            return reset.text.strip('"')
    except Exception as e:
        print(e)
    return False


def addNotice(gameId: int, notice: str):
    """
        添加公告
    """
    global HEADERS, SESSION, GZCTF_URL
    if not checkCookieExpired():
        getLogin()
    API_ADD_NOTICE_URL = GZCTF_URL + f"/api/edit/games/{str(gameId)}/notices"
    data = {"content": notice}
    try:
        add = SESSION.post(url=API_ADD_NOTICE_URL, json=data)
        if add.status_code == 200:
            return True
    except Exception as e:
        print(e)
    return False


def addHint(gameId: int, challengeId: int, hint: str):
    """
        添加提示
    """
    global HEADERS, SESSION, GZCTF_URL
    if not checkCookieExpired():
        getLogin()
    API_ADD_HINT_URL = GZCTF_URL + f"/api/edit/games/{str(gameId)}/challenges/{str(challengeId)}"
    data = SESSION.get(url=API_ADD_HINT_URL, headers=HEADERS, verify=False)
    if data.status_code != 200:
        return False
    datas = data.json()
    datas['hints'].append(hint)
    try:
        add = SESSION.put(url=API_ADD_HINT_URL, headers=HEADERS, verify=False, json=datas)
        if add.status_code == 200:
            return True
    except Exception as e:
        print(e)
    return False
