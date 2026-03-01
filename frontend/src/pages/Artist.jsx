// src/pages/Artist.jsx
import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usePlayer } from '../context/PlayerContext';
import api from '../services/api';
import TrackCard from '../components/TrackCard';

export default function Artist() {
  const { id } = useParams();
  const { user } = useAuth();
  const { playTrack } = usePlayer();
  const [artist, setArtist] = useState(null);
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchArtist = async () => {
      try {
        const artistResp = await api.get(`/artists/${id}`);
        setArtist(artistResp.data);
        const tracksResp = await api.get(`/artists/${id}/tracks`);
        setTracks(tracksResp.data);
      } catch (error) {
        console.error('Error fetching artist', error);
      } finally {
        setLoading(false);
      }
    };
    fetchArtist();
  }, [id]);

  if (loading) return <div className="text-center py-5">Загрузка...</div>;
  if (!artist) return <div className="text-center py-5">Исполнитель не найден</div>;

  return (
    <div>
      {/* Шапка исполнителя */}
      <div className="d-flex align-items-center mb-4 flex-wrap">
        <img
          src={`https://ui-avatars.com/api/?name=${encodeURIComponent(artist.name)}&size=80&background=random&length=1`}
          alt={artist.name}
          className="rounded-circle me-4 mb-2"
          style={{ width: '80px', height: '80px' }}
        />
        <div>
          <h1 className="display-4 mb-0">{artist.name}</h1>
          <div className="mt-2">
            {artist.country && (
              <span className="badge bg-light text-dark me-2">
                <i className="fas fa-globe me-1"></i>{artist.country}
              </span>
            )}
            {artist.formed_year && (
              <span className="badge bg-light text-dark me-2">
                <i className="fas fa-calendar me-1"></i>{artist.formed_year}
              </span>
            )}
            {artist.genres && (
              <span className="badge bg-light text-dark">
                <i className="fas fa-tag me-1"></i>{artist.genres}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Биография */}
      {artist.bio && (
        <div className="card mb-4">
          <div className="card-body">
            <p className="lead">{artist.bio}</p>
          </div>
        </div>
      )}

      {/* Треки */}
      <h3 className="mb-4"><i className="fas fa-music me-2"></i>Треки</h3>
      <div className="row">
        {tracks.map(track => (
          <div key={track.id} className="col-md-6 col-lg-4 mb-4">
            <TrackCard
              track={{ ...track, artist: { id: artist.id, name: artist.name } }}
              playlist={tracks.map(t => ({ ...t, artist: { id: artist.id, name: artist.name } }))}
            />
          </div>
        ))}
      </div>
    </div>
  );
}