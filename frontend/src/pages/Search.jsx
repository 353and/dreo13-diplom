// src/pages/Search.jsx
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usePlayer } from '../context/PlayerContext';
import api from '../services/api';
import TrackCard from '../components/TrackCard';

export default function Search() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') || '';
  const { user } = useAuth();
  const { playTrack } = usePlayer();
  const [tracks, setTracks] = useState([]);
  const [artists, setArtists] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!query) {
      setTracks([]);
      setArtists([]);
      return;
    }
    const fetchSearch = async () => {
      setLoading(true);
      try {
        const response = await api.get('/search', { params: { q: query } });
        setTracks(response.data.tracks || []);
        setArtists(response.data.artists || []);
      } catch (error) {
        console.error('Error searching', error);
      } finally {
        setLoading(false);
      }
    };
    fetchSearch();
  }, [query]);

  if (!query) {
    return (
      <div className="text-center py-5">
        <h2>Введите запрос для поиска</h2>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-4">Результаты поиска "{query}"</h1>

      {loading && <div className="text-center py-3">Загрузка...</div>}

      {artists.length > 0 && (
        <>
          <h3 className="mb-4"><i className="fas fa-users me-2"></i>Исполнители</h3>
          <div className="row mb-5">
            {artists.map(artist => (
              <div key={artist.id} className="col-md-4 mb-3">
                <div className="card track-card">
                  <div className="card-body d-flex align-items-center">
                    <img
                      src={`https://ui-avatars.com/api/?name=${encodeURIComponent(artist.name)}&size=50&background=random&length=1`}
                      alt={artist.name}
                      className="artist-avatar me-3"
                    />
                    <a href={`/artist/${artist.id}`} className="text-decoration-none fs-5">
                      {artist.name}
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {tracks.length > 0 && (
        <>
          <h3 className="mb-4"><i className="fas fa-music me-2"></i>Треки</h3>
          <div className="row">
            {tracks.map(track => (
              <div key={track.id} className="col-md-6 col-lg-4 mb-4">
                <TrackCard track={track} playlist={tracks} />
              </div>
            ))}
          </div>
        </>
      )}

      {!loading && artists.length === 0 && tracks.length === 0 && (
        <div className="text-center py-5">
          <i className="fas fa-search fa-4x mb-3" style={{ color: 'var(--text-muted)' }}></i>
          <h3>Ничего не найдено</h3>
          <p className="text-secondary">Попробуйте изменить запрос</p>
        </div>
      )}
    </div>
  );
}