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
  <tr>
    <td width="50%" valign="top">
      <h3>Blackhole</h3>
      <p>Галактика из символов сжимается в чёрную дыру.</p>
      <img src="artworks/blackhole/preview.gif" alt="Чёрная дыра из символов" loading="lazy" width="320">
      <p><a href="artworks/blackhole/blackhole.py">Код</a></p>
    </td>
    <td width="50%" valign="top">
      <h3>Eye</h3>
      <p>Глаз из символов моргает и затягивает сцену в зрачок.</p>
      <img src="artworks/eye/preview.gif" alt="Глаз из символов" loading="lazy" width="320">
      <p><a href="artworks/eye/eye.py">Код</a></p>
    </td>
  </tr>
</table>

## Инструмент

**Excalibur** превращает видео в ASCII-анимацию. Нужны FFmpeg и FFprobe; исходное видео не включено.

[Код](artworks/excalibur/excalibur.py)

## Установка и запуск

Нужен Python 3.10 или новее.

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

Для запуска другой работы укажи её скрипт вместо `artworks/bloom/main.py`.

## Авторство

Bloom и Butterfly создал [Edward Jones (@edjonesv)](https://github.com/edwardjones7/ascii-art), commit `4e098f4`. Лицензия — [MIT](LICENSE).
