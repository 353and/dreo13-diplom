// src/pages/Collection.jsx
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export default function Collection() {
  const { user } = useAuth();
  const [playlists, setPlaylists] = useState([]);
  const [newPlaylistName, setNewPlaylistName] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPlaylists = async () => {
      try {
        const response = await api.get('/playlists');
        setPlaylists(response.data);
      } catch (error) {
        console.error('Error fetching playlists', error);
      } finally {
        setLoading(false);
      }
    };
    fetchPlaylists();
  }, []);

  const handleCreatePlaylist = async (e) => {
    e.preventDefault();
    if (!newPlaylistName.trim()) return;
    try {
      const response = await api.post('/playlists', new URLSearchParams({ name: newPlaylistName }));
      setPlaylists([...playlists, response.data]);
      setNewPlaylistName('');
    } catch (error) {
      console.error('Error creating playlist', error);
    }
  };

  if (loading) return <div className="text-center py-5">Загрузка...</div>;

  return (
    <div>
      <h1 className="mb-4">Моя коллекция</h1>

      {/* Форма создания плейлиста */}
      <div className="card mb-4">
        <div className="card-body">
          <h5 className="card-title">Создать новый плейлист</h5>
          <form onSubmit={handleCreatePlaylist}>
            <div className="input-group">
              <input
                type="text"
                className="form-control"
                placeholder="Название плейлиста"
                value={newPlaylistName}
                onChange={(e) => setNewPlaylistName(e.target.value)}
                required
              />
              <button className="btn btn-primary" type="submit">Создать</button>
            </div>
          </form>
        </div>
      </div>

      {/* Сетка плейлистов */}
      <div className="row">
        {playlists.map(playlist => (
          <div key={playlist.id} className="col-md-4 col-lg-3 mb-4">
            <div className="card playlist-card h-100">
              <a href={`/playlist/${playlist.id}`} className="text-decoration-none">
                <div className="playlist-cover">
                  <i className="fas fa-music"></i>
                </div>
                <div className="card-body">
                  <h5 className="card-title text-truncate">{playlist.name}</h5>
                  <p className="card-text text-muted">{playlist.track_count} треков</p>
                </div>
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}