import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const appRoot = new URL('../', import.meta.url)

async function source(relativePath) {
  return readFile(new URL(relativePath, appRoot), 'utf8')
}

const [
  appConfig,
  home,
  login,
  loginConfig,
  authApi,
  aiNotice,
  analyzing,
  report,
  radarDetail,
  reportExport,
] = await Promise.all([
  source('src/app.config.ts'),
  source('src/pages/home/index.tsx'),
  source('src/pages/login/index.tsx'),
  source('src/pages/login/index.config.ts'),
  source('src/api/auth.ts'),
  source('src/components/AiGeneratedNotice.tsx'),
  source('src/pages/analyzing/index.tsx'),
  source('src/pages/report/index.tsx'),
  source('src/pages/radar-detail/index.tsx'),
  source('src/components/ReportExport.tsx'),
])

const firstPage = appConfig.match(/pages:\s*\[\s*['"]([^'"]+)['"]/)?.[1]
const handleStartAt = home.indexOf('const handleStart')
const loginGuardAt = home.indexOf('if (!requireLogin()) return', handleStartAt)
const requireLoginCalls = home.match(/requireLogin\(\)/g)?.length ?? 0

const checks = [
  [firstPage === 'pages/home/index', '小程序首屏必须是可匿名浏览的首页'],
  [home.includes('if (!AuthStore.tokens)'), '首页展示时必须对游客静默跳过登录态数据请求'],
  [
    handleStartAt >= 0 && loginGuardAt > handleStartAt && requireLoginCalls === 1,
    '只能在用户点击“开始测一测”后触发登录守卫',
  ],
  [login.includes('手机号快捷登录'), '手机号授权按钮必须使用“手机号快捷登录”文案'],
  [login.includes('暂不登录，先浏览首页'), '登录页必须提供明确的返回匿名浏览入口'],
  [
    !login.includes('微信'),
    '登录页面不得包含易与平台官方能力混淆的“微信”字样',
  ],
  [
    !login.includes('username') &&
      !authApi.includes('username') &&
      !/chooseAvatar|getUserProfile|getUserInfo/.test(login),
    '登录阶段不得收集昵称或头像',
  ],
  [loginConfig.includes("navigationBarTitleText: '手机号快捷登录'"), '登录页标题必须明确为手机号快捷登录'],
  [
    aiNotice.includes('本服务为AI生成内容，结果仅供参考'),
    'AI 内容标识必须使用审核认可的明确文案',
  ],
  [
    analyzing.includes('<AiGeneratedNotice />'),
    'AI 分析生成页必须在显著位置展示 AI 内容标识',
  ],
  [
    report.includes('<AiGeneratedNotice />'),
    'AI 报告页必须在显著位置展示 AI 内容标识',
  ],
  [
    radarDetail.includes('<AiGeneratedNotice />'),
    'AI 报告详情页必须在显著位置展示 AI 内容标识',
  ],
  [
    reportExport.includes('本服务为AI生成内容，结果仅供参考'),
    '导出的 AI 报告图片必须包含 AI 内容标识',
  ],
]

const failures = checks.filter(([ok]) => !ok).map(([, message]) => message)

if (failures.length) {
  console.error('Mini-program review compliance check failed:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exitCode = 1
} else {
  console.log(`Mini-program review compliance check passed (${checks.length} checks).`)
}
