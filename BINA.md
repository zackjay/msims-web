# Sumber binaan laman MSIMS

Cabang ini menyimpan skrip yang menjana laman. Fail yang disiarkan berada di cabang `beta`
(laman beta) dan kelak `main` (laman sebenar).

## Bina semula

    python3 build.py asas.html keluaran            # beta: noindex
    MSIMS_BETA=0 python3 build.py asas.html keluaran   # go-live: boleh diindeks

Hasil dalam `keluaran/site/`: `index.html` (English), `ms/index.html` (Bahasa Melayu),
`robots.txt`, `sitemap.xml`, `llms.txt`. Salin juga `send.php`, `htaccess.txt` (sebagai
`.htaccess`) dan folder `assets/` daripada cabang `beta`.

## Fail

- `build.py`: templat, teks dwibahasa (`[[English||Melayu]]`), katalog, slaid, soalan lazim, data berstruktur
- `asas.html`: asas gaya dan animasi konsol yang dibaca oleh `build.py`
- `images.json`: senarai saiz gambar yang tersedia dalam `assets/img/`
- `proses_gambar.py`: pangkas, pembetulan ton dan mampatan gambar asal kepada WebP
- `send.php`: penghantar borang pertanyaan
