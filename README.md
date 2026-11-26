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

## Text study

A small bloom built around the animations' character ramp: `. : ; = + * x o % # & @`.

```text
                    . : ;
               . : + * x * + : .
          . : + x o % # @ # % o x + : .
        ; + x o % # & @ & # % o x + ;
          . : + x o % # @ # % o x + : .
               . : + * x * + : .
                    = | =
                      |
                *=====+=====*
```

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

## Credits & license

Gallery and presentation by **Pavelcrg**. Bloom and Butterfly, including their original code and artwork, are by **Edward Jones (@edjonesv)** and are included from [his repository](https://github.com/edwardjones7/ascii-art) at commit `4e098f4`.

The original MIT notice is preserved in [LICENSE](LICENSE). Pavelcrg's notice covers the gallery presentation and this README.
