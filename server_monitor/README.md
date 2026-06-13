# Server Monitor

一个轻量级服务器监控平台，提供主机 CPU、内存、磁盘、网络、进程等指标采集，并通过 Docker Engine API 可视化管理本机 Docker 容器。

## 功能

- 服务器指标：CPU 使用率、load average、内存、swap、磁盘、网络、uptime、进程数
- Docker 容器：列表、搜索、状态筛选、启动、停止、重启、暂停、恢复、删除
- 可视化界面：指标卡、趋势图、容器状态统计、磁盘进度条、网络表格
- 安全开关：`MONITOR_API_TOKEN` 保护 API，`MONITOR_READ_ONLY=true` 禁用容器操作
- 容器化部署：挂载 `/var/run/docker.sock` 和 host `/proc` 后即可监控宿主机

## 本地运行

```bash
cd server_monitor
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn monitor_platform.main:app --host 0.0.0.0 --port 8000
```

打开 `http://127.0.0.1:8000`。

如果设置了令牌：

```bash
export MONITOR_API_TOKEN="change-me"
uvicorn monitor_platform.main:app --host 0.0.0.0 --port 8000
```

进入页面后点击右上角“令牌”填入同一个值。

## Docker 运行

```bash
cd server_monitor
cp .env.example .env
docker compose up -d --build
```

默认访问地址为 `http://服务器IP:8080`。

容器模式默认读取宿主机路径：

- `/proc` -> `/host/proc`
- `/sys` -> `/host/sys`
- `/` -> `/host/root`
- `/var/run/docker.sock` -> Docker Engine API

对应环境变量为 `MONITOR_PROC_ROOT`、`MONITOR_SYS_ROOT`、`MONITOR_DISK_PATHS` 和 `DOCKER_SOCKET`。

## API

```bash
curl -H "Authorization: Bearer change-this-token" http://127.0.0.1:8080/api/overview
curl -H "Authorization: Bearer change-this-token" http://127.0.0.1:8080/api/metrics
curl -H "Authorization: Bearer change-this-token" http://127.0.0.1:8080/api/docker/containers
```

容器操作：

```bash
curl -X POST \
  -H "Authorization: Bearer change-this-token" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:8080/api/docker/containers/CONTAINER_ID/actions/restart \
  -d '{"timeout":10}'
```

## 阿里云部署

完整步骤见 [deploy/ALIYUN.md](deploy/ALIYUN.md)。

如果已有 ECS SSH 访问权限，可以使用脚本：

```bash
cd server_monitor
export SSH_TARGET="aliyun"
export MONITOR_API_TOKEN="$(openssl rand -hex 24)"
./deploy/deploy_aliyun.sh
```

如果不用 SSH 别名，也可以设置 `ALIYUN_HOST` 和 `ALIYUN_USER`。

## 安全提示

挂载 Docker socket 等同于授予容器管理宿主机 Docker 的高权限。生产环境建议：

- 使用强 `MONITOR_API_TOKEN`
- 安全组只对可信 IP 开放监控端口
- 对公网使用 Nginx + HTTPS
- 临时巡检场景可设置 `MONITOR_READ_ONLY=true`
