# -*- coding: utf-8 -*-
"""
Cicekci Dukkani - Musteri Yonetim Sistemi (Ana Arayuz)
======================================================
Yenilikler v2:
- Musteriye cift tiklayinca acilan detay penceresi
- Siparis ekleme, listeleme ve silme
- Resmi tatiller (Anneler Gunu, Babalar Gunu, Sevgililer Gunu, vb.)
  yaklasan ozel gunler panelinde gosterilir
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import date

# Veritabani fonksiyonlarini ayri modulden import et
from database import (
    init_db,
    musteri_ekle, musteri_guncelle, musteri_sil, musteri_ara, musteri_getir,
    siparis_ekle, siparis_sil, musteri_siparisleri,
    yaklasan_ozel_gunler, tarih_dogrula, telefon_dogrula,
)


# ============================================================
# OTOMATIK TARIH FORMATLAMA
# ============================================================
def tarih_formatla(event):
    """Entry'ye baglandiginda kullanicinin yazdigi rakamlari otomatik
    GG.AA.YYYY formatina cevirir.
    Ornek: kullanici '20052002' yazinca otomatik '20.05.2002' olur.
    """
    entry = event.widget
    # Yon tuslari, Tab, Shift gibi kontrol tuslarinda hicbir sey yapma
    if event.keysym in ("Left", "Right", "Up", "Down", "Tab",
                          "Shift_L", "Shift_R", "Control_L", "Control_R",
                          "Alt_L", "Alt_R", "Home", "End"):
        return

    metin = entry.get()
    # Sadece rakamlari al, en fazla 8 rakam
    rakamlar = "".join(c for c in metin if c.isdigit())[:8]

    # Rakam sayisina gore formatla
    if len(rakamlar) >= 5:
        yeni = f"{rakamlar[:2]}.{rakamlar[2:4]}.{rakamlar[4:]}"
    elif len(rakamlar) >= 3:
        yeni = f"{rakamlar[:2]}.{rakamlar[2:]}"
    else:
        yeni = rakamlar

    # Sadece gercekten degisiklik varsa entry'yi guncelle
    # (Gereksiz yere imleci tasimamak icin)
    if yeni != metin:
        entry.delete(0, tk.END)
        entry.insert(0, yeni)
        # Imleci en sona getir
        entry.icursor(tk.END)


def tarih_entry_baglar(entry):
    """Bir Entry widget'ina otomatik tarih formatlama ozelligini ekler."""
    entry.bind("<KeyRelease>", tarih_formatla)


