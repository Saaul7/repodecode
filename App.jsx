const { useState, useEffect } = React;

const LoadingState = ({ onComplete }) => {
  const steps = [
    "Fetching repository structure...",
    "Analyzing tech stack...",
    "Scanning dependencies...",
    "Checking for vulnerabilities...",
    "Generating setup guide..."
  ];
  
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  useEffect(() => {
    if (currentStepIndex < steps.length) {
      const timer = setTimeout(() => {
        setCurrentStepIndex(prev => prev + 1);
      }, 400);
      return () => clearTimeout(timer);
    } else {
      setTimeout(onComplete, 500); // Wait a bit before completing
    }
  }, [currentStepIndex, onComplete, steps.length]);

  return (
    <div className="w-full max-w-2xl mx-auto mt-12 animate-fade-in-up">
      <div className="bg-terminal-bg border border-navy-700 rounded-lg p-6 font-mono text-sm shadow-2xl">
        <div className="flex gap-2 mb-4">
          <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50"></div>
          <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50"></div>
          <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50"></div>
        </div>
        <div className="space-y-2 text-gray-300">
          {steps.map((step, index) => {
            const isCompleted = index < currentStepIndex;
            const isCurrent = index === currentStepIndex;
            const isFuture = index > currentStepIndex;

            if (isFuture) return null;

            return (
              <div key={index} className="flex items-center justify-between">
                <span>
                  <span className="text-cyan-400 mr-2">&gt;</span>
                  {step}
                  {isCurrent && <span className="cursor-blink"></span>}
                </span>
                {isCompleted && <span className="text-emerald-400">✓</span>}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

const CopyButton = ({ text }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className={`p-2 rounded transition-all duration-200 ${
        copied ? 'bg-emerald-400/20 text-emerald-400' : 'hover:bg-navy-700 text-gray-400 hover:text-cyan-400'
      }`}
      title="Copy to clipboard"
    >
      {copied ? 'Copied!' : '📋'}
    </button>
  );
};

const ResultsDashboard = ({ data }) => {
  const [openError, setOpenError] = useState(null);

  // Staggered fade-in delays
  const getDelay = (index) => ({ animationDelay: `${index * 150}ms` });

  return (
    <div className="w-full max-w-5xl mx-auto mt-12 space-y-6 pb-24">
      {/* CARD 1 - REPO OVERVIEW */}
      <div className="bg-navy-800/80 backdrop-blur border border-navy-700 rounded-xl p-6 opacity-0 animate-fade-in-up" style={getDelay(0)}>
        <div className="flex items-center gap-2 text-xl font-bold text-white mb-4">
          <span>📦</span> What Is This?
        </div>
        <div className="flex items-baseline gap-4 mb-2">
          <h2 className="text-2xl font-mono text-cyan-400">{data.repo_overview.name}</h2>
          <span className="text-yellow-400 text-sm">★ {data.repo_overview.stars.toLocaleString()}</span>
          <span className="bg-navy-700 text-gray-300 text-xs px-2 py-1 rounded border border-navy-600">{data.repo_overview.language}</span>
        </div>
        <p className="text-gray-300 mb-4">{data.repo_overview.description}</p>
        <div className="flex flex-wrap gap-2">
          <span className="text-sm text-gray-400 mr-2">Tags:</span>
          {data.repo_overview.topics.map(topic => (
            <span key={topic} className="text-xs bg-cyan-400/10 text-cyan-400 px-2 py-1 rounded border border-cyan-400/20">
              {topic}
            </span>
          ))}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* CARD 2 - PREREQUISITES */}
        <div className="bg-navy-800/80 backdrop-blur border border-navy-700 rounded-xl p-6 opacity-0 animate-fade-in-up" style={getDelay(1)}>
          <div className="flex items-center gap-2 text-xl font-bold text-white mb-6">
            <span>⚡</span> Prerequisites
          </div>
          <div className="space-y-4">
            {data.prerequisites.map(req => (
              <div key={req.name} className="flex items-start justify-between p-3 rounded-lg bg-navy-900/50 border border-navy-700/50">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={req.status === 'required' ? 'text-emerald-400' : 'text-yellow-400'}>
                      {req.status === 'required' ? '✅' : '⚠️'}
                    </span>
                    <span className="font-bold text-gray-200">{req.name} {req.version}</span>
                  </div>
                  <div className="text-sm text-gray-400 mt-1 ml-6">Why: {req.why}</div>
                </div>
                <a href={req.download_url} target="_blank" rel="noreferrer" className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors">
                  Download →
                </a>
              </div>
            ))}
          </div>
        </div>

        {/* CARD 3 - DEPENDENCY HEALTH */}
        <div className="bg-navy-800/80 backdrop-blur border border-navy-700 rounded-xl p-6 opacity-0 animate-fade-in-up" style={getDelay(2)}>
          <div className="flex items-center gap-2 text-xl font-bold text-white mb-6">
            <span>🛡️</span> Dependency Health
          </div>
          <div className="flex items-center gap-8 mb-6">
            <div className="relative w-24 h-24 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" fill="transparent" stroke="#1a1a2e" strokeWidth="8" />
                <circle cx="50" cy="50" r="40" fill="transparent" stroke={data.dependency_health.score > 80 ? '#00ff88' : '#f59e0b'} strokeWidth="8" strokeDasharray={`${data.dependency_health.score * 2.51} 251`} strokeLinecap="round" />
              </svg>
              <div className="absolute flex flex-col items-center">
                <span className="text-2xl font-bold text-white">{data.dependency_health.score}</span>
                <span className="text-xs text-gray-400">/100</span>
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2"><span className="text-emerald-400">✅</span> {data.dependency_health.healthy} healthy</div>
              <div className="flex items-center gap-2"><span className="text-yellow-400">⚠️</span> {data.dependency_health.warnings} updates available</div>
              <div className="flex items-center gap-2"><span className="text-red-400">🔴</span> {data.dependency_health.critical} vulnerability found</div>
            </div>
          </div>
          <div className="text-center">
            <button className="text-sm text-gray-400 hover:text-cyan-400 transition-colors">See Details ↓</button>
          </div>
        </div>
      </div>

      {/* CARD 4 - SETUP GUIDE */}
      <div className="bg-navy-800/80 backdrop-blur border border-cyan-400/30 rounded-xl p-6 opacity-0 animate-fade-in-up relative overflow-hidden" style={getDelay(3)}>
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-400 to-emerald-400"></div>
        <div className="flex items-center gap-2 text-2xl font-bold text-white mb-8">
          <span>🚀</span> Setup Guide
        </div>
        <div className="space-y-8">
          {data.setup_steps.map((step, index) => (
            <div key={index} className="relative">
              {index !== data.setup_steps.length - 1 && (
                <div className="absolute left-4 top-10 w-0.5 h-full bg-navy-700"></div>
              )}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-navy-900 border border-cyan-400/50 flex items-center justify-center text-cyan-400 font-mono text-sm z-10">
                  {step.step_number}
                </div>
                <div className="flex-grow pt-1">
                  <h3 className="text-lg font-bold text-gray-200 mb-3">{step.title}</h3>
                  <div className="bg-terminal-bg rounded-lg border border-navy-700 flex justify-between items-start mb-3 group">
                    <pre className="p-4 text-cyan-300 font-mono text-sm overflow-x-auto whitespace-pre-wrap">
                      <code>{step.command}</code>
                    </pre>
                    <div className="p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <CopyButton text={step.command} />
                    </div>
                  </div>
                  <div className="text-sm space-y-1">
                    <p><span className="text-gray-400">What this does:</span> <span className="text-gray-300">{step.what_it_does}</span></p>
                    <p><span className="text-gray-400">What you're learning:</span> <span className="text-emerald-400/80">{step.what_you_learn}</span></p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CARD 5 - TECH STACK */}
      <div className="bg-navy-800/80 backdrop-blur border border-navy-700 rounded-xl p-6 opacity-0 animate-fade-in-up" style={getDelay(4)}>
        <div className="flex items-center gap-2 text-xl font-bold text-white mb-6">
          <span>🧩</span> Tech Stack Explainer
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.tech_stack.map(tech => (
            <div key={tech.name} className="bg-navy-900 rounded-lg p-5 border border-navy-700 hover:border-cyan-400/30 transition-colors">
              <h4 className="font-bold text-white text-lg mb-1">{tech.name}</h4>
              <div className="text-xs text-cyan-400 mb-3 uppercase tracking-wider font-mono">{tech.role}</div>
              <p className="text-sm text-gray-400">{tech.explanation}</p>
            </div>
          ))}
        </div>
      </div>

      {/* CARD 6 - COMMON ERRORS */}
      <div className="bg-navy-800/80 backdrop-blur border border-navy-700 rounded-xl p-6 opacity-0 animate-fade-in-up" style={getDelay(5)}>
        <div className="flex items-center gap-2 text-xl font-bold text-white mb-6">
          <span>🐛</span> Common Errors
        </div>
        <div className="space-y-3">
          {data.common_errors.map((error, index) => (
            <div key={index} className="border border-navy-700 rounded-lg overflow-hidden bg-navy-900/50">
              <button 
                className="w-full flex items-center justify-between p-4 text-left hover:bg-navy-800 transition-colors"
                onClick={() => setOpenError(openError === index ? null : index)}
              >
                <span className="font-mono text-red-400 text-sm">"{error.error}"</span>
                <span className="text-gray-500">{openError === index ? '▲' : '▼'}</span>
              </button>
              {openError === index && (
                <div className="p-4 pt-0 border-t border-navy-700/50 bg-navy-900">
                  <p className="text-sm text-gray-400 mb-3 mt-3"><strong className="text-gray-300">Why this happens:</strong> {error.why}</p>
                  <div className="bg-terminal-bg rounded flex justify-between items-center border border-navy-700">
                    <code className="p-3 text-emerald-400 font-mono text-sm">{error.fix}</code>
                    <div className="pr-2">
                       <CopyButton text={error.fix} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const App = () => {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeRepo = async (githubUrl) => {
    setResult(null);
    setError(null);
    setLoading(true);
    
    try {
      const response = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ github_url: githubUrl })
      });
      
      if (!response.ok) {
        throw new Error("API call failed");
      }
      
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError("Failed to analyze repo. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const handleLoadingComplete = () => {
    // Loading is already managed by the analyzeRepo function
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      analyzeRepo(url);
    }
  };

  return (
    <div className="min-h-screen p-4 md:p-8 flex flex-col font-sans">
      {/* Header/Nav */}
      <header className="w-full max-w-5xl mx-auto flex items-center justify-between mb-16 md:mb-24">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(0,212,255,0.8)] animate-pulse"></div>
          <h1 className="text-xl font-mono font-bold tracking-tight text-white">RepoReady</h1>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-grow flex flex-col items-center">
        {(!loading && !result) && (
          <div className={`w-full max-w-3xl flex flex-col items-center text-center transition-opacity duration-500`}>
            <h2 className="text-4xl md:text-6xl font-bold text-white mb-4 tracking-tight">
              From zero to <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400">running</span> in seconds
            </h2>
            <p className="text-gray-400 mb-10 text-lg">Instantly analyze any GitHub repository and generate a tailored, bulletproof setup guide.</p>
            
            {/* Input Box */}
            <div className="w-full bg-navy-800/50 backdrop-blur-md border border-navy-600 rounded-xl p-2 flex flex-col md:flex-row gap-2 glow-focus transition-all duration-300">
              <div className="flex-grow flex items-center px-4 py-3 md:py-0 bg-navy-900 rounded-lg">
                <span className="text-cyan-400 mr-3">●</span>
                <input 
                  type="text" 
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Paste any GitHub repo URL..."
                  className="w-full bg-transparent border-none outline-none text-white font-mono placeholder-gray-600 cursor-blink-target"
                />
              </div>
              <button 
                onClick={() => analyzeRepo(url)}
                disabled={!url.trim() || loading}
                className="bg-cyan-400 hover:bg-cyan-300 disabled:opacity-50 disabled:cursor-not-allowed text-navy-900 font-bold px-8 py-3 rounded-lg transition-colors flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(0,212,255,0.3)] hover:shadow-[0_0_25px_rgba(0,212,255,0.5)]"
              >
                Analyze <span className="font-mono">→</span>
              </button>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mt-4 text-red-400 text-sm bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-2">
                {error}
              </div>
            )}

            {/* Example Pills */}
            <div className="mt-8 flex flex-col sm:flex-row items-center gap-3 text-sm">
              <span className="text-gray-500">Try an example:</span>
              <div className="flex gap-2">
                {["vercel/next.js", "fastapi/fastapi", "expressjs/express"].map(repo => (
                  <button 
                    key={repo}
                    onClick={() => setUrl(`https://github.com/${repo}`)}
                    className="px-3 py-1.5 rounded-full border border-navy-600 bg-navy-800/50 text-gray-300 hover:text-cyan-400 hover:border-cyan-400/50 transition-colors font-mono text-xs"
                  >
                    {repo}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Scroll Indicator */}
            <div className="mt-24 animate-bounce text-gray-600">
              ↓
            </div>
          </div>
        )}

        {loading && (
          <LoadingState onComplete={handleLoadingComplete} />
        )}

        {!loading && result && (
          <ResultsDashboard data={result} />
        )}
      </main>
    </div>
  );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
