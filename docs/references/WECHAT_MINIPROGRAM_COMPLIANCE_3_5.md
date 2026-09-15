# 微信小程序上线事项 3–5 办理指南

> 核对日期：2026-08-18。以下以微信官方文档、工信部备案查询系统和本项目实际配置为准。微信后台菜单可能改版，若文案略有差异，按同名功能进入。

## 3. 医美相关服务类目与行业资质

### 办理入口

登录 [微信公众平台](https://mp.weixin.qq.com/) 的小程序账号，进入：

`账号设置（或“设置与开发”） → 基本设置 → 服务类目 → 详情/添加服务类目`

微信官方当前没有一个统一名为“医美”的服务类目，应根据主体和实际功能在“医疗服务”下选择。不要用“生活服务 → 丽人服务 → 美容”规避资质；微信官方明确写明该类目不包含医疗美容服务。[来源：微信官方服务类目表](https://developers.weixin.qq.com/miniprogram/product/material/)

### 本项目优先选择建议

本项目包含面部照片分析、报告和“预约到店面诊”。若小程序主体就是单家私立医美机构：

- 二级及以下私立机构：`医疗服务 → 其他私立医疗机构`，上传以下任一项：《医疗机构执业许可证》《中医诊所备案证》《诊所备案证》。医美机构通常应提供《医疗机构执业许可证》。
- 三级私立机构：`医疗服务 → 三级私立医疗机构`，上传《医疗机构执业许可证》。
- 公立机构：`医疗服务 → 公立医疗机构`，同时上传《医疗机构执业许可证》和《事业单位法人证书》。

若小程序主体不是医疗机构，而是技术公司或多机构平台，不能简单借用一家诊所的许可证：

- 推荐多家医疗机构/项目、挂号等平台服务：通常是 `医疗服务 → 就医服务 → 医疗信息服务/挂号`，需要卫健委或医管局批文，或合作医院列表、协议样本、合作医院许可证及承诺书等材料。
- 在线问诊、疾病咨询：必须按 `医疗服务 → 互联网医院` 申报，并提供包含互联网诊疗范围的许可或平台合作及主管部门材料。

提交前确认营业执照主体、许可证主体、小程序认证主体一致；不一致时先准备盖章合作协议、授权链和平台要求的其他材料。最终以后台申请页面在提交当日显示的材料为准，微信官方也明确说明类目和材料会随政策变化。[来源：微信官方服务类目表](https://developers.weixin.qq.com/miniprogram/product/material/)

## 4. 生产域名 ICP、HTTPS 与微信服务器域名

这一步分三处办理，不能只在微信后台完成。

### 4.1 ICP 备案：阿里云办理

本项目部署在阿里云 ECS，因此从 [阿里云 ICP 备案系统](https://beian.aliyun.com/) 发起：

`阿里云控制台 → ICP备案 → 开始备案/去备案 → 首次备案或新增互联网信息服务`

选择实际承载业务的大陆 ECS，填写企业主体、负责人和域名资料，依次完成阿里云初审、工信部短信核验和省通信管理局审核。通过后到 [工信部 ICP/IP 地址/域名信息备案管理系统](https://beian.miit.gov.cn/) 查询域名，确认主体和备案号正确。

小程序备案与域名 ICP 备案是两件事；微信官方服务器域名规则明确要求域名已经 ICP 备案。[来源：微信官方网络文档](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)

### 4.2 DNS 与 HTTPS：阿里云和 ECS/Nginx 配置

1. `阿里云域名控制台 → DNS解析`：为实际业务域名添加 A 记录，指向 ECS 公网 IP。
2. `阿里云控制台 → 数字证书管理服务 → SSL证书管理`：申请/购买证书并完成域名验证。
3. 下载 Nginx 格式证书，按本项目部署文档放到服务器的 `infra/nginx/ssl/fullchain.pem` 与 `privkey.pem`，重启 web/Nginx。
4. 建议统一使用标准 443，不在请求 URL 中显式写 `:443`；确认完整证书链、域名匹配、证书未过期，并支持 TLS 1.2 及以上。

本项目当前生产配置使用 `rernaco.com`（见 [config/frontend.env](../../config/frontend.env) 与 [config/prod.baseline.env](../../config/prod.baseline.env)）。2026-08-20 通过本机 DNS 和 [Google Public DNS](https://dns.google/resolve?name=rernaco.com&type=A) 查询均可解析到 `101.200.45.222`；上线前仍需确认该域名已完成 ICP 备案、HTTPS 证书有效，并已加入微信服务器域名白名单。

### 4.3 微信后台服务器域名

ICP、DNS、证书全部正常后，进入：

`小程序后台 → 开发 → 开发设置 → 服务器域名`

本项目至少配置：

| 类型 | 填写值 | 用途 |
|---|---|---|
| request 合法域名 | `https://<生产域名>` | 登录及普通 API |
| uploadFile 合法域名 | `https://<生产域名>` | 上传面部照片 |
| socket 合法域名 | `wss://<生产域名>` | 分析进度 WebSocket |

只有使用 `wx.downloadFile` 从外部域名下载文件时才补充 downloadFile 合法域名；如直接上传 OSS，还要把实际 OSS 域名加入 uploadFile 合法域名。当前项目不使用 `web-view`，无需为这套原生流程配置“业务域名”。

微信官方要求服务器域名使用 HTTPS/WSS、不能是 IP 或 localhost、必须 ICP 备案。开发者工具中的“不校验合法域名”只能用于调试，不能证明真机或线上可用。[来源：微信官方网络文档](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)

## 5. 用户隐私保护指引

### 配置入口

微信官方当前给出的入口是：

`账号设置 → 服务内容声明 → 用户隐私保护指引 → 去完善`

提交审核时还有一个只针对待审版本的入口：

`管理 → 版本管理 → 提交代码审核 → 信息填写页面`

若提交审核时被拦截，应在第二个入口修改待审版本的指引。第一个入口修改现网版本，两个入口的作用范围不同。[来源：微信官方填写说明](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/)

### 本项目必须填写的三项

后台应使用微信显示的正式信息类型，不要只写接口名：

| 微信信息类型 | 对应项目能力 | 建议用途文案 |
|---|---|---|
| 收集你的手机号 | [`getPhoneNumber`](../../apps/miniapp/src/pages/login/index.tsx) | 用于手机号快捷登录、身份验证及到店预约联系 |
| 收集你选中的照片或视频信息 | [`chooseMedia`](../../apps/miniapp/src/pages/capture/index.tsx) | 用于用户主动选择或拍摄正脸照片，并生成 AI 美学形象参考报告 |
| 使用你的相册（仅写入）权限 | [`saveImageToPhotosAlbum`](../../apps/miniapp/src/components/ReportExport.tsx) | 用于按用户主动操作，将生成的报告图片保存到本机相册 |

以上三组“信息类型 ↔ 接口”的对应关系来自[微信官方隐私信息与接口对应表](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/miniprogram-intro.html)。

还需如实填写开发者联系方式、存储期限、信息使用规则、对外提供情况以及第三方插件/服务商情况。用途必须与代码、页面文案和自有隐私政策一致。面部照片属于高敏感度数据，应明确目的、保存期限和删除方式。

只在小程序内放一页自写《隐私政策》不等于完成微信后台的《用户隐私保护指引》。微信会根据版本实际调用的隐私接口生成必填项；未声明时对应接口会被禁用。平台已提供官方隐私授权弹窗，但必须使用真机清除授权数据后分别测试同意和拒绝路径。[来源：微信官方隐私协议开发指南](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/PrivacyAuthorize.html)

本项目自有隐私页目前仍使用 `privacy@example.com` 占位联系方式（见 [隐私页源码](../../apps/miniapp/src/pages/legal/privacy/index.tsx)），提审前必须替换为真实、可响应的联系方式。

## 提交前验收

- [ ] 服务类目与小程序实际页面、主体类型完全一致，行业资质在有效期内且主体关系清晰。
- [ ] 工信部系统能查询生产域名 ICP，域名已有公网 DNS 解析。
- [ ] `https://<生产域名>/health` 证书校验通过；真机可完成普通请求、照片上传和 WSS 进度。
- [ ] 微信后台已配置 request、uploadFile、socket 三类服务器域名。
- [ ] 待审版本隐私指引包含手机号、选中的照片或视频信息、相册仅写入权限。
- [ ] 清除微信授权状态后，真机测试隐私同意、拒绝及二次操作均符合预期。

## 一手来源

- 微信官方：[小程序开放的服务类目](https://developers.weixin.qq.com/miniprogram/product/material/)
- 微信官方：[网络与服务器域名配置](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)
- 微信官方：[用户隐私保护指引填写说明](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/)
- 微信官方：[隐私信息类型与接口对应表](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/miniprogram-intro.html)
- 微信官方：[小程序隐私协议开发指南](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/PrivacyAuthorize.html)
- 工信部：[ICP/IP 地址/域名信息备案管理系统](https://beian.miit.gov.cn/)
- 阿里云：[ICP备案系统](https://beian.aliyun.com/)
