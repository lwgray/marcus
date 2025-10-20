import { useEffect } from 'react';
import { useVisualizationStore } from '../store/visualizationStore';
import './TimelineControls.css';

const TimelineControls = () => {
  const data = useVisualizationStore((state) => state.data);
  const currentTime = useVisualizationStore((state) => state.currentTime);
  const isPlaying = useVisualizationStore((state) => state.isPlaying);
  const playbackSpeed = useVisualizationStore((state) => state.playbackSpeed);
  const setCurrentTime = useVisualizationStore((state) => state.setCurrentTime);
  const play = useVisualizationStore((state) => state.play);
  const pause = useVisualizationStore((state) => state.pause);
  const setPlaybackSpeed = useVisualizationStore((state) => state.setPlaybackSpeed);
  const reset = useVisualizationStore((state) => state.reset);

  const startTime = new Date(data.metadata.start_time).getTime();
  const endTime = new Date(data.metadata.end_time).getTime();
  const totalDuration = endTime - startTime;

  const currentPercent = (currentTime / totalDuration) * 100;
  const currentMinutes = Math.round(currentTime / 60000);
  const totalMinutes = Math.round(totalDuration / 60000);

  const handleScrub = (e: React.ChangeEvent<HTMLInputElement>) => {
    const percent = parseFloat(e.target.value);
    const newTime = (percent / 100) * totalDuration;
    if (isPlaying) {
      pause(); // Pause playback when scrubbing
    }
    setCurrentTime(newTime);
  };

  const handlePlayPause = () => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        e.preventDefault();
        handlePlayPause();
      } else if (e.code === 'KeyR') {
        e.preventDefault();
        reset();
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        setCurrentTime(Math.max(0, currentTime - 5000)); // -5s
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        setCurrentTime(Math.min(totalDuration, currentTime + 5000)); // +5s
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [currentTime, isPlaying, totalDuration, setCurrentTime, reset, handlePlayPause]);

  return (
    <div className="timeline-controls">
      <div className="timeline-info">
        <span className="current-time">{currentMinutes}m</span>
        <span className="separator">/</span>
        <span className="total-time">{totalMinutes}m</span>
      </div>

      <div className="timeline-bar">
        <input
          type="range"
          min="0"
          max="100"
          step="0.1"
          value={currentPercent}
          onChange={handleScrub}
          className="timeline-scrubber"
        />
      </div>

      <div className="playback-controls">
        <button
          className="control-btn reset-btn"
          onClick={reset}
          title="Reset (R)"
        >
          ⏮
        </button>

        <button
          className="control-btn skip-btn"
          onClick={() => setCurrentTime(Math.max(0, currentTime - 10000))}
          title="Skip Back 10s (←)"
        >
          ⏪
        </button>

        <button
          className="control-btn play-pause-btn"
          onClick={handlePlayPause}
          title="Play/Pause (Space)"
        >
          {isPlaying ? '⏸' : '▶'}
        </button>

        <button
          className="control-btn skip-btn"
          onClick={() => setCurrentTime(Math.min(totalDuration, currentTime + 10000))}
          title="Skip Forward 10s (→)"
        >
          ⏩
        </button>
      </div>

      <div className="speed-controls">
        <span className="speed-label">Speed:</span>
        {[0.5, 1, 2, 5, 10].map(speed => (
          <button
            key={speed}
            className={`speed-btn ${playbackSpeed === speed ? 'active' : ''}`}
            onClick={() => handleSpeedChange(speed)}
          >
            {speed}x
          </button>
        ))}
      </div>
    </div>
  );
};

export default TimelineControls;
