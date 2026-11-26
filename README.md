<div align="right">
<strong>pavelcrg</strong> <sub>· ASCII ART</sub> &nbsp; <a href="README.md">EN</a> / <a href="README.ru.md">RU</a>
</div>

<table>
  <tr>
    <td width="50%" valign="top">
      <details>
        <summary><strong>Bloom</strong> · A flower made of light</summary>
        <br>
        <img src="artworks/bloom/preview.gif" alt="A glowing ASCII flower opening" loading="lazy" width="100%">
        <p><a href="artworks/bloom/main.py">Source</a></p>
      </details>
    </td>
    <td width="50%" valign="top">
      <details>
        <summary><strong>Butterfly</strong> · A flight in symbols</summary>
        <br>
        <img src="artworks/butterfly/preview.gif" alt="A butterfly formed from blue characters" loading="lazy" width="100%">
        <p><a href="artworks/butterfly/main.py">Source</a></p>
      </details>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <details>
        <summary><strong>Blackhole</strong> · A galaxy folding inward</summary>
        <br>
        <img src="artworks/blackhole/preview.gif" alt="A black hole surrounded by character-built stars" loading="lazy" width="100%">
        <p><a href="artworks/blackhole/blackhole.py">Source</a></p>
      </details>
    </td>
    <td width="50%" valign="top">
      <details>
        <summary><strong>Eye</strong> · A gaze drawn in glyphs</summary>
        <br>
        <img src="artworks/eye/preview.gif" alt="An eye made from warm-colored characters" loading="lazy" width="100%">
        <p><a href="artworks/eye/eye.py">Source</a></p>
      </details>
    </td>
  </tr>
</table>

<details>
  <summary><strong>Excalibur</strong> · Video to ASCII</summary>
  <p>Converts a video clip you provide. Requires FFmpeg and FFprobe; no sample clip is included.</p>
  <a href="artworks/excalibur/excalibur.py">Source</a>
</details>

## Run

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

Use the `.venv` interpreter to run the other scripts listed above.

## Credits

Bloom and Butterfly are by [Edward Jones (@edjonesv)](https://github.com/edwardjones7/ascii-art) (commit `4e098f4`). See [LICENSE](LICENSE).
