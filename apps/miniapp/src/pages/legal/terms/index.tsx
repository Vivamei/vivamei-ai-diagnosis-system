import { LegalDoc, LegalPage } from '@/components/Legal'
import { COPY } from '@/config'

// 正文与 apps/web/src/pages/legal/TermsOfService.tsx 逐条对齐，改一处两边都要改。
const doc: LegalDoc = {
  title: '用户协议',
  version: 'v1.0',
  effectiveDate: '2026-06-29',
  contactEmail: 'legal@example.com',
  brand: COPY.brandSubtitle,
  toc: [
    { id: 'service', label: '一、服务说明' },
    { id: 'disclaimer', label: '二、免责声明' },
    { id: 'duties', label: '三、用户责任' },
    { id: 'ip', label: '四、知识产权' },
    { id: 'law', label: '五、争议管辖' },
    { id: 'contact', label: '六、联系方式' },
  ],
  sections: [
    {
      id: 'service',
      index: 'Ⅰ',
      title: '服务说明',
      blocks: [
        {
          type: 'p',
          text: [
            '「薇分美学 4S · AI 美学诊断报告」是一项基于 AI 多模态大模型的美学形象参考服务，输出 4S（分相 / 分型 / 分区 / 分层）结构化报告。',
          ],
        },
      ],
    },
    {
      id: 'disclaimer',
      index: 'Ⅱ',
      title: '免责声明',
      blocks: [
        {
          type: 'callout',
          tone: 'warning',
          text: [
            '本服务为',
            { b: '美学形象参考，不构成医疗诊断、治疗或术式建议。' },
            '任何医疗决策请咨询持证医师，并以面诊评估为准。',
          ],
        },
        {
          type: 'list',
          items: [
            ['AI 模型对个体的美学判断存在主观波动，', { b: '多次测试结果可能略有差异' }],
            ['报告内容不作为任何医疗、消费或法律事项的依据'],
          ],
        },
      ],
    },
    {
      id: 'duties',
      index: 'Ⅲ',
      title: '用户责任',
      blocks: [
        {
          type: 'list',
          items: [
            ['上传的照片须为本人或经授权'],
            ['不上传违法、违规、侵权内容'],
            ['遵守医疗与广告相关法律法规'],
          ],
        },
      ],
    },
    {
      id: 'ip',
      index: 'Ⅳ',
      title: '知识产权',
      blocks: [
        { type: 'p', text: ['服务平台代码、UI 设计、4S 体系均归本机构所有。报告内容归用户所有。'] },
      ],
    },
    {
      id: 'law',
      index: 'Ⅴ',
      title: '争议管辖',
      blocks: [
        { type: 'p', text: ['本协议适用中华人民共和国法律。如发生争议，由本机构注册地法院管辖。'] },
      ],
    },
    {
      id: 'contact',
      index: 'Ⅵ',
      title: '联系方式',
      blocks: [{ type: 'p', text: ['如有疑问，请联系 legal@example.com。'] }],
    },
  ],
}

export default function Terms() {
  return <LegalPage doc={doc} />
}
