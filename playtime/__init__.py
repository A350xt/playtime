from typing import List
from mcdreforged.api.all import *
import datetime
import time

__mcdr_server: PluginServerInterface
data: dict
help_msg = '''-------- §a Playtime §r--------
§b!!pt §f- §c显示帮助消息
§b!!pt list §f- §c全部玩家列表
§b!!pt get <player> §f- §c获取玩家的最后游玩时间和时长
§b!!pt clean <player> §f- §c清除玩家的信息
-----------------------------------
'''

class Config(Serializable):
    # 一周内没上线属于很活跃
    active:int = 7
    # 两周内没上线属于较为一般
    normal:int = 14
    # 三周内没上线属于基本不活跃
    inactive:int = 21
    # 超过三周属于潜水

    reverse:bool = True

config: Config

class PlayerInfo:
    player:str
    last_date:datetime
    activity:str

    def __init__(self, player, last_date):
        self.player = player
        self.last_date = last_date
        self.activity = self.get_activity()

    def get_activity(self) -> str:
        now = datetime.datetime.now()
        days = (now - self.last_date).days
        
        if days < config.active:
            return 'active'
        elif days >= config.active and days < config.normal:
            return 'normal'
        elif days >= config.normal and days < config.inactive:
            return 'inactive'
        else:
            # (这么久不上线，危)
            return 'danger'
class PlayerInfe:
    player:str
    playtime:int
    def __init__(self, player, playtime):
        self.player = player
        self.playtime = playtime
    
starttime : dict
starttime={'14689123789':0}
def on_load(server: PluginServerInterface, old):

    # 获取存量数据
    global config, data,timd, __mcdr_server    
    __mcdr_server = server
    config = server.load_config_simple(target_class=Config)
    data = server.load_config_simple(
        'data.json',
        default_config = {'player_list': {}},##change
        echo_in_console=True
    )['player_list']
    timd = server.load_config_simple(
        'playtime.json',
        default_config = {'player_list': {}},##change
        echo_in_console=True
    )['player_list']
    server.register_help_message('!!pt', '获取玩家总游玩时长')
    for player in timd:
        starttime.update({player:0})
    
    #注册指令
    command_builder = SimpleCommandBuilder()
    command_builder.command('!!pt list', player_list)
    command_builder.command('!!pt get <player>', get_player)
    command_builder.command('!!pt clean <player>', clean_player)
    command_builder.command('!!pt help', help_info)
    command_builder.command('!!pt', help_info)
    command_builder.arg('player', Text)
    command_builder.register(server)

def on_player_joined(server: PluginServerInterface, player: str, info: Info):
    if player not in timd:
        timd.update({player:0})
    starttime.update({player:time.time()})


def on_player_left(server: PluginServerInterface, player: str):
    now = datetime.datetime.now().strftime('%Y-%m-%d')
    data[player] = now
    thistime=0
    if int(starttime[player])!=0:
        thistime = int(time.time()-int(starttime[player]))
    timd[player]+=thistime
    server.logger.debug(f'player {player} last play time updated!!')
    save_data(server)


# -------------------------
# command handlers
# -------------------------
def help_info(server):
    for line in help_msg.splitlines():
        server.reply(line)


def player_list(server):
    resp = '------ &a玩家列表 &r------'
    online_players = get_online_players()
    # 先统计在线的玩家
    for player in online_players:
        # 跳过假人
        if not player.startswith('bot_') and not player.startswith('Bot_'):
            thistime=0
            if int(starttime[player])!=0:
                thistime = int(time.time()-int(starttime[player]))
            timd[player]+=thistime  
            resp = resp + f'\n&r|- &a{player}&r:&a在线 总游玩时间:&r{round(timd[player]/3600,2)}&r小时'

    # 作排序，按日期从近到远排序
    playerssort = []
    for player in data:
        thistime=0
        if int(starttime[player])!=0:
            thistime = int(time.time()-int(starttime[player]))
        timd[player]+=thistime
        playerssort.append(PlayerInfe(player,timd[player]))##change
        
    sorted_off_players = sort_date(playerssort)
    for player in sorted_off_players:
        # 按游玩先后顺序排序
        resp = resp + f'\n|- &a{player.player}&r  总游玩时间:&r{round(timd[player.player ]/3600,2)}&r小时'+f''
    server.reply(replace_code(resp))


def get_player(server, context):
    player = context['player']
    online_players = get_online_players()
    resp:str
    if player in online_players:
        resp = f'玩家&a{player}&r当前&a在线,总游玩时间为&r{round(timd[player]/3600,2)}&r小时'
    elif player in data:
        playerInfo = PlayerInfo(player, datetime.datetime.strptime(data[player], '%Y-%m-%d'))
        resp = f'玩家&a{player}&r总游玩时间为&r{round(timd[player]/3600,2)}&r小时,最近的游玩时间为&{get_color_by_activity(playerInfo.activity)}{data[player]} '
    else:
        resp = f'当前没有玩家&a{player}&r的游玩时间'
    server.reply(replace_code(resp))
    
    
def clean_player(server, context):
    if __mcdr_server.get_permission_level(server) < 3:
        resp = f'&c你没有权限清除玩家的最近游玩时间'
    player = context['player']
    resp:str
    if player in data:
        del data[player]
        del timd[player]
        resp = f'已清除玩家&a{player}&r最近的游玩时间'
    else:
        resp = f'当前没有玩家&a{player}&r的游玩时间'
    server.reply(replace_code(resp))
    
    


# -------------------------
# utils
# -------------------------

def save_data(server: PluginServerInterface):
    server.save_config_simple({'player_list': data}, 'data.json')
    server.save_config_simple({'player_list': timd}, 'playtime.json')


def replace_code(msg: str) -> str:
    return msg.replace('&','§')


def get_online_players() -> list:
    online_player_api = __mcdr_server.get_plugin_instance('online_player_api')
    return online_player_api.get_player_list()

def sort_date(player_list:List[PlayerInfe]) -> List[PlayerInfe]:
    sorted_player_list = sorted(player_list,key= lambda playerInfe: playerInfe.playtime, reverse=True) 
    return sorted_player_list

def get_color_by_activity(activity:str) -> str:
    print(activity)
    if activity == 'active' :
        # 绿色
        return 'a'
    elif activity == 'normal':
        # 黄色
        return 'e'
    elif activity == 'inactive':
        # 红色
        return 'c'
    else:
        # 灰色
        return '7'