# ============================================================
# MUSTERI DETAY PENCERESI (Sipariş geçmişi içerir)
# ============================================================
class MusteriDetayPenceresi(tk.Toplevel):
    """Musteriye cift tiklayinca acilan detay penceresi."""

    def __init__(self, parent, telefon):
        super().__init__(parent)
        self.telefon = telefon
        self.title(f"Musteri Detaylari - {telefon}")
        self.geometry("900x650")
        self.configure(bg="#fdf2f8")
        self.transient(parent)
        self._arayuz()
        self._yukle()

    def _arayuz(self):
        # Ust baslik
        bs = tk.Frame(self, bg="#ec4899", height=50)
        bs.pack(fill="x")
        bs.pack_propagate(False)
        self.baslik_label = tk.Label(bs, text="Musteri Detaylari",
                                       font=("Segoe UI", 14, "bold"),
                                       bg="#ec4899", fg="white")
        self.baslik_label.pack(pady=12)

        # Kisisel bilgi karti
        bilgi = tk.LabelFrame(self, text=" Kisisel Bilgiler ",
                                font=("Segoe UI", 10, "bold"),
                                bg="#fdf2f8", fg="#831843", padx=15, pady=10)
        bilgi.pack(fill="x", padx=10, pady=10)
        self.bilgi_lbl = {}
        alanlar = [
            ("Telefon:", "telefon"),
            ("Ad Soyad:", "ad_soyad"),
            ("Dogum Gunu:", "dogum"),
            ("Evlilik Yildonumu:", "evlilik"),
            ("Adres:", "adres"),
            ("Notlar:", "notlar"),
            ("Kayit Tarihi:", "kayit"),
        ]
        for i, (et, key) in enumerate(alanlar):
            tk.Label(bilgi, text=et, font=("Segoe UI", 10, "bold"),
                     bg="#fdf2f8", fg="#831843").grid(row=i, column=0,
                                                        sticky="nw", pady=2, padx=5)
            lbl = tk.Label(bilgi, text="-", font=("Segoe UI", 10),
                           bg="#fdf2f8", fg="#1f2937", anchor="w",
                           justify="left", wraplength=700)
            lbl.grid(row=i, column=1, sticky="w", pady=2, padx=5)
            self.bilgi_lbl[key] = lbl

        # Siparis gecmisi bolumu
        sip = tk.LabelFrame(self, text=" Siparis Gecmisi ",
                              font=("Segoe UI", 10, "bold"),
                              bg="#fdf2f8", fg="#831843", padx=10, pady=10)
        sip.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        btn = tk.Frame(sip, bg="#fdf2f8")
        btn.pack(fill="x", pady=(0, 5))
        ttk.Button(btn, text="Yeni Siparis Ekle", style="Yesil.TButton",
                   command=self._yeni_siparis).pack(side="left", padx=2)
        ttk.Button(btn, text="Secili Siparisi Sil", style="Kirmizi.TButton",
                   command=self._siparis_sil).pack(side="left", padx=2)
        ttk.Button(btn, text="Kapat", style="Gri.TButton",
                   command=self.destroy).pack(side="right", padx=2)

        # Siparis tablosu
        tf = tk.Frame(sip, bg="#fdf2f8")
        tf.pack(fill="both", expand=True)
        cols = ("id", "tarih", "urun", "fiyat", "ozel_gun", "notlar")
        self.s_tree = ttk.Treeview(tf, columns=cols, show="headings", height=10)
        for c, h, w in [("id", "No", 50), ("tarih", "Tarih", 100),
                         ("urun", "Urun", 250), ("fiyat", "Fiyat", 90),
                         ("ozel_gun", "Ozel Gun", 130), ("notlar", "Notlar", 200)]:
            self.s_tree.heading(c, text=h)
            anchor = "center" if c in ("id", "tarih") else "w"
            self.s_tree.column(c, width=w, anchor=anchor)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.s_tree.yview)
        self.s_tree.configure(yscrollcommand=sb.set)
        self.s_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.toplam_label = tk.Label(sip, text="", font=("Segoe UI", 9, "italic"),
                                       bg="#fdf2f8", fg="#831843")
        self.toplam_label.pack(anchor="w", pady=(5, 0))

    def _yukle(self):
        """Musteri bilgilerini ve siparis listesini yukler."""
        m = musteri_getir(self.telefon)
        if not m:
            messagebox.showerror("Hata", "Musteri bulunamadi.")
            self.destroy()
            return
        tel, isim, soyisim, adres, dogum, evlilik, notlar, kayit = m
        self.baslik_label.config(text=f"{isim} {soyisim}")
        self.bilgi_lbl["telefon"].config(text=tel)
        self.bilgi_lbl["ad_soyad"].config(text=f"{isim} {soyisim}")
        self.bilgi_lbl["dogum"].config(text=dogum or "-")
        self.bilgi_lbl["evlilik"].config(text=evlilik or "-")
        self.bilgi_lbl["adres"].config(text=adres or "-")
        self.bilgi_lbl["notlar"].config(text=notlar or "-")
        self.bilgi_lbl["kayit"].config(text=kayit or "-")

        for r in self.s_tree.get_children():
            self.s_tree.delete(r)
        sipler = musteri_siparisleri(self.telefon)
        for s in sipler:
            self.s_tree.insert("", "end", values=s)
        if sipler:
            self.toplam_label.config(text=f"Toplam {len(sipler)} siparis kaydi.")
        else:
            self.toplam_label.config(text="Bu musteriye ait henuz siparis kaydi yok.")

    def _yeni_siparis(self):
        SiparisFormPenceresi(self, self.telefon, self._yukle)

    def _siparis_sil(self):
        sec = self.s_tree.selection()
        if not sec:
            messagebox.showwarning("Secim Yok",
                                    "Lutfen silmek istediginiz siparisi secin.",
                                    parent=self)
            return
        d = self.s_tree.item(sec[0], "values")
        if messagebox.askyesno("Silme Onayi",
                                f"'{d[2]}' siparisini silmek istediginize emin misiniz?",
                                parent=self):
            try:
                siparis_sil(d[0])
                self._yukle()
            except Exception as e:
                messagebox.showerror("Hata", f"Silme basarisiz: {e}", parent=self)


