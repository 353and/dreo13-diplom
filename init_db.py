import random
import os
from database import engine, Base, SessionLocal, Artist, Track, User, Interaction
from scipy.sparse import csr_matrix
import implicit
import pickle
from scipy.sparse import save_npz

NUM_TRACKS = 300

for f in ['music.db', 'als_model.pkl', 'mappings.pkl', 'user_item_matrix.npz']:
    if os.path.exists(f):
        os.remove(f)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Генерация исполнителей и треков
prefixes = ["The", "Young", "Old", "New", "Modern", "Electric", "Acoustic", "Digital", "Analog", "Cosmic"]
suffixes = ["Band", "Orchestra", "Trio", "Quartet", "Ensemble", "Project", "Experience", "Sound", "Syndicate", "Collective"]
names = ["Beatles", "Stones", "Floyd", "Zeppelin", "Nirvana", "Radiohead", "Muse", "Coldplay", "U2", "Queen",
         "Bowie", "Prince", "Jackson", "Springsteen", "Dylan", "Cohen", "Mitchell", "Joplin", "Hendrix", "Morrison"]

artists_pool = []
for _ in range(70):
    if random.random() > 0.4:
        artist = f"{random.choice(prefixes)} {random.choice(names)}"
    else:
        artist = f"{random.choice(names)} {random.choice(suffixes)}"
    artists_pool.append(artist)
unique_artists = list(set(artists_pool))[:50]

song_words = [
    "Sunshine", "Rainbow", "Midnight", "Dreams", "Fire", "Water", "Earth", "Wind", "Stars", "Moon",
    "Love", "Hate", "Joy", "Pain", "Life", "Death", "Time", "Space", "Heart", "Soul",
    "Revolution", "Freedom", "Glory", "Mystery", "Echo", "Shadow", "Light", "Darkness", "Paradise", "Utopia",
    "Summer", "Winter", "Autumn", "Spring", "Ocean", "Mountain", "Desert", "Forest", "City", "Country",
    "Angel", "Demon", "Ghost", "Spirit", "Magic", "Wonder", "Fantasy", "Reality", "Illusion", "Truth"
]

genres = ["Rock", "Pop", "Electronic", "Hip-Hop", "Jazz", "Classical", "Reggae", "Blues", "Folk", "Metal",
          "R&B", "Soul", "Punk", "Disco", "Funk", "Alternative", "Indie", "Country", "Latin", "Ambient"]

countries = ["USA", "UK", "Canada", "Australia", "Germany", "France", "Sweden", "Japan", "Brazil", "Italy",
             "Netherlands", "Spain", "Norway", "Finland", "Denmark", "Belgium", "Switzerland", "Austria", "Ireland"]

bio_templates = [
    "{} – {}-я группа, основанная в {}. Их музыка сочетает в себе элементы {} и других жанров.",
    "Коллектив {} появился на сцене в {} и быстро завоевал популярность благодаря уникальному стилю в жанре {}.",
    "Группа {} образовалась в {} и стала известна благодаря экспериментам с {}.",
    "{} – проект из {}, созданный в {}. Основное влияние – {}.",
    "Музыканты {} начали свой путь в {} и с тех пор выпустили множество хитов в стиле {}.",
    "{} – одна из самых ярких групп, вышедших из {} в {}. Их звучание определяет {}.",
]

track_list = []
used_combinations = set()
while len(track_list) < NUM_TRACKS:
    artist = random.choice(unique_artists)
    title = f"{random.choice(song_words)} {random.choice(song_words)}" if random.random() > 0.3 else random.choice(song_words)
    if (artist, title) in used_combinations:
        continue
    used_combinations.add((artist, title))
    genre = random.choice(genres)
    duration = random.randint(120, 360)
    popularity = random.randint(30, 100)
    track_list.append((artist, title, genre, duration, popularity))

print(f"Сгенерировано {len(track_list)} треков")

