interface Props {
  text: string;
  active: boolean;
}

export function StreamingText({ text, active }: Props) {
  return (
    <div
      style={{
        fontSize: 13,
        lineHeight: 1.75,
        color: "inherit",
        minHeight: 24,
      }}
    >
      {text}
      {active && (
        <span style={{ animation: "blink 1s steps(2) infinite" }}>▌</span>
      )}
    </div>
  );
}
