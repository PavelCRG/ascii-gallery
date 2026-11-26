<div align="center">

# pavelcrg · ASCII ART

**Символы в движении.**

[English](README.md) · [Русский](README.ru.md)

</div>

<table>
  <tr>
    <td width="50%" valign="top">
      <details>
        <summary><strong>Bloom</strong> · Цветок из света</summary>
        <br>
        <img src="artworks/bloom/preview.gif" alt="Светящийся ASCII-цветок раскрывается" loading="lazy" width="100%">
        <p><a href="artworks/bloom/main.py">Код</a></p>
      </details>
    </td>
    <td width="50%" valign="top">
      <details>
        <summary><strong>Butterfly</strong> · Полёт из символов</summary>
        <br>
        <img src="artworks/butterfly/preview.gif" alt="Бабочка из синих символов" loading="lazy" width="100%">
        <p><a href="artworks/butterfly/main.py">Код</a></p>
      </details>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <details>
        <summary><strong>Blackhole</strong> · Галактика схлопывается внутрь</summary>
        <br>
        <img src="artworks/blackhole/preview.gif" alt="Чёрная дыра среди звёзд из символов" loading="lazy" width="100%">
        <p><a href="artworks/blackhole/blackhole.py">Код</a></p>
      </details>
    </td>
    <td width="50%" valign="top">
      <details>
        <summary><strong>Eye</strong> · Взгляд из символов</summary>
        <br>
        <img src="artworks/eye/preview.gif" alt="Глаз из символов тёплых оттенков" loading="lazy" width="100%">
        <p><a href="artworks/eye/eye.py">Код</a></p>
      </details>
    </td>
  </tr>
</table>

<details>
  <summary><strong>Excalibur</strong> · Видео в ASCII</summary>
  <p>Преобразует выбранный видеофрагмент. Нужны FFmpeg и FFprobe; примера видео нет.</p>
  <a href="artworks/excalibur/excalibur.py">Код</a>
</details>

## Запуск

Python 3.10+.

### Windows · PowerShell

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe .\artworks\bloom\main.py
```

### macOS · Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python artworks/bloom/main.py
```

Для запуска остальных работ используй Python из `.venv` и путь к нужному скрипту выше.

## Авторство

Bloom и Butterfly создал [Edward Jones (@edjonesv)](https://github.com/edwardjones7/ascii-art) (commit `4e098f4`). См. [LICENSE](LICENSE).
