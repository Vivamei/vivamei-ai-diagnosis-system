# venus-4s 文档索引

## 阿里云部署

本项目在阿里云上的部署流程按以下顺序阅读:

| 编号 | 文档 | 内容 | 阅读时机 |
|---|---|---|---|
| 01 | [01-部署前准备.md](./01-部署前准备.md) | 创建阿里云资源(ECS、RDS、KVStore、OSS、ACR、RAM、短信、内容审核),办理域名、ICP 备案与 SSL 证书,生成应用侧密钥,汇总所有连接信息 | 项目立项即启动。ICP 备案通常需要 1 至 2 周,应尽早启动 |
| 02 | [02-部署实施.md](./02-部署实施.md) | 本地构建镜像、推送至 ACR,ECS 上安装 Docker、拉取镜像、初始化数据库、启动容器 | 完成 01 §16 检查项后 |
| 03 | [03-部署验证.md](./03-部署验证.md) | 从公网视角完整验证:DNS、证书、健康检查、前端页面、端到端业务链路 | 完成 02 §12 检查项后 |
| 04 | [04-日常运维与排查.md](./04-日常运维与排查.md) | 发布与回滚、备份恢复、扩容、迁移、故障排查、性能监控、安全事件响应 | 上线后长期查阅 |
| 05 | [05-小程序接入.md](./05-小程序接入.md) | 微信小程序上线全流程:注册企业主体取 AppID、配三个域名白名单、后端从 mock 切真实微信、构建与上传、审核发布 | H5 侧完成 03 验证后。账号认证与备案是长周期项,应与 01 同期启动 |

阅读顺序: 01 → 02 → 03 → 04,小程序端另见 05

## 本地上手

| 文档 | 说明 |
|---|---|
| [双击启动.md](./双击启动.md) | Windows 双击 `start-dev.bat` 一键装依赖并启动 |
| [本地数据库连接指南.md](./本地数据库连接指南.md) | 本地连 MySQL/Redis 的连接串、图形化工具与排查查询 |

## 设计

- [design/](./design/):项目设计文档,包括接口契约、数据模型、合规要求。

## 参考资料

`references/` 目录下的文档不属于阿里云部署主线,按需查阅。

| 文档 | 说明 |
|---|---|
| [references/LOCAL_DEV.md](./references/LOCAL_DEV.md) | 本地基于 Docker 的开发环境搭建 |
| [references/LOCAL_DEV_NO_DOCKER.md](./references/LOCAL_DEV_NO_DOCKER.md) | 本地不使用 Docker 的开发环境搭建 |
| [references/MINIAPP.md](./references/MINIAPP.md) | 小程序 / H5 双端开发指南:双端差异、API 基址策略、登录双模、CORS 与 Nginx WebSocket、目录结构、共用配置真源、部署与切换 |
| [references/LLM_API_ALIGNMENT.md](./references/LLM_API_ALIGNMENT.md) | 与 LLM 服务方对齐的接口协议 |
| [references/ACR_GUIDE.md](./references/ACR_GUIDE.md) | 阿里云 ACR 从注册到配合 build.sh 推镜像的详细教程 + 排错 |
| [references/DEPLOY_K8S.md](./references/DEPLOY_K8S.md) | 阿里云 ACK 托管 Kubernetes 部署方案(当前不使用) |
| [references/DEPLOY_K3S.md](./references/DEPLOY_K3S.md) | 单机 k3s 部署方案:同 ECS 跑业务 Pod + 模型服务 Pod,通过 ClusterIP Service 互访 |

## 外部交接材料

[操作手册-新建RAM子账号与MySQL-Redis资源.docx](./操作手册-新建RAM子账号与MySQL-Redis资源.docx):可打印分发的资源开通操作手册,内容与 01 §2 至 §5 一致,便于外部协作人员离线阅读。
