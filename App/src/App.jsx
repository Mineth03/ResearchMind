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
      setSummary('❗ Error fetching summary. Please check your server.');
      console.error(error);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-100 to-purple-200 font-sans p-4">
      <div className="bg-white bg-opacity-80 backdrop-blur-md rounded-lg shadow-lg p-8 max-w-2xl w-full">
        <h1 className="text-2xl font-bold text-center mb-6 text-gray-800">AI Research Paper Summarizer</h1>

        <textarea
          rows="4"
          className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 transition resize-none"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your research topic..."
        />

        <button
          onClick={handleSummarize}
          disabled={loading}
          className={`w-full py-2 mt-4 rounded-lg text-white font-semibold transition ${
            loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-500 hover:bg-blue-600'
          }`}
        >
          {loading ? '⏳ Summarizing...' : 'Summarize'}
        </button>

        {loading && (
          <div className="flex justify-center mt-4">
            <div className="w-8 h-8 border-4 border-blue-500 border-dashed rounded-full animate-spin"></div>
          </div>
        )}

        {summary && (
          <div className="mt-6 bg-white bg-opacity-70 p-4 rounded-lg shadow text-gray-800">
            <h3 className="font-semibold mb-2">Summary:</h3>
            <pre className="whitespace-pre-wrap">{summary}</pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