# ============================================================
# SIPARIS FORM PENCERESI
# ============================================================
class SiparisFormPenceresi(tk.Toplevel):
    """Yeni siparis eklemek icin acilir form."""

    def __init__(self, parent, telefon, yenile_cb):
        super().__init__(parent)
        self.telefon = telefon
        self.yenile_cb = yenile_cb
        self.title("Yeni Siparis Ekle")
        self.geometry("500x420")
        self.configure(bg="#fdf2f8")
        self.transient(parent)
        self.grab_set()
        self._arayuz()

    def _arayuz(self):
        tk.Label(self, text="Yeni Siparis Kaydi",
                 font=("Segoe UI", 14, "bold"),
                 bg="#ec4899", fg="white", pady=10).pack(fill="x")

        f = tk.Frame(self, bg="#fdf2f8", padx=20, pady=15)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="Siparis Tarihi (GG.AA.YYYY) *",
                 font=("Segoe UI", 10), bg="#fdf2f8",
                 fg="#831843").grid(row=0, column=0, sticky="w", pady=4)
        self.tarih_e = tk.Entry(f, font=("Segoe UI", 10), width=30, relief="solid", bd=1)
        self.tarih_e.grid(row=0, column=1, pady=4, padx=10, sticky="w")
        self.tarih_e.insert(0, date.today().strftime("%d.%m.%Y"))
        # Otomatik nokta ekleme: 20052026 -> 20.05.2026
        tarih_entry_baglar(self.tarih_e)

        tk.Label(f, text="Urun / Cicek Aciklamasi *",
                 font=("Segoe UI", 10), bg="#fdf2f8",
                 fg="#831843").grid(row=1, column=0, sticky="w", pady=4)
        self.urun_e = tk.Entry(f, font=("Segoe UI", 10), width=30, relief="solid", bd=1)
        self.urun_e.grid(row=1, column=1, pady=4, padx=10, sticky="w")

        tk.Label(f, text="Fiyat (orn: 750 TL)",
                 font=("Segoe UI", 10), bg="#fdf2f8",
                 fg="#831843").grid(row=2, column=0, sticky="w", pady=4)
        self.fiyat_e = tk.Entry(f, font=("Segoe UI", 10), width=30, relief="solid", bd=1)
        self.fiyat_e.grid(row=2, column=1, pady=4, padx=10, sticky="w")

        tk.Label(f, text="Hangi Ozel Gun Icin",
                 font=("Segoe UI", 10), bg="#fdf2f8",
                 fg="#831843").grid(row=3, column=0, sticky="w", pady=4)
        self.ozel_combo = ttk.Combobox(f, font=("Segoe UI", 10), width=28,
                                         values=["", "Dogum Gunu",
                                                 "Evlilik Yildonumu",
                                                 "Sevgililer Gunu",
                                                 "Anneler Gunu",
                                                 "Babalar Gunu",
                                                 "Kadinlar Gunu",
                                                 "Ogretmenler Gunu",
                                                 "Yilbasi", "Dugun",
                                                 "Cenaze", "Acilis", "Diger"])
        self.ozel_combo.grid(row=3, column=1, pady=4, padx=10, sticky="w")

        tk.Label(f, text="Notlar", font=("Segoe UI", 10),
                 bg="#fdf2f8", fg="#831843").grid(row=4, column=0,
                                                    sticky="nw", pady=4)
        self.notlar_t = tk.Text(f, font=("Segoe UI", 10), width=30, height=4,
                                 relief="solid", bd=1, wrap="word")
        self.notlar_t.grid(row=4, column=1, pady=4, padx=10, sticky="w")

        bf = tk.Frame(f, bg="#fdf2f8")
        bf.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(bf, text="Kaydet", style="Yesil.TButton",
                   command=self._kaydet).pack(side="left", padx=5)
        ttk.Button(bf, text="Iptal", style="Gri.TButton",
                   command=self.destroy).pack(side="left", padx=5)

    def _kaydet(self):
        tarih = self.tarih_e.get().strip()
        urun = self.urun_e.get().strip()
        fiyat = self.fiyat_e.get().strip()
        ozel = self.ozel_combo.get().strip()
        notlar = self.notlar_t.get("1.0", "end-1c").strip()

        if not tarih or not urun:
            messagebox.showwarning("Eksik Bilgi",
                                    "Tarih ve urun zorunludur.", parent=self)
            return
        if not tarih_dogrula(tarih):
            messagebox.showwarning("Gecersiz Tarih",
                                    "Tarih GG.AA.YYYY formatinda olmali.\n"
                                    "Gun: 1-31, Ay: 1-12, Yil: 1900-2200",
                                    parent=self)
            return
        try:
            siparis_ekle(self.telefon, tarih, urun, fiyat, ozel, notlar)
            messagebox.showinfo("Basarili", "Siparis kaydedildi.", parent=self)
            self.yenile_cb()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Hata",
                                  f"Siparis kaydedilemedi: {e}", parent=self)


