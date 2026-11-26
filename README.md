<div align="center">

# PAVELCRG · ASCII ART

Animated scenes built from characters, color, and motion.

[English](README.md) · [Русский](README.ru.md)

</div>

---

## Gallery

### 01 — Bloom

A flower opens, then scatters into glowing fragments.

![Bloom ASCII animation](artworks/bloom/preview.gif)

[Source code](artworks/bloom/main.py)

### 02 — Butterfly

A chrysalis cracks open, and a butterfly takes flight.

![Butterfly ASCII animation](artworks/butterfly/preview.gif)

[Source code](artworks/butterfly/main.py)

### 03 — Blackhole

A 3D character galaxy collapses into a black hole, flashes, then loops back to the beginning.

![Blackhole ASCII animation](artworks/blackhole/preview.gif)

[Source code](artworks/blackhole/blackhole.py)

### 04 — Eye

A symbol-built eye blinks, then draws the camera into its pupil.

![Eye ASCII animation](artworks/eye/preview.gif)

[Source code](artworks/eye/eye.py)

### 05 — Excalibur

A video-to-ASCII tool that turns a clip you provide into animated character art. It needs an input video, FFmpeg, and FFprobe; no sample video is included.

[Source code](artworks/excalibur/excalibur.py)

## Run

Requires Python 3.10 or newer. From the repository root, create a virtual environment and install the shared dependencies:

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

Run either command from the repository root. The frames will be written beside each piece's source:

```bash
# From the repository root
cd artworks/bloom
python main.py
```

```bash
# From the repository root
cd artworks/butterfly
python main.py
```

Press Space to replay; press Esc to close. The character rendering varies slightly with the system monospace font.

Eye opens a live window. Blackhole can export a video with `python blackhole.py --export blackhole.mp4 --plain`. Excalibur takes a video path, for example `python excalibur.py clip.mp4 --export result.mp4 --to 10`. Video exports need FFmpeg and FFprobe.

## Credits & license

Gallery and presentation by **Pavelcrg**. Bloom and Butterfly, including their original code and artwork, are by **Edward Jones (@edjonesv)** and are included from [his repository](https://github.com/edwardjones7/ascii-art) at commit `4e098f4`.

Blackhole, Eye, and Excalibur were provided by Pavelcrg.

The original MIT notice is preserved in [LICENSE](LICENSE). Pavelcrg's notice covers the gallery presentation and this README.
