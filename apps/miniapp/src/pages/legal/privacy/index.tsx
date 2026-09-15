import { LegalDoc, LegalPage } from '@/components/Legal'
import { COPY } from '@/config'

// 正文与 apps/web/src/pages/legal/PrivacyPolicy.tsx 逐条对齐，改一处两边都要改。
const doc: LegalDoc = {
  title: '隐私政策',
  version: 'v1.0',
  effectiveDate: '2026-06-29',
  contactEmail: 'privacy@example.com',
  brand: COPY.brandSubtitle,
  toc: [
    { id: 'collect', label: '一、信息收集' },
    { id: 'purpose', label: '二、用途与保留期' },
    { id: 'sharing', label: '三、第三方共享' },
    { id: 'rights', label: '四、您的权利' },
    { id: 'disclaimer', label: '五、免责声明' },
  ],
  sections: [
    {
      id: 'collect',
      index: 'Ⅰ',
      title: '信息收集',
      blocks: [
        { type: 'p', text: ['为了向您提供 4S 美学诊断服务，我们会收集以下信息：'] },
        {
          type: 'list',
          items: [
            [{ b: '面部照片' }, '：用于 AI 4S 美学诊断分析'],
            [{ b: '手机号' }, '：用于身份验证与到店预约联系'],
            [{ b: '设备 IP / User Agent' }, '：用于安全审计与异常防护'],
          ],
        },
      ],
    },
    {
      id: 'purpose',
      index: 'Ⅱ',
      title: '用途与保留期',
      blocks: [
        {
          type: 'table',
          headers: ['信息类别', '用途', '保留期'],
          rows: [
            [['面部照片'], ['AI 分析生成 4S 报告'], ['上传后 ', { b: '10 天内自动删除' }]],
            [['手机号'], ['身份认证、到店预约联系'], ['加密存储，可申请删除']],
            [['4S 报告内容'], ['复看历史报告'], ['加密存储，可申请删除']],
            [['操作审计日志'], ['安全审计与合规'], ['6 个月']],
          ],
        },
      ],
    },
    {
      id: 'sharing',
      index: 'Ⅲ',
      title: '第三方共享',
      blocks: [
        {
          type: 'list',
          items: [
            [
              { b: '阿里云对象存储 / 内容安全 / 短信服务' },
              '：已签订《数据处理协议》(DPA)，仅在本服务范围内使用',
            ],
            [{ b: 'AI 模型服务' }, '：仅传输 OSS 内网签名 URL，不长期留存原图'],
          ],
        },
      ],
    },
    {
      id: 'rights',
      index: 'Ⅳ',
      title: '您的权利',
      blocks: [
        {
          type: 'list',
          items: [
            [{ b: '查询' }, '：通过我们的客服查询您的个人信息'],
            [{ b: '删除' }, '：随时申请删除您的照片与历史数据'],
            [{ b: '撤回同意' }, '：撤回后将停止处理您的数据'],
            [{ b: '投诉' }, '：发送邮件至 privacy@example.com'],
          ],
        },
      ],
    },
    {
      id: 'disclaimer',
      index: 'Ⅴ',
      title: '免责声明',
      blocks: [
        {
          type: 'callout',
          tone: 'warning',
          text: [
            '本服务输出的 4S 美学报告为',
            { b: '美学形象参考，不构成医疗诊断、治疗或术式建议。' },
            '美学判断存在主观波动，结果仅供参考。',
          ],
        },
      ],
    },
  ],
}

export default function Privacy() {
  return <LegalPage doc={doc} />
}