# ============================================================
# ANA UYGULAMA
# ============================================================
class CicekciUygulamasi:
    """Ana uygulama sinifi - musteri listesi, form, yaklasan gunler."""

    def __init__(self, root):
        self.root = root
        self.root.title("Cicekci Dukkani - Musteri Yonetim Sistemi")
        self.root.geometry("1320x740")
        self.root.configure(bg="#fdf2f8")
        self.duzenleme_modu = False
        self.duzenlenen_telefon = None
        self.yildonumu_sirali = False  # False = normal, True = tarihe gore sirali
        self.isim_sirala_yon = None    # None = sirali degil, "az" = A-Z, "za" = Z-A
        self._stil_ayarla()
        self._arayuz()
        self._listeyi_yenile()
        self._yaklasan_yenile()

    def _stil_ayarla(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Treeview", background="white", foreground="black",
                    rowheight=28, fieldbackground="white",
                    font=("Segoe UI", 10))
        s.configure("Treeview.Heading", background="#ec4899",
                    foreground="white", font=("Segoe UI", 10, "bold"))
        s.map("Treeview", background=[("selected", "#f9a8d4")])
        # Buton stilleri
        for ad, bg, hover in [("Pembe", "#ec4899", "#db2777"),
                                ("Yesil", "#10b981", "#059669"),
                                ("Kirmizi", "#ef4444", "#dc2626"),
                                ("Gri", "#6b7280", "#4b5563"),
                                ("Mor", "#8b5cf6", "#7c3aed")]:
            s.configure(f"{ad}.TButton", background=bg, foreground="white",
                        font=("Segoe UI", 10, "bold"), padding=8)
            s.map(f"{ad}.TButton", background=[("active", hover)])

    def _arayuz(self):
        # Ust baslik
        bs = tk.Frame(self.root, bg="#ec4899", height=60)
        bs.pack(fill="x")
        bs.pack_propagate(False)
        tk.Label(bs, text="Cicekci Dukkani - Musteri Yonetim Sistemi",
                 font=("Segoe UI", 18, "bold"),
                 bg="#ec4899", fg="white").pack(pady=12)

        ana = tk.Frame(self.root, bg="#fdf2f8")
        ana.pack(fill="both", expand=True, padx=10, pady=10)
        sol = tk.Frame(ana, bg="#fdf2f8")
        sol.pack(side="left", fill="both", expand=True, padx=(0, 10))
        sag = tk.Frame(ana, bg="#fce7f3", width=320, relief="ridge", bd=2)
        sag.pack(side="right", fill="y")
        sag.pack_propagate(False)

        self._form_olustur(sol)
        self._liste_olustur(sol)
        self._yaklasan_panel(sag)

    def _form_olustur(self, parent):
        form = tk.LabelFrame(parent, text=" Musteri Bilgileri ",
                              font=("Segoe UI", 11, "bold"),
                              bg="#fdf2f8", fg="#831843", padx=15, pady=10)
        form.pack(fill="x", pady=(0, 10))
        self.giris = {}
        sf = tk.Frame(form, bg="#fdf2f8")
        sf.grid(row=0, column=0, sticky="nw", padx=(0, 20))
        sgf = tk.Frame(form, bg="#fdf2f8")
        sgf.grid(row=0, column=1, sticky="nw")

        # Telefon icin max 10 rakam dogrulama komutu
        vcmd_tel = (self.root.register(
            lambda yeni_deger: yeni_deger.isdigit() and len(yeni_deger) <= 10
                               or yeni_deger == ""
        ), "%P")

        alanlar = [("Telefon * (Musteri ID)", "telefon"),
                   ("Isim *", "isim"),
                   ("Soyisim *", "soyisim"),
                   ("Dogum Gunu (GG.AA.YYYY)", "dogum"),
                   ("Evlilik Yildonumu (GG.AA.YYYY)", "evlilik")]
        for i, (et, k) in enumerate(alanlar):
            tk.Label(sf, text=et, font=("Segoe UI", 9),
                     bg="#fdf2f8", fg="#831843").grid(row=i, column=0,
                                                        sticky="w", pady=3)
            if k == "telefon":
                e = tk.Entry(sf, width=25, font=("Segoe UI", 10),
                              relief="solid", bd=1,
                              validate="key", validatecommand=vcmd_tel)
            else:
                e = tk.Entry(sf, width=25, font=("Segoe UI", 10),
                              relief="solid", bd=1)
            e.grid(row=i, column=1, pady=3, padx=5)
            self.giris[k] = e
            # Tarih alanlarina otomatik nokta ekleme: 20052002 -> 20.05.2002
            if k in ("dogum", "evlilik"):
                tarih_entry_baglar(e)

        tk.Label(sgf, text="Adres", font=("Segoe UI", 9),
                 bg="#fdf2f8", fg="#831843").grid(row=0, column=0,
                                                    sticky="w", pady=3)
        self.adres = tk.Text(sgf, width=40, height=4,
                              font=("Segoe UI", 10),
                              relief="solid", bd=1, wrap="word")
        self.adres.grid(row=1, column=0, pady=3)
        tk.Label(sgf, text="Ekstra Notlar / Diger Ozel Gunler",
                 font=("Segoe UI", 9), bg="#fdf2f8",
                 fg="#831843").grid(row=2, column=0, sticky="w", pady=(8, 3))
        self.notlar = tk.Text(sgf, width=40, height=4,
                               font=("Segoe UI", 10),
                               relief="solid", bd=1, wrap="word")
        self.notlar.grid(row=3, column=0, pady=3)

        bf = tk.Frame(form, bg="#fdf2f8")
        bf.grid(row=1, column=0, columnspan=2, pady=(15, 0), sticky="ew")
        self.kaydet_btn = ttk.Button(bf, text="Kaydet",
                                       style="Yesil.TButton",
                                       command=self._kaydet)
        self.kaydet_btn.pack(side="left", padx=5)
        ttk.Button(bf, text="Formu Temizle", style="Gri.TButton",
                   command=self._formu_temizle).pack(side="left", padx=5)
        self.iptal_btn = ttk.Button(bf, text="Duzenlemeyi Iptal Et",
                                      style="Kirmizi.TButton",
                                      command=self._duzenlemeyi_iptal)

    def _liste_olustur(self, parent):
        af = tk.Frame(parent, bg="#fdf2f8")
        af.pack(fill="x", pady=(0, 5))
        tk.Label(af, text="Arama:", font=("Segoe UI", 10, "bold"),
                 bg="#fdf2f8", fg="#831843").pack(side="left", padx=(0, 5))
        self.arama = tk.Entry(af, width=25, font=("Segoe UI", 10),
                                relief="solid", bd=1)
        self.arama.pack(side="left", padx=5)
        self.arama.bind("<KeyRelease>",
                          lambda e: self._listeyi_yenile())
        ttk.Button(af, text="Temizle", style="Gri.TButton",
                   command=self._aramayi_temizle).pack(side="left", padx=5)
        ttk.Button(af, text="Sil", style="Kirmizi.TButton",
                   command=self._secileni_sil).pack(side="right", padx=2)
        ttk.Button(af, text="Duzenle", style="Pembe.TButton",
                   command=self._secileni_duzenle).pack(side="right", padx=2)
        ttk.Button(af, text="Detay / Siparisler", style="Mor.TButton",
                   command=self._secilenin_detayi).pack(side="right", padx=2)

        tk.Label(parent,
                 text="Ipucu: Bir musteriye cift tiklayarak siparis gecmisini gorebilirsiniz",
                 font=("Segoe UI", 9, "italic"),
                 bg="#fdf2f8", fg="#9f1239").pack(anchor="w", pady=(0, 5))

        tf = tk.Frame(parent, bg="#fdf2f8")
        tf.pack(fill="both", expand=True)
        cols = ("telefon", "isim", "soyisim", "dogum",
                "evlilik", "adres", "notlar")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", height=15)
        for c, h, w, a in [("telefon", "Telefon", 120, "w"),
                            ("isim", "Isim", 110, "w"),
                            ("soyisim", "Soyisim", 110, "w"),
                            ("dogum", "Dogum Gunu", 95, "center"),
                            ("evlilik", "Yildonumu", 95, "center"),
                            ("adres", "Adres", 200, "w"),
                            ("notlar", "Notlar", 180, "w")]:
            if c == "evlilik":
                self.tree.heading(c, text=h,
                                  command=self._yildonumu_sirala)
            elif c == "isim":
                self.tree.heading(c, text=h,
                                  command=self._isim_sirala)
            else:
                self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor=a)
        sb = ttk.Scrollbar(tf, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        # Cift tiklama = detay penceresi
        self.tree.bind("<Double-1>",
                         lambda e: self._secilenin_detayi())

    def _yildonumu_sirala(self):
        """Yildonumu basligina her tiklamada siralama / normal arasinda toggle yapar."""
        self.yildonumu_sirali = not self.yildonumu_sirali

        if not self.yildonumu_sirali:
            # Normal hale don: listeyi yeniden yukle
            self._listeyi_yenile()
            return

        bugun = date.today()

        def kalan_gun(tarih_str):
            if not tarih_str:
                return 9999
            try:
                parca = tarih_str.strip().split(".")
                gun, ay = int(parca[0]), int(parca[1])
                t = date(bugun.year, ay, gun)
                if t < bugun:
                    t = date(bugun.year + 1, ay, gun)
                return (t - bugun).days
            except Exception:
                return 9999

        satirlar = [(self.tree.set(k, "evlilik"), k)
                    for k in self.tree.get_children("")]
        satirlar.sort(key=lambda x: kalan_gun(x[0]))
        for idx, (_, k) in enumerate(satirlar):
            self.tree.move(k, "", idx)

    def _isim_sirala(self):
        """Isim basligina her tiklamada A-Z / Z-A siralamasi arasinda toggle yapar."""
        if self.isim_sirala_yon != "az":
            self.isim_sirala_yon = "az"
            ters = False
        else:
            self.isim_sirala_yon = "za"
            ters = True

        satirlar = [(self.tree.set(k, "isim").lower(), k)
                    for k in self.tree.get_children("")]
        satirlar.sort(key=lambda x: x[0], reverse=ters)
        for idx, (_, k) in enumerate(satirlar):
            self.tree.move(k, "", idx)

        ok = " ▲" if not ters else " ▼"
        self.tree.heading("isim", text="Isim" + ok)

    def _yaklasan_panel(self, parent):
        tk.Label(parent, text="Yaklasan Ozel Gunler",
                 font=("Segoe UI", 13, "bold"),
                 bg="#fce7f3", fg="#831843",
                 pady=10).pack(fill="x")
        tk.Label(parent, text="(Onumuzdeki 15 gun icinde)",
                 font=("Segoe UI", 9, "italic"),
                 bg="#fce7f3", fg="#9f1239").pack()

        lf = tk.Frame(parent, bg="#fce7f3")
        lf.pack(fill="both", expand=True, padx=10, pady=10)
        sb = tk.Scrollbar(lf)
        sb.pack(side="right", fill="y")
        self.y_listbox = tk.Listbox(lf, font=("Segoe UI", 10),
                                      bg="white", fg="#831843",
                                      selectbackground="#f9a8d4",
                                      relief="flat",
                                      yscrollcommand=sb.set)
        self.y_listbox.pack(side="left", fill="both", expand=True)
        sb.config(command=self.y_listbox.yview)
        ttk.Button(parent, text="Yenile", style="Pembe.TButton",
                   command=self._yaklasan_yenile).pack(pady=10, padx=10, fill="x")
        self.bilgi_label = tk.Label(parent, text="",
                                      font=("Segoe UI", 9),
                                      bg="#fce7f3", fg="#831843",
                                      wraplength=290)
        self.bilgi_label.pack(pady=10, padx=10)

    # --- Etkilesimler ---
    def _kaydet(self):
        tel = self.giris["telefon"].get().strip()
        isim = self.giris["isim"].get().strip()
        soyisim = self.giris["soyisim"].get().strip()
        dogum = self.giris["dogum"].get().strip()
        evlilik = self.giris["evlilik"].get().strip()
        adres = self.adres.get("1.0", "end-1c").strip()
        notlar = self.notlar.get("1.0", "end-1c").strip()

        if not tel or not isim or not soyisim:
            messagebox.showwarning("Eksik Bilgi",
                                    "Telefon, Isim ve Soyisim zorunludur.")
            return
        if not telefon_dogrula(tel):
            messagebox.showwarning("Gecersiz Telefon",
                                    "Telefon numarasi tam 10 haneli olmalidir.")
            return
        if not tarih_dogrula(dogum):
            messagebox.showwarning("Gecersiz Tarih",
                                    "Dogum gunu GG.AA.YYYY formatinda olmali.\n"
                                    "Gun: 1-31, Ay: 1-12, Yil: 1900-2200")
            return
        if not tarih_dogrula(evlilik):
            messagebox.showwarning("Gecersiz Tarih",
                                    "Yildonumu GG.AA.YYYY formatinda olmali.\n"
                                    "Gun: 1-31, Ay: 1-12, Yil: 1900-2200")
            return
        try:
            if self.duzenleme_modu:
                musteri_guncelle(self.duzenlenen_telefon, tel, isim, soyisim,
                                  adres, dogum, evlilik, notlar)
                messagebox.showinfo("Basarili",
                                      f"{isim} {soyisim} guncellendi.")
                self._duzenlemeyi_iptal()
            else:
                musteri_ekle(tel, isim, soyisim, adres, dogum, evlilik, notlar)
                messagebox.showinfo("Basarili",
                                      f"{isim} {soyisim} eklendi.")
                self._formu_temizle()
            self._listeyi_yenile()
            self._yaklasan_yenile()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata",
                                  f"Bu telefon numarasi ({tel}) zaten kayitli!")
        except Exception as e:
            messagebox.showerror("Hata", f"Islem basarisiz: {e}")

    def _formu_temizle(self):
        for e in self.giris.values():
            e.delete(0, tk.END)
        self.adres.delete("1.0", tk.END)
        self.notlar.delete("1.0", tk.END)

    def _aramayi_temizle(self):
        self.arama.delete(0, tk.END)
        self._listeyi_yenile()

    def _listeyi_yenile(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        try:
            for k in musteri_ara(self.arama.get()):
                self.tree.insert("", "end", values=k)
        except Exception as e:
            messagebox.showerror("DB Hata", f"Liste yuklenemedi: {e}")

    def _secileni_duzenle(self):
        sec = self.tree.selection()
        if not sec:
            messagebox.showwarning("Secim Yok",
                                    "Lutfen bir musteri secin.")
            return
        d = self.tree.item(sec[0], "values")
        self._formu_temizle()
        self.giris["telefon"].insert(0, d[0])
        self.giris["isim"].insert(0, d[1])
        self.giris["soyisim"].insert(0, d[2])
        self.giris["dogum"].insert(0, d[3] or "")
        self.giris["evlilik"].insert(0, d[4] or "")
        self.adres.insert("1.0", d[5] or "")
        self.notlar.insert("1.0", d[6] or "")
        self.duzenleme_modu = True
        self.duzenlenen_telefon = d[0]
        self.kaydet_btn.configure(text="Guncellemeyi Kaydet")
        self.iptal_btn.pack(side="left", padx=5)

    def _duzenlemeyi_iptal(self):
        self.duzenleme_modu = False
        self.duzenlenen_telefon = None
        self.kaydet_btn.configure(text="Kaydet")
        self.iptal_btn.pack_forget()
        self._formu_temizle()

    def _secileni_sil(self):
        sec = self.tree.selection()
        if not sec:
            messagebox.showwarning("Secim Yok",
                                    "Lutfen bir musteri secin.")
            return
        d = self.tree.item(sec[0], "values")
        if messagebox.askyesno("Silme Onayi",
                                f"'{d[1]} {d[2]}' musterisini ve TUM SIPARISLERINI silmek istediginize emin misiniz?\n"
                                "Bu islem geri alinamaz!"):
            try:
                musteri_sil(d[0])
                self._listeyi_yenile()
                self._yaklasan_yenile()
                if self.duzenleme_modu and self.duzenlenen_telefon == d[0]:
                    self._duzenlemeyi_iptal()
            except Exception as e:
                messagebox.showerror("Hata", f"Silme basarisiz: {e}")

    def _secilenin_detayi(self):
        """Cift tiklama veya 'Detay' butonu ile cagrilir."""
        sec = self.tree.selection()
        if not sec:
            messagebox.showwarning("Secim Yok",
                                    "Lutfen detayini gormek istediginiz musteriyi secin.")
            return
        d = self.tree.item(sec[0], "values")
        MusteriDetayPenceresi(self.root, d[0])

    def _yaklasan_yenile(self):
        """Yaklasan ozel gunler panelini gunceller (resmi tatiller dahil)."""
        self.y_listbox.delete(0, tk.END)
        try:
            yk = yaklasan_ozel_gunler(15)
            if not yk:
                self.y_listbox.insert(tk.END, "  Onumuzdeki 15 gun icinde")
                self.y_listbox.insert(tk.END, "  ozel gun bulunmuyor.")
                self.bilgi_label.config(text="Bugun rahat bir gun!")
                return
            for g in yk:
                if g["kalan_gun"] == 0:
                    onek = "BUGUN"
                elif g["kalan_gun"] == 1:
                    onek = "YARIN"
                else:
                    onek = f"{g['kalan_gun']} gun"
                # Resmi tatiller icin farkli ikon
                ikon = "[*]" if g["tip"] == "resmi" else "[#]"
                self.y_listbox.insert(tk.END,
                                        f"{ikon} {onek} - {g['baslik']}")
                self.y_listbox.insert(tk.END,
                                        f"    {g['ad_soyad']} ({g['tarih']})")
                if g["telefon"]:
                    self.y_listbox.insert(tk.END,
                                            f"    Tel: {g['telefon']}")
                self.y_listbox.insert(tk.END, "")
            self.bilgi_label.config(
                text=f"{len(yk)} adet yaklasan ozel gun var!\n[*] = Resmi tatil  [#] = Musteri ozel gunu")
        except Exception as e:
            self.y_listbox.insert(tk.END, f"Hata: {e}")


def main():
    try:
        init_db()
        root = tk.Tk()
        CicekciUygulamasi(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Kritik Hata",
                              f"Uygulama baslatilamadi:\n{e}")


if __name__ == "__main__":
    main()
