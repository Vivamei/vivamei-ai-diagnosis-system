import { useParams } from "react-router-dom";
import PrivacyPolicy from "./legal/PrivacyPolicy";
import TermsOfService from "./legal/TermsOfService";

export default function LegalPage() {
  const { kind } = useParams<{ kind: string }>();

  if (kind === "privacy") return <PrivacyPolicy />;
  if (kind === "terms") return <TermsOfService />;

  return (
    <div
      style={{
        padding: 24,
        textAlign: "center",
        color: "var(--ink-soft)",
        fontSize: 14,
      }}
    >
      未找到该文档。
    </div>
  );
}
