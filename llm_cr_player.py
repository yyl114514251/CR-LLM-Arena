"""
llm_cr_player.py —— LLM 皇室战争棋手

职责：调用智谱 API，输入战场文本状态，让模型输出
      {"card": "卡牌ID", "x": 坐标, "y": 坐标} 决策。
     只负责"策略决策"，规则由 cr_sim.py 校验。
"""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ZHIPU_API_KEY", "")
MODEL = os.getenv("ZHIPU_MODEL", "glm-4-flash")
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


def _build_prompt(state):
    units = "\n".join(
        f"- {u['card']} ({u['team']}) 位置({u['x']},{u['y']}) HP {u['hp']}"
        for u in state["units"]
    ) or "（场上暂无单位）"

    prompt = f"""
你是一个皇室战争 AI 选手，正在一场自制模拟器中对战。
战场尺寸：x 0~10，y 0~16。你在上方（y 小的一侧），敌人（玩家）在下方（y 大的一侧）。

你的圣水：{state['ai_elixir']}
你的手牌：{state['ai_hand']}
敌方塔血量：
- 国王塔 {state['towers']['player']['king']['hp']}
- 左公主塔 {state['towers']['player']['left']['hp']}
- 右公主塔 {state['towers']['player']['right']['hp']}
场上单位：
{units}

请根据当前局面选择一张手牌并给出部署位置。
要求：
1. 只从手牌 {state['ai_hand']} 中选择一张牌
2. 圣水不足的牌不能选
3. 输出严格 JSON 格式，不要任何其他文字，例如：
{{"card": "hog", "x": 5, "y": 4}}
"""
    return prompt


def ai_choose_action(state, max_retries=2):
    """调用 LLM 返回 {"card": str, "x": float, "y": float}，失败返回 None。"""
    if not API_KEY:
        print("[LLM] 未配置 ZHIPU_API_KEY")
        return None
    if state.get("game_over"):
        return None

    prompt = _build_prompt(state)
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 64,
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            # 提取第一个 JSON 对象
            start = text.find("{")
            end = text.rfind("}") + 1
            if start < 0 or end <= start:
                print(f"[LLM] 输出无 JSON: {text!r}")
                continue
            action = json.loads(text[start:end])
            card = str(action.get("card", "")).strip()
            x = float(action.get("x", -1))
            y = float(action.get("y", -1))
            if card not in state["ai_hand"]:
                print(f"[LLM] 出的牌不在手牌: {card}")
                continue
            return {"card": card, "x": x, "y": y}
        except Exception as e:
            print(f"[LLM] 第 {attempt + 1} 次调用失败: {type(e).__name__}: {e}")
    return None


if __name__ == "__main__":
    from cr_sim import CrSim

    sim = CrSim()
    state = sim.get_state()
    action = ai_choose_action(state)
    print("AI 决策:", action)
    if action:
        result = sim.deploy_card("ai", action["card"], action["x"], action["y"])
        print("部署结果:", result)
