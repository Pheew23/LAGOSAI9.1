import os
import subprocess

print("Memulai proses persiapan Chainlit...")

# 1. Jalankan Chainlit sejenak untuk memaksa pembuatan folder dan file .chainlit/config.toml
subprocess.run(["chainlit", "create-secret"], capture_output=True)

config_path = ".chainlit/config.toml"

# 2. Periksa apakah file config berhasil dibuat
if os.path.exists(config_path):
    print(f"File {config_path} ditemukan. Melakukan injeksi fitur Audio...")
    
    # 3. Baca isi file tersebut
    with open(config_path, "r", encoding="utf-8") as file:
        config_lines = file.readlines()

    # 4. Cari pengaturan audio dan ubah menjadi true
    new_config = []
    in_audio_section = False
    
    for line in config_lines:
        if line.strip() == "[features.audio]":
            in_audio_section = True
            new_config.append(line)
        elif in_audio_section and line.startswith("enabled ="):
            new_config.append('enabled = true\n')
            in_audio_section = False # Selesai mengubah
        else:
            new_config.append(line)

    # 5. Tulis kembali file dengan fitur audio yang sudah aktif
    with open(config_path, "w", encoding="utf-8") as file:
        file.writelines(new_config)
    print("Injeksi fitur Audio berhasil!")
else:
    print(f"Peringatan: File {config_path} tidak ditemukan. Chainlit mungkin menggunakan default sistem.")

# 6. Nyalakan server Chainlit dengan host dan port yang benar untuk Render
port = os.environ.get("PORT", "10000")
print(f"Menyalakan server di port {port}...")
os.system(f"chainlit run app.py --host 0.0.0.0 --port {port}")