artist_cache = {}
track_count = 0
for artist_name, title, genre, duration, popularity in track_list:
    if artist_name not in artist_cache:
        artist = db.query(Artist).filter_by(name=artist_name).first()
        if not artist:
            country = random.choice(countries)
            formed_year = random.randint(1960, 2020)
            artist_genres_set = {genre}
            extra_genres = random.sample(genres, random.randint(0, 2))
            artist_genres_set.update(extra_genres)
            artist_genres = ", ".join(artist_genres_set)
            template = random.choice(bio_templates)
            bio = template.format(artist_name, country, formed_year, artist_genres.split(',')[0])
            artist = Artist(name=artist_name, bio=bio, country=country, formed_year=formed_year, genres=artist_genres)
            db.add(artist)
            db.flush()
        artist_cache[artist_name] = artist.id
    artist_id = artist_cache[artist_name]
    track = Track(title=title, artist_id=artist_id, genre=genre, duration=duration, popularity=popularity)
    db.add(track)
    track_count += 1
    if track_count % 50 == 0:
        db.commit()
        print(f"  Добавлено {track_count} треков...")
db.commit()
print(f"Добавлено треков: {track_count}")

# Тестовый пользователь
test_user = db.query(User).filter(User.id == 1).first()
if not test_user:
    hashed = User.hash_password('password')
    test_user = User(id=1, username="test", email="test@test.com", hashed_password=hashed, full_name="Test User")
    db.add(test_user)
    print("Создан тестовый пользователь (test/password)")
else:
    print("Тестовый пользователь уже существует")

# Администратор
admin = db.query(User).filter(User.username == 'admin').first()
if not admin:
    hashed = User.hash_password('admin123')
    admin = User(username='admin', email='admin@example.com', hashed_password=hashed, full_name='Administrator')
    db.add(admin)
    print("Создан администратор (admin/admin123)")
else:
    print("Администратор уже существует")
db.commit()

# Генерация взаимодействий для тестового пользователя
all_tracks_db = db.query(Track).all()
track_ids = [t.id for t in all_tracks_db]
user_ids = [1]
interactions = []
for uid in user_ids:
    num_inter = random.randint(10, 30)
    if len(track_ids) < num_inter:
        num_inter = len(track_ids)
    chosen = random.sample(track_ids, num_inter)
    for tid in chosen:
        weight = random.randint(1, 5)
        interactions.append((uid, tid, weight))
for uid, tid, w in interactions:
    inter = Interaction(user_id=uid, track_id=tid, event_type='play', weight=w)
    db.add(inter)
db.commit()
print(f"Сгенерировано {len(interactions)} взаимодействий для тестового пользователя")

# Обучение ALS модели
all_interactions = db.query(Interaction).all()
user_ids_list = list(set(i.user_id for i in all_interactions))
track_ids_list = [t.id for t in all_tracks_db]

if not user_ids_list or not track_ids_list:
    print("Ошибка: нет пользователей или треков для обучения ALS!")
    exit()

user_map = {uid: i for i, uid in enumerate(user_ids_list)}
track_map = {tid: i for i, tid in enumerate(track_ids_list)}

rows = [user_map[i.user_id] for i in all_interactions]
cols = [track_map[i.track_id] for i in all_interactions]
data = [i.weight for i in all_interactions]
user_item_matrix = csr_matrix((data, (rows, cols)), shape=(len(user_ids_list), len(track_ids_list)))

model = implicit.als.AlternatingLeastSquares(factors=10, iterations=15, regularization=0.1, random_state=42)
model.fit(user_item_matrix)

with open('als_model.pkl', 'wb') as f:
    pickle.dump(model, f)
with open('mappings.pkl', 'wb') as f:
    pickle.dump({
        'user_map': user_map,
        'track_map': track_map,
        'user_ids': user_ids_list,
        'track_ids': track_ids_list
    }, f)
save_npz('user_item_matrix.npz', user_item_matrix)

print("✅ Модель ALS обучена и сохранена.")
print(f"   Пользователей: {len(user_ids_list)}")
print(f"   Треков: {len(track_ids_list)}")
print(f"   Взаимодействий: {len(all_interactions)}")