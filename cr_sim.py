"""
cr_sim.py —— 皇室战争模拟器核心（自制，非官方）

职责：
- 战场状态：圣水、手牌、牌堆、场上单位、双方塔血
- 规则校验：圣水不足 / 不在手牌 / 位置越界 一律拦截
- 战斗逻辑：单位移动、索敌、攻击、法术范围伤害、塔血扣减、胜负判定

设计原则：LLM 只负责"出哪张牌、部署在哪"，本模块负责"能不能下、下了之后发生什么"。
任何非法部署都会被拦截并返回错误信息。

⚠️ 本项目为独立教学模拟器，与 Supercell 官方游戏无任何交互。
"""

import random
import time

# ---------------- 战场常量 ----------------
ARENA_W = 10          # 宽度（x: 0~10）
ARENA_H = 16          # 高度（y: 0~16，玩家在下方 y 大，AI 在上方 y 小）
ELIXIR_MAX = 10
ELIXIR_START = 5
ELIXIR_RATE = 1.0 / 2.8   # 每 2.8 秒回复 1 点（近似官方节奏）

# ---------------- 卡牌定义 ----------------
# type: troop=单位卡, spell=法术卡
# target: ground=只打地面单位/塔, air=只打空中, any=都打, build=只打建筑(塔)
CARDS = {
    "hog":      {"name": "野猪骑士", "cost": 4, "hp": 1400, "dmg": 280, "speed": 1.6,
                 "range": 0.8, "attack_speed": 1.5, "target": "build", "type": "troop"},
    "cannon":   {"name": "加农炮",   "cost": 3, "hp": 800,  "dmg": 60,  "speed": 0.0,
                 "range": 3.0, "attack_speed": 0.8, "target": "ground", "type": "troop"},
    "goblin":   {"name": "哥布林",   "cost": 2, "hp": 300,  "dmg": 80,  "speed": 1.4,
                 "range": 0.8, "attack_speed": 1.1, "target": "any", "type": "troop"},
    "ice_spirit": {"name": "冰精灵", "cost": 1, "hp": 200,  "dmg": 70,  "speed": 2.0,
                 "range": 0.8, "attack_speed": 1.0, "target": "any", "type": "troop"},
    "knight":   {"name": "骑士",     "cost": 3, "hp": 1450, "dmg": 110, "speed": 1.0,
                 "range": 0.8, "attack_speed": 1.2, "target": "ground", "type": "troop"},
    "fireball": {"name": "火球",     "cost": 4, "dmg": 500, "radius": 1.5, "type": "spell"},
    "log":      {"name": "滚木",     "cost": 2, "dmg": 140, "radius": 4.0, "type": "spell"},
    "zap":      {"name": "电击法术", "cost": 1, "dmg": 80,  "radius": 1.0, "type": "spell"},
}
CARD_LIST = list(CARDS.keys())
DECK = CARD_LIST[:]          # 默认 2.6 快猪：以上 8 张

TEAM_PLAYER = "player"
TEAM_AI = "ai"


class Unit:
    """场上单位（含法术弹）"""
    __slots__ = ("uid", "card_id", "team", "x", "y", "hp", "max_hp",
                 "is_spell", "cd", "next_attack")

    def __init__(self, uid, card_id, team, x, y, is_spell=False):
        self.uid = uid
        self.card_id = card_id
        self.team = team
        self.x = x
        self.y = y
        self.is_spell = is_spell
        self.cd = CARDS[card_id]
        if is_spell:
            self.hp = 0
            self.max_hp = 0
        else:
            self.hp = self.cd["hp"]
            self.max_hp = self.cd["hp"]
        self.next_attack = 0.0

    def dist_to(self, x, y):
        return ((self.x - x) ** 2 + (self.y - y) ** 2) ** 0.5


