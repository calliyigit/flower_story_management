# -*- coding: utf-8 -*-
"""
Veritabani islemleri - SQLite katmani
Cicekci dukkani musteri yonetim sisteminin tum DB fonksiyonlari burada.
"""
import sqlite3
import os
import sys
from datetime import datetime, date, timedelta


def get_db_path():
    """Veritabani dosyasinin tam yolunu dondurur (.exe ile uyumlu)."""
    if getattr(sys, 'frozen', False):
        # PyInstaller ile paketlendiginde
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "musteriler.db")


DB_PATH = get_db_path()


def _connect():
    """Veritabanina baglanti acar. timeout=10sn -> 'database is locked' hatasini onler.
    WAL modu ile birden fazla okuma/yazma islemi guvenle yapilir.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    # WAL modu: ayni anda okuma ve yazma yapilabilmesini saglar (kilit hatalarini azaltir)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def init_db():
    """Veritabanini ve gerekli tablolari olusturur."""
    conn = _connect()
    try:
        c = conn.cursor()
        # Musteriler tablosu - telefon birincil anahtar
        c.execute("""CREATE TABLE IF NOT EXISTS musteriler (
            telefon TEXT PRIMARY KEY,
            isim TEXT NOT NULL,
            soyisim TEXT NOT NULL,
            adres TEXT,
            dogum_gunu TEXT,
            evlilik_yildonumu TEXT,
            notlar TEXT,
            kayit_tarihi TEXT)""")
        # Siparisler tablosu - musteriye bagli
        c.execute("""CREATE TABLE IF NOT EXISTS siparisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefon TEXT NOT NULL,
            tarih TEXT NOT NULL,
            urun TEXT NOT NULL,
            fiyat TEXT,
            ozel_gun TEXT,
            notlar TEXT,
            FOREIGN KEY (telefon) REFERENCES musteriler(telefon) ON DELETE CASCADE)""")
        conn.commit()
    finally:
        conn.close()


# ============================================================
# MUSTERI ISLEMLERI
# ============================================================

def musteri_ekle(telefon, isim, soyisim, adres, dogum, evlilik, notlar):
    """Yeni musteri ekler. Ayni telefon varsa IntegrityError firlatir."""
    conn = _connect()
    try:
        conn.execute("""INSERT INTO musteriler
            (telefon, isim, soyisim, adres, dogum_gunu, evlilik_yildonumu, notlar, kayit_tarihi)
            VALUES (?,?,?,?,?,?,?,?)""",
            (telefon, isim, soyisim, adres, dogum, evlilik, notlar,
             datetime.now().strftime("%d.%m.%Y %H:%M")))
        conn.commit()
    finally:
        conn.close()


def musteri_guncelle(eski_tel, telefon, isim, soyisim, adres, dogum, evlilik, notlar):
    """Mevcut musteriyi gunceller (telefon degisirse siparisler de takip eder)."""
    conn = _connect()
    try:
        if eski_tel != telefon:
            conn.execute("UPDATE siparisler SET telefon=? WHERE telefon=?",
                         (telefon, eski_tel))
        conn.execute("""UPDATE musteriler SET telefon=?, isim=?, soyisim=?, adres=?,
            dogum_gunu=?, evlilik_yildonumu=?, notlar=? WHERE telefon=?""",
            (telefon, isim, soyisim, adres, dogum, evlilik, notlar, eski_tel))
        conn.commit()
    finally:
        conn.close()


def musteri_sil(telefon):
    """Musteriyi ve tum siparislerini siler."""
    conn = _connect()
    try:
        conn.execute("DELETE FROM siparisler WHERE telefon=?", (telefon,))
        conn.execute("DELETE FROM musteriler WHERE telefon=?", (telefon,))
        conn.commit()
    finally:
        conn.close()


def musteri_ara(arama=""):
    """Telefon veya isim/soyisim ile arama. Bos ise tumunu listeler."""
    conn = _connect()
    try:
        if not arama.strip():
            rows = conn.execute("""SELECT telefon, isim, soyisim, dogum_gunu,
                evlilik_yildonumu, adres, notlar FROM musteriler ORDER BY isim""").fetchall()
        else:
            like = f"%{arama}%"
            rows = conn.execute("""SELECT telefon, isim, soyisim, dogum_gunu,
                evlilik_yildonumu, adres, notlar FROM musteriler
                WHERE telefon LIKE ? OR isim LIKE ? OR soyisim LIKE ?
                ORDER BY isim""", (like, like, like)).fetchall()
        return rows
    finally:
        conn.close()


def musteri_getir(telefon):
    """Tek musterinin tum bilgilerini dondurur."""
    conn = _connect()
    try:
        row = conn.execute("""SELECT telefon, isim, soyisim, adres, dogum_gunu,
            evlilik_yildonumu, notlar, kayit_tarihi FROM musteriler
            WHERE telefon=?""", (telefon,)).fetchone()
        return row
    finally:
        conn.close()


# ============================================================
# SIPARIS ISLEMLERI
# ============================================================

def siparis_ekle(telefon, tarih, urun, fiyat, ozel_gun, notlar):
    """Belirli bir musteriye yeni siparis ekler."""
    conn = _connect()
    try:
        conn.execute("""INSERT INTO siparisler (telefon, tarih, urun, fiyat, ozel_gun, notlar)
            VALUES (?,?,?,?,?,?)""", (telefon, tarih, urun, fiyat, ozel_gun, notlar))
        conn.commit()
    finally:
        conn.close()


def siparis_sil(siparis_id):
    """Verilen ID'ye sahip siparisi siler."""
    conn = _connect()
    try:
        conn.execute("DELETE FROM siparisler WHERE id=?", (siparis_id,))
        conn.commit()
    finally:
        conn.close()


