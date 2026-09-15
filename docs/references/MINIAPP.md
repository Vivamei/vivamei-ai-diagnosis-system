# 小程序 / H5 双端开发指南（apps/miniapp）

`apps/miniapp` 是一套 Taro 4.2 代码，同时编译出**微信原生小程序**和 **H5**两个产物。
它与 `apps/web`（纯 React + Vite 的 H5）**并存**，互不影响：`apps/web` 是既有 H5 主线，
`apps/miniapp` 是小程序主线并顺带产出一份 H5，便于在浏览器里调页面而不必开小程序开发者工具。

后端只有一套（`apps/api`），三个前端产物共用同一批接口。

| 章节 | 内容 |
|---|---|
| §1 | 微信 / H5 两个产物差在哪 |
| §2 | API 基址与 SSE 策略 |
| §3 | 登录：微信一键 + 短信双模 |
| §4 | 开发期 devServer 代理 |
| §5 | 后端 CORS |
| §6 | 生产 Nginx 的 SSE 规则 |
| §7 | 构建命令与自查清单 |
| §8 | 排查速查表 |
| **§9** | **目录结构**（页面 / 组件 / 配置链路） |
| **§10** | **配置：两端共用一份真源** |
| **§11** | **部署、切换、要不要改 Nginx** |

## 1. 两个产物差在哪

这是理解后面所有配置的前提。差异只有三处，其余代码完全共用。

| | 微信小程序（`weapp`） | H5（`h5`） |
|---|---|---|
| 请求地址 | **必须绝对域名**，小程序发不了相对路径请求 | **相对路径**即可，同源无跨域 |
| 域名白名单 | 要在微信后台分别配 request 与 uploadFile；不需要 socket | 不涉及，受浏览器同源策略约束 |
| 登录 | `wx.login` 静默登录 + `getPhoneNumber` 一键授权，短信作为兜底 | 没有 `wx.login`，**只能**走短信验证码 |

代码里用 `process.env.TARO_ENV` 区分。这是 Taro 的构建目标常量，编译期会被替换成字面量，
**未命中的分支会被 webpack 摇掉**——所以 H5 产物里不会残留微信登录的代码，反之亦然。

```ts
const IS_WEAPP = process.env.TARO_ENV === 'weapp'
```

## 2. API 基址策略

见 `src/config/index.ts`。规则一句话：**小程序默认绝对地址，H5 默认留空走同源**。

```ts
const DEFAULT_BASE = process.env.TARO_ENV === 'h5' ? '' : 'http://localhost:8080'
const API_BASE = (process.env.TARO_APP_API_BASE || DEFAULT_BASE).replace(/\/+$/, '')
```

- `apiBase` 为空串时，请求路径就是 `/api/xxx`，浏览器按当前页面同源发出；
- 开发期由 Taro devServer 代理到后端，生产期由 Nginx 反代 `/api`，两端都无跨域。

分析进度也只使用这个 API 基址：

```ts
`${config.apiBase}/api/analyze/${taskId}/stream`
```

H5 用浏览器 `EventSource`，微信小程序用
`Taro.request({ enableChunked: true })` 增量读取同一个 SSE 响应。两端事件契约完全一致，
微信端不再推导 `wsBase`，也不需要 socket 合法域名。

### 构建期覆盖

Taro **只注入 `TARO_APP_` 前缀**的环境变量，别的名字传了也读不到。

生产值不要在命令行上现写，写进 `config/frontend.env`（唯一真源，见 §10），构建时自动生成：

```bash
pnpm --filter @venus/miniapp build:weapp   # 读 .env.production（由真源生成）
pnpm --filter @venus/miniapp build:h5
```

临时压测、验证别的后端时可以用环境变量临时压过文件里的值：

```bash
TARO_APP_API_BASE=https://staging.example.com pnpm --filter @venus/miniapp build:weapp
```

只有把 H5 挂到**独立域名**（比如走 CDN）时才需要给 H5 传 `TARO_APP_API_BASE`，
那时后端必须同步配 `CORS_ORIGINS`（见 §5）。

## 3. 登录：两套逻辑并存

`src/pages/login/index.tsx` 一个页面同时承载两种方式，靠 `IS_WEAPP` 决定默认形态。

