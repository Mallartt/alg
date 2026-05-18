# Price-Tag Recognition Pipeline

Пайплайн распознавания ценников по видео с робота. На вход принимается MP4, на
выход — CSV в формате `sample.csv` (см. корень репозитория).

## Быстрый старт

### 1. Установить зависимости

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Если вы на macOS — для `pyzbar` понадобится `zbar` из Homebrew:
`brew install zbar`. На Linux: `apt install libzbar0`. На Windows можно работать
без `pyzbar` — пайплайн автоматически переключится на детекторы из OpenCV.

### 2. Скачать веса моделей

Карта файлов (всё в `config.toml`, ничего не нужно вручную править, если положите в дефолтные места):

| Файл                                  | Куда положить                                                                | Статус |
|---------------------------------------|------------------------------------------------------------------------------|--------|
| `best.pt` (YOLOv8, наша дообученная модель) | `pipeline/models/best.pt`. В конфиге `[paths] weights = "models/best.pt"`. | **уже лежит здесь** |
| `db_hack.csv` (справочник)            | На уровень выше `pipeline/`, то есть в корне репозитория. В конфиге `[paths] product_catalog = "../db_hack.csv"`. Файл не коммитим в git (большой), его надо положить вручную. | хранится локально |
| GGUF-веса VLM, напр. `Qwen2.5-VL-7B-Instruct-q5_k_m.gguf` (~5.5 GB) | `pipeline/models/`                                          | скачать с HuggingFace (см. §2.1) |
| `mmproj-*.gguf` (vision-проектор, ~1.35 GB) | `pipeline/models/`                                                  | скачать с HuggingFace, парный файл к GGUF |
| `bytetrack.yaml`                      | ничего не трогать                                                            | идёт внутри `ultralytics` |

> `pipeline/models/best.pt` уже на месте — пайплайн самодостаточен с точки зрения детектора.
> В ту же папку `pipeline/models/` потом положишь GGUF-файлы VLM.

#### Почему именно Qwen2.5-VL

В пайплайне в качестве VLM-«мозга» по умолчанию используется **Qwen2.5-VL** (через её квантованную GGUF-сборку, запущенную на `llama.cpp` сервере). Причины такие:

* **Хорошо читает русский текст и мелкий шрифт** — в отличие от LLaVA / MiniCPM-V более ранних поколений, Qwen2.5-VL стабильно справляется с ценниками, где есть смесь рублей, копеек (мелкие цифры «степенью»), процентов скидки и кириллицы. Это критично, потому что у нас на каждом ценнике есть до 4 разных цен (default / card / discount / wholesale).
* **Высокая точность structured-output** — модель умеет выдавать **строгий JSON** по схеме (`prompt.toml`), что нам нужно, чтобы напрямую раскладывать ответ по колонкам CSV (`product_name`, `price_card`, …). Старые VL-модели часто срывались в «свободный пересказ» картинки.
* **Совместима с `llama.cpp`** — `chat_format=qwen2.5-vl` поддерживается из коробки в `llama-cpp-python`, что позволяет крутить её локально (CPU / GPU) без поднятия отдельного inference-сервера типа vLLM.
* **Лицензия и размер** — есть квантованные варианты 3B/7B (~4–8 ГБ ОЗУ/VRAM), которые помещаются в умеренный сервер; лицензия позволяет использование в проектных задачах.
* **Существующая инфраструктура** — оригинальный proof-of-concept (папка `code/`) уже использовал `chat_format = "qwen2.5-vl"` со сборкой `ZwZ-8B` (это файнтьюн на базе Qwen2.5-VL). Мы оставляем эту же семью, чтобы промпт-схема и поведение OCR-валидации не менялись.

Любую другую OpenAI-совместимую VLM можно подключить, просто заменив `[vlm] base_url` (и, если надо, `chat_format` на стороне сервера). Код пайплайна с VLM общается только через стандартный OpenAI-протокол.

#### Откуда скачать GGUF для VLM

Нужно **два файла**: основные веса + парный `mmproj-…gguf` (vision-проектор; без него модель не сможет смотреть на картинку).

Два проверенных репозитория на HuggingFace:

