# 阿里云 ACR 注册与配合 build.sh 推镜像

> 从零注册阿里云容器镜像服务(ACR),到把 api / web 镜像推上去,配合 [`infra/build.sh`](../../infra/build.sh)。
> 只做一次的部分标了 **【一次性】**。部署主线的精简版见 [01-部署前准备.md §9](../01-部署前准备.md#9-开通容器镜像服务acr),本文是详细教程 + 排错。

---

## 0. ACR 是什么 / 选哪个版本

ACR(Container Registry)是阿里云的私有 Docker 镜像仓库,等价于「自己的私有 Docker Hub」。`build.sh` 打出的 `api`、`web` 两个镜像推到这里,ECS 再从这里拉。

| 版本 | 价格 | 适用 | 本项目 |
|---|---|---|---|
| **个人版** | 免费 | 单人/小团队,私有仓库够用 | ✅ **用这个** |
| 企业版 | 按月付费 | 大规模、跨地域同步、加签名扫描 | 不需要 |

> **地域要和其它资源一致**:ACR 实例的地域必须跟 ECS/RDS/Redis/OSS 同一个(如都在 `cn-hangzhou`),这样 ECS 走 VPC 内网拉镜像免流量费。

---

## 1. 【一次性】注册 / 开通 ACR 实例

1. 登录[阿里云控制台](https://home.console.aliyun.com/) → 搜索「容器镜像服务」进入 ACR。
2. 首次进入会提示开通,选 **个人实例(免费)** → 确认开通。
3. 开通后系统提示 **设置 Registry 登录密码**。
   - 这个密码就是后面 `docker login` 要输的密码,**长期有效,务必记下来**。
   - 忘了可在 ACR 控制台「访问凭证 → 设置固定密码」重设。

---

## 2. 【一次性】创建命名空间

命名空间 = 镜像的一级目录,镜像最终地址是 `<registry>/<namespace>/<仓库名>`。

1. ACR 控制台 → 左侧「命名空间」→ **创建命名空间**。
2. 名称填 **`venus`**(要和 [`infra/build.conf`](../../infra/build.conf) 里的 `ACR_NAMESPACE` 一致)。
3. 默认仓库类型选 **私有**。

---

## 3. 【一次性】创建 api / web 两个镜像仓库

`build.sh` 会打 **两个** 镜像,所以要建两个仓库。

1. ACR 控制台 → 左侧「镜像仓库」→ **创建镜像仓库**。
2. 在 `venus` 命名空间下建第一个:
   - 仓库名称 **`api`**
   - 类型 **私有**
   - 代码源选 **本地仓库**(我们用本地 docker push,不接 GitHub 自动构建)
3. 重复一次,建仓库 **`web`**,配置相同。

建完后你应该有:
```
venus/api
venus/web
```

---

## 4. 【一次性】拿到登录凭证(用户名 + 密码)

ACR 控制台 → 左侧「访问凭证」页,记下:

| 项 | 长什么样 | 用在哪 |
|---|---|---|
| **用户名** | `ops@1234567890123456`(@前是 RAM 用户名,@后是主账号 UID) | `docker login` 的 Username |
| **密码** | §1 设的固定密码 | `docker login` 的 Password |
| **公网地址** | `registry.cn-hangzhou.aliyuncs.com` | 本机开发推镜像用 |
| **VPC 地址** | `registry-vpc.cn-hangzhou.aliyuncs.com` | 在 ECS 上推/拉用(走内网免流量费) |

> 阿里云 ACR **没有浏览器 OAuth 登录**,只能用「用户名 + 密码」走 Docker 标准协议。好消息:首次 `docker login` 成功后凭证会缓存到 `~/.docker/config.json`,之后终身免密(类似 `gh auth login`)。

### 建议:用 RAM 子账号,而不是主账号

主账号权限过大,泄露风险高。建议在 RAM 控制台建个子账号专门用于推镜像,授予权限 **`cr:PushRepository`**(或直接挂 `AliyunContainerRegistryFullAccess`)。子账号的用户名/密码同样在 ACR「访问凭证」页查看。

---

## 5. 【一次性】把 ACR 坐标填进 build.conf

`build.sh` 的构建参数来自 `infra/build.conf`(仓库里只有 `build.conf.example` 模板,需复制填写)。

```bash
cd /c/work/md_file/weixin/yimei-rfp/yimei-4s    # 项目根目录
cp infra/build.conf.example infra/build.conf
```

编辑 `infra/build.conf`,四个字段对应上面记的信息:

```ini
ACR_REGISTRY=registry.cn-hangzhou.aliyuncs.com   # §4 的公网地址(本机打包用公网)
ACR_NAMESPACE=venus                              # §2 建的命名空间,必须一致
IMAGE_TAG=v1.0.0                                 # 镜像版本号,别长期用 latest 以便回滚
PLATFORM=linux/amd64                             # x86 ECS 用这个;Apple Silicon 也保持 amd64
```

> 最终镜像地址 = `ACR_REGISTRY/ACR_NAMESPACE/api:IMAGE_TAG`,即
> `registry.cn-hangzhou.aliyuncs.com/venus/api:v1.0.0`,要和 §2/§3 建的一致。

**不要** 把密码填进 build.conf(除非做 CI 自动化);普通用法靠下一步 `docker login` 的免密缓存即可。若确实要填 `ACR_PASSWORD`,必须 `chmod 600 infra/build.conf` 并确认它在 `.gitignore` 里。

---

## 6. 【一次性】docker login 登录 ACR

确保 Docker Desktop 已启动(右下角鲸鱼图标变绿),然后:

```bash
docker login registry.cn-hangzhou.aliyuncs.com
# Username: ops@1234567890123456   ← 输 §4 的用户名
# Password: ****                    ← 输 §4 的密码(不回显)
# Login Succeeded                   ← 看到这行即成功
```

之后所有推送自动免密——凭证已缓存到 `~/.docker/config.json`。`build.sh --push` 会自动检测缓存并跳过 login。

> **在 ECS 上推/拉**换成 VPC 地址(和公网是两套独立凭证,需各 login 一次):
> ```bash
> docker login registry-vpc.cn-hangzhou.aliyuncs.com
> ```

---

## 7. 打镜像并推送

一次性准备(§1~§6)做完后,日常就这一条命令:

```bash
bash infra/build.sh --push
```

脚本会依次:
1. 校验 `build.conf` / `config/prod.baseline.env` / Dockerfile 等齐全(缺啥报啥);
2. 构建 `api`、`web` 两个镜像;
3. 检测到 §6 的登录缓存 → 跳过 login,直接 `docker push` 两个镜像。

**常用变体**:

| 场景 | 命令 |
|---|---|
| 只本地构建,不推 | `bash infra/build.sh` |
| 首次推(未 login) | `bash infra/build.sh --push` → 会弹交互式 login |
| 指定版本 tag | `bash infra/build.sh --tag=v1.1.0 --push` |
| 凭证过期强制重登 | `bash infra/build.sh --push --relogin` |
| 零交互(CI/脚本) | `ACR_USERNAME='ops@<UID>' ACR_PASSWORD='xxx' bash infra/build.sh --push` |

推成功后,ACR 控制台对应仓库的「镜像版本」页能看到刚推的 tag。

---

## 8. 推完之后:ECS 上部署

`build.sh` 结尾会打印下一步。核心是在 ECS 上拉镜像起容器:

```bash
export API_IMAGE=registry-vpc.cn-hangzhou.aliyuncs.com/venus/api:v1.0.0
export WEB_IMAGE=registry-vpc.cn-hangzhou.aliyuncs.com/venus/web:v1.0.0
docker compose -f infra/docker-compose.ecs.yml pull
docker compose -f infra/docker-compose.ecs.yml up -d
```

> 运行时密钥(DATABASE_URL / JWT_SECRET / 阿里云 AK 等)**不在镜像里**,需在服务器
> `/etc/venus-4s/.env` 提供,内容照抄 [`config/prod.secrets.example`](../../config/prod.secrets.example) 填真实值。
> k3s 方案见 [DEPLOY_K3S.md](./DEPLOY_K3S.md)。

---

## 9. 常见报错定位

| 报错 | 原因 | 解决 |
|---|---|---|
| `docker: command not found` | Docker Desktop 没启动 / 没装 | 启动 Docker Desktop,等图标变绿 |
| `Login Succeeded` 后仍推不动 | 用了公网 login 却推 VPC 地址(或反之) | 两套地址各自 `docker login` 一次 |
| `denied: requested access to the resource is denied` | 用户名密码对,但该 RAM 用户没有该 namespace 的推送权限 | 主账号在 ACR / RAM 给该用户加 `cr:PushRepository` |
| `Error saving credentials` (Windows) | 凭据管理器服务被关 | `services.msc` → 启用 "Credential Manager" |
| `name unknown` / `repository does not exist` | 命名空间或仓库没建 / 名字对不上 build.conf | 核对 §2/§3 与 `ACR_NAMESPACE`、仓库名 api/web 一致 |
| `no basic auth credentials`(ECS 拉取时) | ECS 上没登录 ACR | 在 ECS 上 `docker login registry-vpc.cn-hangzhou.aliyuncs.com` |
| build.sh 报 `config/prod.baseline.env 里出现了密钥` | 基线文件里误填了密钥 | 把 DATABASE_URL/JWT_SECRET 等挪到 `/etc/venus-4s/.env`,基线只留非密钥 |

**验证 login 真的进了加密存储**:`cat ~/.docker/config.json`,`auths` 下应出现 `"registry.cn-hangzhou.aliyuncs.com": {}` 空对象(密码不落文件,存在 Windows 凭据管理器)。

---

## 附:整个流程一图

```
【一次性】
  开通 ACR 个人版 → 设 Registry 密码(§1)
        ↓
  建命名空间 venus(§2) → 建仓库 api / web(§3)
        ↓
  记 用户名/密码/公网地址/VPC地址(§4)
        ↓
  cp build.conf.example build.conf 填 4 个字段(§5)
        ↓
  docker login registry.cn-hangzhou.aliyuncs.com(§6)

【每次发版】
  bash infra/build.sh --push        # 打 api+web 镜像 + 推 ACR(§7)
        ↓
  ECS: docker compose ... pull && up -d(§8)
```
