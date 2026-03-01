# api.py
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Response
from sqlalchemy.orm import Session
from datetime import timedelta
import pickle
import numpy as np
from scipy.sparse import load_npz, csr_matrix

from database import get_db
from database import Artist, Track, User, Interaction, Playlist, PlaylistTrack
# Импортируем функции аутентификации из auth
from auth import get_current_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
# Импортируем глобальные переменные модели из main
import main  # целиком, чтобы избежать цикла

router = APIRouter(prefix="/api")

# === Аутентификация ===
@router.post("/auth/login")
async def api_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.verify_password(password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60)
    return {"status": "ok", "access_token": access_token}

@router.post("/auth/register")
async def api_register(
    response: Response,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Имя или email уже заняты")
    hashed = User.hash_password(password)
    user = User(username=username, email=email, hashed_password=hashed, full_name=full_name)
    db.add(user)
    db.commit()
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60)
    return {"status": "ok"}

@router.post("/auth/logout")
async def api_logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "ok"}

@router.get("/user/me")
async def api_me(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    liked_count = db.query(Interaction).filter(
        Interaction.user_id == user.id, Interaction.event_type == 'like'
    ).count()
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "liked_count": liked_count,
        "interactions_count": len(user.interactions)
    }

# === Треки и рекомендации ===
def get_popular_tracks(db: Session, limit: int = 20):
    return db.query(Track).order_by(Track.popularity.desc()).limit(limit).all()

@router.get("/recommendations")
async def api_recommendations(request: Request, limit: int = 20, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    user_id = user.id if user else None
    if user_id and main.als_model is not None and user_id in main.user_map:
        user_idx = main.user_map[user_id]
        rec_ids_idx, scores = main.als_model.recommend(
            user_idx,
            main.user_item_matrix[user_idx],
            N=limit,
            filter_already_liked_items=True
        )
        track_ids = [main.idx_to_track[i] for i in rec_ids_idx]
        tracks = db.query(Track).filter(Track.id.in_(track_ids)).all()
        order = {tid: pos for pos, tid in enumerate(track_ids)}
        tracks.sort(key=lambda t: order[t.id])
    else:
        tracks = get_popular_tracks(db, limit)
    result = []
    for t in tracks:
        result.append({
            "id": t.id,
            "title": t.title,
            "artist": {"id": t.artist.id, "name": t.artist.name} if t.artist else None,
            "genre": t.genre,
            "duration": t.duration,
            "popularity": t.popularity
        })
    return result

@router.get("/tracks")
async def api_tracks(
    request: Request,
    genre: str = "",
    sort: str = "popularity",
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(Track)
    if genre:
        query = query.filter(Track.genre.ilike(f"%{genre}%"))
    if sort == "popularity":
        query = query.order_by(Track.popularity.desc())
    elif sort == "date":
        query = query.order_by(Track.id.desc())
    elif sort == "genre":
        query = query.order_by(Track.genre)
    total = query.count()
    tracks = query.offset(offset).limit(limit).all()
    result = []
    for t in tracks:
        result.append({
            "id": t.id,
            "title": t.title,
            "artist": {"id": t.artist.id, "name": t.artist.name} if t.artist else None,
            "genre": t.genre,
            "duration": t.duration,
            "popularity": t.popularity
        })
    return {"items": result, "total": total, "limit": limit, "offset": offset}

@router.get("/tracks/{track_id}")
async def api_track_detail(track_id: int, db: Session = Depends(get_db)):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404)
    return {
        "id": track.id,
        "title": track.title,
        "artist": {"id": track.artist.id, "name": track.artist.name} if track.artist else None,
        "genre": track.genre,
        "duration": track.duration,
        "popularity": track.popularity
    }

@router.get("/tracks/{track_id}/play")
async def api_track_play(track_id: int, db: Session = Depends(get_db)):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404)
    return {
        "id": track.id,
        "title": track.title,
        "artist": track.artist.name if track.artist else "Unknown",
        "audio_url": "/static/placeholder.mp3"
    }

# === Исполнители ===
@router.get("/artists/{artist_id}")
async def api_artist_detail(artist_id: int, db: Session = Depends(get_db)):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404)
    return {
        "id": artist.id,
        "name": artist.name,
        "bio": artist.bio,
        "country": artist.country,
        "formed_year": artist.formed_year,
        "genres": artist.genres
    }

@router.get("/artists/{artist_id}/tracks")
async def api_artist_tracks(artist_id: int, db: Session = Depends(get_db)):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404)
    tracks = artist.tracks
    result = []
    for t in tracks:
        result.append({
            "id": t.id,
            "title": t.title,
            "genre": t.genre,
            "duration": t.duration
        })
    return result

# === Поиск ===
@router.get("/search")
async def api_search(q: str, db: Session = Depends(get_db)):
    tracks = db.query(Track).filter(Track.title.ilike(f"%{q}%")).all()
    artists = db.query(Artist).filter(Artist.name.ilike(f"%{q}%")).all()
    return {
        "tracks": [{"id": t.id, "title": t.title, "artist": t.artist.name if t.artist else None} for t in tracks],
        "artists": [{"id": a.id, "name": a.name} for a in artists]
    }

