export const TECHNOLOGIES = [
  "LangGraph",
  "RAG",
  "OpenAI",
  "LangSmith",
  "Pydantic",
  "FastAPI",
  "Vercel",
  "Render",
  "Supabase PostgreSQL",
  "SSE",
] as const;

export function TechnologyStrip({ className = "", technologies = TECHNOLOGIES }: { className?: string; technologies?: readonly string[] }) {
  return (
    <p className={`briefing-technology-line mono${className ? ` ${className}` : ""}`}>
      {technologies.map((technology) => <span key={technology}>{technology}</span>)}
    </p>
  );
}
