import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { PlayerProvider } from './context/PlayerContext';
import Navbar from './components/Navbar';
import Player from './components/Player';
import Home from './pages/Home';
import Library from './pages/Library';
import Artist from './pages/Artist';
import Search from './pages/Search';
import Collection from './pages/Collection';
import Playlist from './pages/Playlist';
import Login from './pages/Login';
import Register from './pages/Register';

function App() {
  const { loading } = useAuth();
  if (loading) return <div className="text-center py-5">Загрузка...</div>;

  return (
    <BrowserRouter>
      <PlayerProvider>
        <Navbar />
        <main className="container mt-4">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/library" element={<Library />} />
            <Route path="/artist/:id" element={<Artist />} />
            <Route path="/search" element={<Search />} />
            <Route path="/collection" element={<Collection />} />
            <Route path="/playlist/:id" element={<Playlist />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
          </Routes>
        </main>
        <Player />
      </PlayerProvider>
    </BrowserRouter>
  );
}

export default App;