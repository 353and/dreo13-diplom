// src/components/TrackCard.jsx
import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { usePlayer } from '../context/PlayerContext'; // создадим позже
import api from '../services/api';
// import './TrackCard.css'; // создадим позже

export default function TrackCard({ track, playlist = [] }) {
  const { user } = useAuth();
  const { playTrack } = usePlayer(); // будет в PlayerContext
  const [liked, setLiked] = useState(track.liked || false);
  const [showPlaylists, setShowPlaylists] = useState(false);
  const [userPlaylists, setUserPlaylists] = useState([]);

  const handleLike = async (e) => {
    e.stopPropagation();
    try {
      const response = await api.post(`/like/${track.id}`);
      setLiked(response.data.status === 'liked');
    } catch (error) {
      console.error('Error toggling like', error);
    }
  };

  const handleAddToPlaylist = async (e, playlistId) => {
    e.stopPropagation();
    try {
      await api.post(`/playlists/${playlistId}/tracks`, new URLSearchParams({ track_id: track.id }));
      alert('Трек добавлен в плейлист');
    } catch (error) {
      console.error('Error adding to playlist', error);
    }
  };

  const loadPlaylists = async () => {
    if (!user) return;
    try {
      const response = await api.get('/playlists');
      setUserPlaylists(response.data);
    } catch (error) {
      console.error('Error loading playlists', error);
    }
  };

  const handlePlay = () => {
    playTrack(track, playlist);
  };

  return (
    <div className="track-card" onClick={handlePlay}>
      <img
        src={`https://ui-avatars.com/api/?name=${encodeURIComponent(track.artist?.name || 'Unknown')}&size=200&background=random&length=1`}
        alt={track.title}
        className="cover-art"
      />
      <div className="track-title">{track.title || 'Без названия'}</div>
      <div className="track-artist">{track.artist?.name || 'Неизвестный исполнитель'}</div>
      <div className="d-flex justify-content-between align-items-center mt-2">
        <span className="track-duration">
          {track.duration ? `${Math.floor(track.duration / 60)}:${(track.duration % 60).toString().padStart(2, '0')}` : '0:00'}
        </span>
        <div>
          {user && (
            <>
              <i
                className={`fa-heart like-button ${liked ? 'fas liked' : 'far'}`}
                onClick={handleLike}
              />
              <button
                className="btn btn-sm btn-outline-secondary ms-2"
                onClick={async (e) => {
                  e.stopPropagation();
                  await loadPlaylists();
                  setShowPlaylists(!showPlaylists);
                }}
              >
                <i className="fas fa-plus"></i>
              </button>
            </>
          )}
        </div>
      </div>
      {showPlaylists && userPlaylists.length > 0 && (
        <div className="playlist-menu mt-2">
          {userPlaylists.map(p => (
            <div
              key={p.id}
              className="playlist-item"
              onClick={(e) => handleAddToPlaylist(e, p.id)}
            >
              {p.name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}