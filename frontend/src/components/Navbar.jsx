// src/components/Navbar.jsx
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <nav className="navbar navbar-expand-lg">
      <div className="container-fluid">
        <Link className="navbar-brand" to="/">
          <i className="fas fa-headphones me-2"></i>Music Recommender
        </Link>

        <form className="search-form d-none d-lg-block" onSubmit={(e) => {
          e.preventDefault();
          const formData = new FormData(e.target);
          const query = formData.get('q');
          if (query.trim()) navigate(`/search?q=${encodeURIComponent(query)}`);
        }}>
          <div className="input-group">
            <input type="search" className="form-control" name="q" placeholder="Поиск треков, исполнителей" />
          </div>
        </form>

        <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span className="navbar-toggler-icon"></span>
        </button>

        <div className="collapse navbar-collapse" id="navbarNav">
          <ul className="navbar-nav ms-auto">
            <li className="nav-item">
              <Link className="nav-link" to="/">Главная</Link>
            </li>
            <li className="nav-item">
              <Link className="nav-link" to="/library">Библиотека</Link>
            </li>
            <li className="nav-item">
              <Link className="nav-link" to="/collection">Моя коллекция</Link>
            </li>
            {user && user.username === 'admin' && (
              <li className="nav-item">
                <button className="nav-link" onClick={() => alert('Переобучение пока не реализовано')}>
                  <i className="fas fa-sync-alt me-1"></i>Переобучить
                </button>
              </li>
            )}
            {user ? (
              <li className="nav-item dropdown">
                <a className="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                  <i className="fas fa-user-circle me-1"></i>{user.full_name || user.username}
                </a>
                <ul className="dropdown-menu dropdown-menu-end">
                  <li><button className="dropdown-item" onClick={handleLogout}><i className="fas fa-sign-out-alt me-2"></i>Выйти</button></li>
                </ul>
              </li>
            ) : (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/login">Вход</Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/register">Регистрация</Link>
                </li>
              </>
            )}
          </ul>
        </div>
      </div>
    </nav>
  );
}