def musteri_siparisleri(telefon):
    """Bir musterinin tum siparislerini en yeniden eskiye dondurur."""
    conn = _connect()
    try:
        rows = conn.execute("""SELECT id, tarih, urun, fiyat, ozel_gun, notlar
            FROM siparisler WHERE telefon=? ORDER BY id DESC""", (telefon,)).fetchall()
        return rows
    finally:
        conn.close()


# ============================================================
# RESMI TATILLER VE YAKLASAN GUNLER
# ============================================================

def nth_haftanin_gunu(yil, ay, n, hedef_haftagunu):
    """Bir ayin n. belirli haftagununu hesaplar.
    hedef_haftagunu: 0=Pazartesi, 1=Sali, ..., 6=Pazar
    Ornek: Anneler Gunu = Mayis 2. Pazar = nth_haftanin_gunu(yil, 5, 2, 6)
    """
    ilk = date(yil, ay, 1)
    fark = (hedef_haftagunu - ilk.weekday()) % 7
    return ilk + timedelta(days=fark + (n - 1) * 7)


def ayin_nth_haftasinin_ilk_gunu(yil, ay, n):
    """Bir ayin n. haftasinin Pazartesi gununu dondurur."""
    ilk = date(yil, ay, 1)
    # 1. haftanin Pazartesisi: ayin ilk Pazartesisi veya onceki Pazartesi
    ilk_pazartesi = ilk - timedelta(days=ilk.weekday())
    if ilk_pazartesi < ilk:
        ilk_pazartesi += timedelta(weeks=1)
    return ilk_pazartesi + timedelta(weeks=n - 1)


def ayin_son_haftaici_gunu(yil, ay, hedef_haftagunu):
    """Bir ayin son belirli hafta gununu dondurur (orn: son Pazartesi)."""
    son_gun = date(yil, ay + 1, 1) - timedelta(days=1) if ay < 12 else date(yil, 12, 31)
    fark = (son_gun.weekday() - hedef_haftagunu) % 7
    return son_gun - timedelta(days=fark)


