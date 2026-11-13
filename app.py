# 1.) import library yang dibutuhkan untuk menjalankan aplikasi flask, database, upload file, RSS, dan klasifikasi gambar
import os
import re
import time
import html

import feedparser
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from urllib.parse import quote_plus

from inference import predict_image
import sqlite3
from functools import wraps
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


# 2.) inisialisasi aplikasi flask dan konfigurasi session
app = Flask(__name__)
app.secret_key = "botaniq-dev"


# 3.) konfigurasi database SQLite
DB_NAME = "botaniq.db"


def get_db():
    # membuka koneksi ke database dan mengatur hasil query agar bisa diakses seperti dictionary
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# 4.) data koordinat kecamatan di Kabupaten Blora untuk kebutuhan peta dashboard analisis
KOORDINAT = {
    "Blora": [-6.9696, 111.4180],
    "Cepu": [-7.1470, 111.5900],
    "Randublatung": [-7.1913, 111.3835],
    "Ngawen": [-7.0085, 111.2910],
    "Jepon": [-6.9968, 111.4632],
    "Sambong": [-7.0515, 111.5213],
    "Jati": [-7.3043, 111.4450],
    "Banjarejo": [-6.9862, 111.3315],
    "Tunjungan": [-6.9840, 111.3847],
    "Kedungtuban": [-7.1487, 111.5212],
    "Kradenan": [-7.2332, 111.5710],
    "Bogorejo": [-6.9975, 111.2978],
    "Japah": [-7.1435, 111.3137],
    "Kunduran": [-7.0203, 111.2605],
    "Todanan": [-6.9932, 111.2541],
    "Jiken": [-6.9337, 111.4992]
}