```
weapp 进页面
 └→ Taro.login() 拿 code → POST /api/auth/wx/login
    ├→ needPhone=false → 已绑过手机号，直接发 token，用户无感进首页
    └→ needPhone=true  → 返回 bindToken
       └→ 用户点 <Button open-type="getPhoneNumber">
          └→ POST /api/auth/wx/phone { bindToken, phoneCode } → 换正式登录态
       └→ 微信侧不可用（未配 appid 等）→ catch 里自动切到短信模式，不打断用户

h5 进页面
 └→ 直接就是短信模式（smsMode 初值 = !IS_WEAPP），不调 wx.login
    └→ POST /api/auth/sms/send → POST /api/auth/sms/verify
```

小程序端额外提供一个「使用手机验证码登录」的切换入口，H5 端不渲染该入口
（没有第二种方式可切）。

**未配正式 appid 时怎么联调**：后端 `WX_APPID` / `WX_SECRET` 任一为空即进入 mock 模式，
openid 由 `wx.login` 的 code 派生，手机号返回 `SMS_TEST_PHONE_PREFIX` 打头的固定号。
开发者工具用 touristappid 时 `getPhoneNumber` 拿不到 code，前端会带占位值 `'mock'` 继续走，
同样能拿到登录态。

## 4. 开发期：H5 的 devServer 代理

`config/dev.ts`：

```ts
h5: {
  devServer: {
    port: 10086,
    proxy: {
      '/api': { target: 'http://localhost:8080', changeOrigin: true },
    },
  },
}
```

- 前端在 `http://localhost:10086`，请求 `/api/*` 由 devServer 转给 8080，**浏览器看到的是同源**，
  不必为了本地联调去放开后端 CORS；
- 分析进度也是普通 HTTPS 请求，由该代理直接转发 SSE 响应。

小程序端不吃这个代理（它不经过 devServer），本地直连 `http://localhost:8080`，
微信开发者工具里勾上「不校验合法域名」即可。

## 5. 后端 CORS：默认不开，且大多数情况不该开

`apps/api` 提供了 `CORS_ORIGINS` 配置项（逗号分隔的完整 origin，含协议与端口）：

- **留空 = 完全不挂 `CORSMiddleware`**，这是默认值，也是同域部署下的正确选择；
- 只有前端挂在独立域名时才填，例如 `CORS_ORIGINS=https://h5.your-domain.com`。

中间件挂在 `RequestIdMiddleware` **之后**（Starlette 里后加的更靠外），
这样异常响应也带得上跨域头——否则前端只看到一个没有 CORS 头的 500，拿不到真实错误码。

**小程序与此项无关**：它不受同源策略约束，看的是微信后台的服务器域名白名单。

验证配置是否生效：

```bash
cd apps/api
poetry run python -c "from app.main import app; print([m.cls.__name__ for m in app.user_middleware])"
# 留空时     → ['RequestIdMiddleware']
# 配了域名时 → ['CORSMiddleware', 'RequestIdMiddleware']   # CORS 在最外层
```

## 6. 生产：Nginx 必须正确转发 SSE

生产主线的 Nginx 配置是 `infra/nginx/edge.conf`（由 `docker-compose.ecs.yml` 挂进 web 容器）。
里面有一条**专门**给分析进度 SSE 的 location，位置在通用 `/api/` 之前：

```nginx
location ~ ^/api/analyze/.+/stream$ {
    proxy_pass http://api;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    chunked_transfer_encoding on;
}
```

**为什么不能只靠通用 `location /api/`**：默认代理缓冲可能攒住 SSE 内容，客户端无法逐帧看到进度；
并且通用规则的 `proxy_read_timeout` 只有 60s，而出一份报告可达数分钟，连接会被中途掐断。

这条规则**对小程序和 H5 同等重要**——两端都读取 `/stream`。

仓库里的 nginx 配置只有两份，改 `/api` 规则时别改错文件：

| 文件 | 谁在用 | 有没有 `/api` 反代 |
|---|---|---|
| `infra/nginx/edge.conf` | `docker-compose.ecs.yml`（**生产主线**） | 有，SSE 规则在这里 |
| `infra/nginx/web.conf` | 烤进 web 镜像的内层静态服务 | 无，只托管静态文件 |


## 7. 构建与产物

```bash
pnpm --filter @venus/miniapp build:weapp   # → dist/weapp，用微信开发者工具导入这个目录
pnpm --filter @venus/miniapp build:h5      # → dist/h5，静态目录，交给 Nginx
pnpm --filter @venus/miniapp dev:h5        # watch 模式
```

`build:weapp` 实际是三步串联（用 `&&` 而不是 npm 的 pre 钩子——pnpm 的
`enable-pre-post-scripts` 默认值随版本变化，钩子可能被静默跳过）：

