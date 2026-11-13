# 1) import library yang dibutuhkan
import numpy as np
from PIL import Image

from tensorflow import keras
from tensorflow.keras.applications.efficientnet import preprocess_input


# 2) konfigurasi input model
# ukuran gambar input yang diharapkan model (sesuaikan dengan saat training)
IMG_SIZE = (380, 380)

# mapping index output model -> label kelas
# urutan ini harus sama persis dengan urutan label saat training/dataset
IDX2LABEL = {
    0: "healthy_leaf",
    1: "yellowish_leaf",
    2: "curl_leaf",
    3: "spot_leaf",
}


# 3) load model (sekali saja saat program mulai)
# model akan disimpan di memori sehingga prediksi berikutnya lebih cepat
MODEL_PATH = "skenario3.keras"
model = keras.models.load_model(MODEL_PATH)


# 4) fungsi utama untuk prediksi satu gambar
def predict_image(image_path: str):
    # load gambar dari path, pastikan format rgb (3 channel)
    img = Image.open(image_path).convert("RGB")

    # resize gambar sesuai input model
    img = img.resize(IMG_SIZE)

    # ubah gambar menjadi array numpy float32
    x = np.array(img, dtype=np.float32)

    # tambahkan dimensi batch agar bentuknya (1, h, w, c)
    x = np.expand_dims(x, axis=0)

    # lakukan preprocessing bawaan efficientnet
    x = preprocess_input(x)

    # jalankan prediksi model untuk mendapatkan probabilitas tiap kelas
    # output model bentuknya (1, jumlah_kelas)
    probs = model.predict(x, verbose=0)[0]

    # ambil index kelas dengan probabilitas terbesar
    idx = int(np.argmax(probs))

    # ubah index tersebut menjadi nama label kelas
    label = IDX2LABEL.get(idx, str(idx))

    # ambil confidence dari kelas terpilih
    conf = float(probs[idx])

    # kembalikan hasil untuk dipakai di app.py (label, confidence, semua probabilitas)
    return label, conf, probs.tolist()