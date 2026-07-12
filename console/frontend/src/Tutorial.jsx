import React, { useState } from "react";

const ICON_PROPS = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

function SearchIcon() {
  return (
    <svg {...ICON_PROPS}>
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M12 16V4M12 4l-4 4M12 4l4 4" />
      <path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
    </svg>
  );
}

function GavelIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M13 6l5 5" />
      <path d="M4 21h9" />
      <path d="M9.5 3.5l5 5-6 6-5-5z" />
      <path d="M13.5 8.5L6 16" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg {...ICON_PROPS}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 3" />
    </svg>
  );
}

function KeyIcon() {
  return (
    <svg {...ICON_PROPS}>
      <circle cx="8" cy="15" r="4" />
      <path d="M11 12l9-9M17 6l3 3M14 9l2 2" />
    </svg>
  );
}

function RobotIcon() {
  return (
    <svg {...ICON_PROPS}>
      <rect x="4" y="8" width="16" height="12" rx="2" />
      <path d="M12 8V4" />
      <circle cx="12" cy="3" r="1" />
      <line x1="9" y1="14" x2="9" y2="15" />
      <line x1="15" y1="14" x2="15" y2="15" />
      <path d="M2 12h2M20 12h2" />
    </svg>
  );
}

function WaveIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M3 12h2l2-6 4 12 3-9 2 5h5" />
    </svg>
  );
}

const PAGES = [
  {
    icon: <WaveIcon />,
    kicker: "Welcome",
    title: "How to use the Context Layer",
    body: "This is the one place your team and your AI agents both read company knowledge from. Every page in this booklet covers one thing you can actually do here -- flip through with Next, or jump to any page below.",
  },
  {
    icon: <SearchIcon />,
    kicker: "Step 1",
    title: "Browse & search the Dashboard",
    body: "Open Dashboard, pick a category on the left (Products, Features, Proof Points, Decisions, ICP Segments, Personas, Email Threads, People), or type into the search bar for hybrid keyword + semantic search across all of them at once.",
  },
  {
    icon: <UploadIcon />,
    kicker: "Step 2",
    title: "Submit a document for review",
    body: "In Review Queue, click \"+ Submit a new document for review\" and paste in Markdown -- a product doc, an email thread, anything. This runs the real extraction pipeline and lands the result on its own review branch. It never touches main by itself.",
  },
  {
    icon: <GavelIcon />,
    kicker: "Step 3",
    title: "Review the diff, approve or reject",
    body: "Select a pending run to see exactly what would change -- new nodes, updated fields, reaffirmed facts -- next to the source text it came from. Approve merges it to main under your name; reject discards the branch. Only admin and reviewer accounts can do this.",
  },
  {
    icon: <ClockIcon />,
    kicker: "Step 4",
    title: "Audit what changed, and who changed it",
    body: "Recent Changes shows main's real commit history -- every merge attributed to the actual person who approved it, not a field anyone could type into. Nothing reaches main without a name attached.",
  },
  {
    icon: <RobotIcon />,
    kicker: "Step 5",
    title: "Agents read the same approved facts",
    body: "The Content Agent and GTM Agent connect over MCP and can only call an allowlisted set of read queries -- never anything unapproved, never each other's data. Ask one to write a blog post or a prospecting brief and it grounds every claim in what's actually on main.",
  },
  {
    icon: <KeyIcon />,
    kicker: "Roles",
    title: "Who can do what",
    body: "Viewer: read-only, self-service sign-up. Reviewer: everything a viewer can do, plus approve/reject in the Review Queue, provisioned by an admin. Admin: same as reviewer, plus account management. Every login is a real, verified session -- nothing is ever trusted from the browser alone.",
  },
];

export default function Tutorial() {
  const [index, setIndex] = useState(0);
  const [dir, setDir] = useState("next");

  const go = (next) => {
    if (next === index) return;
    setDir(next > index ? "next" : "prev");
    setIndex(next);
  };

  const page = PAGES[index];
  const isFirst = index === 0;
  const isLast = index === PAGES.length - 1;

  return (
    <div className="tutorial">
      <div className="booklet">
        <div className="booklet-spine" aria-hidden="true" />
        <div key={index} className={`booklet-page anim-${dir}`}>
          <div className="booklet-page-icon">{page.icon}</div>
          <div className="booklet-kicker">{page.kicker}</div>
          <h2>{page.title}</h2>
          <p>{page.body}</p>
        </div>
      </div>

      <div className="booklet-controls">
        <button type="button" className="secondary" disabled={isFirst} onClick={() => go(index - 1)}>
          ← Previous
        </button>
        <div className="booklet-dots">
          {PAGES.map((p, i) => (
            <button
              key={p.title}
              type="button"
              className={`booklet-dot ${i === index ? "active" : ""}`}
              aria-label={`Go to page ${i + 1}: ${p.title}`}
              onClick={() => go(i)}
            />
          ))}
        </div>
        <button type="button" disabled={isLast} onClick={() => go(index + 1)}>
          Next →
        </button>
      </div>
    </div>
  );
}
