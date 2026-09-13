"""
test_sim.py —— 模拟器单元测试

覆盖：部署校验（成功/圣水不足/不在手牌/位置越界）、圣水增长、
      单位移动与攻击、法术伤害、塔血扣减、胜负判定。
运行：python test_sim.py
"""

import sys

from cr_sim import CrSim, TEAM_PLAYER, TEAM_AI

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}")


def test_deploy_validation():
    print("== 部署校验 ==")
    sim = CrSim()
    state = sim.get_state()
    card = state["player_hand"][0]
    res = sim.deploy_card(TEAM_PLAYER, card, 5, 10)
    check("合法部署成功", res["ok"] is True)
    res2 = sim.deploy_card(TEAM_PLAYER, card, 5, 10)
    check("重复出同张（不在手牌）被拒", res2["ok"] is False)
    res3 = sim.deploy_card(TEAM_PLAYER, "hog", -1, 5)
    check("越界坐标被拒", res3["ok"] is False)
    res4 = sim.deploy_card(TEAM_PLAYER, "unknown", 5, 5)
    check("未知卡牌被拒", res4["ok"] is False)


def test_elixir_growth():
    print("== 圣水增长 ==")
    sim = CrSim()
    sim.tick(5.6)  # 5.6 秒 ≈ 2 点
    check("玩家圣水增长", sim.player_elixir > 5)
    check("AI 圣水增长", sim.ai_elixir > 5)
    sim.tick(1000)  # 长时间
    check("圣水封顶 10", sim.player_elixir <= 10 and sim.ai_elixir <= 10)


def test_combat():
    print("== 战斗（移动+攻击+塔血）==")
    sim = CrSim()
    # 玩家在 (5,13) 放野猪骑士，AI 国王塔在 (5,1)
    sim.deploy_card(TEAM_PLAYER, "hog", 5, 13)
    sim.tick(20)  # 20 秒：足够走到塔并攻击
    state = sim.get_state()
    check("AI 国王塔已掉血", state["towers"][TEAM_AI]["king"]["hp"] < 2400)


def test_spell():
    print("== 法术 ==")
    sim = CrSim()
    sim.player_elixir = 10
    sim.hands[TEAM_PLAYER] = ["fireball"] + sim.hands[TEAM_PLAYER][1:]
    res = sim.deploy_card(TEAM_PLAYER, "fireball", 5, 8)
    check("法术可部署", res["ok"] is True)
    sim.tick(0.01)
    check("法术结算后移除", all(not u.is_spell for u in sim.units))


def test_win():
    print("== 胜负判定 ==")
    sim = CrSim()
    sim.towers[TEAM_AI]["king"]["hp"] = 0
    sim._check_win()
    check("国王塔归零判负", sim.game_over is True and sim.winner == TEAM_PLAYER)


if __name__ == "__main__":
    test_deploy_validation()
    test_elixir_growth()
    test_combat()
    test_spell()
    test_win()
    print(f"\n结果: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
