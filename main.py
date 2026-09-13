"""
main.py —— 终端人机对战（简易）

输入示例：
  deploy hog 5 10     部署野猪骑士到 (5,10)
  ai                  让 LLM 走一步
  show                查看战场状态
  reset               重置对局
  quit                退出
"""

import time

from cr_sim import CrSim, TEAM_PLAYER
from llm_cr_player import ai_choose_action


def main():
    sim = CrSim()
    print("=== CR-LLM-Arena 终端对战 ===")
    print("命令: deploy <卡牌> <x> <y> | ai | show | reset | quit")
    last = time.time()
    while True:
        now = time.time()
        sim.tick(now - last)
        last = now
        if sim.game_over:
            print(f"对局结束，胜者：{sim.winner}")
            break

        cmd = input("> ").strip().lower()
        if not cmd:
            continue
        if cmd.startswith("deploy"):
            parts = cmd.split()
            if len(parts) != 4:
                print("格式: deploy <卡牌> <x> <y>")
                continue
            _, card, x, y = parts
            result = sim.deploy_card(TEAM_PLAYER, card, x, y)
            print(result)
        elif cmd == "ai":
            state = sim.get_state()
            action = ai_choose_action(state)
            if action:
                result = sim.deploy_card("ai", action["card"], action["x"], action["y"])
                print("AI 决策:", action)
                print("部署结果:", result)
            else:
                print("LLM 无有效决策")
        elif cmd == "show":
            s = sim.get_state()
            print(f"圣水 玩家={s['player_elixir']} AI={s['ai_elixir']}")
            print(f"手牌 玩家={s['player_hand']} AI={s['ai_hand']}")
            print("塔:", s["towers"])
            print("单位:", s["units"])
        elif cmd == "reset":
            sim = CrSim()
            print("已重置")
        elif cmd == "quit":
            break
        else:
            print("未知命令")


if __name__ == "__main__":
    main()
