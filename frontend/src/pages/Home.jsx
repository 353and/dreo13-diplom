// src/pages/Home.jsx
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { usePlayer } from '../context/PlayerContext';
import api from '../services/api';
import TrackCard from '../components/TrackCard';


export default function Home() {
  const { user } = useAuth();
  const { playTrack } = usePlayer();
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRecommendations = async () => {
      try {
        const response = await api.get('/recommendations?limit=20');
        setRecommendations(response.data);
      } catch (error) {
        console.error('Error fetching recommendations', error);
      } finally {
        setLoading(false);
      }
    };
    fetchRecommendations();
  }, []);

  if (loading) return <div className="text-center py-5">Загрузка...</div>;

  return (
    <div>
      {/* Герой "Моя волна" */}
      <div className="hero-wave">
        <h1>Моя волна</h1>
        <p>Персональные рекомендации на основе ваших предпочтений</p>
        {recommendations.length > 0 && (
          <button
            className="btn-play"
            onClick={() => playTrack(recommendations[0], recommendations)}
          >
            <i className="fas fa-play me-2"></i>Слушать
          </button>
        )}
      </div>

      {/* Статистика (опционально) */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{user?.interactions_count || 0}</div>
          <div className="stat-label">Прослушано треков</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{user?.liked_count || 0}</div>
          <div className="stat-label">Мне нравится</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{recommendations.length}</div>
          <div className="stat-label">Рекомендаций</div>
        </div>
      </div>

      {/* Для вас */}
      <h2 className="mb-4">Для вас</h2>
      <div className="horizontal-scroll">
        {recommendations.map(track => (
          <TrackCard key={track.id} track={track} playlist={recommendations} />
        ))}
      </div>

      {/* Тренды (популярные) */}
      <h2 className="mb-4 mt-5">Тренды</h2>
      <div className="horizontal-scroll">
        {recommendations.slice(0, 5).map(track => (
          <TrackCard key={track.id} track={track} playlist={recommendations} />
        ))}
      </div>

      {/* Чипы жанров (пока без функционала) */}
      <div className="chip-container mt-5">
        <span className="chip active">Все</span>
        <span className="chip">Рок</span>
        <span className="chip">Поп</span>
        <span className="chip">Электроника</span>
        <span className="chip">Хип-хоп</span>
        <span className="chip">Джаз</span>
        <span className="chip">Классика</span>
      </div>
    </div>
  );
}