import { POLARITY, aspectLabel } from "../lib/aspects";

/**
 * A review with each aspect phrase underlined in its sentiment colour and
 * labelled underneath. Used in the hero (static examples) and in results.
 *
 * segments: [{ text, aspect?, polarity? }]
 */
export function AnnotatedText({ segments, size = "lg", animate = false, labels = true }) {
  const sizes = {
    xl: "text-[2rem] leading-[1.9] sm:text-5xl sm:leading-[1.75] lg:text-[3.6rem] lg:leading-[1.7]",
    lg: "text-2xl leading-[1.6] sm:text-3xl sm:leading-[1.55]",
  };
  let marked = 0;
  return (
    <p className={`font-serif ${sizes[size]} ${animate ? "draw" : ""}`}>
      {segments.map((seg, i) => {
        if (!seg.aspect) return <span key={i}>{seg.text}</span>;
        const p = POLARITY[seg.polarity] ?? POLARITY.neutral;
        const delay = `${0.3 + marked++ * 0.55}s`;
        if (!labels) {
          // underline only; short phrases close together would make labels collide
          return <span key={i} className={`mark ${p.mark}`} title={`${aspectLabel(seg.aspect)}: ${p.label.toLowerCase()}`}>{seg.text}</span>;
        }
        return (
          <span key={i} className="inline-flex flex-col items-start align-baseline">
            <span className={`mark ${p.mark}`} style={animate ? { "--d": delay } : undefined}>
              {seg.text}
            </span>
            <span
              className={`mt-0.5 w-0 whitespace-nowrap font-sans text-sm font-medium tracking-normal sm:text-base ${p.text} ${animate ? "fade-in" : ""}`}
              style={animate ? { animationDelay: `calc(${delay} + 0.45s)` } : undefined}
            >
              {aspectLabel(seg.aspect)}: {p.label.toLowerCase()}
            </span>
          </span>
        );
      })}
    </p>
  );
}

/** Turn an API result into segments, using each aspect's character span. */
export function segmentsFromResult(result) {
  const { text, aspects } = result;
  const isWord = (ch) => ch !== undefined && /[\p{L}\p{N}']/u.test(ch);
  const spans = aspects
    .filter((a) => Array.isArray(a.span) && a.span[1] > a.span[0])
    .map((a) => {
      // snap to whole words, so "deliver" inside "delivery" underlines the full word
      let start = Math.max(0, a.span[0]), end = Math.min(text.length, a.span[1]);
      while (start > 0 && isWord(text[start - 1])) start--;
      while (end < text.length && isWord(text[end])) end++;
      return { start, end, aspect: a.aspect, polarity: a.polarity };
    })
    .sort((a, b) => a.start - b.start);

  const segments = [];
  let pos = 0;
  for (const s of spans) {
    if (s.start < pos) continue; // skip overlapping spans
    if (s.start > pos) segments.push({ text: text.slice(pos, s.start) });
    segments.push({ text: text.slice(s.start, s.end), aspect: s.aspect, polarity: s.polarity });
    pos = s.end;
  }
  if (pos < text.length) segments.push({ text: text.slice(pos) });
  return segments;
}
