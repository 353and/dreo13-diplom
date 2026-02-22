# main.py
from fastapi import FastAPI, Request, Depends, Form, HTTPException, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional
import pickle
import numpy as np
from scipy.sparse import load_npz, csr_matrix
import implicit
import threading
import os

# Импорты из наших модулей
from database import SessionLocal, engine, get_db
from database import Artist, Track, User, Interaction

# ===== НАСТРОЙКИ JWT =====
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# =========================

app = FastAPI(title="Music Recommender Service")

# Подключаем статику и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Глобальные переменные для модели
als_model = None
user_map = {}
track_map = {}
user_ids_list = []
track_ids_list = []
idx_to_track = {}
user_item_matrix = None

def load_model():
    """Загружает ALS модель и маппинги из файлов"""
    global als_model, user_map, track_map, user_ids_list, track_ids_list, idx_to_track, user_item_matrix
    try:
        with open('als_model.pkl', 'rb') as f:
            als_model = pickle.load(f)

        with open('mappings.pkl', 'rb') as f:
            mappings = pickle.load(f)
            user_map = mappings['user_map']
            track_map = mappings['track_map']
            user_ids_list = mappings['user_ids']
            track_ids_list = mappings['track_ids']

        idx_to_track = {v: k for k, v in track_map.items()}
        user_item_matrix = load_npz('user_item_matrix.npz')
        print("✅ Модель ALS успешно загружена")
    except Exception as e:
        print(f"⚠️ Не удалось загрузить модель: {e}")
        print("Будет использован режим холодного старта (популярные треки)")

# Загружаем модель при старте
load_model()

# --- Вспомогательные функции ---
def get_popular_tracks(db: Session, limit: int = 20):
    """Возвращает популярные треки (по полю popularity)"""
    return db.query(Track).order_by(Track.popularity.desc()).limit(limit).all()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    user = db.query(User).filter(User.username == username).first()
    return user

# --- Эндпоинты аутентификации ---
@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "user": None})

@app.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.verify_password(password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "user": None,
            "error": "Неверное имя пользователя или пароль"
        })
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60)
    return response

@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "user": None})

@app.post("/register")
async def register(
    request: Request,
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
        return templates.TemplateResponse("register.html", {
            "request": request,
            "user": None,
            "error": "Имя пользователя или email уже заняты"
        })
    hashed = User.hash_password(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed,
        full_name=full_name
    )
    db.add(user)
    db.commit()
    # Сразу логиним
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response

# --- Основные эндпоинты ---
@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user(request, db)
    user_id = current_user.id if current_user else None

    if user_id and als_model is not None and user_id in user_map:
        user_idx = user_map[user_id]
        rec_ids_idx, scores = als_model.recommend(
            user_idx,
            user_item_matrix[user_idx],
            N=20,
            filter_already_liked_items=True
        )
        track_ids = [idx_to_track[i] for i in rec_ids_idx]
        recs = db.query(Track).filter(Track.id.in_(track_ids)).all()
        order = {tid: pos for pos, tid in enumerate(track_ids)}
        recs.sort(key=lambda t: order[t.id])
    else:
        recs = get_popular_tracks(db, 20)

    # Получаем ID лайкнутых треков для текущего пользователя
    liked_ids = []
    if current_user:
        liked = db.query(Interaction).filter(
            Interaction.user_id == current_user.id,
            Interaction.event_type == 'like'
        ).all()
        liked_ids = [l.track_id for l in liked]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "recommendations": recs,
        "user": current_user,
        "liked_ids": liked_ids
    })

