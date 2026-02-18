type EvidenceRecord = Record<string, unknown>;
type StreamMatchEvidenceMap = Record<string, { [key: string]: unknown }> | null | undefined;

type MatchedTerm = {
  key: string;
  value: string;
  field: "title" | "content";
};

const asRecord = (value: unknown): EvidenceRecord | null => {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as EvidenceRecord;
};

const toString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const normalized = value.trim();
  return normalized || null;
};

const normalizeField = (field: unknown): "title" | "content" | null => {
  if (field === "title") {
    return "title";
  }
  if (field === "content_text") {
    return "content";
  }
  return null;
};

const addMatchedTerm = (
  terms: MatchedTerm[],
  seen: Set<string>,
  payload: { value: unknown; field: unknown }
) => {
  const normalizedValue = toString(payload.value);
  const normalizedField = normalizeField(payload.field);
  if (!normalizedValue || !normalizedField) {
    return;
  }
  const key = `${normalizedValue.toLowerCase()}|${normalizedField}`;
  if (seen.has(key)) {
    return;
  }
  seen.add(key);
  terms.push({ key, value: normalizedValue, field: normalizedField });
};

export const buildMatchedTermsSummary = (
  streamIds: string[],
  streamMatchEvidence: StreamMatchEvidenceMap,
  maxTerms: number = 3
): string | null => {
  if (maxTerms <= 0) {
    return null;
  }
  const terms: MatchedTerm[] = [];
  const seen = new Set<string>();

  for (const streamId of streamIds) {
    const evidence = asRecord(streamMatchEvidence?.[streamId]);
    if (!evidence) {
      continue;
    }
    const matcherType = toString(evidence.matcher_type);
    const rulesEvidence = matcherType === "hybrid" ? asRecord(evidence.rules) : evidence;
    const classifierEvidence = matcherType === "hybrid" ? asRecord(evidence.classifier) : evidence;

    const keywordHits = Array.isArray(rulesEvidence?.keyword_hits) ? rulesEvidence.keyword_hits : [];
    keywordHits.forEach((entry) => {
      const hit = asRecord(entry);
      if (!hit) {
        return;
      }
      addMatchedTerm(terms, seen, { value: hit.value, field: hit.field });
    });

    const regexHits = Array.isArray(rulesEvidence?.regex_hits) ? rulesEvidence.regex_hits : [];
    regexHits.forEach((entry) => {
      const hit = asRecord(entry);
      if (!hit) {
        return;
      }
      addMatchedTerm(terms, seen, { value: hit.value, field: hit.field });
    });

    const queryHits = Array.isArray(rulesEvidence?.query_hits) ? rulesEvidence.query_hits : [];
    queryHits.forEach((entry) => {
      const hit = asRecord(entry);
      if (!hit) {
        return;
      }
      addMatchedTerm(terms, seen, { value: hit.token ?? hit.value, field: hit.field });
    });

    const classifierFindings = Array.isArray(classifierEvidence?.findings) ? classifierEvidence.findings : [];
    classifierFindings.forEach((entry) => {
      const finding = asRecord(entry);
      if (!finding) {
        return;
      }
      addMatchedTerm(terms, seen, { value: finding.value ?? finding.text, field: finding.field });
    });
  }

  if (terms.length === 0) {
    return null;
  }
  const orderedTerms = [...terms].sort((left, right) => {
    if (left.field === right.field) {
      return 0;
    }
    return left.field === "title" ? -1 : 1;
  });
  const displayed = orderedTerms.slice(0, maxTerms).map((term) => `${term.value} (${term.field})`);
  const remainder = orderedTerms.length - displayed.length;
  if (remainder > 0) {
    return `${displayed.join(", ")} +${remainder}`;
  }
  return displayed.join(", ");
};
