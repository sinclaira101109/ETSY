# 腾讯云部署

目标服务器：106.55.38.151，Ubuntu，2 核 1 GB。COS 桶 horyalf-1471649074 的地域尚待确认；当前应用尚未接 COS。

## 先决条件

- 在腾讯云控制台终端操作；不要通过聊天传送 SSH 密码或云密钥。
- 安装 Docker Engine 及 Compose 插件，使用 Docker 官方 Ubuntu 安装说明，保留签名校验：https://docs.docker.com/engine/install/ubuntu/
- 可用域名解析到服务器 IP。中国大陆服务器的域名访问须按腾讯云要求办理备案。
- 防火墙仅开放应用需要的 80/443；8000 不对公网开放。

## 启动

将整个项目上传至服务器的独立目录，在该目录执行：

```bash
cp deploy/.env.example deploy/.env
chmod 600 deploy/.env
nano deploy/.env
```

填写真实域名、用户名和长随机密码；不要保留示例密码。然后执行：

```bash
docker compose --env-file deploy/.env -f deploy/compose.yaml config --quiet
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d --build
docker compose --env-file deploy/.env -f deploy/compose.yaml ps
```

首次下载镜像需要 Docker Hub 网络访问。Caddy 自动申请 HTTPS 证书，需真实域名和可达的 80/443 端口。

## 验证

访问配置的 HTTPS 域名：未登录应提示认证，登录后显示上传页。上传包含 title,tags,views,orders 的测试 CSV，检查分析结果。不要使用 HTTP 传输登录密码或真实店铺数据。

当前评分是实验性规则分数，不是 Etsy 官方 SEO 分数。当前 CSV 需要浏览量和订单列，Etsy 商品导出未必包含这两列，实际导出字段映射仍需后续适配。产品文档解析、COS 同步、日报尚未实现。

排错时查看：

```bash
docker compose --env-file deploy/.env -f deploy/compose.yaml logs --tail 100
```

停止仅本项目服务：

```bash
docker compose --env-file deploy/.env -f deploy/compose.yaml down
```

不要加 -v，以保留证书卷。
