# 🌸 Çiçekçi Dükkanı - Müşteri Yönetim Sistemi

## 📋 İçindekiler
1. Hızlı Başlangıç (Test Etme)
2. .exe Dosyasına Çevirme - Adım Adım
3. .exe Sorun Giderme
4. Uygulama Özellikleri

---

## 🚀 1. Hızlı Başlangıç (Önce Python ile Test Etme)

`.exe`'ye çevirmeden önce uygulamanın çalıştığından emin olmak için:

### Adım 1: Python'u Kurun
- https://www.python.org/downloads/ adresinden **Python 3.10 veya üstünü** indirin.
- Kurulum sırasında **"Add Python to PATH"** kutucuğunu mutlaka işaretleyin!

### Adım 2: Uygulamayı Çalıştırın
Klasörün içinde **shift + sağ tık** yapıp **"PowerShell penceresini burada aç"** seçeneğine tıklayın ve şunu yazın:

```bash
python main.py
```

Uygulama açılırsa her şey yolundadır, .exe oluşturmaya hazırsınız!

---

## 📦 2. .exe Dosyasına Çevirme (PyInstaller ile)

### Adım 1: PyInstaller'ı Kurun
PowerShell'de proje klasörü içindeyken şu komutu çalıştırın:

```bash
pip install pyinstaller
```

Doğrulamak için:
```bash
pyinstaller --version
```

### Adım 2: .exe Dosyasını Oluşturun
Aynı PowerShell penceresinde şu komutu çalıştırın:

```bash
pyinstaller --onefile --windowed --name "CicekciMusteriYonetim" main.py
```

> 📌 **NOT:** Proje artık `main.py` ve `database.py` olmak üzere iki dosyadan oluşuyor.
> PyInstaller `--onefile` modunda otomatik olarak ikisini de paketler — endişelenmenize gerek yok.

### 📌 Komut Parametrelerinin Anlamı:
| Parametre | Açıklama |
|-----------|----------|
| `--onefile` | Tüm bağımlılıkları **tek bir .exe dosyasına** paketler |
| `--windowed` | Programı çalıştırırken **siyah komut ekranı (cmd) açılmasını engeller** |
| `--name "..."` | Oluşacak .exe dosyasının adını belirler |
| `main.py` | Paketlenecek ana Python dosyası |

### Adım 3: .exe Dosyasını Bulun
İşlem 1-3 dakika sürer. Tamamlandığında klasörünüzde şunlar oluşur:

```
flower_story_management_system/
├── main.py
├── build/                    ← Geçici dosyalar (silebilirsiniz)
├── dist/                     ← İŞTE BURADA!
│   └── CicekciMusteriYonetim.exe   ← .exe dosyanız bu!
├── CicekciMusteriYonetim.spec  ← Yapılandırma dosyası (silebilirsiniz)
```

### Adım 4: .exe'yi Test Edin ve Masaüstüne Taşıyın
1. `dist` klasöründeki **`CicekciMusteriYonetim.exe`** dosyasına çift tıklayın.
2. Çalıştığını gördükten sonra bu dosyayı **masaüstüne kopyalayın**.
3. Artık çift tıklayarak istediğiniz zaman çalıştırabilirsiniz!

> ⚠️ **Önemli Not:** `.exe` ilk açıldığında, yanına otomatik olarak `musteriler.db` adında bir veritabanı dosyası oluşturur. Bu dosyada tüm müşteri kayıtlarınız tutulur. **`.exe` ile aynı klasörde kalmalı**, silmeyin!

---

## 🎨 BONUS: İkon (Logo) ile .exe Oluşturmak İsterseniz

Eğer .exe'nizin masaüstünde özel bir çiçek ikonuyla görünmesini isterseniz:

1. İnternetten bir `.ico` dosyası bulun (örn: çiçek ikonu) veya bir PNG'yi https://convertio.co/png-ico/ üzerinden ICO'ya çevirin.
2. `.ico` dosyasını proje klasörünüze koyun (örn: `cicek.ico`).
3. Komutu şöyle çalıştırın:

