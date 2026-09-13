"""
web_server.py —— 皇室战争网页版后端（Flask）

提供 HTTP API 给 webui/index.html 调用：
  GET  /             返回网页前端
  GET  /api/state    返回战场状态（并推进模拟）
  POST /api/player_deploy  玩家部署 {"card","x","y"}
  POST /api/ai_action      AI（LLM）行动
  POST /api/reset    重置对局

运行：python web_server.py
浏览器打开 http://127.0.0.1:5002
（端口 5002：与 GoLLM-Playground 的 5000 错开，两个项目可同时运行）
"""

import threading

from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

from cr_sim import CrSim, TEAM_PLAYER, TEAM_AI
from llm_cr_player import ai_choose_action

load_dotenv()

app = Flask(__name__, static_folder="webui", static_url_path="/static")

sim = CrSim()
lock = threading.Lock()


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/state", methods=["GET"])
def api_state():
    with lock:
        sim.tick()
        return jsonify(sim.get_state())


@app.route("/api/player_deploy", methods=["POST"])
def api_player_deploy():
    data = request.get_json() or {}
    with lock:
        sim.tick()
        result = sim.deploy_card(
            TEAM_PLAYER,
            data.get("card", ""),
            data.get("x", -1),
            data.get("y", -1),
        )
        return jsonify(result)


@app.route("/api/ai_action", methods=["POST"])
def api_ai_action():
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


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global sim
    with lock:
        sim = CrSim()
        return jsonify({"ok": True})


if __name__ == "__main__":
    print("CR-LLM-Arena WebUI: http://127.0.0.1:5002")
    app.run(host="127.0.0.1", port=5002, debug=False)
