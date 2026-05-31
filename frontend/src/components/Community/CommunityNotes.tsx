import { useState } from "react";
import type { CommunityNote } from "../../hooks/useCommunity";

const MAX_CHARS = 280;

const QUICK_NOTES = [
  "Transformer issue reported nearby",
  "REG crew spotted in the area",
  "Power back on my street",
  "Generator noise from neighbors",
];

interface Props {
  notes: CommunityNote[];
  loading: boolean;
  onAdd: (body: string) => Promise<void>;
  onUpvote: (id: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

function timeLeft(iso: string): string {
  const diff = Math.floor((new Date(iso).getTime() - Date.now()) / 1000 / 60);
  if (diff <= 0) return "expired";
  if (diff < 60) return `${diff}m left`;
  return `${Math.floor(diff / 60)}h left`;
}

export default function CommunityNotes({ notes, loading, onAdd, onUpvote, onDelete }: Props) {
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit() {
    if (!body.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await onAdd(body.trim());
      setBody("");
    } catch {
      setError("Failed to post note. Try again.");
    }
    setSubmitting(false);
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Add note form */}
      <div className="bg-slate-800 rounded-2xl p-4 flex flex-col gap-3">
        <p className="text-xs text-slate-400 uppercase tracking-widest">Community Notes</p>

        {/* Quick note chips */}
        <div className="flex flex-wrap gap-2">
          {QUICK_NOTES.map(q => (
            <button
              key={q}
              onClick={() => setBody(q)}
              className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-3 py-1.5 rounded-full transition-colors"
            >
              {q}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-2">
          <textarea
            placeholder="What's happening in your area? (max 280 chars)"
            value={body}
            onChange={e => setBody(e.target.value.slice(0, MAX_CHARS))}
            rows={2}
            className="bg-slate-700 text-white text-sm rounded-xl px-3 py-2.5 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex justify-between items-center">
            <span className={`text-xs ${body.length > 250 ? "text-red-400" : "text-slate-500"}`}>
              {body.length}/{MAX_CHARS}
            </span>
            <button
              onClick={handleSubmit}
              disabled={!body.trim() || submitting}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white text-sm font-semibold px-4 py-2 rounded-xl"
            >
              {submitting ? "Posting..." : "Post Note"}
            </button>
          </div>
          {error && <p className="text-red-400 text-xs">{error}</p>}
        </div>
      </div>

      {/* Notes list */}
      {loading ? (
        <div className="bg-slate-800 rounded-2xl p-6 text-slate-500 text-sm text-center">Loading notes...</div>
      ) : notes.length === 0 ? (
        <div className="bg-slate-800 rounded-2xl p-6 text-slate-500 text-sm text-center">
          No notes yet — be the first to report what's happening!
        </div>
      ) : (
        notes.map(note => (
          <div key={note.id} className="bg-slate-800 rounded-xl p-4 flex flex-col gap-2">
            <p className="text-sm text-white leading-relaxed">{note.body}</p>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => onUpvote(note.id)}
                  className="flex items-center gap-1 text-xs text-slate-400 hover:text-blue-400 transition-colors"
                  aria-label="Upvote note"
                >
                  👍 {note.upvotes}
                </button>
                <span className="text-xs text-slate-600">{timeAgo(note.created_at)}</span>
                <span className="text-xs text-slate-600">· {timeLeft(note.expires_at)}</span>
              </div>
              {note.is_mine && (
                <button
                  onClick={() => onDelete(note.id)}
                  className="text-xs text-red-400 hover:text-red-300"
                  aria-label="Delete note"
                >
                  Delete
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
