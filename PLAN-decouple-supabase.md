# План: де-прив'язка від Supabase (storage/DB/auth → стандартні сервіси)

Мета: зробити Nesti незалежним від Supabase-інфраструктури, щоб продукт
користувалися будь-де (Vercel, DigitalOcean, AWS, локально).

- **Object storage**: S3-сумісний (вже реалізовано: `S3StorageBackend` через
  aiobotocore; лишити тільки його).
- **База даних**: Postgres (основна) + SQLite (для невеликих каталогів).
- **Аутентифікація**: проста локальна — email+пароль, argon2, підписана
  JWT-кука (HS256 через `secret_key`), без зовнішніх сервісів.
- **Локальний запуск**: Dockerfile + docker-compose (podman-compose) —
  app + postgres + rustfs (S3-сумісне сховище для локального тестування
  та малих каталогів).

## Зафіксовані рішення
- Сесія: підписана JWT-кука (без таблиці сесій).
- Перший адмін: `ADMIN_EMAIL`/`ADMIN_PASSWORD` з env → upsert при старті.
- SQLite: підтримуємо повністю (не лише Postgres).
- Скидання забутих паролів: через адміна (без SMTP).
- 2FA: опційний TOTP (Google Authenticator / Authy тощо), вимкнено за
  замовчуванням, вмикається індивідуально на акаунт; адмін може скинути пароль
  та вимкнути 2FA будь-якому користувачу (включно зі своїм).
- Storage: універсальний S3-контракт — один набір змінних (стандартних AWS)
  для будь-якого об'єктного сховища; без `storage_type`.
- Локальний запуск: Dockerfile + docker-compose.yaml (podman-compose) —
  сервіси `app`, `db` (postgres), `rustfs` (S3); SQLite — опційний профіль.
- Конфігурація: читається з env-змінних АБО з config-файлу (env має пріоритет) —
  один і той самий образ працює в `docker run`, docker-compose та Kubernetes
  (env прямо, або ConfigMap/Secret → env / змонтований файл).
- Захист від перебору: на рівні акаунта — лічильник невдалих спроб у БД
  (портативно для PG/SQLite) з тимчасовим блокуванням; на рівні IP —
  простий in-memory throttle (зауважити про мульти-воркер/множинні інстанси).

## Конфігурація (універсальний підхід)
Єдиний інтерфейс для будь-якого object storage — S3. Ніякого `storage_type`:
наявність AWS-креденшелів визначає, чи увімкнено зберігання.

- **DB**: тільки `DATABASE_URL` — схема визначає драйвер
  (`postgresql+asyncpg://…` → Postgres, `sqlite+aiosqlite://…` → SQLite).
- **Storage** — стандартні імена AWS-змінних (їх споконвічно читає
  boto3/aiobotocore/aws-cli):
  - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — креденші (одні на всі сховища)
  - `AWS_DEFAULT_REGION` (default `us-east-1`)
  - `AWS_ENDPOINT_URL` (аліас `S3_ENDPOINT_URL`) — endpoint;
    для rustfs/minio/supabase; пустий = класичний AWS
  - `S3_BUCKET_NAME` — бакет (нестандартна, наша)
  - `S3_FORCE_PATH_STYLE` (default `true`) — path-style для rustfs/minio/supabase
- Провайдери відрізняються лише значенням endpoint (і, де треба, path-style) —
  конфіг уніфікований.

### Джерела конфігурації (пріоритет ↓)
1. **env-змінні середовища** (головне джерело; docker, compose, Kubernetes —
   ConfigMap/Secret → `env`).
2. **Config-файл** (`.env`, шлях можна змінити через `SETTINGS_FILE`) —
   опційний, зручний для локального запуску та змонтованого файлу в pod/K8s.
3. **Дефолти** в `app/config.py`.

Реалізація — `pydantic-settings`: `SettingsConfigDict(env_file=<SETTINGS_FILE або
.env>)` — це дає «файл АБО env» з пріоритетом env одразу, без зайвого коду.
Один-єдиний образ: у docker-compose значення можна передати і в `.env`
(`environment` або `env_file:`), і в Kubernetes (маніфест з `env`/`envFrom`)

---

## Фаза 1 — Залежності та конфіг ✅
- `pyproject.toml`: **додано** `pwdlib[argon2]`, `aiosqlite`, `pyotp` (+ mypy-overrides);
  `supabase` і `supabase.*`-override прибираються у Фазі 4 (код ще його використовує).
