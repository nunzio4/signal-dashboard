import { useState } from "react";
import { useCreateSource } from "../../hooks/useDashboard";

interface AddFeedFormProps {
  onClose: () => void;
}

export function AddFeedForm({ onClose }: AddFeedFormProps) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [sourceType, setSourceType] = useState<"rss" | "newsapi">("rss");
  const createSource = useCreateSource();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !url.trim()) return;

    createSource.mutate(
      {
        name: name.trim(),
        source_type: sourceType,
        url: url.trim(),
        enabled: true,
      },
      {
        onSuccess: () => {
          setName("");
          setUrl("");
          onClose();
        },
      }
    );
  };

  return (
    <form className="add-feed-form" onSubmit={handleSubmit}>
      <div className="form-header">
        <h3>Add New Feed</h3>
        <button type="button" className="btn-close" onClick={onClose}>
          &times;
        </button>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="feed-name">Feed Name</label>
          <input
            id="feed-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. TechCrunch AI"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="feed-type">Feed Type</label>
          <select
            id="feed-type"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value as "rss" | "newsapi")}
          >
            <option value="rss">RSS Feed</option>
            <option value="newsapi">NewsAPI</option>
          </select>
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="feed-url">Feed URL</label>
        <input
          id="feed-url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/feed.xml"
          required
        />
        <span className="form-hint">
          {sourceType === "rss"
            ? "Enter the URL of an RSS or Atom feed"
            : "Enter a NewsAPI endpoint URL"}
        </span>
      </div>

      <div className="rss-tips">
        <h4>Quick Add Tips</h4>
        <ul>
          <li>
            <strong>Google News:</strong>{" "}
            <code>
              https://news.google.com/rss/search?q=YOUR+KEYWORDS&hl=en-US&gl=US&ceid=US:en
            </code>
          </li>
          <li>
            <strong>Reddit:</strong>{" "}
            <code>https://www.reddit.com/r/SUBREDDIT/.rss</code>
          </li>
          <li>
            <strong>Any site:</strong> Try appending <code>/feed</code>,{" "}
            <code>/rss</code>, or <code>/atom.xml</code> to the site URL
          </li>
        </ul>
      </div>

      {createSource.isError && (
        <div className="form-error">
          Failed to add feed: {(createSource.error as Error).message}
        </div>
      )}

      <div className="form-actions">
        <button type="button" className="btn btn-secondary" onClick={onClose}>
          Cancel
        </button>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={createSource.isPending || !name.trim() || !url.trim()}
        >
          {createSource.isPending ? "Adding..." : "Add Feed"}
        </button>
      </div>
    </form>
  );
}
