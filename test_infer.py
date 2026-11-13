# 1) import fungsi prediksi dari file inference.py
from inference import predict_image


# 2) tentukan path gambar yang akan diuji
# ganti path ini dengan gambar daun cabai yang ingin diuji
IMG_PATH = "contoh.jpg"


# 3) jalankan proses prediksi
# fungsi akan mengembalikan:
# - label  : nama kelas hasil klasifikasi
# - conf   : nilai confidence (0 - 1)
# - probs  : daftar probabilitas semua kelas
label, conf, probs = predict_image(IMG_PATH)


# 4) tampilkan hasil ke terminal
print("        HASIL UJI INFERENSI         ")

# tampilkan label hasil prediksi
print(f"Hasil Prediksi          : {label}")

# tampilkan confidence dalam persen
print(f"Tingkat Keyakinan       : {conf * 100:.2f}%")

# tampilkan probabilitas tiap kategori
print("Probabilitas Per-Kategori:")
print(probs)