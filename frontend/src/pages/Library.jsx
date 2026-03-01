// src/pages/Library.jsx
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { usePlayer } from '../context/PlayerContext';
import api from '../services/api';
import TrackCard from '../components/TrackCard';

export default function Library() {
  const { user } = useAuth();
  const { playTrack } = usePlayer();
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [genre, setGenre] = useState('');
  const [sort, setSort] = useState('popularity');
  const [stats, setStats] = useState({ total: 0, genreCount: 0, artistCount: 0 });

  useEffect(() => {
    const fetchTracks = async () => {
      try {
        const response = await api.get('/tracks', {
          params: { genre, sort, limit: 100 }
        });
        setTracks(response.data.items || []);
        
        // Получаем статистику (можно отдельным запросом, но для простоты считаем здесь)
        const uniqueGenres = new Set(response.data.items.map(t => t.genre).filter(Boolean));
        const uniqueArtists = new Set(response.data.items.map(t => t.artist?.id).filter(Boolean));
        setStats({
          total: response.data.total || response.data.items.length,
          genreCount: uniqueGenres.size,
          artistCount: uniqueArtists.size
        });
      } catch (error) {
        console.error('Error fetching tracks', error);
      } finally {
        setLoading(false);
      }
    };
    fetchTracks();
  }, [genre, sort]);

  const handleGenreClick = (g) => {
    setGenre(g === genre ? '' : g);
  };

  const handleSortClick = (s) => {
    setSort(s);
  };

  if (loading) return <div className="text-center py-5">Загрузка...</div>;

  return (
    <div>
      <h1 className="mb-4">Коллекция</h1>

      {/* Статистика */}
      <div className="stats-grid mb-4">
        <div className="stat-card">
          <div className="stat-number">{stats.total}</div>
          <div className="stat-label">Всего треков</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.genreCount}</div>
          <div className="stat-label">Жанров</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.artistCount}</div>
          <div className="stat-label">Исполнителей</div>
        </div>
      </div>

      {/* Чипы фильтрации */}
      <div className="chip-container mb-4">
        <button
          className={`chip ${!genre ? 'active' : ''}`}
          onClick={() => setGenre('')}
        >
          Все
        </button>
        <button
          className={`chip ${sort === 'popularity' ? 'active' : ''}`}
          onClick={() => handleSortClick('popularity')}
        >
          По популярности
        </button>
        <button
          className={`chip ${sort === 'date' ? 'active' : ''}`}
          onClick={() => handleSortClick('date')}
        >
          По дате
        </button>
        <button
          className={`chip ${sort === 'genre' ? 'active' : ''}`}
          onClick={() => handleSortClick('genre')}
        >
          По жанру
        </button>
      </div>

      {/* Сетка треков */}
      <div className="row">
        {tracks.map(track => (
          <div key={track.id} className="col-md-6 col-lg-4 mb-4">
            <TrackCard track={track} playlist={tracks} />
          </div>
        ))}
      </div>
    </div>
  );
}