# Indeks Kualitas Udara (AQI) Beijing

Panduan ini akan membantu Anda untuk menjalankan Dashboard Indeks Kualitas Udara (AQI) Beijing dengan Streamlit di komputer lokal Anda. Kami akan menggunakan file `app.py` sebagai file utama dan `requirements.txt` untuk daftar dependensi.

## Persyaratan

Pastikan Anda sudah menginstal:
- [Python 3.10+](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installation/)

## Langkah-langkah

### 1. Clone atau Download Repository

Jika Anda belum memiliki kode sumber aplikasi, clone atau download dari repository.

```
git clone github.com/andharsm/beijing-air-quality-dashboard-streamlit.git
cd beijing-air-quality-dashboard-streamlit
```

### 2. Buat Virtual Environment
Disarankan untuk menggunakan virtual environment agar dependensi proyek terisolasi dari sistem utama.

```
python -m venv venv
```

Aktifkan virtual environment:
Di Windows:
```
.\venv\Scripts\activate
```

Di macOS/Linux:
```
source venv/bin/activate
```

### 3. Instal Dependensi
Instal semua paket yang diperlukan yang tercantum dalam requirements.txt.
```
pip install -r requirements.txt
```

### 4. Jalankan Aplikasi Streamlit
Jalankan aplikasi Streamlit Anda dengan menjalankan perintah berikut:
```
streamlit run app.py
```

5. Akses Aplikasi
Setelah menjalankan perintah di atas, Anda akan melihat output yang mirip dengan ini:
```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.43.173:8501
```

Buka URL tersebut di browser Anda untuk melihat aplikasi Streamlit yang berjalan.

## Struktur Direktori
Pastikan struktur direktori Anda sesuai dengan berikut:
```
.
├── datasets
├── app.py
├── func.py
├── analysis_data_air_quality.ipynb
├── requirements.txt
└── venv/
```

* `datasets`: Folder dengan kumpulan dataset dalam format CSV
* `app.py`: File utama aplikasi Streamlit Anda.
* `func.py`: File berisi kumpulan fungsi pendukung
* `analysis_data_air_quality.ipynb`: File notebook yang digunakan untuk mengolah dan menganalisa dataset
* `requirements.txt`: Daftar dependensi yang dibutuhkan aplikasi Anda.
* `venv/`: Virtual environment yang berisi instalasi paket-paket Python.

## Catatan Tambahan
Mematikan Virtual Environment:
Untuk menonaktifkan virtual environment, cukup jalankan perintah:
```
deactivate
```
Memperbarui requirements.txt:
Jika Anda menambahkan paket baru, jangan lupa untuk memperbarui requirements.txt dengan perintah:
```
pip freeze > requirements.txt
```

Dengan mengikuti langkah-langkah di atas, Anda akan dapat menjalankan aplikasi Streamlit di komputer lokal Anda. Selamat mencoba!