* **`Mungert/Qwen2.5-VL-7B-Instruct-GGUF`** — рекомендую: имена файлов чистые, без префиксов.
* **`bartowski/Qwen_Qwen2.5-VL-7B-Instruct-GGUF`** — у него в имени файла продублирован префикс `Qwen_`.

Сначала ставим CLI:
```bash
pip install -U "huggingface_hub[cli]"
```

**Вариант 1 (Mungert, рекомендую):**
```bash
huggingface-cli download Mungert/Qwen2.5-VL-7B-Instruct-GGUF \
    Qwen2.5-VL-7B-Instruct-q5_k_m.gguf \
    --local-dir pipeline/models

huggingface-cli download Mungert/Qwen2.5-VL-7B-Instruct-GGUF \
    Qwen2.5-VL-7B-Instruct-mmproj-f16.gguf \
    --local-dir pipeline/models
```

**Вариант 2 (bartowski):** обрати внимание на префикс `Qwen_` в именах:
```bash
huggingface-cli download bartowski/Qwen_Qwen2.5-VL-7B-Instruct-GGUF \
    Qwen_Qwen2.5-VL-7B-Instruct-Q5_K_M.gguf \
    --local-dir pipeline/models

huggingface-cli download bartowski/Qwen_Qwen2.5-VL-7B-Instruct-GGUF \
    mmproj-Qwen_Qwen2.5-VL-7B-Instruct-f16.gguf \
    --local-dir pipeline/models
```

Если оперативки/VRAM мало — берёшь Q4_K_M (~4.7 GB) вместо Q5_K_M (~5.5 GB).

#### Перед запуском сервера: убедись, что вижн-handler есть в твоём wheel

`llama-cpp-python` с PyPI **иногда поставляется без vision-handler-ов** для Qwen2.5-VL. Проверка:

```bash
python -c "from llama_cpp.llama_chat_format import Qwen25VLChatHandler; print('vision OK')"
```

Если получаешь `ImportError`, пересобираем из исходников (один из вариантов):

```bash
# CPU (везде):
CMAKE_ARGS="-DLLAMA_VISION=ON" pip install --upgrade --force-reinstall \
    --no-cache-dir "llama-cpp-python[server,vision]"

# macOS Apple Silicon (быстрее на Metal):
CMAKE_ARGS="-DLLAMA_METAL=ON -DLLAMA_VISION=ON" pip install --upgrade \
    --force-reinstall --no-cache-dir "llama-cpp-python[server,vision]"

# NVIDIA CUDA:
CMAKE_ARGS="-DGGML_CUDA=on -DLLAMA_VISION=ON" pip install --upgrade \
    --force-reinstall --no-cache-dir "llama-cpp-python[server,vision]"
```

#### Запуск llama.cpp сервера локально

Поднимаем сервер **в отдельном терминале** (он работает независимо от пайплайна). Команды отличаются по тому, у какого автора качал файлы.

**Если качал у Mungert:**
```bash
cd pipeline
source .venv/bin/activate

python -m llama_cpp.server \
    --model            models/Qwen2.5-VL-7B-Instruct-q5_k_m.gguf \
    --clip_model_path  models/Qwen2.5-VL-7B-Instruct-mmproj-f16.gguf \
    --chat_format      qwen2.5-vl \
    --n_ctx            4096 \
    --host             0.0.0.0 \
    --port             8000
```

**Если качал у bartowski:**
```bash
cd pipeline
source .venv/bin/activate

python -m llama_cpp.server \
    --model            models/Qwen_Qwen2.5-VL-7B-Instruct-Q5_K_M.gguf \
    --clip_model_path  models/mmproj-Qwen_Qwen2.5-VL-7B-Instruct-f16.gguf \
    --chat_format      qwen2.5-vl \
    --n_ctx            4096 \
    --host             0.0.0.0 \
    --port             8000
```

* `--chat_format` подбирается под модель: для Qwen2-VL → `qwen2-vl`, для Qwen2.5-VL → `qwen2.5-vl`. Список поддерживаемых форматов смотри в `llama_cpp/llama_chat_format.py`.
* Порт `8000` совпадает с `[vlm] base_url = "http://localhost:8000/v1"` в `config.toml`. Если меняешь порт — поправь и конфиг.

