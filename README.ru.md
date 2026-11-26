<div align="center">

# ASCII-галерея

**Маленькие миры, нарисованные символами.**

[English](README.md) · [Русский](README.ru.md)

</div>

---

## Галерея

Нажми на изображение, чтобы открыть анимацию.

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>Bloom</h3>
      <a href="artworks/bloom/preview.gif"><img src="artworks/bloom/thumbnail.png" width="360" alt="Цветок из светящихся символов"></a>
      <p>Цветок раскрывается и рассыпается на светящиеся частицы.</p>
      <a href="artworks/bloom/preview.gif">▶ Анимация</a> · <a href="artworks/bloom/main.py">Код</a>
    </td>
    <td width="50%" valign="top">
      <h3>Butterfly</h3>
      <a href="artworks/butterfly/preview.gif"><img src="artworks/butterfly/thumbnail.png" width="360" alt="Бабочка из синих символов"></a>
      <p>Кокон раскрывается, и бабочка отправляется в полёт.</p>
      <a href="artworks/butterfly/preview.gif">▶ Анимация</a> · <a href="artworks/butterfly/main.py">Код</a>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>Blackhole</h3>
      <a href="artworks/blackhole/preview.gif"><img src="artworks/blackhole/thumbnail.png" width="360" alt="Чёрная дыра среди звёзд из символов"></a>
      <p>Галактика из символов сжимается в чёрную дыру.</p>
      <a href="artworks/blackhole/preview.gif">▶ Анимация</a> · <a href="artworks/blackhole/blackhole.py">Код</a>
    </td>
    <td width="50%" valign="top">
      <h3>Eye</h3>
      <a href="artworks/eye/preview.gif"><img src="artworks/eye/thumbnail.png" width="360" alt="Глаз из символов тёплых оттенков"></a>
      <p>Внимательный глаз моргает и затягивает сцену в зрачок.</p>
      <a href="artworks/eye/preview.gif">▶ Анимация</a> · <a href="artworks/eye/eye.py">Код</a>
    </td>
  </tr>
</table>

## Инструмент

**Excalibur** превращает выбранный видеофрагмент в ASCII-анимацию. Нужны FFmpeg и FFprobe; примера видео в проекте нет.

[Исходный код](artworks/excalibur/excalibur.py)

## Быстрый запуск

Нужен Python 3.10 или новее.

```bash
python -m venv .venv
```

Активируй виртуальное окружение:

```powershell
.venv\Scripts\Activate.ps1
```

```bash
source .venv/bin/activate
```

Установи зависимости:

```bash
python -m pip install -r requirements.txt
```

Запусти работу из её папки. Например:

```bash
cd artworks/bloom
python main.py
```

Eye открывает окно с анимацией. Blackhole умеет сохранять видео командой `python blackhole.py --export blackhole.mp4 --plain`. Excalibur принимает путь к видео, например `python excalibur.py clip.mp4 --export result.mp4 --to 10`.

## Авторство и лицензия

Bloom и Butterfly, включая оригинальный код и изображения, создал [Edward Jones (@edjonesv)](https://github.com/edwardjones7/ascii-art) (commit `4e098f4`). Оригинальное уведомление о лицензии MIT сохранено в [LICENSE](LICENSE).
