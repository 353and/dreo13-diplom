// src/components/Player.jsx
import { usePlayer } from '../context/PlayerContext';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
// import './Player.css'; // создадим позже

export default function Player() {
  const { currentTrack, isPlaying, currentTime, duration, togglePlay, nextTrack, prevTrack, seek } = usePlayer();
  const { user } = useAuth();

  if (!currentTrack) return null;

  const handleLike = async () => {
    if (!user) return;
    try {
      await api.post(`/like/${currentTrack.id}`);
      // Можно обновить состояние лайка, но для простоты перезагрузим данные
    } catch (error) {
      console.error('Error liking track', error);
    }
  };

  const handleDislike = async () => {
    if (!user) return;
    try {
      await api.post('/interactions', new URLSearchParams({
        track_id: currentTrack.id,
        event_type: 'dislike'
      }));
      nextTrack();
    } catch (error) {
      console.error('Error disliking track', error);
    }
  };

  const formatTime = (sec) => {
    const mins = Math.floor(sec / 60);
    const secs = Math.floor(sec % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const handleSeek = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const percent = offsetX / rect.width;
    seek(percent * duration);
  };

  return (
    <div className="player-bar">
      <div className="container">
        <div className="row align-items-center">
          <div className="col-md-3">
            <div className="player-info">
              <img
                src={`https://ui-avatars.com/api/?name=${encodeURIComponent(currentTrack.artist?.name || 'Unknown')}&size=40&background=random&length=1`}
                alt={currentTrack.title}
                className="avatar"
              />
              <div>
                <div className="fw-medium">{currentTrack.title}</div>
                <small className="text-secondary">{currentTrack.artist?.name}</small>
              </div>
            </div>
          </div>
          <div className="col-md-6">
            <div className="player-controls">
              <button onClick={prevTrack} className="control-btn"><i className="fas fa-step-backward"></i></button>
              <button onClick={togglePlay} className="play-pause">
                <i className={`fas fa-${isPlaying ? 'pause' : 'play'}`}></i>
              </button>
              <button onClick={nextTrack} className="control-btn"><i className="fas fa-step-forward"></i></button>
            </div>
            <div className="player-progress-container">
              <span>{formatTime(currentTime)}</span>
              <div className="player-progress" onClick={handleSeek}>
                <div className="player-progress-bar" style={{ width: `${(currentTime / duration) * 100}%` }}></div>
              </div>
              <span>{formatTime(duration)}</span>
            </div>
          </div>
          <div className="col-md-3 text-end">
            {user && (
              <>
                <button onClick={handleLike} className="like-button me-3"><i className="far fa-heart"></i></button>
                <button onClick={handleDislike} className="dislike-button"><i className="fas fa-thumbs-down"></i></button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}