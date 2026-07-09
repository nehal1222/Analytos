import React, { useEffect, useState } from "react";
import { api } from "./api.js";

const SECTIONS = [
  { key: "products", label: "Products" },
  { key: "features", label: "Features" },
  { key: "proofPoints", label: "Proof Points" },
  { key: "decisions", label: "Decisions" },
  { key: "icpSegments", label: "ICP Segments" },
  { key: "personas", label: "Personas" },
  { key: "emailThreads", label: "Email Threads (internal)" },
];

function SearchResults({ results }) {
  if (!results) return null;
  const groups = [
    ["products", "Products"],
    ["features", "Features"],
    ["proof_points", "Proof Points"],
    ["decisions", "Decisions"],
    ["icp_segments", "ICP Segments"],
  ];
  const total = groups.reduce((n, [k]) => n + (results[k]?.length || 0), 0);
  if (total === 0) {
    return (
      <p className="muted">
        No matches for that search. This box does hybrid (vector + BM25) search
        over entity *content* -- try a specific fact or metric (e.g. "stockout",
        "defect rate", "audit prep") rather than a category name. To browse
        every Proof Point (or any other type), clear the search and use the
        tabs above instead.
      </p>
    );
  }
  return (
    <div className="search-results">
      {groups.map(([key, label]) =>
        results[key]?.length ? (
          <div key={key} className="search-group">
            <h4>{label}</h4>
            <ul>
              {results[key].map((r) => (
                <li key={r.slug}>
                  <strong>{r.name || r.title || r.label}</strong>
                  {r.summary || r.description || r.competitor_angle ? (
                    <span className="muted"> — {r.summary || r.description || r.competitor_angle}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null
      )}
    </div>
  );
}

function ProductDetail({ slug, onClose }) {
  const [detail, setDetail] = useState(null);
  useEffect(() => {
    api.product(slug).then(setDetail).catch((e) => setDetail({ error: e.message }));
  }, [slug]);
  if (!detail) return <p className="muted">Loading…</p>;
  if (detail.error) return <p className="error">{detail.error}</p>;
  const { product, features, proof_points, decisions, segments } = detail;
  return (
    <div className="detail-panel">
      <button className="link-button" onClick={onClose}>← back</button>
      <h2>{product.name}</h2>
      <p className="muted">{product.category}</p>
      <p>{product.summary}</p>
      <p className="provenance">source: {product.source_doc}</p>

      <h3>Proof Points</h3>
      <ul>
        {proof_points.map((p) => (
          <li key={p.slug}>
            <strong>{p.value}</strong> — {p.description}
          </li>
        ))}
      </ul>

      <h3>Features</h3>
      {features.map((f) => (
        <div key={f.slug} className="feature-card">
          <strong>{f.name}</strong>
          <p>{f.description}</p>
          {f.proof_points.length > 0 && (
            <ul>
              {f.proof_points.map((p) => (
                <li key={p.slug}>
                  <strong>{p.value}</strong> — {p.description}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}

      <h3>ICP Segments Targeted</h3>
      <ul>
        {segments.map((s) => (
          <li key={s.slug}>{s.name}</li>
        ))}
      </ul>

      <h3>Decisions</h3>
      <ul>
        {decisions.map((d) => (
          <li key={d.slug}>
            <strong>{d.decided_at}</strong> — {d.title}
            <div className="muted">{d.description}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function EntityList({ section }) {
  const [items, setItems] = useState(null);
  useEffect(() => {
    setItems(null);
    const loaders = {
      products: api.products,
      features: api.features,
      proofPoints: api.proofPoints,
      decisions: api.decisions,
      icpSegments: api.icpSegments,
      personas: api.personas,
      emailThreads: api.emailThreads,
    };
    loaders[section]().then(setItems).catch((e) => setItems({ error: e.message }));
  }, [section]);

  const [openProduct, setOpenProduct] = useState(null);

  if (openProduct) {
    return <ProductDetail slug={openProduct} onClose={() => setOpenProduct(null)} />;
  }
  if (!items) return <p className="muted">Loading…</p>;
  if (items.error) return <p className="error">{items.error}</p>;
  if (items.length === 0) return <p className="muted">Nothing here yet.</p>;

  return (
    <ul className="entity-list">
      {items.map((item) => (
        <li key={item.slug}>
          {section === "products" ? (
            <button className="link-button" onClick={() => setOpenProduct(item.slug)}>
              <strong>{item.name}</strong>
            </button>
          ) : (
            <strong>{item.name || item.title || item.label || item.subject}</strong>
          )}
          <div className="muted">
            {item.description || item.summary || item.value || item.competitor_angle || item.category}
          </div>
          {item.source_doc && <div className="provenance">source: {item.source_doc}</div>}
        </li>
      ))}
    </ul>
  );
}

export default function Dashboard() {
  const [section, setSection] = useState("products");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);

  const runSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) {
      setResults(null);
      return;
    }
    setSearching(true);
    try {
      setResults(await api.search(query));
    } catch (err) {
      setResults({ error: err.message });
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="dashboard">
      <form className="search-bar" onSubmit={runSearch}>
        <input
          type="text"
          placeholder="Search products, features, proof points, decisions, ICP segments…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" disabled={searching}>
          {searching ? "Searching…" : "Search"}
        </button>
        {results && (
          <button type="button" className="link-button" onClick={() => { setResults(null); setQuery(""); }}>
            clear
          </button>
        )}
      </form>

      {results ? (
        <SearchResults results={results} />
      ) : (
        <div className="dashboard-body">
          <nav className="section-nav">
            {SECTIONS.map((s) => (
              <button
                key={s.key}
                className={s.key === section ? "active" : ""}
                onClick={() => setSection(s.key)}
              >
                {s.label}
              </button>
            ))}
          </nav>
          <div className="section-content">
            <EntityList section={section} />
          </div>
        </div>
      )}
    </div>
  );
}
