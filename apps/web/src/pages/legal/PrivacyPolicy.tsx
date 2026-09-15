import {
  LegalLayout,
  LegalSection,
  LegalList,
  LegalItem,
  LegalTable,
  LegalCallout,
  TocItem,
} from "./LegalLayout";

const toc: TocItem[] = [
  { id: "collect", label: "一、信息收集" },
  { id: "purpose", label: "二、用途与保留期" },
  { id: "sharing", label: "三、第三方共享" },
  { id: "rights", label: "四、您的权利" },
  { id: "disclaimer", label: "五、免责声明" },
];

export default function PrivacyPolicy() {
  return (
    <LegalLayout
      title="隐私政策"
      version="v1.0"
      effectiveDate="2026-06-29"
      toc={toc}
      contactEmail="privacy@example.com"
    >
      <LegalSection id="collect" index="Ⅰ" title="信息收集">
        <p>为了向您提供 4S 美学诊断服务,我们会收集以下信息:</p>
        <LegalList>
          <LegalItem>
            <strong>面部照片</strong>:用于 AI 4S 美学诊断分析
          </LegalItem>
          <LegalItem>
            <strong>手机号</strong>:用于身份验证与到店预约联系
          </LegalItem>
          <LegalItem>
            <strong>设备 IP / User Agent</strong>:用于安全审计与异常防护
          </LegalItem>
        </LegalList>
      </LegalSection>

      <LegalSection id="purpose" index="Ⅱ" title="用途与保留期">
        <LegalTable
          headers={["信息类别", "用途", "保留期"]}
          rows={[
            [
              "面部照片",
              "AI 分析生成 4S 报告",
              <span key="p1">
                上传后 <strong>10 天内自动删除</strong>
              </span>,
            ],
            ["手机号", "身份认证、到店预约联系", "加密存储,可申请删除"],
            ["4S 报告内容", "复看历史报告", "加密存储,可申请删除"],
            ["操作审计日志", "安全审计与合规", "6 个月"],
          ]}
        />
      </LegalSection>

      <LegalSection id="sharing" index="Ⅲ" title="第三方共享">
        <LegalList>
          <LegalItem>
            <strong>阿里云对象存储 / 内容安全 / 短信服务</strong>:已签订
            《数据处理协议》(DPA),仅在本服务范围内使用
          </LegalItem>
          <LegalItem>
            <strong>AI 模型服务</strong>:仅传输 OSS 内网签名 URL,不长期留存原图
          </LegalItem>
        </LegalList>
      </LegalSection>

      <LegalSection id="rights" index="Ⅳ" title="您的权利">
        <LegalList>
          <LegalItem>
            <strong>查询</strong>:通过我们的客服查询您的个人信息
          </LegalItem>
          <LegalItem>
            <strong>删除</strong>:随时申请删除您的照片与历史数据
          </LegalItem>
          <LegalItem>
            <strong>撤回同意</strong>:撤回后将停止处理您的数据
          </LegalItem>
          <LegalItem>
            <strong>投诉</strong>:发送邮件至{" "}
            <a
              href="mailto:privacy@example.com"
              style={{
                color: "var(--gold-deep)",
                textDecoration: "underline",
              }}
            >
              privacy@example.com
            </a>
          </LegalItem>
        </LegalList>
      </LegalSection>

      <LegalSection id="disclaimer" index="Ⅴ" title="免责声明">
        <LegalCallout tone="warning">
          本服务输出的 4S 美学报告为
          <strong>美学形象参考,不构成医疗诊断、治疗或术式建议。</strong>
          美学判断存在主观波动,结果仅供参考。
        </LegalCallout>
      </LegalSection>
    </LegalLayout>
  );
}
