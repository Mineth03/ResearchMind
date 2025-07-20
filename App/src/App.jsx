import { useState } from 'react';

function App() {
  const [query, setQuery] = useState('');
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSummarize = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSummary('');
    try {
      const response = await fetch('http://localhost:8000/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();
      setSummary(data.summary);
    } catch (error) {
      setSummary('Error fetching summary. Please check your server.');
      console.error(error);
    }
    setLoading(false);
  };

  return (
    <div style={{ padding: '30px', maxWidth: '700px', margin: 'auto', fontFamily: 'Arial' }}>
      <h1>AI Research Paper Summarizer</h1>
      <textarea
        rows="3"
        style={{ width: '100%', padding: '10px', marginBottom: '10px' }}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Enter your research topic..."
      />
      <button
        onClick={handleSummarize}
        disabled={loading}
        style={{
          padding: '10px 20px',
          backgroundColor: '#007bff',
          color: '#fff',
          border: 'none',
          cursor: 'pointer',
        }}
      >
        {loading ? 'Summarizing...' : 'Summarize'}
      </button>

      {summary && (
        <div style={{ marginTop: '20px', backgroundColor: '#f9f9f9', padding: '15px', borderRadius: '5px' }}>
          <h3>Summary:</h3>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{summary}</pre>
        </div>
      )}
    </div>
  );
}

export default App;
