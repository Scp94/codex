# 阿里云 ECS 部署

## 1. 准备 ECS

- 镜像：Ubuntu 22.04、Alibaba Cloud Linux 3 或其他主流 Linux
- 规格：1 vCPU / 1 GiB 可运行，建议 2 vCPU / 2 GiB 起
- 安全组：开放 `22/tcp` 给你的办公 IP，开放 `8080/tcp` 给可信来源
- ECS 内安装 Docker 和 Docker Compose 插件

Ubuntu 示例：

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
docker compose version
```

Alibaba Cloud Linux 可使用系统包管理器或 Docker 官方安装脚本，安装完成后确认：

```bash
docker version
docker compose version
```

## 2. 上传并启动

方式一：本地脚本部署。

```bash
cd server_monitor
export SSH_TARGET="aliyun"
export MONITOR_API_TOKEN="$(openssl rand -hex 24)"
./deploy/deploy_aliyun.sh
```

`SSH_TARGET` 会原样传给 `ssh` 和 `scp`，所以可以使用你在 `~/.ssh/config` 中配置好的别名。没有别名时可改用：

```bash
export ALIYUN_HOST="your-ecs-public-ip"
export ALIYUN_USER="root"
```

方式二：手动部署。

```bash
scp -r server_monitor root@your-ecs-public-ip:/opt/server-monitor
ssh root@your-ecs-public-ip
cd /opt/server-monitor
cp .env.example .env
sed -i "s/change-this-token/$(openssl rand -hex 24)/" .env
docker compose up -d --build
```

## 3. 访问

浏览器打开：

```text
http://your-ecs-public-ip:8080
```

页面右上角点击“令牌”，填入 `.env` 中的 `MONITOR_API_TOKEN`。

部署后确认采集的是宿主机指标，而不是监控容器自身：

```bash
docker exec server-monitor sh -lc 'test -r /host/proc/meminfo && test -S /var/run/docker.sock && echo ok'
curl -H "Authorization: Bearer $(grep MONITOR_API_TOKEN .env | cut -d= -f2)" \
  http://127.0.0.1:8080/api/overview
```

## 4. 常用运维命令

```bash
cd /opt/server-monitor
docker compose ps
docker compose logs -f
docker compose pull
docker compose up -d --build
docker compose down
```

## 5. 生产加固

- 将 `MONITOR_API_TOKEN` 设置为高强度随机值
- 安全组限制 `8080/tcp` 来源 IP，避免全网开放
- 如需公网长期访问，建议在 ECS 上配置 Nginx 反向代理和 HTTPS
- 如果只想查看指标，不想允许容器操作，设置 `MONITOR_READ_ONLY=true`
- Docker socket 权限很高，不要把这个平台暴露给不可信用户