@app.get("/library")
async def library(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user(request, db)
    tracks = db.query(Track).all()
    liked_ids = []
    if current_user:
        liked = db.query(Interaction).filter(
            Interaction.user_id == current_user.id,
            Interaction.event_type == 'like'
        ).all()
        liked_ids = [l.track_id for l in liked]
    return templates.TemplateResponse("library.html", {
        "request": request,
        "tracks": tracks,
        "user": current_user,
        "liked_ids": liked_ids
    })

@app.get("/artist/{artist_id}")
async def artist_page(request: Request, artist_id: int, db: Session = Depends(get_db)):
    current_user = await get_current_user(request, db)
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    liked_ids = []
    if current_user:
        liked = db.query(Interaction).filter(
            Interaction.user_id == current_user.id,
            Interaction.event_type == 'like'
        ).all()
        liked_ids = [l.track_id for l in liked]
    return templates.TemplateResponse("artist.html", {
        "request": request,
        "artist": artist,
        "tracks": artist.tracks,
        "user": current_user,
        "liked_ids": liked_ids
    })

@app.get("/search")
async def search(request: Request, q: str = "", db: Session = Depends(get_db)):
    current_user = await get_current_user(request, db)
    tracks = []
    artists = []
    if q:
        tracks = db.query(Track).filter(Track.title.ilike(f"%{q}%")).all()
        artists = db.query(Artist).filter(Artist.name.ilike(f"%{q}%")).all()
    liked_ids = []
    if current_user:
        liked = db.query(Interaction).filter(
            Interaction.user_id == current_user.id,
            Interaction.event_type == 'like'
        ).all()
        liked_ids = [l.track_id for l in liked]
    return templates.TemplateResponse("search.html", {
        "request": request,
        "query": q,
        "tracks": tracks,
        "artists": artists,
        "user": current_user,
        "liked_ids": liked_ids
    })

@app.get("/liked")
async def liked_page(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login")
    liked = db.query(Interaction).filter(
        Interaction.user_id == current_user.id,
        Interaction.event_type == 'like'
    ).all()
    # Получаем треки
    track_ids = [l.track_id for l in liked]
    tracks = db.query(Track).filter(Track.id.in_(track_ids)).all() if track_ids else []
    liked_ids = track_ids  # для подсветки
    return templates.TemplateResponse("liked.html", {
        "request": request,
        "tracks": tracks,
        "user": current_user,
        "liked_ids": liked_ids
    })

@app.post("/toggle-like")
async def toggle_like(
    request: Request,
    track_id: int = Form(...),
    db: Session = Depends(get_db)
):
    current_user = await get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Проверяем, есть ли уже лайк
    existing = db.query(Interaction).filter(
        Interaction.user_id == current_user.id,
        Interaction.track_id == track_id,
        Interaction.event_type == 'like'
    ).first()

    if existing:
        # Удаляем лайк
        db.delete(existing)
        db.commit()
        return JSONResponse({"status": "unliked"})
    else:
        # Добавляем лайк (с весом 2.0)
        like = Interaction(
            user_id=current_user.id,
            track_id=track_id,
            event_type='like',
            weight=2.0
        )
        db.add(like)
        db.commit()
        return JSONResponse({"status": "liked"})

# Существующий эндпоинт взаимодействий оставляем для других типов (play, skip, dislike)
@app.post("/interaction")
async def interaction(
    request: Request,
    track_id: int = Form(...),
    event_type: str = Form(...),
    db: Session = Depends(get_db)
):
    current_user = await get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if event_type == 'play':
        weight = 1.0
    elif event_type == 'skip':
        weight = 0.5
    elif event_type == 'dislike':
        weight = 0.2
    else:
        weight = 0.0

    interaction = Interaction(
        user_id=current_user.id,
        track_id=track_id,
        event_type=event_type,
        weight=weight
    )
    db.add(interaction)
    db.commit()
    return JSONResponse({"status": "ok"})

@app.get("/track/{track_id}/play")
async def play_track(track_id: int, db: Session = Depends(get_db)):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return {
        "id": track.id,
        "title": track.title,
        "artist": track.artist.name if track.artist else "Unknown",
        "audio_url": "/static/placeholder.mp3"
    }

# --- Админский эндпоинт для переобучения модели ---
def retrain_model_task():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        tracks = db.query(Track).all()
        interactions = db.query(Interaction).all()

        if not users or not tracks or not interactions:
            print("Недостаточно данных для переобучения")
            return

        user_ids = [u.id for u in users]
        track_ids = [t.id for t in tracks]

        user_map_new = {uid: i for i, uid in enumerate(user_ids)}
        track_map_new = {tid: i for i, tid in enumerate(track_ids)}

        rows = [user_map_new[i.user_id] for i in interactions]
        cols = [track_map_new[i.track_id] for i in interactions]
        data = [i.weight for i in interactions]

        user_item_matrix_new = csr_matrix((data, (rows, cols)), shape=(len(user_ids), len(track_ids)))

        model = implicit.als.AlternatingLeastSquares(
            factors=10,
            iterations=15,
            regularization=0.1,
            random_state=42
        )
        model.fit(user_item_matrix_new)

        with open('als_model.pkl', 'wb') as f:
            pickle.dump(model, f)

        with open('mappings.pkl', 'wb') as f:
            pickle.dump({
                'user_map': user_map_new,
                'track_map': track_map_new,
                'user_ids': user_ids,
                'track_ids': track_ids
            }, f)

        from scipy.sparse import save_npz
        save_npz('user_item_matrix.npz', user_item_matrix_new)

        print("✅ Модель успешно переобучена в фоне")
        load_model()
    except Exception as e:
        print(f"❌ Ошибка при переобучении: {e}")
    finally:
        db.close()

@app.post("/admin/retrain")
async def admin_retrain(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user(request, db)
    if not current_user or current_user.username != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")

    thread = threading.Thread(target=retrain_model_task)
    thread.start()

    return JSONResponse({"status": "ok", "message": "Переобучение запущено"})

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": als_model is not None}