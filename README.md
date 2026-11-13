# 🌱 BOTANIQ

### Platform Web untuk Identifikasi Penyakit Tanaman

BOTANIQ merupakan aplikasi berbasis web yang dikembangkan sebagai bagian
dari proyek skripsi. Aplikasi ini dibangun menggunakan Python dan Flask,
serta mengintegrasikan model deep learning berformat Keras untuk
mendukung proses identifikasi penyakit tanaman melalui citra.

> **Catatan:** Deskripsi fitur dan teknologi di bawah disusun
> berdasarkan struktur folder project yang terlihat. Sesuaikan kembali
> nama tanaman, kelas penyakit, metode/model, dan fitur setelah
> memeriksa kode serta hasil penelitian.

------------------------------------------------------------------------

## 📌 Tentang BOTANIQ

BOTANIQ dirancang untuk membantu pengguna melakukan identifikasi
penyakit tanaman melalui gambar. Pengguna dapat mengunggah citra tanaman
melalui website, kemudian aplikasi memproses citra tersebut menggunakan
model yang telah dilatih dan menampilkan hasil prediksi.

Project ini menggunakan Flask sebagai framework aplikasi web. Proses
inferensi model dipisahkan dalam file `inference.py`, sedangkan halaman
website dikelola melalui folder `templates` dan aset pendukung disimpan
di folder `static`.

## ✨ Fitur

-   **Unggah Gambar** --- Pengguna dapat memasukkan gambar tanaman untuk
    dianalisis.
-   **Prediksi Berbasis Model** --- Aplikasi menghubungkan website
    dengan model Deep Learning.
-   **Antarmuka Website** --- Halaman aplikasi disajikan melalui Flask dan
    template HTML.
-   **Penyimpanan Data** --- Project menyediakan database SQLite
    (`botaniq.db`), sesuai implementasi aplikasi.

*Rincian fitur, jenis tanaman, kelas penyakit, dan informasi hasil
prediksi perlu disesuaikan dengan implementasi final.*

## 🧰 Teknologi

  Teknologi               Kegunaan
  ----------------------- --------------------------------------
  Python                  Bahasa pemrograman utama
  Flask                   Framework aplikasi web
  Keras                   Format/integrasi model deep learning
  SQLite                  Database lokal
  HTML, CSS, JavaScript   Antarmuka website

## 📁 Struktur Project

``` text
BOTANIQ/
├── app.py                 # Program utama aplikasi Flask
├── inference.py           # Proses inferensi/prediksi model
├── test_infer.py          # Script pengujian inferensi
├── skenario3.keras        # File model Deep Learning
├── botaniq.db             # Database SQLite 
├── contoh.jpg             # Gambar Contoh
├── static/                # CSS, JavaScript, dan Konten Website
├── templates/             # Template halaman HTML
├── requirements.txt       # Daftar dependensi Python
├── .gitignore             # Daftar file yang tidak diunggah
└── README.md              # Dokumentasi project
```

## ⚙️ Persyaratan

Sebelum menjalankan aplikasi, siapkan:

-   Python versi yang kompatibel dengan library yang digunakan project.
-   Git.
-   Virtual environment Python.
-   File model `skenario3.keras` dan file pendukung lain yang diperlukan
    aplikasi.

Periksa versi Python dan TensorFlow/Keras yang digunakan saat
pengembangan agar kompatibel, khususnya jika menjalankan project pada
Mac dengan Apple Silicon.

## 🚀 Instalasi dan Menjalankan Aplikasi

### 1. Clone repository

Ganti `<URL-REPOSITORY>` dengan URL repository GitHub BOTANIQ.

``` bash
git clone <URL-REPOSITORY>
cd Botaniq-Plant-Disease-Detection
```

### 2. Buat Virtual Environment

**macOS / Linux**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows**

``` bash
py -m venv .venv
.venv\Scripts\activate
```

### 3. Pasang Dependensi

Jika file `requirements.txt` sudah tersedia:

``` bash
pip install -r requirements.txt
```

Jika belum tersedia, buat file tersebut berdasarkan seluruh library yang
benar-benar diimpor oleh `app.py` dan `inference.py`. Hindari menebak
versi library karena TensorFlow/Keras perlu disesuaikan dengan
lingkungan pengembangan.

### 4. Siapkan File Dibutuhkan

Pastikan file model `skenario3.keras` berada di lokasi yang sesuai
dengan path yang dipanggil oleh `inference.py` atau `app.py`. Siapkan
juga konfigurasi database jika aplikasi membutuhkannya.

### 5. Jalankan Aplikasi

``` bash
python app.py
```

Buka alamat lokal yang ditampilkan di Terminal (umumnya
`http://127.0.0.1:5000`) melalui browser.

> Jangan gunakan `debug=True` untuk deployment publik. Mode debug hanya
> untuk pengembangan lokal.

## 🧪 Pengujian

Project menyediakan script `test_infer.py` untuk pengujian proses
inferensi. Jalankan dari direktori utama project:

``` bash
python test_infer.py
```

Pastikan dependensi, file model, dan gambar uji yang diperlukan sudah
tersedia. Sesuaikan perintah ini jika script membutuhkan argumen
tambahan.

## 🧠 Model Deep Learning

File model yang terlihat pada struktur project:

``` text
skenario3.keras
```