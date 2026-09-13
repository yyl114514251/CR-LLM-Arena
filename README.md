# CR-LLM-Arena

自制皇室战争模拟器 + LLM 对战 AI，网页可视化，支持人机对战、AI vs AI 对战。

> ⚠️ 本项目为**完全独立的教学模拟器**，不是 Supercell 官方游戏，不与手游客户端交互，
> 仅用于 AI 策略演示与学习。无外挂、无封号风险。

## 特性

- Canvas 网页竞技场，浏览器直接游玩
- 完整模拟器：圣水增长、卡牌部署、单位移动与攻击、法术范围伤害、塔血判定、胜负逻辑
- LLM 智能对手（智谱 GLM 免费 API），AI 自动选卡 + 选部署位置
- 本地规则校验，拦截非法操作（圣水不足、不在手牌、位置越界）
- 支持 AI 对战协议，可以和其他自制 CR 模拟器 AI 互相对战
- 内置经典 2.6 野猪骑士卡组

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/CR-LLM-Arena.git
cd CR-LLM-Arena

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API 密钥（复制模板为 .env 并填入智谱 Key）
#    Windows: copy .env.example .env
cp .env.example .env

# 4. 启动网页服务
python web_server.py
```

浏览器打开 http://127.0.0.1:5002

- 点击手牌选中卡牌，再点击战场位置部署
- 点【AI 行动】让 LLM 对手出牌
- 圣水不足 / 不在手牌 / 越界会被规则引擎拦截

## 其他入口

| 入口 | 命令 | 说明 |
| --- | --- | --- |
| 终端人机对战 | `python main.py` | 命令行下棋，`deploy <卡> <x> <y>` |
| AI 对战协议服务 | `python cr_engine.py` | 端口 5003，HTTP 协议供其他 AI 接入 |
| 模拟器自测 | `python test_sim.py` | 规则与战斗逻辑单元测试 |

## AI 对战协议（对接自制 AI）

`cr_engine.py` 暴露 HTTP 接口，任何语言写的自制 AI 只要调用：

```
GET  /api/get_state      获取战场状态（服务端自动推进模拟）
POST /api/agent_move     部署：{"team":"player|ai","card":"hog","x":5,"y":4}
POST /api/ai_step        让内置 LLM 走一步
POST /api/restart        重置对局
```

即可与你的 AI 互相对战。

## 项目结构

```
CR-LLM-Arena/
├── cr_sim.py            # 模拟器核心：战场、单位、战斗、规则校验
├── llm_cr_player.py     # LLM 决策（智谱 API，输出卡牌+坐标）
├── cr_engine.py         # AI 对战协议服务（HTTP）
├── web_server.py        # 网页版后端（Flask）
├── main.py              # 终端人机对战
├── test_sim.py          # 单元测试
├── webui/
│   └── index.html       # Canvas 网页竞技场前端
├── requirements.txt
├── .env.example / .gitignore / LICENSE / README.md
```

## 项目限制

1. LLM 没有蒙特卡洛 / 深度搜索，强度上限为中端玩家水平，会出现明显失误
2. 卡牌数值、单位行为为自制简化实现，和原版皇室战争不完全一致
3. AI 决策依赖智谱 API，需要免费额度，网络波动会影响响应

## 卡组说明

默认卡组（2.6 快猪）：野猪骑士、加农炮、哥布林、冰精灵、火球、滚木、骑士、电击法术

## License

MIT
