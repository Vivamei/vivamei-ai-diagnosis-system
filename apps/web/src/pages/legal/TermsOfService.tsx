import {
  LegalLayout,
  LegalSection,
  LegalList,
  LegalItem,
  LegalCallout,
  TocItem,
} from "./LegalLayout";

const toc: TocItem[] = [
  { id: "service", label: "一、服务说明" },
  { id: "disclaimer", label: "二、免责声明" },
  { id: "duties", label: "三、用户责任" },
  { id: "ip", label: "四、知识产权" },
  { id: "law", label: "五、争议管辖" },
  { id: "contact", label: "六、联系方式" },
];

export default function TermsOfService() {
  return (
    <LegalLayout
      title="用户协议"
      version="v1.0"
      effectiveDate="2026-06-29"
      toc={toc}
      contactEmail="legal@example.com"
    >
      <LegalSection id="service" index="Ⅰ" title="服务说明">
        <p>
          「薇分美学 4S · AI 美学诊断报告」是一项基于 AI 多模态大模型的美学形象参考服务,
          输出 4S(分相 / 分型 / 分区 / 分层)结构化报告。
        </p>
      </LegalSection>

      <LegalSection id="disclaimer" index="Ⅱ" title="免责声明">
        <LegalCallout tone="warning">
          本服务为
          <strong>美学形象参考,不构成医疗诊断、治疗或术式建议。</strong>
          任何医疗决策请咨询持证医师,并以面诊评估为准。
        </LegalCallout>
        <LegalList>
          <LegalItem>
            AI 模型对个体的美学判断存在主观波动,
            <strong>多次测试结果可能略有差异</strong>
          </LegalItem>
          <LegalItem>报告内容不作为任何医疗、消费或法律事项的依据</LegalItem>
        </LegalList>
      </LegalSection>

      <LegalSection id="duties" index="Ⅲ" title="用户责任">
        <LegalList>
          <LegalItem>上传的照片须为本人或经授权</LegalItem>
          <LegalItem>不上传违法、违规、侵权内容</LegalItem>
          <LegalItem>遵守医疗与广告相关法律法规</LegalItem>
        </LegalList>
      </LegalSection>

      <LegalSection id="ip" index="Ⅳ" title="知识产权">
        <p>
          服务平台代码、UI 设计、4S 体系均归本机构所有。报告内容归用户所有。
        </p>
      </LegalSection>

      <LegalSection id="law" index="Ⅴ" title="争议管辖">
        <p>本协议适用中华人民共和国法律。如发生争议,由本机构注册地法院管辖。</p>
      </LegalSection>

      <LegalSection id="contact" index="Ⅵ" title="联系方式">
        <p>
          如有疑问,请联系{" "}
          <a
            href="mailto:legal@example.com"
            style={{ color: "var(--gold-deep)", textDecoration: "underline" }}
          >
            legal@example.com
          </a>
          。
        </p>
      </LegalSection>
    </LegalLayout>
  );
}
