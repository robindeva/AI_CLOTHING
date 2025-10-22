import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

// Update this with your API Gateway endpoint after deployment
const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT || 'YOUR_API_ENDPOINT_HERE';

function App() {
  const [selectedFiles, setSelectedFiles] = useState({
    front: null,
    back: null,
    side: null
  });
  const [previewUrls, setPreviewUrls] = useState({
    front: null,
    back: null,
    side: null
  });
  const [gender, setGender] = useState('unisex');
  const [height, setHeight] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [captureMode, setCaptureMode] = useState('single'); // 'single' or 'multi'

  const handleFileSelect = (event, angle) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFiles(prev => ({
        ...prev,
        [angle]: file
      }));
      setPreviewUrls(prev => ({
        ...prev,
        [angle]: URL.createObjectURL(file)
      }));
      setResult(null);
      setError(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Check if at least front image is selected
    if (!selectedFiles.front) {
      setError('Please select at least a front-view image');
      return;
    }

    if (!height || height < 100 || height > 250) {
      setError('Please enter your height (between 100cm and 250cm)');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();

    // Add images based on capture mode
    if (captureMode === 'single') {
      formData.append('image', selectedFiles.front);
    } else {
      // Multi-angle mode
      if (selectedFiles.front) formData.append('front_image', selectedFiles.front);
      if (selectedFiles.back) formData.append('back_image', selectedFiles.back);
      if (selectedFiles.side) formData.append('side_image', selectedFiles.side);
    }

    formData.append('gender', gender);
    formData.append('height', height);
    formData.append('multi_angle', captureMode === 'multi');

    try {
      const endpoint = captureMode === 'multi' ? 'analyze-multi-angle' : 'analyze';
      const response = await axios.post(`${API_ENDPOINT}${endpoint}`, formData, {
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
    setSelectedFiles({
      front: null,
      back: null,
      side: null
    });
    setPreviewUrls({
      front: null,
      back: null,
      side: null
    });
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
                  Your Height (required) *
                </label>
                <div className="height-input-group">
                  <input
                    type="number"
                    id="height-input"
                    placeholder="Enter height (e.g., 170)"
                    min="100"
                    max="250"
                    value={height}
                    onChange={(e) => setHeight(e.target.value)}
                    className="height-input"
                    required
                  />
                  <span className="height-unit">cm</span>
                </div>
                {height && height >= 100 && height <= 250 && (
                  <div className="height-info">
                    ✓ Height entered: {height} cm
                  </div>
                )}
              </div>

              {/* Capture Mode Selector */}
              <div className="capture-mode-select">
                <label className="mode-label">Capture Mode:</label>
                <div className="mode-options">
                  <label>
                    <input
                      type="radio"
                      value="single"
                      checked={captureMode === 'single'}
                      onChange={(e) => setCaptureMode(e.target.value)}
                    />
                    Single Photo (Standard)
                  </label>
                  <label>
                    <input
                      type="radio"
                      value="multi"
                      checked={captureMode === 'multi'}
                      onChange={(e) => setCaptureMode(e.target.value)}
                    />
                    Multi-Angle (Higher Accuracy)
                  </label>
                </div>
              </div>

              {/* File Upload Inputs */}
              {captureMode === 'single' ? (
                <div className="file-input-wrapper">
                  <input
                    type="file"
                    id="file-input-front"
                    accept="image/*"
                    onChange={(e) => handleFileSelect(e, 'front')}
                    className="file-input"
                  />
                  <label htmlFor="file-input-front" className="file-label">
                    {selectedFiles.front ? 'Change Photo' : 'Choose Photo'}
                  </label>
                </div>
              ) : (
                <div className="multi-angle-upload">
                  <div className="angle-upload-item">
                    <label className="angle-label">Front View (Required)</label>
                    <input
                      type="file"
                      id="file-input-front"
                      accept="image/*"
                      onChange={(e) => handleFileSelect(e, 'front')}
                      className="file-input"
                    />
                    <label htmlFor="file-input-front" className="file-label">
                      {selectedFiles.front ? '✓ Front Photo' : 'Upload Front'}
                    </label>
                  </div>

                  <div className="angle-upload-item">
                    <label className="angle-label">Back View (Optional)</label>
                    <input
                      type="file"
                      id="file-input-back"
                      accept="image/*"
                      onChange={(e) => handleFileSelect(e, 'back')}
                      className="file-input"
                    />
                    <label htmlFor="file-input-back" className="file-label">
                      {selectedFiles.back ? '✓ Back Photo' : 'Upload Back'}
                    </label>
                  </div>

                  <div className="angle-upload-item">
                    <label className="angle-label">Side View (Optional)</label>
                    <input
                      type="file"
                      id="file-input-side"
                      accept="image/*"
                      onChange={(e) => handleFileSelect(e, 'side')}
                      className="file-input"
                    />
                    <label htmlFor="file-input-side" className="file-label">
                      {selectedFiles.side ? '✓ Side Photo' : 'Upload Side'}
                    </label>
                  </div>
                </div>
              )}

              {/* Preview Section */}
              {(previewUrls.front || previewUrls.back || previewUrls.side) && (
                <div className="preview-section-multi">
                  {previewUrls.front && (
                    <div className="preview-item">
                      <span className="preview-label">Front</span>
                      <img src={previewUrls.front} alt="Front Preview" className="preview-image" />
                    </div>
                  )}
                  {previewUrls.back && (
                    <div className="preview-item">
                      <span className="preview-label">Back</span>
                      <img src={previewUrls.back} alt="Back Preview" className="preview-image" />
                    </div>
                  )}
                  {previewUrls.side && (
                    <div className="preview-item">
                      <span className="preview-label">Side</span>
                      <img src={previewUrls.side} alt="Side Preview" className="preview-image" />
                    </div>
                  )}
                </div>
              )}

              <div className="button-group">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading || !selectedFiles.front || !height || height < 100 || height > 250}
                >
                  {loading ? 'Analyzing...' : 'Get Size Recommendation'}
                </button>
                {(selectedFiles.front || result) && (
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
                  {/* Primary Measurements */}
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
                    <span className="measurement-label">Shoulder</span>
                    <span className="measurement-value">{result.measurements.shoulder}</span>
                  </div>
                  <div className="measurement-item">
                    <span className="measurement-label">Arm Length</span>
                    <span className="measurement-value">{result.measurements.arm}</span>
                  </div>
                  <div className="measurement-item">
                    <span className="measurement-label">Inseam</span>
                    <span className="measurement-value">{result.measurements.inseam}</span>
                  </div>

                  {/* New Measurements */}
                  {result.measurements.neck && (
                    <div className="measurement-item">
                      <span className="measurement-label">Neck</span>
                      <span className="measurement-value">{result.measurements.neck}</span>
                    </div>
                  )}
                  {result.measurements.bicep && (
                    <div className="measurement-item">
                      <span className="measurement-label">Bicep</span>
                      <span className="measurement-value">{result.measurements.bicep}</span>
                    </div>
                  )}
                  {result.measurements.wrist && (
                    <div className="measurement-item">
                      <span className="measurement-label">Wrist</span>
                      <span className="measurement-value">{result.measurements.wrist}</span>
                    </div>
                  )}
                  {result.measurements.thigh && (
                    <div className="measurement-item">
                      <span className="measurement-label">Thigh</span>
                      <span className="measurement-value">{result.measurements.thigh}</span>
                    </div>
                  )}
                  {result.measurements.calf && (
                    <div className="measurement-item">
                      <span className="measurement-label">Calf</span>
                      <span className="measurement-value">{result.measurements.calf}</span>
                    </div>
                  )}
                  {result.measurements.ankle && (
                    <div className="measurement-item">
                      <span className="measurement-label">Ankle</span>
                      <span className="measurement-value">{result.measurements.ankle}</span>
                    </div>
                  )}
                  {result.measurements.torso_length && (
                    <div className="measurement-item">
                      <span className="measurement-label">Torso Length</span>
                      <span className="measurement-value">{result.measurements.torso_length}</span>
                    </div>
                  )}
                  {result.measurements.back_width && (
                    <div className="measurement-item">
                      <span className="measurement-label">Back Width</span>
                      <span className="measurement-value">{result.measurements.back_width}</span>
                    </div>
                  )}
                  {result.measurements.rise && (
                    <div className="measurement-item">
                      <span className="measurement-label">Rise</span>
                      <span className="measurement-value">{result.measurements.rise}</span>
                    </div>
                  )}
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
