// src/context/PlayerContext.jsx
import { createContext, useContext, useState, useRef } from 'react';
import api from '../services/api';

const PlayerContext = createContext();

export const usePlayer = () => useContext(PlayerContext);

export const PlayerProvider = ({ children }) => {
  const [currentTrack, setCurrentTrack] = useState(null);
  const [playlist, setPlaylist] = useState([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef(new Audio());

  const playTrack = async (track, trackList = []) => {
    // trackList может быть передан для навигации по плейлисту
    setCurrentTrack(track);
    setPlaylist(trackList.length ? trackList : [track]);

    try {
      const response = await api.get(`/tracks/${track.id}/play`);
      audioRef.current.src = response.data.audio_url;
      audioRef.current.play();
      setIsPlaying(true);

      // Отправляем событие прослушивания
      await api.post('/interactions', new URLSearchParams({
        track_id: track.id,
        event_type: 'play'
      }));
    } catch (error) {
      console.error('Error playing track', error);
    }
  };

  const togglePlay = () => {
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const nextTrack = () => {
    if (playlist.length === 0) return;
    const currentIndex = playlist.findIndex(t => t.id === currentTrack?.id);
    const nextIndex = (currentIndex + 1) % playlist.length;
    playTrack(playlist[nextIndex], playlist);
  };

  const prevTrack = () => {
    if (playlist.length === 0) return;
    const currentIndex = playlist.findIndex(t => t.id === currentTrack?.id);
    const prevIndex = (currentIndex - 1 + playlist.length) % playlist.length;
    playTrack(playlist[prevIndex], playlist);
  };

  const seek = (time) => {
    audioRef.current.currentTime = time;
  };

  // Обработчики событий аудио
  audioRef.current.addEventListener('timeupdate', () => {
    setCurrentTime(audioRef.current.currentTime);
  });
  audioRef.current.addEventListener('loadedmetadata', () => {
    setDuration(audioRef.current.duration);
  });
  audioRef.current.addEventListener('ended', nextTrack);

  return (
    <PlayerContext.Provider value={{
      currentTrack,
      isPlaying,
      currentTime,
      duration,
      playTrack,
      togglePlay,
      nextTrack,
      prevTrack,
      seek
    }}>
      {children}
    </PlayerContext.Provider>
  );
};