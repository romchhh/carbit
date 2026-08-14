type JsonLdProps = {
  data: Record<string, unknown> | Record<string, unknown>[];
};

/** Безпечний JSON-LD: екранує `<` щоб не зламати HTML. */
export function JsonLd({ data }: JsonLdProps) {
  const payload = Array.isArray(data) ? data : [data];
  const json = JSON.stringify(payload).replace(/</g, "\\u003c");

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: json }}
    />
  );
}
