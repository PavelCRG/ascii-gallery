<div align="center">

# PAVELCRG · ASCII ART

Анимации, собранные из символов, цвета и движения.

[English](README.md) · [Русский](README.ru.md)

</div>

---

## Галерея

### 01 — Bloom

Цветок раскрывается и разлетается на светящиеся частицы.

![ASCII-анимация Bloom](artworks/bloom/preview.gif)

[Исходный код](artworks/bloom/main.py)

### 02 — Butterfly

Кокон трескается, и бабочка отправляется в полёт.

![ASCII-анимация Butterfly](artworks/butterfly/preview.gif)

[Исходный код](artworks/butterfly/main.py)

### 03 — Blackhole

Трёхмерная галактика из символов сжимается в чёрную дыру, вспыхивает и возвращается к началу.

![ASCII-анимация Blackhole](artworks/blackhole/preview.gif)

[Исходный код](artworks/blackhole/blackhole.py)

### 04 — Eye

Глаз из символов моргает и затягивает камеру в зрачок.

![ASCII-анимация Eye](artworks/eye/preview.gif)

[Исходный код](artworks/eye/eye.py)

### 05 — Excalibur

Инструмент превращает выбранное видео в ASCII-анимацию. Нужны входной видеофайл, FFmpeg и FFprobe; пример видео не включён.

[Исходный код](artworks/excalibur/excalibur.py)

## Запуск

Нужен Python 3.10 или новее. Создай виртуальное окружение и установи общие зависимости из корня репозитория:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

```bash
python -m pip install -r requirements.txt
```

Запускай каждую работу из её папки, чтобы записанные кадры оставались рядом с исходным кодом:

```bash
# Из корня репозитория
cd artworks/bloom
python main.py
```

```bash
# Из корня репозитория
cd artworks/butterfly
python main.py
```

Нажми пробел, чтобы запустить анимацию заново; `Esc` закрывает окно. Вид символов немного зависит от моноширинного шрифта системы.

Eye открывает окно с анимацией. Blackhole экспортирует видео командой `python blackhole.py --export blackhole.mp4 --plain`. Excalibur принимает путь к видео, например `python excalibur.py clip.mp4 --export result.mp4 --to 10`. Для экспорта видео нужны FFmpeg и FFprobe.

## Авторство и лицензия

Галерею и её оформление собрал **Pavelcrg**. Bloom и Butterfly, включая оригинальный код и изображения, создал **Edward Jones (@edjonesv)**; работы взяты из [его репозитория](https://github.com/edwardjones7/ascii-art), commit `4e098f4`.

Blackhole, Eye и Excalibur предоставлены Pavelcrg.

Оригинальное уведомление о лицензии MIT сохранено в [LICENSE](LICENSE). Уведомление Pavelcrg относится к оформлению галереи и этому README.