```
gen-frontend-env.mjs miniapp   从 config/frontend.env 生成 .env.production / .env.development
sync-appid.mjs production      把 .env 里的 appid 同步进 project.config.json
taro build --type weapp        真正编译
```

页面清单在 `src/app.config.ts`（小程序的 `pages` 数组即路由表，新增页面必须登记，否则不参与编译）：

```
pages/home/index            首页
pages/login/index           登录（微信一键 + 短信双模）
pages/capture/index         拍照上传
pages/analyzing/index       分析中（分块 SSE）
pages/report/index          报告（4S 雷达图 + 导出长图）
pages/radar-detail/index    单轴详情（点雷达某一维进来）
pages/booking/index         预约到店面诊
pages/legal/privacy/index   隐私政策
pages/legal/terms/index     用户协议
```

### 自查清单

```bash
cd apps/miniapp

# 只看自己代码的类型错误。@tarojs/components 自带的 d.ts 有一批既有告警，属于库的问题，过滤掉
./node_modules/.bin/tsc --noEmit -p tsconfig.json 2>&1 | grep "^src/"

# H5 产物不该残留写死的后端地址
grep -l "localhost:8080" dist/h5/js/*.js     # 期望：无输出

# 小程序产物必须有绝对基址
grep -o "http://localhost:8080" dist/weapp/common.js   # 期望：有输出
```

## 8. 排查速查

| 现象 | 大概率原因 |
|---|---|
| H5 控制台报 CORS 被拦 | devServer 代理没生效（`apiBase` 被 `TARO_APP_API_BASE` 覆盖成了绝对地址），或生产 Nginx 没反代 `/api` |
| 小程序请求全失败，提示域名不合法 | 域名没加进微信后台「服务器域名」；调试期可在开发者工具勾「不校验合法域名」 |
| 分析页进度不动 | 查看 Network 中 `/stream`：域名拦截看 request 白名单，404 看路由，长时间无分块看 Nginx buffering |
| 分析跑到一半连接中断 | `proxy_read_timeout` 太短（通用 `/api/` 是 60s） |
| H5 上微信一键登录按钮不见了 | 正常，H5 没有 `getPhoneNumber`，只渲染短信登录 |
| 改了 `TARO_APP_xxx` 不生效 | Taro 只注入 `TARO_APP_` 前缀；且这是**构建期**替换，改完要重新 build |

## 9. 目录结构

### 9.1 与前端相关的仓库全貌

```
yimei-4s/
├─ config/
│  ├─ frontend.env          前端配置唯一真源（H5 + 小程序共用，见 §10）
│  ├─ prod.baseline.env     后端非敏感配置（会打进镜像，禁止放密钥）
│  └─ dev.env               本地开发配置
├─ scripts/
│  └─ gen-frontend-env.mjs  frontend.env → 三个 .env 产物的分发脚本
├─ apps/
│  ├─ api/                  后端（FastAPI），三个前端产物共用这一套接口
│  ├─ web/                  H5 主线（React + Vite），产物由 web 镜像托管
│  │  └─ .env.production    【生成物，勿手改】
│  └─ miniapp/              小程序主线（Taro），顺带产出一份 H5
│     ├─ .env.production    【生成物，勿手改】
│     ├─ .env.development   【生成物，勿手改】
│     ├─ project.config.json  微信开发者工具读的静态文件，appid 由脚本写入
│     ├─ config/            Taro 构建配置（index/dev/prod）
│     ├─ scripts/sync-appid.mjs
│     └─ src/               见 9.2
└─ infra/
   ├─ build.sh              构建镜像；内含 gen-frontend-env 与密钥泄漏自查
   └─ nginx/
      ├─ edge.conf          生产主线：/api 反代 + SSE 分块配置（见 §6）
      └─ web.conf           镜像内层静态服务，不含 /api
```

### 9.2 `apps/miniapp/src`

