# TikTok 数据分析 AI Agent 设计与实现复核

## 1. 真实实现状态

当前项目已经把 TikTok 数据分析能力封装为 FastAPI 可调用的 Agent，目录为：

- `skills/`: 独立 Skill 模块。
- `agent/`: 规划、路由和执行编排。
- `api/`: FastAPI 网关。
- `docker/`: Nginx、Prometheus、Grafana 部署配置。

当前没有接入 TikTok OpenAPI、数据库、缓存或 LLM Function Calling。`tiktok_fetch` 返回确定性的 mock 数据，接口响应会明确包含 `source="mock"`、`is_live_data=false` 和 warnings，不应被当作真实 TikTok 数据。

## 2. Skill 设计

| Skill | Function | Input | Output | 当前状态 |
|---|---|---|---|---|
| `tiktok_fetch` | 拉取并标准化视频、账号、话题数据 | `target_type`、`target_id`、`date_range`、`limit`、`cursor` | `dataset_id`、`records`、`cursor`、`source`、`is_live_data`、`warnings`、`trace_id` | 已实现，mock 数据源 |
| `trend_analysis` | 计算互动率、增长和趋势洞察 | `dataset_id`、`records`、`metrics` | `analysis_id`、`summary`、`series`、`insights`、`warnings` | 已实现 |
| `user_analysis` | 分析账号健康度和内容表现 | `dataset_id`、`records` | `analysis_id`、`profile`、`recommendations`、`warnings` | 已实现 |
| `report_gen` | 生成结构化报告摘要和图表规格 | `analysis_id`、`dataset_id`、`intent`、`analysis_result`、`source`、`is_live_data` | `report_id`、`summary`、`charts`、`recommendations`、`report_url`、`warnings` | 已实现，不落盘 |

所有 Skill 使用 Pydantic 定义输入输出，便于参数校验、Tool Calling schema 暴露和部署后自检。

## 3. Agent 决策流程

```text
Client -> FastAPI Gateway -> TikTokAgent
                            |-- tiktok_fetch
                            |-- trend_analysis / user_analysis
                            |-- report_gen
                            v
                         AgentResponse
```

执行流程：

1. `/analyze` 接收自然语言 `query`、`target_type`、`target_id`、`date_range`、`limit`。
2. `TikTokAgent._plan()` 根据中英文关键词判断账号分析或趋势分析。
3. Agent 先调用 `tiktok_fetch` 获取标准化记录。
4. 根据意图调用 `trend_analysis` 或 `user_analysis`。
5. 调用 `report_gen` 生成结构化报告。
6. 返回 `intent`、`dataset_id`、`result`、`report`、`steps`、`source`、`is_live_data`、`warnings`、`trace_id`。

## 4. Tool Calling 方案

`GET /skills` 会返回每个 Skill 的 `name`、`description` 和 Pydantic `parameters` JSON Schema。LLM 或外部调度器可以据此注册 tools，再把参数交给 FastAPI 或 Python Agent 执行。

当前项目未内置 LLM SDK。若接入 LLM Function Calling，应新增：

- Skill registry 到 LLM tools 的转换层。
- Tool call dispatcher。
- API key 环境变量管理。
- 速率限制、重试、审计日志和真实 TikTok provider。

## 5. FastAPI 部署方案

已提供 Docker 化部署：

- FastAPI/Uvicorn: 业务 API，暴露 `/healthz`、`/skills`、`/analyze`、`/metrics`。
- Nginx: HTTP 反向代理、限流、安全响应头。
- Prometheus: 抓取 FastAPI 指标。
- Grafana: 读取 Prometheus 数据源并加载 dashboard。

当前 Compose 只暴露 HTTP `80`。HTTPS 需要另行配置证书和 Nginx `listen 443 ssl`，再开放 `443:443`。

## 6. 生产化缺口

- 接入真实 TikTok OpenAPI 或合规数据供应商，替换 `tiktok_fetch` 的 mock provider。
- 增加缓存、数据库和任务队列，支持长任务与结果持久化。
- 对 `/analyze` 增加鉴权、租户隔离和请求配额。
- 将 `report_gen` 扩展为真实文件生成和对象存储 URL。
- 如需 Nginx 指标，新增 `nginx-prometheus-exporter` 并启用 stub status。
