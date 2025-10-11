import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

// Update this with your API Gateway endpoint after deployment
const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT || 'YOUR_API_ENDPOINT_HERE';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [gender, setGender] = useState('unisex');
  const [height, setHeight] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
      setError(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selectedFile) {
      setError('Please select an image first');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('image', selectedFile);
    formData.append('gender', gender);
    if (height && height > 0) {
      formData.append('height', height);
    }

    try {
      const response = await axios.post(`${API_ENDPOINT}analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze image. Please try again.');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <h1>AI Clothing Size Recommender</h1>
          <p>Upload your full-body photo to get personalized size recommendations</p>
        </header>

        <div className="main-content">
          <div className="upload-section">
            <form onSubmit={handleSubmit}>
              <div className="gender-select">
                <label>
                  <input
                    type="radio"
                    value="male"
                    checked={gender === 'male'}
                    onChange={(e) => setGender(e.target.value)}
                  />
                  Male
                </label>
                <label>
                  <input
                    type="radio"
                    value="female"
                    checked={gender === 'female'}
                    onChange={(e) => setGender(e.target.value)}
                  />
                  Female
                </label>
                <label>
                  <input
                    type="radio"
                    value="unisex"
                    checked={gender === 'unisex'}
                    onChange={(e) => setGender(e.target.value)}
                  />
                  Unisex
                </label>
              </div>

              <div className="height-input-wrapper">
                <label htmlFor="height-input" className="height-label">
                  Your Height (optional - improves accuracy)
                </label>
                <div className="height-input-group">
                  <input
                    type="number"
                    id="height-input"
                    placeholder="Enter height"
                    min="100"
                    max="250"
                    value={height}
                    onChange={(e) => setHeight(e.target.value)}
                    className="height-input"
                  />
                  <span className="height-unit">cm</span>
                </div>
                {height && height > 0 && (
                  <div className="height-info">
                    ✓ Height-adjusted measurements for better accuracy
                  </div>
                )}
              </div>

              <div className="file-input-wrapper">
                <input
                  type="file"
                  id="file-input"
                  accept="image/*"
                  onChange={handleFileSelect}
                  className="file-input"
                />
                <label htmlFor="file-input" className="file-label">
                  {selectedFile ? 'Change Photo' : 'Choose Photo'}
                </label>
              </div>

              {previewUrl && (
                <div className="preview-section">
                  <img src={previewUrl} alt="Preview" className="preview-image" />
                </div>
              )}

              <div className="button-group">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading || !selectedFile}
                >
                  {loading ? 'Analyzing...' : 'Get Size Recommendation'}
                </button>
                {(selectedFile || result) && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleReset}
                  >
                    Reset
                  </button>
                )}
              </div>
            </form>

            {error && (
              <div className="error-message">
                <p>{error}</p>
              </div>
            )}
          </div>

          {result && (
            <div className="result-section">
              <div className="result-card">
                <h2>Your Recommended Size</h2>

                {result.quality_score && (
                  <div className={`quality-badge ${result.quality_score >= 80 ? 'quality-good' : result.quality_score >= 60 ? 'quality-fair' : 'quality-poor'}`}>
                    Photo Quality: {result.quality_score}/100
                  </div>
                )}

                {result.quality_warnings && result.quality_warnings.length > 0 && (
                  <div className="quality-warnings">
                    {result.quality_warnings.map((warning, idx) => (
                      <div key={idx} className="warning-item">⚠️ {warning}</div>
                    ))}
                  </div>
                )}

                {result.ai_enhanced && (
                  <div className="ai-badge">
                    ✨ AI-Enhanced Analysis
                    {result.body_type && <span className="body-type"> • {result.body_type}</span>}
                  </div>
                )}
                <h3 className="size-label">Recommended Shirt Size</h3>
                <div className="size-badge">
                  <span className="size">{result.recommended_size}</span>
                </div>
                <div className="confidence-bar">
                  <div className="confidence-label">
                    Confidence: {result.confidence}%
                    {result.ai_enhanced && <span className="ai-boost"> (AI Verified)</span>}
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${result.confidence}%` }}
                    />
                  </div>
                </div>
                <p className="explanation">{result.explanation}</p>
              </div>

              <div className="measurements-card">
                <h3>Your Measurements (cm)</h3>
                <div className="measurements-grid">
                  <div className="measurement-item">
                    <span className="measurement-label">Chest</span>
                    <span className="measurement-value">{result.measurements.chest}</span>
                  </div>
                  <div className="measurement-item">
                    <span className="measurement-label">Waist</span>
                    <span className="measurement-value">{result.measurements.waist}</span>
                  </div>
                  <div className="measurement-item">
                    <span className="measurement-label">Hips</span>
                    <span className="measurement-value">{result.measurements.hips}</span>
                  </div>
                  <div className="measurement-item">
                    <span className="measurement-label">Inseam</span>
                    <span className="measurement-value">{result.measurements.inseam}</span>
                  </div>
                  <div className="measurement-item">
                    <span className="measurement-label">Shoulder</span>
                    <span className="measurement-value">{result.measurements.shoulder}</span>
                  </div>
                  <div className="measurement-item">
                    <span className="measurement-label">Arm</span>
                    <span className="measurement-value">{result.measurements.arm}</span>
                  </div>
                </div>
              </div>

              <div className="size-scores-card">
                <h3>All Size Scores</h3>
                <div className="scores-list">
                  {Object.entries(result.all_size_scores)
                    .sort((a, b) => b[1] - a[1])
                    .map(([size, score]) => (
                      <div key={size} className="score-item">
                        <span className="score-size">{size}</span>
                        <div className="score-bar-container">
                          <div
                            className="score-bar"
                            style={{
                              width: `${score}%`,
                              backgroundColor:
                                size === result.recommended_size
                                  ? '#10b981'
                                  : '#e5e7eb',
                            }}
                          />
                        </div>
                        <span className="score-value">{score.toFixed(1)}</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <footer className="footer">
          <p>For best results, upload a full-body photo taken from the front in good lighting</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