- `app/config.py`: **додано** `admin_email`, `admin_password`, security-поля
  (`login_max_attempts=5`, `login_lockout_seconds=900`, `ip_throttle_per_minute=20`),
  AWS-стандартні storage-поля (з аліасами на старі `S3_*`), `SETTINGS_FILE`.
  `supabase_*`-поля лишаються до Фази 4 (auth ще на Supabase) — адитивний PR.
- Config file: **реалізовано** `SETTINGS_FILE` (шлях до config-файлу, default `.env`).
- `.env.example`: оновлено новими змінними.

## Фаза 1.5 — Config-файл та оркестрація ✅
- `SETTINGS_FILE` підтримується в `get_settings()`; smoke-перевірка підтверджує
  пріоритет env > файл > дефолти (перевірено вручну).

## Фаза 2 — Storage: лишити тільки S3 ✅
- `app/media/storage.py`: **видалено** `SupabaseStorageBackend`; фабрика повертає
  `S3StorageBackend`, без креденшів — чіткий `RuntimeError`.
- `_client_kwargs()`: стандартні AWS-поля; `endpoint_url` = `aws_endpoint_url`
  (порожній → класичний AWS); `addressing_style` керується `s3_force_path_style`.
- `s3_enabled` = наявність `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`.
- `tests/unit/test_storage.py`: тести Supabase-бекенду видалено, оновлено під
  нові поля.

## Фаза 3 — БД: Postgres + SQLite
- `app/db/base.py`: `postgresql.UUID` → портативний `sa.Uuid`.
- `app/db/engine.py`: драйвер за URL (`postgres`→asyncpg, `sqlite`→aiosqlite);
  для SQLite — `PRAGMA foreign_keys=ON` + StaticPool;
  прибрати supabase-хак `ssl=require`; створити директорію для SQLite-файлу.
- `migrations/versions/5ddce1d4cc9b`: прибрати `postgresql_nulls_not_distinct=False`.
- Нова міграція: `users` — drop `supabase_id`, add `password_hash` (nullable),
  `totp_secret` (nullable TEXT; наявність = 2FA увімкнено), `failed_login_attempts`
  (int, default 0), `locked_until` (nullable DateTimeUTC) для анти-брутфорсу.
- `app/users/models.py` (`password_hash` замість `supabase_id`, + `totp_secret`),
  `schemas.py` (без виводу `totp_secret`),
  `service.py` (`get_user_by_email`, `set_password`, `set_totp_secret`,
  `clear_totp_secret`, `register_failed_login`, `reset_login_attempts`,
  `is_account_locked`; прибрати `ensure_user_exists`).

## Фаза 4 — Локальний auth
- `app/auth/service.py` (переписати): `hash_password`/`verify_password` (argon2),
  `create_session_token`/`verify_session_token` (HS256 JWT, `sub` = user.id, exp 7 дн.),
  TOTP: `generate_totp_secret` / `totp_uri(email, secret)` / `verify_totp(secret, code)`
  на `pyotp.TOTP(secret, interval=30, digits=6)`,
  `bootstrap_admin(db)` (upsert з env), dataclass `AuthUser(user_id, email)`.
  Видалити весь Supabase API-шар.
- `app/auth/middleware.py`: одна кука `nesti_session`; `set_session`/`get_session`
  на своєму токені; прибрати refresh-логіку.