#### Про детектор YOLOv8 (`best.pt`)

В качестве детектора ценников используется модель **YOLOv8**, изначально
обученная под общую задачу детекции ценников на полках магазинов
(публичный pretrain, который уже умеет находить ценники в кадре). Мы
**дообучили (fine-tune)** её на нашем датасете: размеченные кадры с
робота, где аннотации проверял и корректировал человек (в частности —
для «поехавших» / скошенных ценников, чтобы детекция оставалась
устойчивой на смазанных и наклонных снимках).

Итоговые веса лежат в `best.pt`. Чтобы поменять модель — положите свой
`.pt` и обновите `[paths] weights` в `config.toml`. Никаких других
изменений не нужно: внутри `PriceTagDetector` модель вызывается через
стандартный `YOLO(...).track(...)`.

### 3. Запустить пайплайн

**Через CLI на видео целиком:**

```bash
python run.py --video /path/to/26_12-20.mp4 --out runtime/outputs/26_12-20.csv
```

**Через HTTP-сервис:**

```bash
python serve.py --port 8080
# затем:
curl -F "video=@26_12-20.mp4" -F "rotation_deg=90" -F "frames_per_second=1.5" \
     http://localhost:8080/jobs/submit
# {"job_id": "...", "status": "queued"}
curl http://localhost:8080/jobs/<job_id>
curl -OJ http://localhost:8080/jobs/<job_id>/result
```

### 4. Запустить только распознавание уже подготовленного кропа

Если у вас есть готовый кроп ценника (картинка) — никакого YOLO не нужно:

```bash
python run_image.py --image crops/some_tag.jpg --out crops/some_tag.csv
```

Выходной CSV будет в том же формате `sample.csv` (с одной строкой).

## Что ещё надо помимо LLama, чтобы пайплайн заработал от MP4 до CSV

1. `pip install -r requirements.txt`.
2. Положить `best.pt` (YOLOv8) — путь прописан в `config.toml → [paths] weights`.
3. Запустить локальный VLM-сервер (`python -m llama_cpp.server …`) на том же
   адресе, что указан в `[vlm] base_url`.
4. (Опционально) Установить `zbar`/`libzbar0` для более точного чтения
   штрихкодов; без него используется только встроенный детектор OpenCV.
5. (Опционально) Подключить камерные коэффициенты — `[lens] enabled = true`,
   если кадры заметно бочат.

После этого `python run.py --video …` уже даст CSV.

## Структура CSV

Колонки строго соответствуют `sample.csv`:

```
filename, product_name, price_default, price_card, price_discount, barcode,
discount_amount, id_sku, print_datetime, code, additional_info, color,
special_symbols, frame_timestamp, x_min, y_min, x_max, y_max, qr_code_barcode,
price1_qr, price2_qr, price3_qr, price4_qr, wholesale_level_1_count,
wholesale_level_1_price, wholesale_level_2_count, wholesale_level_2_price,
action_price_qr, action_code_qr
```

Пустые ячейки заполняются строкой `нет` (как в эталонном `sample.csv`).

## Слепок директорий

```
pipeline/
├── run.py                ← CLI: видео → CSV
├── run_image.py          ← CLI: кроп → CSV
├── serve.py              ← старт FastAPI
├── config.toml           ← все настройки
├── requirements.txt
├── assets/
│   └── prompt.toml       ← промпт VLM в TOML
├── runtime/
│   ├── uploads/          ← сюда сервер кладёт принятые видео
│   ├── outputs/          ← сюда уходят CSV
│   └── tmp/
└── src/
    ├── config_loader.py
    ├── pipeline_runner.py    ← склейка CLI и API
    ├── core/                 ← оркестрация + voting
    ├── stream/               ← сэмплинг кадров, undistort, YOLO+tracker
    ├── crops/                ← геометрия и enhance кропов
    ├── recognize/            ← VLM-клиент, QR/штрихкод, фильтры
    ├── catalog/              ← lookup по db_hack.csv
    ├── export/               ← CSV writer
    └── api/                  ← FastAPI app
```

См. подробное описание в [ARCHITECTURE.md](ARCHITECTURE.md).