def resmi_tatiller(yil):
    """Verilen yilin tum ozel gun ve haftalarini dondurur."""
    gunler = []

    # --- SABIT TARIHLI GUNLER ---
    gunler += [
        ("Uluslararasi Temiz Hava Gunu",        date(yil,  9,  7)),
        ("Gaziler Gunu",                         date(yil,  9, 19)),
        ("15 Temmuz Demokrasi ve Milli Birlik Gunu", date(yil, 7, 15)),
        ("Dunya Okul Sutu Gunu",                 date(yil,  9, 28)),
        ("Hayvanlar Koruma Gunu",                date(yil, 10,  4)),
        ("Ahilik Kulturu Haftasi Baslangic",     date(yil, 10,  8)),
        ("Dunya Afet Azaltma Gunu",              date(yil, 10, 13)),
        ("Birlesmis Milletler Gunu",             date(yil, 10, 24)),
        ("Cumhuriyet Bayrami",                   date(yil, 10, 29)),
        ("Dunya Diyabet Gunu",                   date(yil, 11, 14)),
        ("Afet Egitimi Hazirlik Gunu",           date(yil, 11, 12)),
        ("Dunya Felsefe Gunu",                   date(yil, 11, 20)),
        ("Dunya Cocuk Haklari Gunu",             date(yil, 11, 20)),
        ("Ogretmenler Gunu",                     date(yil, 11, 24)),
        ("Dunya Engelliler Gunu",                date(yil, 12,  3)),
        ("Dunya Madenciler Gunu",                date(yil, 12,  4)),
        ("Turk Kadinina Secme Secilme Hakki",    date(yil, 12,  5)),
        ("Mevlana Haftasi Baslangic",            date(yil, 12,  7)),
        ("Insan Haklari ve Demokrasi Haftasi",   date(yil, 12, 10)),
        ("Tutum Yatirim Turk Mallari Haftasi",   date(yil, 12, 12)),
        ("Mehmet Akif Ersoy Anma Haftasi",       date(yil, 12, 20)),
        ("Dunya Kadinlar Gunu",                  date(yil,  3,  8)),
        ("Bilim ve Teknoloji Haftasi",           date(yil,  3,  8)),
        ("Istiklal Marsinin Kabulu",              date(yil,  3, 12)),
        ("Sehitler Gunu",                        date(yil,  3, 18)),
        ("Dunya Su Gunu",                        date(yil,  3, 22)),
        ("Dunya Tiyatrolar Gunu",                date(yil,  3, 27)),
        ("Dunya Otizm Farkindalik Gunu",         date(yil,  4,  2)),
        ("Kisisel Verileri Koruma Gunu",         date(yil,  4,  7)),
        ("Dunya Saglik Gunu",                    date(yil,  4,  7)),
        ("Ulusal Egemenlik ve Cocuk Bayrami",    date(yil,  4, 23)),
        ("Dunya Fikri Mulkiyet Gunu",            date(yil,  4, 26)),
        ("Is Sagligi ve Guvenligi Haftasi",      date(yil,  5,  4)),
        ("Ataturk'u Anma Genclik ve Spor Bayrami", date(yil, 5, 19)),
        ("Etik Gunu",                            date(yil,  5, 25)),
        ("Istanbul'un Fethi",                    date(yil,  5, 29)),
        ("Zafer Bayrami",                        date(yil,  8, 30)),
        ("Sevgililer Gunu",                      date(yil,  2, 14)),
        ("Yesilay Haftasi Baslangic",            date(yil,  3,  1)),
        ("Orman Haftasi Baslangic",              date(yil,  3, 21)),
        ("Kanser Haftasi Baslangic",             date(yil,  4,  1)),
        ("Turizm Haftasi Baslangic",             date(yil,  4, 15)),
        ("Engelliler Haftasi Baslangic",         date(yil,  5, 10)),
        ("Muzeler Haftasi Baslangic",            date(yil,  5, 18)),
        ("Agiz Dis Sagligi Haftasi Baslangic",   date(yil, 11, 21)),
        ("Losemili Cocuklar Haftasi Baslangic",  date(yil, 11,  2)),
        ("Ataturk Haftasi Baslangic",            date(yil, 11, 10)),
        ("Organ Bagisi ve Nakli Haftasi",        date(yil, 11,  3)),
        ("Kizilay Haftasi Baslangic",            date(yil, 10, 29)),
    ]

    # --- HESAPLANMASI GEREKEN GUNLER ---
    # Eylul ayinin ikinci Cumartesisi -> Dunya Ilk Yardim Gunu
    gunler.append(("Dunya Ilk Yardim Gunu", nth_haftanin_gunu(yil, 9, 2, 5)))

    # Ekim ayinin ilk haftasinin Persembesi -> Dunya Disleksi Gunu
    ekim_ilk_hafta_bas = ayin_nth_haftasinin_ilk_gunu(yil, 10, 1)
    gunler.append(("Disleksi Haftasi Baslangic", ekim_ilk_hafta_bas))
    gunler.append(("Dunya Disleksi Gunu", ekim_ilk_hafta_bas + timedelta(days=3)))

    # Ocak ayinin 2. haftasi -> Enerji Tasarrufu Haftasi
    gunler.append(("Enerji Tasarrufu Haftasi", ayin_nth_haftasinin_ilk_gunu(yil, 1, 2)))

    # Subat ayinin son Pazartesisi -> Vergi Haftasi
    gunler.append(("Vergi Haftasi", ayin_son_haftaici_gunu(yil, 2, 0)))

    # Mart ayinin ilk haftasi -> Girisimcilik Haftasi
    gunler.append(("Girisimcilik Haftasi", ayin_nth_haftasinin_ilk_gunu(yil, 3, 1)))

    # Mart ayinin son Pazartesisi -> Kutuphaneler Haftasi
    gunler.append(("Kutuphaneler Haftasi", ayin_son_haftaici_gunu(yil, 3, 0)))

    # Mayis ayinin 2. Pazari -> Anneler Gunu
    gunler.append(("Anneler Gunu", nth_haftanin_gunu(yil, 5, 2, 6)))

    # Mayis ayinin 2. haftasi -> Vakiflar Haftasi
    gunler.append(("Vakiflar Haftasi", ayin_nth_haftasinin_ilk_gunu(yil, 5, 2)))

    # Mayis ayinin ilk haftasi
    gunler.append(("Bilisim Haftasi", ayin_nth_haftasinin_ilk_gunu(yil, 5, 1)))
    gunler.append(("Trafik ve Ilkyardim Haftasi", ayin_nth_haftasinin_ilk_gunu(yil, 5, 1)))

    # Haziran ayinin ilk haftasi
    gunler.append(("Hayat Boyu Ogrenme Haftasi", ayin_nth_haftasinin_ilk_gunu(yil, 6, 1)))

    # Haziran ayinin 2. haftasi
    gunler.append(("Cevre ve Iklim Degisikligi Haftasi", ayin_nth_haftasinin_ilk_gunu(yil, 6, 2)))

    # Haziran ayinin 3. Pazari -> Babalar Gunu
    gunler.append(("Babalar Gunu", nth_haftanin_gunu(yil, 6, 3, 6)))

    # Diger sabit hafta baslangiclar
    gunler.append(("Tuketiciyi Koruma Haftasi", date(yil, 3, 15)))
    gunler.append(("Nevruz / Turk Dunyasi Haftasi", date(yil, 3, 21)))
    gunler.append(("Yaslilar Haftasi", date(yil, 3, 18)))

    # Eylul ayinin 3. haftasi -> Ilkogretim Haftasi
    ilkogretim_bas = ayin_nth_haftasinin_ilk_gunu(yil, 9, 3)
    gunler.append(("Ilkogretim Haftasi", ilkogretim_bas))
    gunler.append(("Ogrenciler Gunu", ilkogretim_bas + timedelta(days=6)))

    return gunler


