"""
cr_engine.py —— AI 对战协议服务

任何实现本协议的自制皇室战争 AI（Python / C / JS 均可）都可以
通过 HTTP 与本服务对弈：

  GET  /api/get_state    获取战场状态（服务端自动推进模拟）
  POST /api/agent_move   让某方部署 {"team":"player|ai","card","x","y"}
  POST /api/ai_step      （内置）让 LLM 走一步
  POST /api/restart      重置对局

运行：python cr_engine.py  （端口 5003，与网页版 5002 / 围棋 5000 错开）
"""

import threading

from flask import Flask, jsonify, request
from dotenv import load_dotenv

from cr_sim import CrSim, TEAM_PLAYER, TEAM_AI
from llm_cr_player import ai_choose_action

load_dotenv()

app = Flask(__name__)
sim = CrSim()
lock = threading.Lock()


@app.route("/api/get_state", methods=["GET"])
def get_state():
    with lock:
        sim.tick()
        return jsonify(sim.get_state())


@app.route("/api/agent_move", methods=["POST"])
def agent_move():
    d = request.get_json() or {}
    team = d.get("team")
    if team not in (TEAM_PLAYER, TEAM_AI):
        return jsonify({"ok": False, "msg": "team 必须是 player 或 ai"})
    with lock:
        sim.tick()
        result = sim.deploy_card(team, d.get("card", ""), d.get("x", -1), d.get("y", -1))
        return jsonify(result)


@app.route("/api/ai_step", methods=["POST"])
def ai_step():
    with lock:
        sim.tick()
        state = sim.get_state()
        if state["game_over"]:
            return jsonify({"action": None, "result": {"ok": False, "msg": "对局已结束"}})
        action = ai_choose_action(state)
        if not action:
            return jsonify({"action": None, "result": {"ok": False, "msg": "LLM 无有效决策"}})
        result = sim.deploy_card(TEAM_AI, action["card"], action["x"], action["y"])
        return jsonify({"action": action, "result": result})


@app.route("/api/restart", methods=["POST"])
def restart():
    global sim
    with lock:
        sim = CrSim()
        return jsonify({"ok": True})


if __name__ == "__main__":
    print("CR-LLM-Arena 对战协议服务: http://127.0.0.1:5003")
    app.run(host="127.0.0.1", port=5003, debug=False)