class CrSim:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.reset()

    def reset(self):
        self.player_elixir = ELIXIR_START
        self.ai_elixir = ELIXIR_START
        self.elixir_rate = ELIXIR_RATE
        self.last_tick = time.time()
        self.units = []
        self._uid_counter = 0

        # 塔：玩家在下（y 大），AI 在上（y 小）
        self.towers = {
            TEAM_PLAYER: {
                "king":    {"hp": 2400, "max_hp": 2400, "x": ARENA_W / 2, "y": ARENA_H - 1},
                "left":    {"hp": 1400, "max_hp": 1400, "x": 2,           "y": ARENA_H - 3},
                "right":   {"hp": 1400, "max_hp": 1400, "x": ARENA_W - 2, "y": ARENA_H - 3},
            },
            TEAM_AI: {
                "king":    {"hp": 2400, "max_hp": 2400, "x": ARENA_W / 2, "y": 1},
                "left":    {"hp": 1400, "max_hp": 1400, "x": 2,           "y": 3},
                "right":   {"hp": 1400, "max_hp": 1400, "x": ARENA_W - 2, "y": 3},
            },
        }

        self.hands = {TEAM_PLAYER: self.rng.sample(CARD_LIST, 4),
                      TEAM_AI: self.rng.sample(CARD_LIST, 4)}
        self.decks = {
            TEAM_PLAYER: [c for c in CARD_LIST if c not in self.hands[TEAM_PLAYER]],
            TEAM_AI: [c for c in CARD_LIST if c not in self.hands[TEAM_AI]],
        }
        self.game_over = False
        self.winner = None

    # ---------------- 主循环 ----------------

    def tick(self, dt=None):
        """推进模拟（真实时间或指定步长 dt 秒）。

        大 dt 会拆分成 0.25s 的小步执行，保证攻击判定不会跳过。
        """
        if self.game_over:
            return
        if dt is None:
            now = time.time()
            dt = min(now - self.last_tick, 0.25)   # 防止卡顿跳帧
            self.last_tick = now
        while dt > 0 and not self.game_over:
            step = min(0.25, dt)
            self._gain_elixir(step)
            self._update_units(step)
            self._check_win()
            dt -= step

    def _gain_elixir(self, dt):
        self.player_elixir = min(ELIXIR_MAX, self.player_elixir + self.elixir_rate * dt)
        self.ai_elixir = min(ELIXIR_MAX, self.ai_elixir + self.elixir_rate * dt)

    # ---------------- 战斗逻辑 ----------------

    def _enemy_team(self, team):
        return TEAM_AI if team == TEAM_PLAYER else TEAM_PLAYER

    def _update_units(self, dt):
        alive = []
        for u in self.units:
            if u.is_spell:
                self._resolve_spell(u)
                continue
            self._unit_act(u, dt)
            if u.hp > 0:
                alive.append(u)
        self.units = alive

    def _unit_act(self, u, dt):
        enemy = self._enemy_team(u.team)
        # 找最近的敌方单位
        target = None
        best = 1e9
        for o in self.units:
            if o.team == enemy and not o.is_spell:
                d = u.dist_to(o.x, o.y)
                if d < best:
                    best = d
                    target = o
        # 找最近的敌方塔（如果 target 限制或没有单位目标）
        tower_target = None
        for name, tw in self.towers[enemy].items():
            if tw["hp"] <= 0:
                continue
            if u.cd["target"] == "ground" and name != "king" and tw["hp"] > 0:
                pass  # 简化：公主塔也可被 ground 打
            d = u.dist_to(tw["x"], tw["y"])
            if tower_target is None or d < u.dist_to(tower_target["x"], tower_target["y"]):
                tower_target = tw

        # 索敌：射程内有目标就攻击，否则移动
        in_range = None
        if target is not None and best <= u.cd["range"]:
            in_range = target
        elif tower_target is not None and u.dist_to(tower_target["x"], tower_target["y"]) <= u.cd["range"]:
            in_range = tower_target

        if in_range is not None:
            # 攻击
            u.next_attack -= dt
            if u.next_attack <= 0:
                u.next_attack = u.cd["attack_speed"]
                if isinstance(in_range, Unit):
                    in_range.hp -= u.cd["dmg"]
                else:
                    in_range["hp"] -= u.cd["dmg"]
            return

        # 移动：朝敌方国王塔方向
        speed = u.cd["speed"]
        if speed <= 0:
            return  # 静止建筑
        target_y = 1 if u.team == TEAM_PLAYER else ARENA_H - 1
        step = speed * dt
        if abs(u.y - target_y) > step:
            u.y += step if target_y > u.y else -step
        else:
            u.y = target_y

    def _resolve_spell(self, u):
        """法术立即结算：对范围内敌方单位与塔造成伤害。"""
        enemy = self._enemy_team(u.team)
        radius = u.cd["radius"]
        dmg = u.cd["dmg"]
        for o in self.units[:]:
            if o.team == enemy and not o.is_spell:
                if u.dist_to(o.x, o.y) <= radius:
                    o.hp -= dmg
        for tw in self.towers[enemy].values():
            if tw["hp"] > 0 and u.dist_to(tw["x"], tw["y"]) <= radius:
                tw["hp"] -= dmg

    # ---------------- 规则校验 + 部署 ----------------

    def deploy_card(self, team, card_id, x, y):
        """
        部署卡牌。返回 {"ok": bool, "msg": str, ...}
        校验：对局状态、圣水、手牌、位置。
        """
        if self.game_over:
            return {"ok": False, "msg": "对局已结束"}
        if card_id not in CARDS:
            return {"ok": False, "msg": f"未知卡牌: {card_id}"}
        cd = CARDS[card_id]
        try:
            x = float(x)
            y = float(y)
        except (TypeError, ValueError):
            return {"ok": False, "msg": "坐标无效"}

        elixir = self.player_elixir if team == TEAM_PLAYER else self.ai_elixir
        if elixir < cd["cost"]:
            return {"ok": False, "msg": f"圣水不足（需要 {cd['cost']}）"}
        if card_id not in self.hands[team]:
            return {"ok": False, "msg": f"{card_id} 不在手牌中"}
        if not (0 <= x <= ARENA_W and 0 <= y <= ARENA_H):
            return {"ok": False, "msg": "部署位置超出战场"}

        # 扣圣水、出手牌、补一张
        if team == TEAM_PLAYER:
            self.player_elixir -= cd["cost"]
        else:
            self.ai_elixir -= cd["cost"]
        self.hands[team].remove(card_id)
        if self.decks[team]:
            self.hands[team].append(self.decks[team].pop(0))
        else:
            # 牌堆空则随机补一张（避免手牌枯竭）
            self.hands[team].append(self.rng.choice(CARD_LIST))

        self._uid_counter += 1
        uid = f"{team}_{self._uid_counter}"
        unit = Unit(uid, card_id, team, x, y, is_spell=(cd["type"] == "spell"))
        self.units.append(unit)
        return {"ok": True, "msg": "部署成功", "uid": uid}

    # ---------------- 胜负判定 ----------------

    def _check_win(self):
        if self.game_over:
            return
        p_king = self.towers[TEAM_PLAYER]["king"]["hp"]
        a_king = self.towers[TEAM_AI]["king"]["hp"]
        if p_king <= 0 and a_king <= 0:
            self.game_over = True
            self.winner = "draw"
        elif a_king <= 0:
            self.game_over = True
            self.winner = TEAM_PLAYER
        elif p_king <= 0:
            self.game_over = True
            self.winner = TEAM_AI

    # ---------------- 状态输出 ----------------

    def get_state(self):
        return {
            "player_elixir": round(self.player_elixir, 1),
            "ai_elixir": round(self.ai_elixir, 1),
            "player_hand": self.hands[TEAM_PLAYER],
            "ai_hand": self.hands[TEAM_AI],
            "towers": self.towers,
            "units": [
                {"uid": u.uid, "card": u.card_id, "team": u.team,
                 "x": round(u.x, 1), "y": round(u.y, 1),
                 "hp": int(u.hp), "max_hp": int(u.max_hp), "is_spell": u.is_spell}
                for u in self.units
            ],
            "game_over": self.game_over,
            "winner": self.winner,
            "arena": {"w": ARENA_W, "h": ARENA_H},
        }