# === Взаимодействия ===
@router.post("/interactions")
async def api_interaction(
    request: Request,
    track_id: int = Form(...),
    event_type: str = Form(...),
    db: Session = Depends(get_db)
):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    weights = {'play': 1.0, 'skip': 0.5, 'dislike': 0.2, 'like': 2.0}
    weight = weights.get(event_type, 0.0)
    interaction = Interaction(user_id=user.id, track_id=track_id, event_type=event_type, weight=weight)
    db.add(interaction)
    db.commit()
    return {"status": "ok"}

# === Лайки ===
@router.get("/liked")
async def api_liked(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    liked = db.query(Interaction).filter(
        Interaction.user_id == user.id, Interaction.event_type == 'like'
    ).all()
    track_ids = [l.track_id for l in liked]
    tracks = db.query(Track).filter(Track.id.in_(track_ids)).all() if track_ids else []
    result = []
    for t in tracks:
        result.append({
            "id": t.id,
            "title": t.title,
            "artist": {"id": t.artist.id, "name": t.artist.name} if t.artist else None,
            "duration": t.duration
        })
    return result

@router.get("/like/{track_id}")
async def api_check_like(track_id: int, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        return {"liked": False}
    liked = db.query(Interaction).filter(
        Interaction.user_id == user.id, Interaction.track_id == track_id, Interaction.event_type == 'like'
    ).first()
    return {"liked": liked is not None}

@router.post("/like/{track_id}")
async def api_toggle_like(track_id: int, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    existing = db.query(Interaction).filter(
        Interaction.user_id == user.id, Interaction.track_id == track_id, Interaction.event_type == 'like'
    ).first()
    liked_playlist = db.query(Playlist).filter(
        Playlist.user_id == user.id, Playlist.name == "Мне нравится"
    ).first()
    if not liked_playlist:
        liked_playlist = Playlist(name="Мне нравится", user_id=user.id)
        db.add(liked_playlist)
        db.commit()
        db.refresh(liked_playlist)
    if existing:
        db.delete(existing)
        pt = db.query(PlaylistTrack).filter(
            PlaylistTrack.playlist_id == liked_playlist.id, PlaylistTrack.track_id == track_id
        ).first()
        if pt:
            db.delete(pt)
        db.commit()
        return {"status": "unliked"}
    else:
        like = Interaction(user_id=user.id, track_id=track_id, event_type='like', weight=2.0)
        db.add(like)
        pt = PlaylistTrack(playlist_id=liked_playlist.id, track_id=track_id)
        db.add(pt)
        db.commit()
        return {"status": "liked"}

# === Плейлисты ===
@router.get("/playlists")
async def api_playlists(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    playlists = db.query(Playlist).filter(Playlist.user_id == user.id).all()
    return [
        {"id": p.id, "name": p.name, "created_at": p.created_at, "track_count": len(p.tracks)}
        for p in playlists
    ]

@router.get("/playlists/{playlist_id}")
async def api_playlist_detail(playlist_id: int, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == user.id).first()
    if not playlist:
        raise HTTPException(status_code=404)
    tracks = [pt.track for pt in playlist.tracks]
    return {
        "id": playlist.id,
        "name": playlist.name,
        "created_at": playlist.created_at,
        "tracks": [
            {
                "id": t.id,
                "title": t.title,
                "artist": {"id": t.artist.id, "name": t.artist.name} if t.artist else None,
                "duration": t.duration
            }
            for t in tracks
        ]
    }

@router.post("/playlists")
async def api_create_playlist(request: Request, name: str = Form(...), db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    playlist = Playlist(name=name, user_id=user.id)
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return {"id": playlist.id, "name": playlist.name}

@router.post("/playlists/{playlist_id}/tracks")
async def api_add_track_to_playlist(
    playlist_id: int, request: Request, track_id: int = Form(...), db: Session = Depends(get_db)
):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == user.id).first()
    if not playlist:
        raise HTTPException(status_code=404)
    existing = db.query(PlaylistTrack).filter(
        PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.track_id == track_id
    ).first()
    if not existing:
        pt = PlaylistTrack(playlist_id=playlist_id, track_id=track_id)
        db.add(pt)
        db.commit()
    return {"status": "ok"}

@router.delete("/playlists/{playlist_id}/tracks/{track_id}")
async def api_remove_track_from_playlist(
    playlist_id: int, track_id: int, request: Request, db: Session = Depends(get_db)
):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == user.id).first()
    if not playlist:
        raise HTTPException(status_code=404)
    pt = db.query(PlaylistTrack).filter(
        PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.track_id == track_id
    ).first()
    if pt:
        db.delete(pt)
        db.commit()
    return {"status": "ok"}

@router.delete("/playlists/{playlist_id}")
async def api_delete_playlist(playlist_id: int, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == user.id).first()
    if not playlist:
        raise HTTPException(status_code=404)
    if playlist.name == "Мне нравится":
        raise HTTPException(status_code=400, detail="Нельзя удалить плейлист «Мне нравится»")
    db.delete(playlist)
    db.commit()
    return {"status": "ok"}