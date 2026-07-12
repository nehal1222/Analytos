import React from "react";

// Small inline SVG icon set (no external image files/network calls) --
// consistent 24x24 stroke style, colored via currentColor so it follows
// the surrounding text color in both themes.
const ICON_PROPS = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

function DocumentIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="13" y2="17" />
    </svg>
  );
}

function ExtractIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M12 3l1.8 4.9L19 9.5l-4.9 1.8L12 16l-1.8-4.7L5 9.5l5.2-1.6L12 3z" />
      <path d="M19 15l.9 2.4L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.6L19 15z" />
    </svg>
  );
}

function BranchIcon() {
  return (
    <svg {...ICON_PROPS}>
      <line x1="6" y1="3" x2="6" y2="15" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="6" r="3" />
      <path d="M18 9a9 9 0 0 1-9 9" />
    </svg>
  );
}

function ReviewIcon() {
  return (
    <svg {...ICON_PROPS}>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12l3 3 5-6" />
    </svg>
  );
}

function MergeIcon() {
  return (
    <svg {...ICON_PROPS}>
      <circle cx="6" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="18" r="3" />
      <path d="M6 9v3a6 6 0 0 0 6 6h3" />
      <path d="M18 15V6" />
    </svg>
  );
}

function MonitorIcon() {
  return (
    <svg {...ICON_PROPS}>
      <rect x="2" y="4" width="20" height="13" rx="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  );
}

function PlugIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M9 2v5M15 2v5M7 7h10v3a5 5 0 0 1-5 5 5 5 0 0 1-5-5V7z" />
      <line x1="12" y1="20" x2="12" y2="15" />
    </svg>
  );
}

function StageIcon({ children }) {
  return <div className="stage-icon">{children}</div>;
}

// A small animated illustration of the thing this product actually is: a
// graph of typed nodes with a human-approved edge structure. Pure inline
// SVG + CSS keyframes (no canvas/WebGL, no image assets, no library) --
// nodes pulse and edges "flow" on a loop, staggered so it never looks
// static without ever demanding attention from the reader.
const GRAPH_NODES = [
  { x: 70, y: 46, r: 7 },
  { x: 190, y: 24, r: 7 },
  { x: 320, y: 54, r: 7 },
  { x: 232, y: 128, r: 7 },
  { x: 98, y: 138, r: 7 },
  { x: 352, y: 140, r: 7 },
  { x: 208, y: 88, r: 11 }, // hub node
];
const GRAPH_EDGES = [
  [0, 6], [1, 6], [2, 6], [6, 3], [6, 4], [3, 5], [3, 2],
];

const TONES = ["tone-accent", "tone-pink", "tone-orange"];

function GraphIllustration() {
  return (
    <svg className="graph-illustration" viewBox="0 0 420 170" aria-hidden="true">
      {GRAPH_EDGES.map(([a, b], i) => (
        <line
          key={i}
          className={`graph-edge ${TONES[i % TONES.length]}`}
          x1={GRAPH_NODES[a].x}
          y1={GRAPH_NODES[a].y}
          x2={GRAPH_NODES[b].x}
          y2={GRAPH_NODES[b].y}
          style={{ animationDelay: `${i * 0.18}s` }}
        />
      ))}
      {GRAPH_NODES.map((n, i) => (
        <circle
          key={i}
          className={`graph-node ${TONES[i % TONES.length]}`}
          cx={n.x}
          cy={n.y}
          r={n.r}
          style={{ animationDelay: `${i * 0.22}s` }}
        />
      ))}
    </svg>
  );
}

const STAGES = [
  {
    icon: <DocumentIcon />,
    title: "Seed documents",
    body: "Product docs, ICP briefs, internal email threads -- unstructured source material.",
  },
  {
    icon: <ExtractIcon />,
    title: "LLM extraction",
    body: "An extraction pass turns prose into typed entities: Products, Features, Proof Points, Decisions, ICP Segments, People.",
  },
  {
    icon: <BranchIcon />,
    title: "Review branch",
    body: "Every ingestion run lands on its own branch. Nothing ever touches main directly.",
  },
  {
    icon: <ReviewIcon />,
    title: "Human review",
    body: "A reviewer sees the real diff -- inserts, updates, unchanged -- reads the source text, and approves or rejects.",
  },
  {
    icon: <MergeIcon />,
    title: "Merge to main",
    body: "Only on approval. The merge commit is attributed to the actual person who approved it.",
  },
];

const CONSUMERS = [
  {
    icon: <MonitorIcon />,
    title: "Dashboard (this app)",
    body: "Humans browse, search, and audit approved knowledge -- and review pending changes.",
  },
  {
    icon: <PlugIcon />,
    title: "MCP + query gateway",
    body: "Agents read the same approved knowledge through role-scoped tools, gated by an allowlist a leaked credential can't bypass.",
  },
];

export default function Home({ onNavigate }) {
  return (
    <div className="home">
      <section className="hero">
        <h1>GroundTruth Context Layer</h1>
        <p className="hero-tagline">
          One governed, single-source-of-truth knowledge graph for GroundTruth -- humans read it through
          this dashboard, agents read it through MCP, and nothing reaches either one without a human
          approving it first.
        </p>
        <div className="hero-actions">
          <button onClick={() => onNavigate("dashboard")}>Browse the graph</button>
          <button className="secondary" onClick={() => onNavigate("review")}>Open Review Queue</button>
          <button className="secondary" onClick={() => onNavigate("tutorial")}>New here? View the tutorial</button>
        </div>
        <GraphIllustration />
      </section>

      <section>
        <h2>What actually happens to a document</h2>
        <p className="muted">
          This is the full loop, in order. Every stage before "Merge to main" is reversible and
          attributable; nothing after it is guessable -- only approved facts are ever served.
        </p>
        <div className="flow">
          {STAGES.map((s, i) => (
            <React.Fragment key={s.title}>
              <div className="flow-stage">
                <StageIcon>{s.icon}</StageIcon>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </div>
              {i < STAGES.length - 1 && <div className="flow-arrow">→</div>}
            </React.Fragment>
          ))}
        </div>
      </section>

      <section>
        <h2>Once it's on main</h2>
        <p className="muted">Two independent read paths, same approved data, different audiences.</p>
        <div className="consumers">
          {CONSUMERS.map((c) => (
            <div key={c.title} className="consumer-card">
              <StageIcon>{c.icon}</StageIcon>
              <h3>{c.title}</h3>
              <p>{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2>Why this exists</h2>
        <p>
          Company knowledge today lives in scattered docs, email threads, and chat. Every agent
          (content, GTM, support) gets hand-pasted, often-stale context. This gives every team member
          and every agent one place to read <em>current, approved</em> knowledge from -- with Git-style
          governance: agents and pipelines propose changes on branches, a human approves the diff, and
          every commit is attributed and auditable.
        </p>
      </section>
    </div>
  );
}
