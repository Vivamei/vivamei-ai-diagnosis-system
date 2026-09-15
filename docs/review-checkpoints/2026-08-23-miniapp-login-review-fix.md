# 小程序登录提审整改检查点（2026-08-23）

## Fixed point / base

- Git base SHA：不适用。当前交付目录不是 Git worktree，`git status` 返回 `not a git repository`。
- 整改前替代基线（SHA-256）：
  - `apps/miniapp/src/pages/home/index.tsx`：`3D529827354A0BF43E160323D34D9B7FD6A507DD125294CAA094A50A11095190`
  - `apps/miniapp/src/pages/login/index.tsx`：`D0057BEEBCCF743DC0C56D044832F551A0E5EBE4C3612F35ED085E3318B0C2A3`
  - `apps/miniapp/src/pages/login/index.config.ts`：`617927AFE1A2BAC193EECE5BF10E83624B6FAC5C4E463B151A7B3525F1E94AD9`
- 本检查点后的核心源码指纹（SHA-256）：
  - `apps/miniapp/src/pages/home/index.tsx`：`1BCFFEACC9800DBDA7E37B110D54F5BADC5D95BF94E27946883F63F8F030D388`
  - `apps/miniapp/src/pages/login/index.tsx`：`6D4E3F60B98DB5B412D07286E19C24E0CC3E33FAA5F754D7DE079258DB0FD04C`
  - `apps/miniapp/src/api/auth.ts`：`6064AEFABDD0391014D715981115618895E81985BC8DB9CC441533AEF15013C1`
- 后续 review 应从上述“本检查点后”指纹开始，仅检查其后的增量；若目录恢复 Git 管理，则改用当时的提交 SHA。

## 审查范围

- 小程序启动页、首页登录触发时机、登录页手机号快速验证与验证码登录链路。
- 登录请求中的昵称字段、用户可见错误文案、登录页样式与页面标题。
- 生产构建产物 `apps/miniapp/dist/weapp`。
- 不含后端认证机制重构、匿名分析能力或微信开发者工具真机操作。

## 发现与修复

1. 首页 `useDidShow` 对游客调用 `requireLogin()`，打开小程序即跳登录页。
   - 改为游客只跳过个人报告查询；仅在用户主动点击“开始测一测”后触发登录守卫。
2. 手机号授权按钮和相关提示含“微信一键登录”等易混淆平台官方能力的字样。
   - 统一改为“手机号快捷登录”，并将用户可见的相关错误文案改为中性表述。
3. 登录页展示并提交昵称字段。
   - 移除昵称输入及小程序登录 API 的 `username` 参数；未调用头像/用户资料授权接口。
4. 登录页缺少明确的非登录出口。
   - 增加“暂不登录，先浏览首页”，返回匿名首页。
5. 手机号组件在协议未勾选时仍可点击。
   - 未同意协议时禁用手机号快捷登录按钮。
6. 缺少自动化提审回归检查。
   - 新增 `pnpm --dir apps/miniapp run check:review-compliance`，覆盖 8 项关键约束。

## 验证结果

- 整改前回归检查：7 项失败，覆盖本次审核问题。
- `pnpm --dir apps/miniapp run check:review-compliance`：通过（8 项）。
- `pnpm --dir apps/miniapp exec tsc --noEmit --skipLibCheck`：通过。
- `pnpm --dir apps/miniapp run build:weapp`：完成，生产产物已重新生成。
- `pnpm --dir apps/miniapp run check:weapp-wxss`：通过（10 个 WXSS 文件）。
- 构建产物检查：首屏为 `pages/home/index`；登录页标题及按钮为“手机号快捷登录”；包含“暂不登录”入口；登录页 chunk 不含“微信”字样、`username`、头像或用户资料授权 API。
- `python -m py_compile apps/api/app/services/wechat.py`：通过。

## 剩余阻塞与风险

- 裸 `tsc --noEmit` 会被 Taro 4.2.1 依赖声明中的 `CommonEventFunction` 缺失阻断；因此第三方声明文件未做完整类型校验。业务源码已通过 `--skipLibCheck`，生产构建也完成，当前不构成运行时阻塞。
- 当前环境未执行微信开发者工具预览及真机清缓存测试，尚未实测平台原生手机号授权弹窗、拒绝授权和返回首页的视觉/交互。提交前需用游客态真机走一遍：首页可浏览 → 主动点击开始测评 → 登录页 → 暂不登录/授权/拒绝三条路径。
