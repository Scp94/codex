# 阿里云部署与接口示例

以下示例假设部署到一台阿里云 ECS，系统为 Ubuntu/CentOS 类 Linux，服务端口为 `8000`。

## 1. 服务器准备

在 ECS 安全组放行 TCP `8000`，建议只允许你的固定 IP 访问。

安装 Docker 和 Compose 插件：

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker
sudo systemctl start docker
docker compose version
```

## 2. 上传项目

在本机项目根目录执行：

```bash
tar --exclude='.git' --exclude='.venv' --exclude='stock_advisor/reports' \
  -czf fund-advisor.tar.gz requirements.txt stock_advisor

scp fund-advisor.tar.gz root@你的ECS公网IP:/opt/
```

在 ECS 上执行：

```bash
cd /opt
tar -xzf fund-advisor.tar.gz
cd /opt/stock_advisor
cp config.example.json config.json
```

编辑 `config.json`，填入你的钉钉机器人配置、持仓基金和候选基金池。

## 3. 启动服务

```bash
cd /opt/stock_advisor
export STOCK_ADVISOR_API_TOKEN="换成一个长随机密钥"
export STOCK_ADVISOR_DAILY_RUN_TIME="09:30"
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
docker compose logs -f fund-advisor
```

服务地址：

```text
http://你的ECS公网IP:8000
```

## 4. 接口鉴权

如果设置了 `STOCK_ADVISOR_API_TOKEN`，除 `/health` 外的接口都需要请求头：

```text
Authorization: Bearer 换成一个长随机密钥
```

下面示例统一使用：

```bash
BASE_URL="http://你的ECS公网IP:8000"
TOKEN="换成一个长随机密钥"
```

## 5. 接口示例

### 健康检查

```bash
curl "$BASE_URL/health"
```

### 查看持仓、候选基金池和交易流水

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/portfolio"
```

### 修改现金

```bash
curl -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/portfolio/cash" \
  -d '{"cash":15000}'
```

### 新增或更新持仓基金

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/portfolio/funds" \
  -d '{
    "symbol": "007509",
    "name": "华商润丰灵活配置混合C",
    "principal": 2000,
    "shares": 0,
    "cost_basis": 4.4888,
    "weekly_dca_day": "周二",
    "dca_min": 1000,
    "dca_max": 4000
  }'
```

### 删除持仓基金

```bash
curl -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/portfolio/funds/007509"
```

### 记录买入金额

不传 `nav` 时，服务会尝试用 AKShare 获取最新净值；如果你想严格按支付宝成交净值记账，建议传 `nav`。

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/portfolio/trades" \
  -d '{
    "symbol": "007509",
    "action": "buy",
    "amount": 1000,
    "nav": 4.7960,
    "name": "华商润丰灵活配置混合C"
  }'
```

### 记录卖出金额

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/portfolio/trades" \
  -d '{
    "symbol": "014597",
    "action": "sell",
    "amount": 5000,
    "nav": 2.7154
  }'
```

### 查看交易流水

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/portfolio/trades"
```

### 手动触发一次分析并推送钉钉

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/analysis/run" \
  -d '{"send_dingtalk":true}'
```

### 手动触发一次分析但不推送

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/analysis/run" \
  -d '{"send_dingtalk":false}'
```

## 6. 日常运维

更新代码后重启：

```bash
cd /opt/stock_advisor
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f fund-advisor
```

停止服务：

```bash
docker compose down
```

## 7. 注意

- `config.json` 会被 API 写回，不能用只读挂载。
- 推荐定期备份 `/opt/stock_advisor/config.json` 和 `/opt/stock_advisor/reports/`。
- 本服务只生成研究参考，不自动连接支付宝下单。