```
src/
├─ app.tsx / app.css        应用入口与全局样式（CSS 变量：--gold / --rose / --ink-* 等）
├─ app.config.ts            页面路由表 + 导航栏样式（新增页面必须在这里登记）
├─ config/index.ts          API 基址、COPY 文案聚合（见 §2）
├─ api/
│  ├─ client.ts             apiRequest 封装 + AuthStore（注意入参是 data:，不是 body:）
│  ├─ auth.ts               wxLogin / wxBindPhone / smsSend / smsVerify
│  ├─ upload.ts             取直传凭证 + 上传照片
│  ├─ analyze.ts            创建分析任务、查报告
│  ├─ booking.ts            POST /api/bookings，字段与 apps/web/src/api/booking.ts 一一对应
│  └─ meta.ts               品牌/配额等元信息
├─ hooks/
│  ├─ useAnalyzeStream.ts   用分块 request 读取与 H5 相同的 SSE（见 §6）
│  └─ useCountdown.ts       短信验证码倒计时
├─ utils/
│  ├─ nav.ts               requireLogin 等跳转辅助
│  ├─ sse.ts               增量 UTF-8 解码与 SSE 帧解析
│  └─ storage.ts           Taro.storage 读写封装
├─ components/
│  ├─ BrandHeader / BrandLogo / AiBadge / DisclaimerFooter   品牌与合规展示
│  ├─ RadarChart           4S 雷达图（Canvas 绘制）
│  ├─ PhaseProgress        分析阶段进度
│  ├─ StreamingText        流式文本逐字显示
│  ├─ ReportExport         报告导出长图（Canvas，等效 H5 的 html2canvas）
│  └─ Legal                法务页排版组件（LegalDoc 数据驱动，privacy/terms 共用）
└─ pages/
   ├─ home/                首页
   ├─ login/               登录（微信一键 + 短信双模，见 §3）
   ├─ capture/             拍照上传
   ├─ analyzing/           分析中（分块 SSE）
   ├─ report/              报告（4S 雷达图 + 导出 + 预约 CTA）
   ├─ radar-detail/        单轴详情
   ├─ booking/             预约到店面诊
   └─ legal/privacy,terms  隐私政策 / 用户协议
```

### 9.3 小程序侧几处「不得已但等效」的实现

平台缺能力时一律找等效替代，不做视觉降级：

| 能力 | H5（`apps/web`） | 小程序（`apps/miniapp`） |
|---|---|---|
| 分析进度推送 | SSE（`EventSource`） | 同一 SSE（`Taro.request + enableChunked`） |
| 报告导出 | `html2canvas` 截 DOM | `Canvas` 手绘长图 + `saveImageToPhotosAlbum` |
| 加粗行内文本 | `<strong>` | `<Text className='lg-b'>`，数据模型是 `Segment = string \| { b: string }` |
| 日期时间选择 | `<input type="datetime-local">` | 两个 `<Picker>`（date + time）拼成 `` `${date}T${time}` `` |

> `<Canvas>` 是原生组件，用 `display:none` 隐藏会导致画不出来；导出用的画布必须挪到屏幕外
> （`position:fixed; left:-9999px`）。`canvasToTempFilePath` 的 `destWidth/destHeight` 要乘
> `pixelRatio`，否则存下来的图是糊的。

## 10. 配置：两端共用一份真源

**H5 和小程序共用一套配置**，唯一需要手写的文件是 `config/frontend.env`。

### 10.1 为什么最终还是有多个 `.env`

Vite 只注入 `VITE_` 前缀的变量，Taro 只注入 `TARO_APP_` 前缀的，前缀是构建工具的硬规则、
互不相认，两端没法直接共读一个文件。于是真源里写**不带前缀**的键，由
`scripts/gen-frontend-env.mjs` 按目标补前缀分发：

```
config/frontend.env
   ├─[共用] + [H5 专用]                        → apps/web/.env.production        (VITE_*)
   ├─[共用] + [小程序专用]                      → apps/miniapp/.env.production    (TARO_APP_*)
   └─[共用] + [小程序专用] + [小程序开发专用]    → apps/miniapp/.env.development   (TARO_APP_*)
                                                  同名键后者覆盖前者
```

那三个 `.env` 是**生成物，不要手改**，下次构建会被覆盖。人只维护 `config/frontend.env` 一份，
避免「H5 文案改了小程序没改」。

### 10.2 四个段落怎么分

真源里用 `# ===== [段名] =====` 分段，段名是脚本硬校验的，写错会直接报错：

| 段名 | 注入给谁 | 典型内容 |
|---|---|---|
| `[共用]` | 两端 | 品牌名/副标、免责声明、报告 CTA 与留资文案、配额提示、首页文案、`AUTH_MAX_AGE_DAYS` |
| `[H5 专用]` | 只有 H5 | `API_BASE`（**留空 = 同源**）、`BRAND_LOGO_URL` / `BRAND_HERO_ART_URL`（`public/` 相对路径） |
| `[小程序专用]` | 只有小程序 | `API_BASE`（**必须完整域名**）、`WX_APPID`、`BRAND_LOGO_URL`（要换外链得写完整 https） |
| `[小程序开发专用]` | 只有小程序开发态 | 本机联调的 `API_BASE`，覆盖上面的同名项，不影响线上 |