def yaklasan_ozel_gunler(gun_sayisi=15):
    """Onumuzdeki X gun icindeki tum ozel gunleri dondurur:
    1) Musteri dogum gunleri
    2) Musteri evlilik yildonumleri
    3) Resmi tatiller ve ozel gunler
    """
    bugun = date.today()
    yaklasanlar = []

    # 1) Musteri ozel gunleri
    conn = _connect()
    try:
        musteriler = conn.execute(
            "SELECT telefon, isim, soyisim, dogum_gunu, evlilik_yildonumu FROM musteriler"
        ).fetchall()
    finally:
        conn.close()

    for telefon, isim, soyisim, dogum, evlilik in musteriler:
        for tarih_str, baslik in [(dogum, "Dogum Gunu"), (evlilik, "Yildonumu")]:
            if not tarih_str:
                continue
            try:
                gun, ay, _ = tarih_str.split(".")
                t = date(bugun.year, int(ay), int(gun))
                if t < bugun:
                    t = date(bugun.year + 1, int(ay), int(gun))
                fark = (t - bugun).days
                if 0 <= fark <= gun_sayisi:
                    yaklasanlar.append({
                        "tip": "musteri",
                        "baslik": baslik,
                        "ad_soyad": f"{isim} {soyisim}",
                        "telefon": telefon,
                        "tarih": t.strftime("%d.%m"),
                        "kalan_gun": fark
                    })
            except (ValueError, AttributeError):
                continue

    # 2) Resmi tatiller ve ozel gunler (bu yil ve gelecek yil)
    for ad, t in resmi_tatiller(bugun.year) + resmi_tatiller(bugun.year + 1):
        fark = (t - bugun).days
        if 0 <= fark <= gun_sayisi:
            yaklasanlar.append({
                "tip": "resmi",
                "baslik": ad,
                "ad_soyad": "Tum musteriler icin",
                "telefon": "",
                "tarih": t.strftime("%d.%m"),
                "kalan_gun": fark
            })

    yaklasanlar.sort(key=lambda x: x["kalan_gun"])
    return yaklasanlar

# ============================================================
# DOGRULAMA YARDIMCILARI
# ============================================================

def tarih_dogrula(s):
    """GG.AA.YYYY formati ve mantik kontrolu. Bos tarih kabul edilir.
    - Gun: 1-31 arasi
    - Ay: 1-12 arasi
    - Yil: 1900-2200 arasi
    """
    if not s.strip():
        return True
    try:
        dt = datetime.strptime(s.strip(), "%d.%m.%Y")
        gun = dt.day
        ay = dt.month
        yil = dt.year
        if not (1 <= gun <= 31):
            return False
        if not (1 <= ay <= 12):
            return False
        if not (1900 <= yil <= 2200):
            return False
        return True
    except ValueError:
        return False


def telefon_dogrula(t):
    """Tam 10 haneli telefon numarasi kontrolu."""
    temiz = t.replace(" ", "").replace("-", "").replace("+", "")
    return temiz.isdigit() and len(temiz) == 10
