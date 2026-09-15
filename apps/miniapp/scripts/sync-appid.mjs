/**
 * 把 .env.* 里的 TARO_APP_WX_APPID 同步进 project.config.json。
 *
 * 为什么需要这个脚本：project.config.json 是微信开发者工具直接读的静态文件，不参与
 * Taro 构建，Taro 注入的环境变量到不了它里面。而 appid 又必须和 .env 里的域名配置
 * 一起变（换主体 = 换 appid + 换备案域名），分散在两处很容易只改一半，表现为
 * 「上传到了错误的小程序」或「域名白名单对不上」，这两种错都要到真机上才暴露。
 *
 * 用法：由 package.json 的 build:weapp / dev:weapp 用 && 串在 taro build 前面自动调用，
 * 无需手动执行。不用 npm 的 prebuild/predev 钩子，是因为 pnpm 的
 * enable-pre-post-scripts 默认值随版本变化，钩子可能被静默跳过。
 *   node scripts/sync-appid.mjs production   → 读 .env.production
 *   node scripts/sync-appid.mjs              → 读 .env.development
 * 环境名走命令行参数而不是 `NODE_ENV=x node ...`：后者在 Windows 的 cmd 下不是合法
 * 语法，而本项目的日常开发就在 Windows 上。
 *
 * 没配 TARO_APP_WX_APPID 时不报错、不改文件，保持 touristappid 原样——本地用测试号
 * 跑通流程是常规用法，不该被构建脚本拦下。
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const envName = process.argv[2] === 'production' ? 'production' : 'development'
const envPath = resolve(root, `.env.${envName}`)
const configPath = resolve(root, 'project.config.json')

/** 极简 dotenv：只认 KEY=VALUE，够读一个 appid 了，不值得为此加依赖。 */
function readEnvValue(path, key) {
  let text
  try {
    text = readFileSync(path, 'utf8')
  } catch {
    return null
  }
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq === -1) continue
    if (trimmed.slice(0, eq).trim() !== key) continue
    return trimmed
      .slice(eq + 1)
      .trim()
      .replace(/^["']|["']$/g, '')
  }
  return null
}

// 进程环境优先于 .env 文件：CI 里通常用密文变量注入，不会去改仓库里的文件。
const appid = process.env.TARO_APP_WX_APPID || readEnvValue(envPath, 'TARO_APP_WX_APPID')

if (!appid) {
  console.log(`[sync-appid] .env.${envName} 未配 TARO_APP_WX_APPID，保持现有 appid 不变`)
  process.exit(0)
}

// 只放行微信正式 appid 与开发者工具的游客号。写错一个字符，开发者工具只会说
// 「appid 不合法」，不会告诉你它来自哪个文件，所以在这里就拦住。
if (!/^(wx[0-9a-f]{16}|touristappid)$/.test(appid)) {
  console.error(
    `[sync-appid] TARO_APP_WX_APPID="${appid}" 格式不对，应为 wx + 16 位十六进制，或 touristappid`,
  )
  process.exit(1)
}

const config = JSON.parse(readFileSync(configPath, 'utf8'))
if (config.appid === appid) {
  console.log(`[sync-appid] project.config.json 已是 ${appid}，无需改动`)
  process.exit(0)
}

config.appid = appid
// 保留两空格缩进与末尾换行，避免每次构建都在这个文件上制造无谓的 diff。
writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`, 'utf8')
console.log(`[sync-appid] project.config.json appid → ${appid}`)