```bash
pyinstaller --onefile --windowed --icon=cicek.ico --name "CicekciMusteriYonetim" main.py
```

---

## 🔧 3. Sorun Giderme

### "pyinstaller komutu tanınmıyor" hatası alıyorum
- Python kurulumunda "Add to PATH" işaretlenmemiş olabilir. Şu komutu deneyin:
  ```bash
  python -m PyInstaller --onefile --windowed --name "CicekciMusteriYonetim" main.py
  ```

### .exe açılmıyor / hemen kapanıyor
- `--windowed` parametresini kaldırarak hata mesajını görün:
  ```bash
  pyinstaller --onefile --name "CicekciMusteriYonetim" main.py
  ```
  Çıkan siyah ekrandaki mesajı not edin.

### Antivirüs .exe'yi siliyor
- PyInstaller ile oluşturulan .exe'ler bazen yanlışlıkla virüs sanılır. Normal bir durumdur.
- Antivirüs ayarlarınızdan dosyayı **istisna listesine** ekleyin.

### .exe çok büyük (50+ MB)
- Normal bir durumdur. PyInstaller, Python yorumlayıcısının tamamını paketler.
- Boyutu küçültmek için `--onefile` yerine `--onedir` kullanabilirsiniz, ama bu klasör paylaşımını gerektirir.

---

## 🌟 4. Uygulama Özellikleri

| Özellik | Açıklama |
|---------|----------|
| 👤 Müşteri Ekleme | Telefon, isim, soyisim, adres, doğum günü, yıldönümü, notlar |
| 🔍 Hızlı Arama | Telefon veya isim üzerinden anlık arama (yazarken) |
| ✏️ Düzenleme | Tablodan müşteri seçip "Düzenle" ile veya çift tıklama |
| 🗑️ Silme | Seçili müşteriyi onay penceresi sonrası silme |
| 🎉 Hatırlatıcı | Önümüzdeki **15 gün** içindeki doğum günleri, yıldönümleri **VE resmi tatiller** (Anneler Günü, Babalar Günü, Sevgililer Günü, Kadınlar Günü, Öğretmenler Günü) |
| 📋 Detay / Sipariş Geçmişi | Müşteriye **çift tıklayarak** detay penceresini açın — kişisel bilgilerinin yanı sıra geçmiş siparişlerini görür, yeni sipariş ekleyebilir veya silebilirsiniz |
| 🛡️ Hata Kontrolü | Eksik alan, geçersiz tarih (gün 1-31, ay 1-12, yıl 1900-2200), mükerrer telefon uyarıları |
| 🔢 Telefon Kısıtlaması | Telefon alanı yalnızca rakam kabul eder, **tam 10 hane** zorunludur, fazlası yazılamaz |
| 🔃 Akıllı Sıralama | **İsim** sütununa tıklayarak A-Z / Z-A sıralama; **Yıldönümü** sütununa tıklayarak bugüne en yakın tarihe göre sıralama (tekrar tıklayınca normale döner) |
| 💾 Otomatik Kayıt | SQLite veritabanı, internet gerektirmez |

### Form Kullanım İpuçları:
- **Zorunlu Alanlar:** Telefon, İsim, Soyisim (yıldız `*` ile işaretli)
- **Tarih Formatı:** GG.AA.YYYY (örn: `15.03.1985`)
- **Telefon:** Yalnızca rakam, tam 10 hane (fazlası yazılamaz)
- **Aynı Telefon:** İki farklı müşteriye aynı telefon eklenmez (otomatik uyarı)
- **Adres ve Notlar:** Çok satırlı, uzun metin yazabilirsiniz

---

## 💾 Veritabanı Yedekleme

Müşteri verileriniz `musteriler.db` adlı dosyada tutulur. Yedekleme için:
1. `.exe` ile aynı klasördeki `musteriler.db` dosyasını **bir USB belleğe veya bulut hesabınıza kopyalayın**.
2. Verileri geri yüklemek için bu dosyayı eski yerine kopyalamanız yeterlidir.

---

İyi çalışmalar! 🌸💐
