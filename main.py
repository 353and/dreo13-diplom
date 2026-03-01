# main.py
from fastapi import FastAPI, Request, Depends, Form, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import pickle
import numpy as np
from scipy.sparse import load_npz, csr_matrix
import implicit
import threading
import os

from database import SessionLocal, engine, get_db
from database import Artist, Track, User, Interaction, Playlist, PlaylistTrack
from auth import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, get_current_user

app = FastAPI(title="Music Recommender")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем API роутер
from api import router as api_router
app.include_router(api_router)

# CORS
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные переменные модели
als_model = None
user_map = {}
track_map = {}
user_ids_list = []
track_ids_list = []
idx_to_track = {}
user_item_matrix = None

def load_model():
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
        print("✅ ALS модель загружена")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки модели: {e}")
        print("Будет использован холодный старт")

load_model()

# Админский эндпоинт переобучения
@app.post("/admin/retrain")
async def admin_retrain(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user(request, db)
    if not current_user or current_user.username != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    thread = threading.Thread(target=retrain_model_task)
    thread.start()
    return JSONResponse({"status": "ok", "message": "Переобучение запущено"})

def retrain_model_task():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        tracks = db.query(Track).all()
        interactions = db.query(Interaction).all()
        if not users or not tracks or not interactions:
            print("Недостаточно данных")
            return
        user_ids = [u.id for u in users]
        track_ids = [t.id for t in tracks]
        user_map_new = {uid: i for i, uid in enumerate(user_ids)}
        track_map_new = {tid: i for i, tid in enumerate(track_ids)}
        rows = [user_map_new[i.user_id] for i in interactions]
        cols = [track_map_new[i.track_id] for i in interactions]
        data = [i.weight for i in interactions]
        user_item_matrix_new = csr_matrix((data, (rows, cols)), shape=(len(user_ids), len(track_ids)))
        model = implicit.als.AlternatingLeastSquares(factors=10, iterations=15, regularization=0.1, random_state=42)
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
        print("✅ Модель переобучена")
        load_model()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": als_model is not None}

# SPA обслуживание
SPA_DIR = "static_frontend"
if os.path.exists(SPA_DIR):
    assets_path = os.path.join(SPA_DIR, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    from fastapi.responses import FileResponse
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return {"error": "API route not found"}
        index_path = os.path.join(SPA_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Frontend not built"}
else:
    print("⚠️ SPA директория не найдена – фронтенд не будет раздаваться")