同名键在不同段里语义不同——这正是要分段的原因：`API_BASE` 对 H5 留空最好（同源），对小程序
留空则直接不可用。

### 10.3 安全边界

这些值会**明文出现在前端产物里**（小程序包能被解包看到），所以只放公开信息：
接口基址、appid、品牌文案、图片地址。任何密钥都留在后端环境变量里
（服务器 `/etc/venus-4s/.env`），绝不写进本文件。`infra/build.sh` 里有一道自查，
发现 `config/prod.baseline.env` 里出现密钥类键名会直接中止构建。

### 10.4 appid 怎么进 `project.config.json`

`project.config.json` 是微信开发者工具直接读的静态文件，不参与 Taro 构建，
环境变量到不了它里面。所以 `build:weapp` 前会跑 `scripts/sync-appid.mjs`：

- 从 `.env.production` 读 `TARO_APP_WX_APPID`（进程环境变量优先，方便 CI 注入密文）；
- 校验格式必须是 `wx` + 16 位十六进制，或开发者工具的 `touristappid`；
- 留空**不报错、不改文件**，保持 `touristappid` 原样——用测试号跑通流程是常规用法。

所以内测转正式的流程就是：**拿到审核通过的 appid，填进 `config/frontend.env` 的
`[小程序专用] WX_APPID`，重新 `build:weapp` 上传**，不用去开发者工具手改任何东西。

## 11. 部署与切换

### 11.1 H5 和微信是两套系统吗

**不是。** 一套后端 `apps/api`、一套配置真源 `config/frontend.env`、
小程序与 H5 调**同一批 `/api/*` 接口**。不同的只是前端产物的编译目标。

### 11.2 怎么切换 H5 / 微信

不存在「切换」这个动作——两个产物由同一份源码分别编译，可以同时在线：

```bash
pnpm --filter @venus/miniapp build:h5      # → dist/h5     交给 Nginx 当静态站
pnpm --filter @venus/miniapp build:weapp   # → dist/weapp  微信开发者工具导入并上传
```

运行时不需要判断：`src/config/index.ts` 里用编译期常量 `process.env.TARO_ENV` 分流
（见 §1、§2），未命中的分支会被 webpack 摇掉。

### 11.3 重新部署要单独做什么

| 改动落在哪 | 要做什么 |
|---|---|
| 只改了 `apps/miniapp/src/**` | `pnpm build:weapp` → 微信开发者工具重新上传体验版。后端、数据库、Nginx 都不用动 |
| 改了 `config/frontend.env` 的 `[共用]` 或 `[H5 专用]` | 重打 web 镜像（`infra/build.sh` 会自动重新生成 `.env.production`）→ 推 ACR → ECS 上 `docker compose -f docker-compose.ecs.yml pull && up -d` |
| 改了 `[小程序专用]` / `[小程序开发专用]` | 只影响小程序，重新 `build:weapp` 上传 |
| 只改了后端 | 重打 api 镜像，前端不用动 |

关键点：**这些配置是构建期注入的，不是运行时读取的**——改完不重新构建，线上不会有任何变化。

### 11.4 要改 Nginx 吗

**不用。** `infra/nginx/edge.conf` 里已有 `location ~ ^/api/analyze/.+/stream$`
（关闭 buffering/cache、超时 3600s，见 §6），小程序与 H5 直接复用同一条规则。
小程序与 H5 在 Nginx 眼里就是同一批 `/api` 请求，没有第二套入口。

要配的东西在**微信公众平台**，不在服务器 ——「开发管理 → 服务器域名」两个白名单都要加：

```
request 合法域名：https://rernaco.com     普通接口
uploadFile 合法域名：https://rernaco.com  照片上传 /api/upload/local
```

分析进度走 request 白名单下的 `/api/analyze/{id}/stream`，不需要 socket 合法域名。
只配 request 不配 uploadFile 的表现是：登录和普通接口正常，但照片上传失败。
白名单生效前，内测只能在开发者工具里勾「不校验合法域名」跑。



- [config/README.md](../../config/README.md)：`CORS_ORIGINS` 等配置项的落盘位置与优先级
- [02-部署实施.md](../02-部署实施.md)：Nginx 与镜像构建
- [04-日常运维与排查.md](../04-日常运维与排查.md)：线上故障排查
- [design/sections/06-frontend.md](../design/sections/06-frontend.md)：前端设计（含 `apps/web` H5 主线）
