<div align="right"><a href="README.md">Русский</a> · <a href="README.en.md">English</a></div>

# ASCII-галерея Павла

## Галерея

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>Bloom</h3>
      <p>Цветок раскрывается и рассыпается на светящиеся символы.</p>
      <img src="artworks/bloom/preview.gif" alt="Цветок из символов" loading="lazy" width="320">
      <p><a href="artworks/bloom/main.py">Код</a></p>
    </td>
    <td width="50%" valign="top">
      <h3>Butterfly</h3>
      <p>Бабочка вылетает из кокона.</p>
      <img src="artworks/butterfly/preview.gif" alt="Бабочка из символов" loading="lazy" width="320">
      <p><a href="artworks/butterfly/main.py">Код</a></p>
    </td>
  </tr>
</table>

## Установка

Нужен Python 3.10 или новее. Создай окружение и установи зависимости:

### Windows · PowerShell

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -c "import importlib.util as u; print({m: u.find_spec(m) is not None for m in ('numpy', 'PIL', 'pygame', 'cv2', 'tkinter')})"
```

### macOS · Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c "import importlib.util as u; print({m: u.find_spec(m) is not None for m in ('numpy', 'PIL', 'pygame', 'cv2', 'tkinter')})"
```

В проверке `True` означает, что модуль найден. Для `numpy`, `PIL`, `pygame` или `cv2` при `False` повтори установку зависимостей. Для окон нужен Tkinter; в Ubuntu установи его командой `sudo apt install python3-tk`.

FFmpeg нужен только для экспорта видео. Проверь его командой `ffmpeg -version`; Excalibur также требует `ffprobe -version`. Аудио необязательно, но указанный файл должен существовать.

## Запуск

Запускай из корня репозитория через Python из `.venv`:

- Bloom: `& .\.venv\Scripts\python.exe .\artworks\bloom\main.py`
- Butterfly: `& .\.venv\Scripts\python.exe .\artworks\butterfly\main.py`
- Supernova: `& .\.venv\Scripts\python.exe .\artworks\supernova\supernova.py`
- Train: `& .\.venv\Scripts\python.exe .\artworks\train\train.py`

Для macOS и Linux используй `.venv/bin/python` и пути `artworks/...`.

Supernova и Train открывают окно. Для сохранения видео добавь `--export result.mp4`; нужен FFmpeg в `PATH`. Аудио добавляется отдельно через `--audio track.m4a`. Excalibur требует входное видео, FFmpeg и FFprobe.

## Другие работы

[Blackhole](artworks/blackhole/blackhole.py) · [Eye](artworks/eye/eye.py) · [Excalibur](artworks/excalibur/excalibur.py)
