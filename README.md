<div align="center">

# PAVELCRG · ASCII ART

**Two small animations, drawn with symbols.**

**Две короткие анимации, нарисованные символами.**

</div>

---

## Works

**Работы**

### 01 — Bloom

**EN:** A flower opens, then scatters into glowing fragments.

**RU:** Цветок раскрывается и разлетается на светящиеся частицы.

![Bloom ASCII animation / ASCII-анимация Bloom](artworks/bloom/preview.gif)

[Source code / Исходный код](artworks/bloom/main.py)

### 02 — Butterfly

**EN:** A chrysalis cracks open; a butterfly takes flight.

**RU:** Кокон трескается, и бабочка отправляется в полёт.

![Butterfly ASCII animation / ASCII-анимация Butterfly](artworks/butterfly/preview.gif)

[Source code / Исходный код](artworks/butterfly/main.py)

## A text sketch

**Текстовый этюд**

**EN:** A little bloom, typed with the same character ramp `. : ; = + * x o % # & @`.

**RU:** Маленький цветок, набранный тем же набором символов `. : ; = + * x o % # & @`.

```text
                  .       .
             :   +  x  +   :
         .   + x o % # % o x +   .
            : o % # @ # % o :
         .   + x o % # % o x +   .
             :   +  x  +   :
                  . | .
                    |
              *-----+-----*
```

## Run

**Запуск**

**EN:** Python 3.10 or newer. Create a virtual environment and install the shared dependencies from the repository root.

**RU:** Нужен Python 3.10 или новее. Создай виртуальное окружение и установи общие зависимости из корня репозитория.

```bash
python -m venv .venv
```

**Windows PowerShell — activate / активация:**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux — activate / активация:**

```bash
source .venv/bin/activate
```

```bash
python -m pip install -r requirements.txt
```

**Run Bloom / запуск Bloom:**

```bash
cd artworks/bloom
python main.py
```

**Run Butterfly / запуск Butterfly:**

```bash
cd artworks/butterfly
python main.py
```

**EN:** Press Space to replay; press Esc to close. The look varies slightly with the system's monospace font.

**RU:** Пробел запускает анимацию заново, Esc закрывает окно. Вид символов немного зависит от моноширинного шрифта системы.

## Credits

**Авторство**

**EN:** Gallery and presentation by Pavelcrg. Bloom and Butterfly, including their original code and artwork, are by **Edward Jones (@edjonesv)** and are included from [his repository](https://github.com/edwardjones7/ascii-art) (commit `4e098f4`). The original MIT notice is preserved. Pavelcrg's notice applies to the gallery presentation and this README.

**RU:** Галерею и её оформление сделал Pavelcrg. Bloom и Butterfly, вместе с оригинальным кодом и изображениями, создал **Edward Jones (@edjonesv)**; работы взяты из [его репозитория](https://github.com/edwardjones7/ascii-art) (commit `4e098f4`). Уведомление об оригинальной лицензии MIT сохранено. Уведомление Pavelcrg относится к оформлению галереи и этому README.

See [LICENSE](LICENSE) / См. [лицензию](LICENSE).
