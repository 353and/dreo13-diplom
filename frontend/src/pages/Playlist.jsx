// src/pages/Playlist.jsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usePlayer } from '../context/PlayerContext';
import api from '../services/api';
import TrackCard from '../components/TrackCard';

export default function Playlist() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { playTrack } = usePlayer();
  const [playlist, setPlaylist] = useState(null);
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPlaylist = async () => {
      try {
        const response = await api.get(`/playlists/${id}`);
        setPlaylist(response.data);
        setTracks(response.data.tracks || []);
      } catch (error) {
        console.error('Error fetching playlist', error);
      } finally {
        setLoading(false);
      }
    };
    fetchPlaylist();
  }, [id]);

  const handleDeletePlaylist = async () => {
    if (!window.confirm('Удалить плейлист?')) return;
    try {
      await api.delete(`/playlists/${id}`);
      navigate('/collection');
    } catch (error) {
      console.error('Error deleting playlist', error);
    }
  };

  const handleRemoveTrack = async (trackId) => {
    try {
      await api.delete(`/playlists/${id}/tracks/${trackId}`);
      setTracks(tracks.filter(t => t.id !== trackId));
    } catch (error) {
      console.error('Error removing track', error);
    }
  };

  if (loading) return <div className="text-center py-5">Загрузка...</div>;
  if (!playlist) return <div className="text-center py-5">Плейлист не найден</div>;

  return (
    <div>
      <div className="d-flex align-items-center mb-4">
        <div className="playlist-cover-large me-4">
          <i className="fas fa-music"></i>
        </div>
        <div>
          <h1 className="display-4 mb-0">{playlist.name}</h1>
          <p className="text-secondary mt-2">{tracks.length} треков</p>
          {playlist.name !== "Мне нравится" && (
            <button className="btn btn-outline-danger btn-sm" onClick={handleDeletePlaylist}>
              Удалить плейлист
            </button>
          )}
        </div>
      </div>

      <div className="row">
        {tracks.map(track => (
          <div key={track.id} className="col-md-6 col-lg-4 mb-4">
            <div className="track-card">
              <TrackCard track={track} playlist={tracks} />
              {playlist.name !== "Мне нравится" && (
                <button
                  className="btn btn-sm btn-outline-danger mt-2"
                  onClick={() => handleRemoveTrack(track.id)}
                >
                  <i className="fas fa-times me-1"></i>Убрать
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {tracks.length === 0 && (
        <div className="text-center py-5">
          <i className="fas fa-music fa-4x mb-3" style={{ color: 'var(--text-muted)' }}></i>
          <h3>В плейлисте пока нет треков</h3>
          <p className="text-secondary">Добавляйте треки из библиотеки, поиска или рекомендаций</p>
        </div>
      )}
    </div>
  );
}