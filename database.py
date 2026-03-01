# database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import hashlib
import os

SQLALCHEMY_DATABASE_URL = "sqlite:///./music.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Artist(Base):
    __tablename__ = "artists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    bio = Column(String, default="")
    country = Column(String, default="")
    formed_year = Column(Integer, nullable=True)
    genres = Column(String, default="")
    tracks = relationship("Track", back_populates="artist")

class Track(Base):
    __tablename__ = "tracks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    artist_id = Column(Integer, ForeignKey("artists.id"))
    genre = Column(String)
    duration = Column(Integer)
    popularity = Column(Integer, default=0)
    artist = relationship("Artist", back_populates="tracks")
    interactions = relationship("Interaction", back_populates="track")
    playlist_tracks = relationship("PlaylistTrack", back_populates="track")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    interactions = relationship("Interaction", back_populates="user")
    playlists = relationship("Playlist", back_populates="user", cascade="all, delete-orphan")

    def verify_password(self, password: str) -> bool:
        if not self.hashed_password or '$' not in self.hashed_password:
            return False
        salt, hash_val = self.hashed_password.split('$', 1)
        test_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return test_hash == hash_val

    @staticmethod
    def hash_password(password: str) -> str:
        salt = os.urandom(16).hex()
        hash_val = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return f"{salt}${hash_val}"

class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    track_id = Column(Integer, ForeignKey("tracks.id"))
    event_type = Column(String)   # 'play', 'like', 'dislike', 'skip'
    weight = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="interactions")
    track = relationship("Track", back_populates="interactions")

class Playlist(Base):
    __tablename__ = "playlists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user = relationship("User", back_populates="playlists")
    tracks = relationship("PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan")

class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"
    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"))
    track_id = Column(Integer, ForeignKey("tracks.id"))
    added_at = Column(DateTime, default=datetime.datetime.utcnow)
    playlist = relationship("Playlist", back_populates="tracks")
    track = relationship("Track", back_populates="playlist_tracks")

# Индексы
Index('idx_interactions_user', Interaction.user_id)
Index('idx_interactions_track', Interaction.track_id)
Index('idx_tracks_artist', Track.artist_id)
Index('idx_artist_name', Artist.name)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()