# 5.) membuat tabel utama aplikasi 
def init_db():
    # menyiapkan koneksi dan cursor database
    conn = get_db()
    cur = conn.cursor()

    # membuat tabel users untuk menyimpan data user dan admin
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('user', 'admin')),
        kecamatan TEXT NOT NULL
    )
    """)

    # membuat tabel detections untuk menyimpan hasil deteksi penyakit
    cur.execute("""
    CREATE TABLE IF NOT EXISTS detections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        image TEXT NOT NULL,
        label TEXT NOT NULL,
        conf REAL NOT NULL,
        kecamatan TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # membuat tabel edukasi untuk menyimpan artikel edukasi yang dikelola admin
    cur.execute("""
    CREATE TABLE IF NOT EXISTS edukasi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        link TEXT NOT NULL UNIQUE,
        summary TEXT,
        image TEXT,
        is_published INTEGER NOT NULL DEFAULT 0 CHECK (is_published IN (0, 1)),
        is_featured INTEGER NOT NULL DEFAULT 0 CHECK (is_featured IN (0, 1)),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    try:
        cur.execute("ALTER TABLE edukasi ADD COLUMN kategori_penyakit TEXT")
    except:
        pass
    
    try:
        cur.execute("ALTER TABLE edukasi ADD COLUMN is_featured INTEGER NOT NULL DEFAULT 0 CHECK (is_featured IN (0, 1))")
    except:
        pass

    # menyimpan perubahan dan menutup koneksi
    conn.commit()
    conn.close()


# 6.) konfigurasi folder upload dan format file gambar yang diizinkan
UPLOAD_DIR = os.path.join("static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED = {"png", "jpg", "jpeg"}


def allowed_file(name: str) -> bool:
    # memeriksa apakah file memiliki ekstensi yang diizinkan
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED


# 7.) data gejala penyakit berdasarkan label hasil prediksi
GEJALA = {
    "healthy_leaf": "Daun terlihat sehat dengan warna hijau merata tanpa tanda-tanda penyakit.",
    "yellowish_leaf": "Daun mengalami perubahan warna menjadi kuning (klorosis) yang menandakan gangguan pertumbuhan.",
    "curl_leaf": "Daun mengalami penggulungan atau pengeritingan yang dapat menghambat proses fotosintesis.",
    "spot_leaf": "Daun menunjukkan munculnya bercak pada permukaan yang dapat menyebar dan menurunkan kualitas tanaman.",
}


# 8.) data solusi penanganan penyakit berdasarkan label hasil prediksi
SOLUSI = {
    "healthy_leaf": {
        "kategori_penyakit": "Healthy Leaf - Tanaman Sehat",
        "penyebab": "Kondisi ini menunjukkan tanaman berada dalam keadaan normal tanpa gejala serangan hama atau penyakit.",
        "catatan": [
            "Penanganan dilakukan secara bertahap sesuai kondisi tanaman di lapangan. Tidak semua tindakan harus diterapkan sekaligus. Urutan prioritas digunakan untuk menentukan tindakan yang perlu didahulukan.",
            "Monitoring rutin penting untuk mendeteksi gejala awal, perawatan dasar membantu menjaga ketahanan tanaman, dan pemangkasan daun tua membantu mengurangi sumber penyakit dan meningkatkan sirkulasi udara."
        ],
        "tindakan_penanganan": [
            {
                "prioritas": "Prioritas 1",
                "judul": "Monitoring Rutin - Sampling Sederhana",
                "kapan": "Dilakukan sebagai langkah awal saat tanaman terdeteksi sehat dan secara berkala selama masa budidaya.",
                "tujuan": "Mendeteksi gejala awal serangan hama atau penyakit secara dini.",
                "poin": [
                    "Lakukan pengambilan sampel pada 5 tanaman per-petak.",
                    "Periksa 2 daun untuk setiap tanaman sehingga total 10 daun.",
                    "Amati perubahan warna, bercak, keriting, atau keberadaan hama.",
                    "Tingkatkan frekuensi pengecekan menjadi setiap 2–3 hari jika di area pengamatan menunjukkan gejala baru."
                ],
                "img": "icons/monitor-healthy.png"
            },
            {
                "prioritas": "Prioritas 2",
                "judul": "Perawatan Dasar Tanaman",
                "kapan": "Dilakukan secara rutin selama masa pertumbuhan tanaman.",
                "tujuan": "Menjaga kondisi tanaman tetap stabil dan meningkatkan ketahanan terhadap hama dan penyakit.",
                "poin": [
                    "Pastikan penyiraman stabil dan hindari genangan air.",
                    "Lakukan pemupukan seimbang sesuai fase pertumbuhan tanaman.",
                    "Bersihkan gulma untuk menjaga sirkulasi udara tetap baik."
                ],
                "img": "icons/care-healthy.png"
            },
            {
                "prioritas": "Prioritas 3",
                "judul": "Pemangkasan Daun Tua",
                "kapan": "Dilakukan jika ditemukan daun tua, rusak, atau gugur di sekitar tanaman.",
                "tujuan": "Mengurangi sumber inokulum penyakit dan meningkatkan sirkulasi udara.",
                "poin": [
                    "Buang daun tua atau rusak yang jatuh di permukaan tanah.",
                    "Hindari penumpukan sisa tanaman di sekitar bedengan atau area tanah yang lebih tinggi.",
                    "Bersihkan alat kebun setelah digunakan."
                ],
                "img": "icons/sanitation-healthy.png"
            }
        ],
        "monitoring": {
            "poin": [
                "Lakukan pengecekan ulang 3–5 hari setelah pengamatan awal.",
                "Lakukan pengamatan pada tanaman sampel dan area sekitar.",
                "Amati jumlah daun sehat dan daun yang menunjukkan gejala baru.",
                "Perhatikan perubahan warna, bercak, keriting, atau keberadaan hama."
            ],
            "img": "icons/monitoring.png"
        },
        "evaluasi": {
            "poin": [
                "Jika sebagian besar daun tetap sehat, kondisi tanaman dinilai stabil dan perawatan rutin dapat dilanjutkan.",
                "Jika dalam waktu 5 hari lebih dari 20 daun di area pengamatan menunjukkan gejala baru, maka frekuensi pengecekan ditingkatkan menjadi setiap 2–3 hari.",
                "Jika gejala terus bertambah, lakukan penanganan sesuai kategori penyakit yang terdeteksi."
            ],
            "img": "icons/evaluation.png"
        }
    },

    "yellowish_leaf": {
        "kategori_penyakit": "Yellowish Leaf - Tanaman Menguning",
        "penyebab": "Kondisi ini dapat disebabkan oleh kekurangan unsur hara, drainase yang kurang baik, atau serangan hama penghisap.",
        "catatan": [
            "Penanganan dilakukan secara bertahap sesuai kondisi tanaman dan gejala yang diamati di lapangan. Tidak semua tindakan harus diterapkan sekaligus. Urutan prioritas digunakan untuk menentukan tindakan yang perlu didahulukan.",
            "Pada kondisi awal, tindakan seperti pemasangan perangkap kuning, penanaman tanaman pembatas, dan pemanfaatan predator alami dapat dilakukan sebagai langkah pengendalian awal. Jika gejala semakin meluas, tindakan lanjutan seperti pemangkasan daun yang terdampak dapat diterapkan.",
            "Perlu diperhatikan bahwa penyebaran gejala yang cepat memerlukan evaluasi nutrisi dan kelembapan tanah."
        ],
        "tindakan_penanganan": [
            {
                "prioritas": "Prioritas 1",
                "judul": "Pemasangan Perangkap Kuning",
                "kapan": "Dilakukan saat awal muncul gejala atau sebagai langkah pencegahan di area budidaya.",
                "tujuan": "Mengurangi populasi serangan hama penghisap.",
                "poin": [
                    "Pasang perangkap kuning setinggi pucuk tanaman.",
                    "Gunakan 6–10 perangkap untuk setiap 100 m².",
                    "Atur jarak antar perangkap sekitar 3 m² hingga 5 m².",
                    "Ganti perangkap jika sudah penuh serangga.",
                    "Tambahkan perangkap pada area dengan gejala terbanyak."
                ],
                "img": "icons/sticky-trap-yellow.png"
            },
            {
                "prioritas": "Prioritas 2",
                "judul": "Penanaman Tanaman Pembatas",
                "kapan": "Dilakukan saat persiapan atau selama masa budidaya untuk mengurangi penyebaran hama.",
                "tujuan": "Membatasi pergerakan hama antar petak dan menciptakan penghalang alami.",
                "poin": [
                    "Tanam jagung atau tanaman tinggi sebagai pembatas antar petak.",
                    "Buat minimal satu baris pembatas pada sisi yang berbatasan dengan lahan lain.",
                    "Lakukan monitoring hama juga pada tanaman pembatas."
                ],
                "img": "icons/barrier-yellow.png"
            },
            {
                "prioritas": "Prioritas 3",
                "judul": "Pemanfaatan Predator Alami",
                "kapan": "Dilakukan saat populasi hama mulai terdeteksi di lapangan.",
                "tujuan": "Menekan populasi hama secara biologis dan menjaga keseimbangan ekosistem.",
                "poin": [
                    "Memanfaatkan musuh alami untuk menekan populasi hama penghisap.",
                    "Gunakan predator, seperti kumbang koksi atau parasitoid sesuai kondisi lapangan.",
                    "Hindari penggunaan pestisida berlebihan agar musuh alami tetap terjaga."
                ],
                "img": "icons/predator-yellow.png"
            },
            {
                "prioritas": "Prioritas 4",
                "judul": "Pemangkasan Daun Menguning",
                "kapan": "Dilakukan jika daun sudah menguning berat dan tidak produktif.",
                "tujuan": "Mengurangi sumber inokulum penyakit dan menekan perkembangan hama.",
                "poin": [
                    "Pangkas daun yang menguning berat dan tidak produktif.",
                    "Kumpulkan daun dalam wadah tertutup.",
                    "Kubur daun minimal 30 cm atau komposkan secara terpisah.",
                    "Bersihkan alat setelah pemangkasan selesai."
                ],
                "img": "icons/pruning-yellow.png"
            }
        ],
        "monitoring": {
            "poin": [
                "Lakukan pengecekan ulang 3–5 hari setelah penanganan awal.",
                "Lakukan pengamatan pada tanaman sampel dan area sekitar.",
                "Amati perubahan warna daun, penyebaran gejala, dan keberadaan hama penghisap.",
                "Perhatikan area dengan gejala terbanyak untuk melihat pola penyebaran."
            ],
            "img": "icons/monitoring.png"
        },
        "evaluasi": {
            "poin": [
                "Jika jumlah daun yang menguning tidak bertambah dan kondisi tanaman mulai membaik, maka penanganan dinilai efektif.",
                "Jika dalam waktu 5 hari lebih dari 20 daun di area pengamatan menunjukkan gejala baru, maka frekuensi pengecekan ditingkatkan menjadi setiap 2–3 hari.",
                "Jika gejala semakin meluas atau tanaman menunjukkan kerusakan lebih lanjut, disarankan untuk melakukan konsultasi dengan penyuluh pertanian guna mendapatkan penanganan lanjutan yang lebih tepat."
            ],
            "img": "icons/evaluation.png"
        }
    },

    "curl_leaf": {
        "kategori_penyakit": "Curl Leaf - Daun Menggulung",
        "penyebab": "Kondisi ini disebabkan oleh serangan hama penghisap atau kondisi lingkungan seperti panas berlebih dan kekurangan air.",
        "catatan": [
            "Penanganan dilakukan secara bertahap sesuai kondisi tanaman dan gejala yang diamati di lapangan. Tidak semua tindakan harus diterapkan sekaligus. Urutan prioritas digunakan untuk menentukan tindakan yang perlu didahulukan.",
            "Pada kondisi awal, tindakan seperti pemasangan perangkap kuning dan pemanfaatan predator alami dapat dilakukan sebagai langkah pengendalian awal. Jika gejala semakin meluas, tindakan lanjutan seperti pemangkasan daun yang terdampak dapat diterapkan.",
            "Peningkatan populasi hama umumnya terjadi dalam 5–7 hari pertama, sehingga tindakan pengendalian perlu dilakukan sejak awal untuk mencegah penyebaran yang lebih luas."
        ],
        "tindakan_penanganan": [
            {
                "prioritas": "Prioritas 1",
                "judul": "Pemasangan Perangkap Kuning",
                "kapan": "Dilakukan saat awal muncul gejala atau sebagai langkah pencegahan di area budidaya.",
                "tujuan": "Mengurangi populasi hama penghisap yang menjadi penyebab daun menggulung.",
                "poin": [
                    "Pasang perangkap kuning setinggi pucuk tanaman.",
                    "Gunakan 6–10 perangkap untuk setiap 100 m².",
                    "Atur jarak antar perangkap sekitar 3 m² hingga 5 m².",
                    "Ganti perangkap jika sudah penuh serangga.",
                    "Tambahkan perangkap pada area dengan gejala terbanyak."
                ],
                "img": "icons/sticky-trap-curl.png"
            },
            {
                "prioritas": "Prioritas 2",
                "judul": "Pemanfaatan Predator Alami",
                "kapan": "Dilakukan saat keberadaan hama mulai terdeteksi di lapangan.",
                "tujuan": "Menekan populasi hama secara biologis dan menjaga keseimbangan ekosistem.",
                "poin": [
                    "Memanfaatkan musuh alami untuk menekan populasi hama penghisap.",
                    "Gunakan predator, seperti kepik atau agen hayati lain sesuai kondisi lapangan.",
                    "Hindari penggunaan pestisida berlebihan agar musuh alami tetap terjaga."
                ],
                "img": "icons/predator-curl.png"
            },
            {
                "prioritas": "Prioritas 3",
                "judul": "Pemangkasan Daun Menggulung",
                "kapan": "Dilakukan jika ditemukan daun atau pucuk yang sudah menggulung dan tidak produktif.",
                "tujuan": "Mengurangi sumber hama dan mencegah penyebaran gejala ke bagian tanaman lain.",
                "poin": [
                    "Pangkas daun atau pucuk yang menggulung.",
                    "Kumpulkan daun dalam wadah tertutup.",
                    "Kubur daun minimal 30 cm atau komposkan secara terpisah.",
                    "Bersihkan alat setelah digunakan."
                ],
                "img": "icons/pruning-curl.png"
            }
        ],
        "monitoring": {
            "poin": [
                "Lakukan pengecekan ulang 3–5 hari setelah penanganan awal.",
                "Lakukan pengamatan pada tanaman sampel dan area sekitar.",
                "Amati tingkat penggulungan daun dan keberadaan hama penghisap.",
                "Perhatikan area dengan gejala terbanyak untuk melihat pola penyebaran."
            ],
            "img": "icons/monitoring.png"
        },
        "evaluasi": {
            "poin": [
                "Jika gejala tidak bertambah dan kondisi tanaman mulai stabil, maka penanganan dinilai efektif.",
                "Jika dalam waktu 5 hari lebih dari 20 daun di area pengamatan menunjukkan gejala baru, maka frekuensi pengecekan ditingkatkan menjadi setiap 2–3 hari.",
                "Jika gejala semakin meluas atau tanaman menunjukkan kerusakan lebih lanjut, disarankan untuk melakukan konsultasi dengan penyuluh pertanian guna mendapatkan penanganan lanjutan yang lebih tepat."
            ],
            "img": "icons/evaluation.png"
        }
    },

    "spot_leaf": {
        "kategori_penyakit": "Spot Leaf - Bercak Daun",
        "penyebab": "Kondisi ini disebabkan oleh infeksi jamur atau bakteri yang berkembang pada lingkungan lembap.",
        "catatan": [
            "Penanganan dilakukan secara bertahap sesuai kondisi tanaman dan gejala yang diamati di lapangan. Tidak semua tindakan harus diterapkan sekaligus. Urutan prioritas digunakan untuk menentukan tindakan yang perlu didahulukan.",
            "Pada kondisi awal, tindakan seperti pengaturan penyiraman dan aplikasi biokontrol dapat dilakukan sebagai langkah pengendalian awal. Jika gejala semakin meluas, tindakan lanjutan seperti pemangkasan daun yang terdampak dapat diterapkan.",
            "Kelembapan yang tinggi dapat mempercepat penyebaran penyakit, sehingga pengendalian kondisi lingkungan dan sanitasi tanaman perlu dilakukan sejak awal."
        ],
        "tindakan_penanganan": [
            {
                "prioritas": "Prioritas 1",
                "judul": "Pengaturan Penyiraman",
                "kapan": "Dilakukan secara rutin selama masa budidaya, terutama pada kondisi lingkungan lembap.",
                "tujuan": "Mengurangi kelembapan pada daun dan mencegah perkembangan jamur atau bakteri.",
                "poin": [
                    "Siram tanaman langsung ke tanah dan hindari mengenai daun.",
                    "Hindari penyiraman pada sore atau malam hari.",
                    "Pastikan drainase lahan berfungsi dengan baik."
                ],
                "img": "icons/sanitation-spot.png"
            },
            {
                "prioritas": "Prioritas 2",
                "judul": "Aplikasi Biokontrol",
                "kapan": "Dilakukan saat gejala bercak mulai terlihat pada daun.",
                "tujuan": "Menghambat perkembangan patogen penyebab penyakit secara biologis.",
                "poin": [
                    "Gunakan agen hayati berbasis jamur antagonis sesuai anjuran label.",
                    "Lakukan aplikasi pada pagi atau sore hari.",
                    "Evaluasi perkembangan bercak setelah 5–7 hari.",
                    "Ulangi aplikasi sesuai interval jika gejala masih bertambah."
                ],
                "img": "icons/biocontrol-spot.png"
            },
            {
                "prioritas": "Prioritas 3",
                "judul": "Pemangkasan Daun Berbercak",
                "kapan": "Dilakukan jika bercak pada daun sudah menyebar dan berpotensi menular ke bagian lain.",
                "tujuan": "Mengurangi sumber inokulum penyakit dan mencegah penyebaran lebih lanjut.",
                "poin": [
                    "Pangkas daun dengan bercak yang sudah menyebar luas.",
                    "Kumpulkan daun dalam wadah tertutup.",
                    "Kubur daun minimal 30 cm atau komposkan secara terpisah.",
                    "Bersihkan alat setelah digunakan."
                ],
                "img": "icons/pruning-spot.png"
            }
        ],
        "monitoring": {
            "poin": [
                "Lakukan pengecekan ulang 3–5 hari setelah penanganan awal.",
                "Lakukan pengamatan pada tanaman sampel dan area sekitar.",
                "Amati perkembangan bercak pada daun serta penyebarannya.",
                "Perhatikan kondisi kelembapan lingkungan dan keberadaan daun yang terinfeksi."
            ],
            "img": "icons/monitoring.png"
        },
        "evaluasi": {
            "poin": [
                "Jika perkembangan bercak tidak bertambah dan kondisi tanaman mulai stabil, maka penanganan dinilai efektif.",
                "Jika dalam waktu 5 hari lebih dari 20 daun di area pengamatan menunjukkan gejala baru, maka frekuensi pengecekan ditingkatkan menjadi setiap 2–3 hari.",
                "Jika gejala semakin meluas atau tanaman menunjukkan kerusakan lebih lanjut, disarankan untuk melakukan konsultasi dengan penyuluh pertanian guna mendapatkan penanganan lanjutan yang lebih tepat."
            ],
            "img": "icons/evaluation.png"
        }
    }
}


# 9.) konfigurasi sumber RSS untuk halaman edukasi
PLACEHOLDER_IMG = "https://via.placeholder.com/320x200?text=Budidaya+Cabai"

RSS_SOURCES = [
    "https://news.google.com/rss/search?q=budidaya%20cabai&hl=id&gl=ID&ceid=ID:id",
    "https://news.google.com/rss/search?q=tanaman%20cabai%20hama%20penyakit&hl=id&gl=ID&ceid=ID:id",
    "https://news.google.com/rss/search?q=cara%20menanam%20cabai&hl=id&gl=ID&ceid=ID:id",
]

KEYWORDS_CABAI = [
    "edukasi budidaya tanaman cabai", "teknik budidaya cabai ramah lingkungan", "praktik budidaya cabai berkelanjutan",
    "gerakan tanam cabai edukatif", "budidaya cabai blora", "budidaya cabai", "cabai", "penanganan penyakit tanaman cabai",
    "rekomendasi penanganan penyakit cabai", "pengendalian hama cabai secara alami", "pengendalian penyakit cabai organik",
    "penanganan penyakit cabai", "penyakit cabai", "antraknosa cabai", "patek cabai", "thrips cabai", "kutu kebul cabai",
    "yellowish", "leaf curl", "leaf spot", "hama cabai", "biokontrol cabai", "agen hayati cabai", "jamur antagonis cabai",
    "trichoderma cabai", "beauveria bassiana cabai", "pestisida nabati cabai", "larutan organik untuk cabai", 
    "pengendalian hama cabai organik", "sanitasi lahan cabai", "pengelolaan lahan cabai sehat"
]


CACHE_TTL_SECONDS = 10 * 60
_RSS_CACHE = {}


# 10.) helper function untuk memproses data RSS edukasi
def _norm(s: str) -> str:
    # Menormalkan teks agar mudah dibandingkan saat proses filter
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _strip_html(s: str) -> str:
    # membersihkan tag HTML dari ringkasan artikel
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _extract_image_from_entry(entry) -> str | None:
    # mengambil URL gambar dari item RSS jika tersedia
    mc = getattr(entry, "media_content", None)
    if mc and isinstance(mc, list) and len(mc) > 0:
        url = mc[0].get("url")
        if url:
            return url

    mt = getattr(entry, "media_thumbnail", None)
    if mt and isinstance(mt, list) and len(mt) > 0:
        url = mt[0].get("url")
        if url:
            return url

    links = getattr(entry, "links", None)
    if links:
        for lk in links:
            if lk.get("type", "").startswith("image/") and lk.get("href"):
                return lk["href"]

    return None


def clean_title(title: str) -> str:
    # membersihkan judul artikel dari teks tambahan yang tidak diperlukan
    t = html.unescape(title or "")
    t = re.sub(r'^"\s*[^"]+\s*"\s*-\s*', "", t)
    t = re.sub(r"\s-\s[^-]{2,}$", "", t)
    t = re.sub(r"(berita|kabar|news)\s.*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def fetch_articles(query: str | None = None, limit: int = 30) -> list[dict]:
    # mengambil artikel dari beberapa sumber RSS dan memfilter artikel yang relevan
    sources = list(RSS_SOURCES)

    if query and query.strip():
        q = quote_plus(query.strip())
        sources.insert(0, f"https://news.google.com/rss/search?q={q}&hl=id&gl=ID&ceid=ID:id")

    kws = [_norm(k) for k in KEYWORDS_CABAI]
    items = []
    seen = set()

    for rss_url in sources:
        feed = feedparser.parse(rss_url)
        feed_title = ""

        for e in getattr(feed, "entries", []) or []:
            raw_title = getattr(e, "title", "") or ""
            title = clean_title(raw_title)
            link = getattr(e, "link", "") or ""
            summary = getattr(e, "summary", "") or getattr(e, "description", "") or ""

            if not link or link in seen:
                continue

            hay = _norm(f"{title} {summary}")
            if not any(k in hay for k in kws):
                continue

            img = _extract_image_from_entry(e)

            items.append({
                "source": feed_title,
                "title": title.replace("...", "").strip(),
                "link": link,
                "summary": _strip_html(summary)[:180],
                "image": img or "icons/new.png",
            })
            seen.add(link)

    return items[: max(1, limit)]


def fetch_articles_cached(query: str | None = None) -> list[dict]:
    # menyimpan hasil artikel sementara agar tidak terlalu sering mengambil RSS
    key = (query or "").strip().lower()
    now = time.time()

    if key in _RSS_CACHE:
        cached = _RSS_CACHE[key]
        if cached["data"] and (now - cached["ts"] < CACHE_TTL_SECONDS):
            return cached["data"]

    data = fetch_articles(query=query, limit=10000)
    _RSS_CACHE[key] = {"ts": now, "data": data}
    return data


def paginate(items: list[dict], page: int, per_page: int = 5):
    # membagi data artikel menjadi beberapa halaman
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page

    return items[start:end], page, total_pages


# 11.) helper untuk validasi session hasil deteksi
def get_label_or_redirect():
    # Mengambil label hasil prediksi dari session
    label = session.get("label")
    if not label:
        return None
    return label


# 12.) helper untuk proteksi halaman login dan admin
def login_required(f):
    # Membatasi akses hanya untuk user yang sudah login
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    # membatasi akses hanya untuk akun admin
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# 13.) helper untuk pengolahan waktu deteksi
def parse_created_at(value):
    # Mengubah nilai waktu dari database menjadi objek datetime
    if not value:
        return value

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime.fromisoformat(value)
    return value


WIB_TZ = ZoneInfo("Asia/Jakarta")


def utc_now_naive():
    # membuat waktu UTC tanpa timezone untuk disimpan ke SQLite
    return datetime.now(timezone.utc).replace(tzinfo=None)


def format_datetime_wib(value):
    # mengubah waktu UTC dari database ke format WIB
    dt = parse_created_at(value)
    if not dt:
        return "-"

    dt_utc = dt.replace(tzinfo=timezone.utc)
    dt_wib = dt_utc.astimezone(WIB_TZ)
    return dt_wib.strftime("%Y-%m-%d %H:%M WIB")


# 14.) route halaman utama
@app.route("/")
def index():
    # Menghapus hasil prediksi lama dari session saat kembali ke beranda
    session.pop("label", None)
    session.pop("conf", None)
    session.pop("image_file", None)
    session.pop("probs", None)

    # Menampilkan halaman beranda
    return render_template("index.html")


@app.route("/about")
def about():
    # Menampilkan halaman tentang aplikasi
    return render_template("about.html")


# 15.) route register user dan admin
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nama = request.form["nama"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]
        kecamatan = request.form["kecamatan"]
        admin_code = request.form.get("admin_code", "").strip()

        if role == "admin" and admin_code != "BotaniQ2026":
            flash("Kode Admin Salah!", "danger")
            return redirect(url_for("register"))

        conn = get_db()

        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing:
            conn.close()
            flash("Email Sudah Terdaftar!", "danger")
            return redirect(url_for("register"))

        try:
            conn.execute(
                "INSERT INTO users (nama, email, password, role, kecamatan) VALUES (?, ?, ?, ?, ?)",
                (nama, email, password, role, kecamatan)
            )
            conn.commit()
            flash("Registrasi Berhasil! Silakan Login.", "success")
            return redirect(url_for("login"))
        finally:
            conn.close()

    return render_template("register.html")


# 16.) route login user dan admin
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["nama"] = user["nama"]
            return redirect(url_for("index"))

        error = "Login Gagal! Email Atau Password Salah."

    return render_template("login.html", error=error)


# 17.) route deteksi penyakit tanaman
@app.route("/detect", methods=["GET", "POST"])
@login_required
def detect():
    # menangani upload gambar dan proses prediksi penyakit
    if request.method == "POST":
        f = request.files.get("image")

        if not f or f.filename == "":
            return render_template("detect.html", error="Pilih gambar dulu.")

        if not allowed_file(f.filename):
            return render_template("detect.html", error="Format harus png/jpg/jpeg.")

        filename = secure_filename(f.filename)
        save_path = os.path.join(UPLOAD_DIR, filename)
        f.save(save_path)

        # menjalankan model klasifikasi terhadap gambar yang diunggah
        label, conf, probs = predict_image(save_path)

        # menyimpan hasil klasifikasi ke session
        session["image_file"] = f"uploads/{filename}"
        session["label"] = label
        session["conf"] = round(conf * 100, 2)
        session["probs"] = probs

        conn = get_db()

        # mengambil kecamatan user yang sedang login
        user = conn.execute(
            "SELECT kecamatan FROM users WHERE id=?",
            (session["user_id"],)
        ).fetchone()

        kecamatan = user["kecamatan"] if user else None

        # menyimpan hasil deteksi ke database
        conn.execute("""
            INSERT INTO detections
            (user_id, image, label, conf, kecamatan, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            f"uploads/{filename}",
            label,
            conf,
            kecamatan,
            utc_now_naive().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

        # mengarahkan ke halaman hasil prediksi
        return redirect(url_for("result"))

    # menampilkan halaman deteksi
    return render_template("detect.html")


# 18.) route hasil prediksi
@app.route("/result")
def result():
    # memastikan hasil prediksi tersedia di session
    label = get_label_or_redirect()
    if not label:
        return redirect(url_for("detect"))

    # menampilkan halaman hasil prediksi
    return render_template(
        "result.html",
        image_file=session.get("image_file"),
        label=label,
        conf=session.get("conf"),
        probs=session.get("probs", []),
    )


# 19.) route gejala penyakit
@app.route("/symptoms")
def symptoms():
    # Memastikan label hasil prediksi tersedia di session
    label = get_label_or_redirect()
    if not label:
        return redirect(url_for("detect"))

    # Menampilkan gejala berdasarkan label penyakit
    return render_template(
        "symptoms.html",
        image_file=session.get("image_file"),
        label=label,
        gejala=GEJALA.get(label, "Gejala belum tersedia untuk kategori ini."),
    )


# 20.) route solusi penanganan penyakit
@app.route("/solution")
def solution():
    label = get_label_or_redirect()
    if not label:
        return redirect(url_for("detect"))

    conn = get_db()
    featured_articles = conn.execute("""
        SELECT * FROM edukasi
        WHERE is_published = 1
          AND is_featured = 1
          AND kategori_penyakit = ?
        ORDER BY created_at DESC
        LIMIT 3
    """, (label,)).fetchall()
    conn.close()

    return render_template(
        "solution.html", image_file=session.get("image_file"),
        label=label, solusi=SOLUSI.get(label), featured_articles=featured_articles)


# 21.) route riwayat deteksi milik user
@app.route("/riwayat")
def riwayat():
    # memastikan user sudah login sebelum membuka riwayat
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    data = conn.execute(
        "SELECT * FROM detections WHERE user_id=? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    # menyiapkan data riwayat agar siap ditampilkan ke template
    data_riwayat = []
    for d in data:
        item = dict(d)
        item["kecamatan"] = item.get("kecamatan") or "-"

        if item["created_at"]:
            item["created_at"] = format_datetime_wib(item["created_at"])

        item["gejala_text"] = GEJALA.get(item["label"], "Gejala Belum Tersedia.")
        item["solusi_obj"] = SOLUSI.get(item["label"], {})
        data_riwayat.append(item)

    # menampilkan halaman riwayat user
    return render_template("riwayat.html", data=data_riwayat)


# 22.) route riwayat deteksi untuk admin
@app.route('/admin/riwayat')
@admin_required
def admin_riwayat():
    # membuka koneksi database untuk mengambil data riwayat semua user
    conn = get_db()

    # mengambil daftar user untuk kebutuhan filter pada halaman admin
    users = conn.execute(
        "SELECT DISTINCT id, nama, role FROM users"
    ).fetchall()

    # mengambil parameter filter dari URL
    nama = request.args.get('nama')
    kecamatan = request.args.get('kecamatan')
    label = request.args.get('label')
    sort = request.args.get('sort', 'terbaru')

    # menyusun query dasar untuk mengambil data deteksi beserta identitas user
    query = """
        SELECT d.id, d.image, d.label, d.conf, d.created_at,
               u.nama, u.kecamatan AS user_kecamatan
        FROM detections d
        JOIN users u ON d.user_id = u.id
        WHERE 1=1
    """
    params = []

    # menambahkan filter nama jika dipilih admin
    if nama:
        query += " AND u.nama LIKE ?"
        params.append(f"%{nama}%")

    # menambahkan filter kecamatan jika dipilih admin
    if kecamatan:
        query += " AND u.kecamatan LIKE ?"
        params.append(f"%{kecamatan}%")

    # menambahkan filter label penyakit jika dipilih admin
    if label:
        query += " AND d.label = ?"
        params.append(label)

    # mengatur urutan data berdasarkan waktu deteksi
    if sort == "terlama":
        query += " ORDER BY d.created_at ASC"
    else:
        query += " ORDER BY d.created_at DESC"

    # menjalankan query sesuai filter yang dipilih
    data = conn.execute(query, params).fetchall()
    conn.close()

    # menyiapkan data agar siap ditampilkan di template admin
    data_fixed = []
    for d in data:
        item = dict(d)

        # mengubah format waktu deteksi ke WIB
        if item["created_at"]:
            item["created_at"] = format_datetime_wib(item["created_at"])

        # menyimpan kecamatan user dengan nilai default jika kosong
        item["kecamatan"] = item.get("user_kecamatan") or "-"
        data_fixed.append(item)

    # menampilkan halaman riwayat admin
    return render_template("admin_riwayat.html", data=data_fixed, users=users)


# 23.) route kelola edukasi oleh admin
@app.route("/admin/edukasi", methods=["GET", "POST"])
@admin_required
def admin_edukasi():
    # memastikan hanya admin yang dapat mengakses halaman kelola edukasi
    if session.get("role") != "admin":
        return redirect(url_for("index"))

    conn = get_db()

    # menangani proses penyimpanan artikel edukasi ke database
    if request.method == "POST":
        title = request.form.get("title")
        link = request.form.get("link")
        summary = request.form.get("summary")
        image = request.form.get("image")
        kategori_penyakit = request.form.get("kategori_penyakit")

        # mengambil halaman aktif agar setelah simpan kembali ke halaman yang sama
        page = int(request.form.get("page", 1))
        tab = request.form.get("tab", "unsaved")
        q = request.form.get("q", "")

        # menentukan status publish artikel dari form admin
        publish = request.form.get("publish")
        is_published = 1 if publish == "on" else 0

        # menentukan status berita unggulan dari form admin
        featured = request.form.get("is_featured")
        is_featured = 1 if featured == "on" else 0

        # mengecek apakah artikel dengan link yang sama sudah ada
        existing = conn.execute(
            "SELECT id FROM edukasi WHERE link = ?",
            (link,)
        ).fetchone()

        # simpan jika belum ada, update jika sudah ada
        if not existing:
            conn.execute("""
                INSERT INTO edukasi
                (title, link, summary, image, kategori_penyakit, is_featured, is_published)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, link, summary, image, kategori_penyakit, is_featured, is_published))
        else:
            conn.execute("""
                UPDATE edukasi
                SET title = ?,
                    summary = ?,
                    image = ?,
                    kategori_penyakit = ?,
                    is_featured = ?,
                    is_published = ?
                WHERE link = ?
            """, (title, summary, image, kategori_penyakit, is_featured, is_published, link))

        conn.commit()
        conn.close()
        return redirect(url_for("admin_edukasi", page=page, tab=tab, q=q))

    tab = request.args.get("tab", "unsaved")
    page = int(request.args.get("page", 1))
    q = request.args.get("q", "").lower()

    # mengambil artikel dari RSS untuk ditampilkan ke admin
    rss_articles = fetch_articles_cached()

    # ambil semua artikel yang sudah tersimpan
    existing_rows = conn.execute("""
        SELECT * FROM edukasi
        ORDER BY created_at DESC
    """).fetchall()

    saved_articles = [dict(row) for row in existing_rows]

    # ambil semua link artikel yang sudah tersimpan
    existing_links = {row["link"] for row in existing_rows}

    # artikel RSS yang belum tersimpan
    unsaved_articles = [a for a in rss_articles if a["link"] not in existing_links]

    # default value untuk artikel RSS
    for a in unsaved_articles:
        a["is_published"] = 0
        a["kategori_penyakit"] = ""
        a["is_featured"] = 0

    # pilih sumber data berdasarkan tab aktif
    if tab == "saved":
        data_source = saved_articles
    else:
        data_source = unsaved_articles
        tab = "unsaved"
    
    if q:
        data_source = [
            a for a in data_source
            if q in (a.get("title", "").lower()) or
               q in (a.get("summary", "").lower()) or
               q in (a.get("kategori_penyakit", "").lower())
        ]

    # pagination
    paginated, page, total_pages = paginate(data_source, page, per_page=10)

    conn.close()

    # menampilkan halaman kelola edukasi admin
    return render_template(
        "admin_edukasi.html", articles=paginated, q=q, page=page,
        total_pages=total_pages, active_tab=tab)

# 24.) route edukasi untuk user
@app.route("/edukasi")
@login_required
def education():
    # membuka koneksi database untuk mengambil artikel edukasi
    conn = get_db()

    # mengambil keyword pencarian dari URL
    q = request.args.get("q", "").strip()

    # mengambil artikel yang sudah dipublish, dengan atau tanpa pencarian judul
    if q:
        articles = conn.execute(
            "SELECT * FROM edukasi WHERE is_published = 1 AND title LIKE ? ORDER BY id DESC",
            (f"%{q}%",)
        ).fetchall()
    else:
        articles = conn.execute(
            "SELECT * FROM edukasi WHERE is_published = 1 ORDER BY id DESC"
        ).fetchall()

    conn.close()

    # mengubah hasil query menjadi list dictionary untuk kebutuhan pagination
    page = int(request.args.get("page", 1))
    articles_list = [dict(a) for a in articles]

    # membagi artikel ke beberapa halaman
    paginated, page, total_pages = paginate(articles_list, page, per_page=5)

    # menampilkan halaman edukasi user
    return render_template("edukasi.html", articles=paginated, page=page, total_pages=total_pages, q=q)


# 25.) route dashboard analisis untuk admin
@app.route("/admin/analisis")
@admin_required
def admin_analisis():
    # membuka koneksi database untuk mengambil data analisis
    conn = get_db()

    # menghitung total user dengan role user
    total_user = conn.execute("""
        SELECT COUNT(*) as total
        FROM users
        WHERE role = 'user'
    """).fetchone()["total"]

    # menghitung total deteksi yang dilakukan oleh user
    total_deteksi = conn.execute("""
        SELECT COUNT(*) as total
        FROM detections d
        JOIN users u ON d.user_id = u.id
        WHERE u.role = 'user'
    """).fetchone()["total"]

    # menghitung jumlah kecamatan aktif berdasarkan data user
    total_kecamatan = conn.execute("""
        SELECT COUNT(DISTINCT kecamatan) as total
        FROM users
        WHERE role = 'user'
          AND kecamatan IS NOT NULL
          AND kecamatan != ''
    """).fetchone()["total"]

    # mengambil label penyakit dengan jumlah kasus tertinggi
    top_penyakit_row = conn.execute("""
        SELECT d.label, COUNT(*) as total
        FROM detections d
        JOIN users u ON d.user_id = u.id
        WHERE u.role = 'user'
        GROUP BY d.label
        ORDER BY total DESC
        LIMIT 1
    """).fetchone()

    # mengubah label internal menjadi label yang lebih mudah dibaca
    def label_view(label):
        mapping = {
            "healthy_leaf": "Healthy Leaf",
            "yellowish_leaf": "Yellowish Leaf",
            "curl_leaf": "Curl Leaf",
            "spot_leaf": "Spot Leaf"
        }
        return mapping.get(label, label or "-")

    # menentukan warna statistik berdasarkan label penyakit
    def label_color(label):
        return {
            "healthy_leaf": "#198754",
            "yellowish_leaf": "#f59f00",
            "curl_leaf": "#fd7e14",
            "spot_leaf": "#dc3545"
        }.get(label, "#6c757d")

    # menentukan nama penyakit tertinggi untuk summary card
    penyakit_tertinggi = label_view(top_penyakit_row["label"]) if top_penyakit_row else "-"

    # mengambil jumlah user pada setiap kecamatan
    users_per_kecamatan = [
        {"kecamatan": row["kecamatan"], "total": row["total"]}
        for row in conn.execute("""
            SELECT kecamatan, COUNT(*) as total
            FROM users
            WHERE role = 'user'
              AND kecamatan IS NOT NULL
              AND kecamatan != ''
            GROUP BY kecamatan
            ORDER BY total DESC
        """).fetchall()
    ]

    # mengambil detail user untuk ditampilkan saat marker peta diklik
    detail_users = [
        {
            "nama": row["nama"],
            "email": row["email"],
            "kecamatan": row["kecamatan"]
        }
        for row in conn.execute("""
            SELECT nama, email, kecamatan
            FROM users
            WHERE role = 'user'
              AND kecamatan IS NOT NULL
              AND kecamatan != ''
            ORDER BY kecamatan, nama
        """).fetchall()
    ]

    # mengambil persebaran penyakit pada setiap kecamatan
    penyakit_per_kecamatan = [
        {
            "kecamatan": row["user_kecamatan"],
            "label": row["label"],
            "total": row["total"]
        }
        for row in conn.execute("""
            SELECT u.kecamatan AS user_kecamatan, d.label, COUNT(*) as total
            FROM detections d
            JOIN users u ON d.user_id = u.id
            WHERE u.role = 'user'
              AND u.kecamatan IS NOT NULL
              AND u.kecamatan != ''
            GROUP BY u.kecamatan, d.label
            ORDER BY u.kecamatan, d.label
        """).fetchall()
    ]

    # mengambil data statistik jumlah deteksi per label penyakit
    statistik_raw = conn.execute("""
        SELECT d.label, COUNT(*) as total
        FROM detections d
        JOIN users u ON d.user_id = u.id
        WHERE u.role = 'user'
        GROUP BY d.label
        ORDER BY total DESC
    """).fetchall()

    # menentukan nilai maksimum untuk kebutuhan progress bar statistik
    max_total = max([row["total"] for row in statistik_raw], default=1)

    # menyiapkan data statistik penyakit beserta persen dan warna
    statistik_penyakit = []
    for row in statistik_raw:
        statistik_penyakit.append({
            "label": label_view(row["label"]),
            "total": row["total"],
            "persen": round((row["total"] / max_total) * 100, 2),
            "color": label_color(row["label"])
        })

    conn.close()

    # menampilkan dashboard analisis admin
    return render_template("admin_analisis.html", total_user=total_user, total_deteksi=total_deteksi,
        total_kecamatan=total_kecamatan, penyakit_tertinggi=penyakit_tertinggi,
        users_per_kecamatan=users_per_kecamatan, detail_users=detail_users,
        penyakit_per_kecamatan=penyakit_per_kecamatan, statistik_penyakit=statistik_penyakit, koordinat=KOORDINAT)


# 26.) route profil user dan admin
@app.route("/profile", methods=["GET", "POST"])
def profile():
    # memastikan user sudah login sebelum membuka halaman profil
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    # menangani perubahan password dari form profil
    if request.method == "POST":
        password = request.form["password"]

        conn.execute(
            "UPDATE users SET password=? WHERE id=?",
            (password, session["user_id"])
        )
        conn.commit()

    # mengambil data user yang sedang login
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    # menampilkan halaman profil
    return render_template("profile.html", user=user)


# 27.) route logout
@app.route("/logout")
def logout():
    # menghapus seluruh data session saat user logout
    session.clear()

    # mengarahkan pengguna kembali ke halaman beranda
    return redirect(url_for("index"))


# 28.) menjalankan aplikasi Flask
if __name__ == "__main__":
    # membuat tabel database saat aplikasi dijalankan
    init_db()

    # menjalankan aplikasi pada mode development
    app.run(debug=True)