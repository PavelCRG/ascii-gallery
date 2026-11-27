<div align="right"><a href="README.md">Русский</a> · <a href="README.en.md">English</a></div>

# Pavel's ASCII Gallery

## Gallery

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>Bloom</h3>
      <p>A flower opens and scatters into glowing characters.</p>
      <img src="artworks/bloom/preview.gif" alt="A flower made of characters" loading="lazy" width="320">
      <p><a href="artworks/bloom/main.py">Source</a></p>
    </td>
    <td width="50%" valign="top">
      <h3>Butterfly</h3>
      <p>A butterfly takes flight from its chrysalis.</p>
      <img src="artworks/butterfly/preview.gif" alt="A butterfly made of characters" loading="lazy" width="320">
      <p><a href="artworks/butterfly/main.py">Source</a></p>
    </td>
  </tr>
</table>

## Install

Requires Python 3.10 or newer. Create a virtual environment and install dependencies:

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

`True` means a module is available. If `numpy`, `PIL`, `pygame`, or `cv2` is `False`, install the dependencies again. Windowed mode needs Tkinter; on Ubuntu, install it with `sudo apt install python3-tk`.

FFmpeg is only needed for video export. Check it with `ffmpeg -version`; Excalibur also needs `ffprobe -version`. Audio is optional, but the supplied file must exist.

## Run

Run scripts from the repository root with the `.venv` Python interpreter:

- Bloom: `& .\.venv\Scripts\python.exe .\artworks\bloom\main.py`
- Butterfly: `& .\.venv\Scripts\python.exe .\artworks\butterfly\main.py`
- Supernova: `& .\.venv\Scripts\python.exe .\artworks\supernova\supernova.py`
- Train: `& .\.venv\Scripts\python.exe .\artworks\train\train.py`

On macOS and Linux, use `.venv/bin/python` with paths under `artworks/`.

Supernova and Train open a window. Add `--export result.mp4` to save a video; FFmpeg must be on `PATH`. Add audio with `--audio track.m4a`. Excalibur needs an input video, FFmpeg, and FFprobe.

## Other projects

[Blackhole](artworks/blackhole/blackhole.py) · [Eye](artworks/eye/eye.py) · [Excalibur](artworks/excalibur/excalibur.py)
