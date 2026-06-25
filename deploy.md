# TikTok Data Analysis Agent 部署说明

## 1. 当前部署能力

本项目可通过 Docker Compose 部署以下服务：

| 服务 | 端口 | 说明 |
|---|---:|---|
| Nginx | `80` | 反向代理 FastAPI，提供限流和安全响应头 |
| FastAPI App | 内部 `8000` | 提供 `/healthz`、`/skills`、`/analyze`、`/metrics` |
| Prometheus | 内部 `9090` | 抓取 FastAPI 指标 |
| Grafana | `127.0.0.1:3000` | 读取 Prometheus 数据源并加载 dashboard，仅服务器本机可访问 |

Nginx、Prometheus、Grafana 的配置会构建进本地镜像，避免不同宿主机对单文件 bind mount 的兼容问题。

真实性边界：当前 `tiktok_fetch` 使用 mock 数据，没有接入 TikTok OpenAPI。接口响应会返回 `source="mock"`、`is_live_data=false` 和 warnings。

## 2. Linux 服务器准备

```bash
curl -fsSL https://get.docker.com | sudo bash
sudo usermod -aG docker $USER

# Debian/Ubuntu
sudo apt install docker-compose-plugin

docker --version
docker compose version
```

## 3. 上传项目

```bash
git clone <your-repo-url> /opt/tiktok-agent
cd /opt/tiktok-agent
```

也可以用 `rsync` 上传，排除 `.git`、`__pycache__`、`.venv` 等本地文件。

## 4. 配置环境变量

建议至少设置 Grafana 管理员密码：

```bash
cp .env.example .env
# 编辑 .env，将 GRAFANA_ADMIN_PASSWORD 改成强密码
```

未设置 `GRAFANA_ADMIN_PASSWORD` 时，Compose 会直接失败，避免使用弱默认密码上线。

## 5. 构建并启动

本地交付验收：

```bash
python -m compileall agent api skills tools tests
python -m unittest discover -s tests
python tools/smoke_check.py
```

服务器启动：

```bash
docker compose build --no-cache
docker compose up -d
docker compose ps
```

验证：

```bash
curl http://localhost/healthz
curl http://localhost/skills
curl -X POST http://localhost/analyze \
  -H "Content-Type: application/json" \
  -d '{"query":"分析账号表现","target_type":"account","target_id":"demo","limit":5}'
```

`/healthz` 应返回 `data_source=mock` 和 `is_live_tiktok_api_configured=false`。

## 6. 日志与监控

查看日志：

```bash
docker compose logs -f --tail=100 app
docker compose logs -f --tail=100 nginx
docker compose logs -f --tail=100 prometheus
docker compose logs -f --tail=100 grafana
```

Prometheus 通过内部网络抓取 `app:8000/metrics`。Grafana 只绑定服务器本机回环地址，建议通过 SSH 隧道访问：

```bash
ssh -L 3000:localhost:3000 user@server
```

然后在本地浏览器打开 `http://localhost:3000`。

## 7. HTTPS

当前 Compose 只暴露 HTTP `80`。启用 HTTPS 时需要：

1. 获取证书，例如 Let's Encrypt。
2. 在 `docker/nginx/default.conf` 增加 `listen 443 ssl` server。
3. 在 `docker-compose.yml` 挂载证书并增加 `443:443`。
4. 重新加载 Nginx。

不要只开放 `443:443` 而不配置 SSL server，否则 HTTPS 不会真正可用。

## 8. 生产化待办

- 替换 `skills/tiktok_fetch.py` 的 mock provider，接入真实且合规的数据源。
- 为 `/analyze` 增加鉴权、请求配额和审计日志。
- 将报告生成扩展为真实文件落盘或对象存储 URL。
- 如需 Nginx 指标，增加 `nginx-prometheus-exporter`，再在 Prometheus 中配置抓取目标。
- 长任务可增加 Redis/Celery，结果可落 PostgreSQL。