- `app/auth/routes.py`: login POST перевіряє пароль локально; видалити
  `/login/supabase` та `/callback`. **2FA-потік**: після правильного пароля, якщо
  у користувача є `totp_secret` — не видавати куку одразу, а повертати форму
  «ввести код» (крок 2) із короткочасним підписаним тимчасовим токеном
  (`pending_2fa`, exp ~5 хв., прив'язаний до user.id); POST коду верифікує
  `verify_totp` → видає `nesti_session`. Якщо 2FA вимкнена — кука одразу.
- **Анти-брутфорс** (пароль і 2FA-крок): перед login перевіряємо
  `is_account_locked()` (`locked_until` у майбутньому → відмова 423/429, не
  доходячи до хешування — це економить CPU і не дає таймінг-сигналу).
  Невірний пароль → `register_failed_login()` (інкремент `failed_login_attempts`;
  на досягненні `login_max_attempts` — встановити `locked_until` = now +
  `login_lockout_seconds`). Успішний пароль/2FA → `reset_login_attempts()`.
  Помилка на OTP-кроці теж лічиться в `failed_login_attempts` того ж юзера;
  `pending_2fa` — ім'yя токена, прив'язане до конкретного юзера, не дає
  brute-force на інших. Увесь лічильник — у БД (спільний для всіх інстансів).
- **IP-throttle** (опційно, окремо від акаунта): `ip_throttle_per_minute`
  запитів login з однієї IP — простий sliding-window у пам'яті процесу
  (dict[ip] → list[timestamps]); достатньо для одного контейнера, для
  K8s/декількох реплік це не глобально — відмітити в документації (потребує
  Redis/зовнішнього сторджу, в першу чергу покладаємось на anti-bruteforce
  по акаунту в БД).
- **Введення коду 2FA — «комірковий» OTP-input (як на популярних сайтах)**:
  одна справжня (реальна для форми й автозаповнення) скрита `<input>`
  з `inputmode="numeric"`, `autocomplete="one-time-code"`, `maxlength=6`,
  `pattern="\d{6}"` + шість візуальних комірок поверх неї (одна цифра в одній).
  Реалізація — Alpine.js (вже в `base.html`):
  - значення скритої інпут-поля розбивається на 6 комірок реактивно
    (одне джерело правди — реальний інпут, комірки — лише відображення);
  - фокус/каретка — на реальному інпуті, активна комірка підсвічується
    (Autofocus на відкритті форми);
  - **Paste/Ctrl-V/вставити (десктоп і мобільний/PWA)**: один `paste`-обробник
    → з тексту буфера лишаються лише цифри → вставляються в інпут → всі комірки
    заповнюються миттєво і одразу сабмітиться форма (не треба тиснути по комірочках);
  - посимвольне введення: цифра → наступна комірка стає активною; Backspace —
    попередня; літеру/не-цифру ігноруємо;
  - по досягненні 6 цифр — авто-сабміт форми на перевірку коду;
- 2FA-налаштування у профілі (`templates/users/2fa.html`): увімкнути →
  `generate_totp_secret` + показати QR (inline SVG через `qrcode`, без Pillow)
  і `otpauth://totp/Nesti:<email>?secret=…&issuer=Nesti` + текстовий secret
  (ручне введення); підтвердження — ввести поточний код (секрет зберігається
  лише після успішної перевірки). Вимкнути → підтвердження паролем/кодом
  видаляє `totp_secret`.
- `app/dependencies.py`, `app/main.py`: `get_current_user` шукає користувача за
  `user_id` з токена; перенести bootstrap-адміна в `lifespan`; прибрати
  `try_refresh_session`.
- `app/users/routes.py`: створення/зміна пароля → хеш у БД; **адмін-операції**:
  скинути пароль користувачу та вимкнути його 2FA (`clear_totp_secret`);
  розблокувати (скинути `failed_login_attempts`/`locked_until`);
  видалення — тільки з БД.
- `templates/auth/login.html`, `templates/users/*`: прибрати Supabase-згадки
  (перевірити grep'ом); додати форму коду другого кроку та налаштування 2FA.

## Фаза 5 — Тести та документація
- Переписати `tests/unit/test_auth.py` (login/verify/bootstrap), адаптувати
  `test_admin.py` та що звертається до `ensure_user_exists`/`AuthUser(supabase_id=…)`.
- Додати тести 2FA: вмикання (запит секрету → підтвердження кодом), логін з 2FA
  (крок 1 пароль → крок 2 код; невірний код → 401, короткотривалий тимчасовий
  токен), вимкнення адміном та самим користувачем; `totp_secret` не світиться в API.
- Додати тести анти-брутфорсу: 5 невдалих паролів → акаунт заблокований → 429;
  після lockout-часу спроби дозволені знову; успішний вхід скидає лічильник;
  невірний 2FA-код теж інкрементує; адмін-розблокування працює.
- Прогнати: ruff, mypy, pytest (SQLite як швидкий шлях; PG — валідація міграцій).
- Оновити `README.md` / `ARCHITECTURE.md`: деплой у DO/AWS/Vercel/local — це просто
  `DATABASE_URL` + `AWS_*` (+ `AWS_ENDPOINT_URL` за потреби, `S3_BUCKET_NAME`)
  + `SECRET_KEY` + `ADMIN_EMAIL/ADMIN_PASSWORD`; опційно `LOGIN_MAX_ATTEMPTS` /
  `LOGIN_LOCKOUT_SECONDS` / `IP_THROTTLE_PER_MINUTE` для анти-брутфорсу.
- Оновити `.env.example` (якщо є) тими самими змінними.

## Фаза 6 — Деплой та валідація
- Оновити Vercel env: `DATABASE_URL` (тепер сам має містити `?sslmode=require`),
  прибрати `SUPABASE_*`, додати `ADMIN_EMAIL`/`ADMIN_PASSWORD`.
- Commit+push → перевірити на проді: логін адміна, фото продовжують віддаватися
  через S3, CRUD предметів/користувачів.

## Фаза 7 — Docker / локальний запуск
- `Dockerfile`: Python 3.13-slim; встановлення залежностей з `pyproject.toml`;
  копіювання `app/`, `migrations/`, `static/`, `templates/`; запуск
  `uvicorn app.main:app`; `HEALTHCHECK` на `/health`; non-root користувач.
- `.dockerignore` (виключити `.venv`, `.git`, `tests`, `*.db`, кеш).
- Контейнер «один для всіх середовищ»: конфіг — лише через env/`SETTINGS_FILE`;
  в Kubernetes той самий образ: ConfigMap/Secret → `env` (або змонтований файл
  конфігу на шлях `SETTINGS_FILE`). Жодних build-аргументів для налаштувань.
- `docker-compose.yaml` (сумісний із podman-compose):
  - `app`: build з Dockerfile, порт `8000`, `depends_on` → `db` (healthy) + `rustfs`,
    env береться з `.env`.
  - `db` (`postgres:16-alpine`): volume `pgdata`, env
    `POSTGRES_USER/PASSWORD/DB`, healthcheck `pg_isready`.
  - `rustfs` (`rustfs/rustfs:latest`): S3 API на `9000`, консоль на `9001`,
    volume `rustfs-data`; env `RUSTFS_ACCESS_KEY/SECRET_KEY/ADDRESS/CONSOLE_*`;
    пермісія директорій під UID `10001`; healthcheck `/health`.
  - Профіль `sqlite`: `DATABASE_URL=sqlite+aiosqlite:///./data/nesti.db`,
    сервіс `db` не потрібен.
  - S3-реквізити спільно для app і rustfs:
    `AWS_ENDPOINT_URL=http://rustfs:9000`,
    `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` (=`RUSTFS_ACCESS_KEY`/`RUSTFS_SECRET_KEY`),
    `S3_BUCKET_NAME=inventory-images`, `S3_FORCE_PATH_STYLE=true` (path-style —
    вже в `storage.py`).
- Ініціалізація: під час старту `run_migrations()` на обрану БД; створення
  бакету `inventory-images` — auto-ensure у `S3StorageBackend` на старті або
  init-container.
- Документація в `README.md`: розділ «Локальний запуск» — `podman-compose up -d`,
  дефолтні креденші rustfs (`rustfsadmin`), створення бакету, доступ на
  `http://localhost:8000`, адмін-бутстрап із `ADMIN_EMAIL`/`ADMIN_PASSWORD`.
- Розділ «Конфігурація» в `README.md`: як передавати налаштування
  (env / `.env` / `SETTINGS_FILE`) для `docker run`, docker-compose і Kubernetes
  (приклад: створення `Secret` + `envFrom` у pod).

## Ризики/нюанси
- Існуючі користувачі prod лишаються (email/роль), але паролі заново
  (адмін-скидання); адмін `admin@brun.if.ua` отримає пароль з `ADMIN_PASSWORD`
  при першому старті.
- Вихід лише «локальний» (кука); деактивованого користувача блокує перевірка
  `is_active` при кожному запиті.
- `totp_secret` зберігається відкритим текстом у БД (стандартна практика для
  TOTP; можна шифрувати `secret_key`-ом як опцію пізніше).
- Втрачений автентифікатор/пристрій → відновлення лише через адміна
  (скидання пароля або вимкнення 2FA); recovery-коди не плануємо (запит).
- `pyotp` відраховує час — важливо синхронізовані годинники сервера; додаємо
  ±1 крок (drift) до перевірки коду.
- Лічильник спроб — у БД з 1+ інстанс спільний; IP-throttle лише per-instance
  (задокументований ліміт для K8s). Загалом: username enumeration — login
  відповідає однаково часово для неіснуючого email / невірного пароля.