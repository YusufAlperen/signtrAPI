import re


class NLPProcessor:
    def __init__(self):
        self.unluler = "aeıioöuü"

        # Geniş ünlü uyumu: -a/-e ekleri için
        self.genis_uyum = {
            'a': 'a', 'ı': 'a', 'o': 'a', 'u': 'a',
            'e': 'e', 'i': 'e', 'ö': 'e', 'ü': 'e'
        }
        # Dar ünlü uyumu: -ı/-i/-u/-ü ekleri için
        self.dar_uyum = {
            'a': 'ı', 'ı': 'ı', 'o': 'u', 'u': 'u',
            'e': 'i', 'i': 'i', 'ö': 'ü', 'ü': 'ü'
        }

        # Özne kelimeleri — labels.txt'deki yazımla birebir
        self.ozne_kelimeleri = {
            "ben": "Ben", "sen": "Sen", "siz": "Siz",
            "biz": "Biz", "onlar": "Onlar", "o": "O"
        }

        # Soru kelimeleri
        self.soru_kelimeleri = {"nasıl", "neden", "nerede", "kim"}

        # Olumsuzluk tetikleyicileri
        self.olumsuz_kelimeleri = {"hayır", "olmaz", "yok", "hiç"}

        # Zaman belirteçleri
        self.gecmis_zamanlari = {"dun", "geçmiş"}
        self.gelecek_zamanlari = {"yarın"}

        # Kalıp ifadeler — labels.txt'deki boşluklu yazımla birebir eşleşir
        # cumle_kur'a gelen liste bu kelimeleri TEK eleman olarak içerebilir
        # ya da ayrı ayrı elemanlar olarak gelebilir; her iki durum ele alınır.
        self.kaliplar = {
            "teşekkür":        "Teşekkür ederim.",
            "geçmiş olsun":    "Geçmiş olsun.",
            "afiyet olsun":    "Afiyet olsun.",
            "hayırlı olsun":   "Hayırlı olsun.",
            "selam":           "Selam.",
            "hoşçakal":        "Hoşça kal.",
            "rica etmek":      "Rica ederim.",
            "maşallah":        "Maşallah.",
            "özür dilemek":    "Özür dilerim.",
            "bilgi vermek":    "Bilgi vereyim.",
        }

        # Fiil kökleri: labels.txt'deki tam yazım → çekim tabanı
        self.fiil_kokleri = {
            "acıkmak":          "acık",
            "ağlamak":          "ağla",
            "bakmak":           "bak",
            "beklemek":         "bekle",
            "bilgi vermek":     "ver",
            "çalışmak":         "çalış",
            "değiştirmek":      "değiştir",
            "devirmek":         "devir",
            "ezberlemek":       "ezbele",
            "getirmek":         "getir",
            "gitmek":           "git",
            "gelmek":           "gel",
            "görmek":           "gör",
            "göstermek":        "göster",
            "gülmek":           "gül",
            "içmek":            "iç",
            "ilgilenmemek":     "ilgilenme",   # zaten olumsuz kök
            "itmek":            "it",
            "kaçmak":           "kaç",
            "memnun olmak":     "ol",
            "özür dilemek":     "dile",
            "rica etmek":       "et",
            "sevmek":           "sev",
            "söylemek":         "söyle",
            "yapmak":           "yap",
            "yemek":            "ye",
            "yemek pişirmek":   "pişir",
        }

        # Otomatik geçmiş zamana alınan durumlar
        self.otomatik_gecmis = {"acıkmak", "hasta", "yorgun", "memnun olmak"}

        # Mekan isimleri — lokatif (-da/-de) eki alır
        self.mekanlar = {
            "ev", "okul", "hastane", "eczane", "bahçe", "Türkiye",
            "pazar", "orman", "oda", "mutfak", "tuvalet", "kavsak",
            "köprü", "yol"
        }

        # Sıfat/zarf — fiil almaz, niteleyen olarak durur
        self.sifatlar = {
            "iyi", "kotu", "çirkin", "hafif", "ağır", "dolu",
            "akıllı", "akılsız", "üzgün", "hasta", "yorgun",
            "evli", "bekar", "serbest", "yanlış", "haklı", "yalnız",
            "emekli", "tatlı", "turuncu", "yasak", "uzak", "yakın",
            "zor", "hep", "hiç", "beraber", "ayni", "keşke",
            "tamam", "evet", "olur", "olmaz", "var", "yok",
            "yavaş", "helal", "dolu",
        }

        # Nesne konumundaki isimler — belirtme hali (-ı/-i/-u/-ü) alır
        self.nesne_isimleri = {
            "bardak", "kalem", "kitap", "para", "telefon", "anahtar",
            "ilaç", "havlu", "sabun", "masa", "hediye", "yastık",
            "yatak", "tarak", "makas", "kemer", "ayakkabı", "gömlek",
            "pantolon", "şapka", "eldiven", "şemsiye", "cüzdan",
            "kimlik", "senet", "fotoğraf", "bayrak", "çaydanlık",
            "çatal", "çekiç", "tornavida", "iğne", "yarabandı",
            "mendil", "kolonya", "pamuk", "leke", "koku", "süt",
            "çay", "et", "kıyma", "patates", "yumurta", "bal",
            "salca", "un", "pastırma", "tatlı", "çorba", "şeker",
            "odun", "kömür", "benzin", "vergi", "kira", "maaş",
        }

        # Şimdiki zaman kişi ekleri
        self.simdiki_sahis = {
            "Ben": "um", "Sen": "sun", "O": "",
            "Biz": "uz", "Siz": "sunuz", "Onlar": "lar"
        }
        # Geçmiş zaman kişi ekleri (Siz özel, diğerleri ek ünlüsünü taşır)
        self.gecmis_sahis = {
            "Ben": "m", "Sen": "n", "O": "",
            "Biz": "k", "Onlar": ""
        }

    # ── YARDIMCI FONKSİYONLAR ──────────────────────────────────────────

    def _son_unlu(self, s):
        """Dizinin son ünlüsünü döndürür; yoksa 'a'."""
        found = re.findall(f"[{self.unluler}]", s)
        return found[-1] if found else 'a'

    def _sert_mi(self, s):
        """Son harf sert ünsüz mü? (f s t k ç ş h p)"""
        return bool(s) and s[-1] in "fstkçşhp"

    def _kok_al(self, fiil):
        """labels.txt yazımından çekim tabanını döndürür."""
        return self.fiil_kokleri.get(fiil, fiil)

    def _simdiki(self, kok, ozne):
        """Şimdiki zaman: -ıyor/-iyor/-uyor/-üyor + kişi eki."""
        if kok[-1] in self.unluler:        # ünlü daralması
            kok = kok[:-1]
        u = self.dar_uyum[self._son_unlu(kok)]
        ek = f"{u}yor"
        if ozne == "Onlar":
            return f"{kok}{ek}lar"
        return f"{kok}{ek}{self.simdiki_sahis[ozne]}"

    def _gecmis(self, kok, ozne):
        """Geçmiş zaman: -dı/-di/-du/-dü / -tı/-ti/-tu/-tü + kişi eki."""
        u = self.dar_uyum[self._son_unlu(kok)]
        d = "t" if self._sert_mi(kok) else "d"
        ek = f"{d}{u}"
        if ozne == "Onlar":
            return f"{kok}{ek}lar"
        if ozne == "Siz":
            return f"{kok}{ek}n{u}z"
        return f"{kok}{ek}{self.gecmis_sahis[ozne]}"

    def _gelecek(self, kok, ozne):
        """
        Gelecek zaman: -acak/-ecek + kişi eki.
        Ben → çalışacağım  |  Sen → çalışacaksın
        O   → çalışacak    |  Biz → çalışacağız
        Siz → çalışacaksınız | Onlar → çalışacaklar
        """
        if kok[-1] in self.unluler:
            kok = kok[:-1]
        u = self.genis_uyum[self._son_unlu(kok)]
        govde = f"{kok}a" if u == "a" else f"{kok}e"
        govde += "cak" if u == "a" else "cek"      # çalışacak / gelecek

        if ozne == "O":
            return govde
        if ozne == "Onlar":
            return f"{govde}lar" if u == "a" else f"{govde}ler"

        dar = self.dar_uyum[self._son_unlu(govde)]
        if ozne == "Ben":
            return govde[:-1] + f"ğ{dar}m"          # çalışacağım
        if ozne == "Biz":
            return govde[:-1] + f"ğ{dar}z"          # çalışacağız
        if ozne == "Sen":
            return govde + f"s{dar}n"               # çalışacaksın
        if ozne == "Siz":
            return govde + f"s{dar}n{dar}z"         # çalışacaksınız
        return govde

    def _olumsuz_kok(self, kok, zaman):
        """
        Olumsuz tabanı:
          Şimdiki → kok + m + dar_ünlü   (çalış → çalışmıyor)
          Diğer   → kok + ma/me + y       (çalış → çalışmay-acak / çalışmadı)
        """
        u_genis = self.genis_uyum[self._son_unlu(kok)]
        ma = "ma" if u_genis == "a" else "me"

        if zaman == "simdiki":
            u_dar = self.dar_uyum[self._son_unlu(kok)]
            return kok + "m" + u_dar         # çalışmı / gelmi
        else:
            return kok + ma + "y"            # çalışmay / gelMey

    def fiil_cek(self, fiil, ozne, zaman, olumsuz=False):
        """
        Dışarıdan çağrılabilen tek nokta.
        fiil: labels.txt'deki tam yazım (örn. 'çalışmak', 'yemek pişirmek')
        """
        if fiil in self.otomatik_gecmis:
            zaman = "gecmis"
        kok = self._kok_al(fiil)

        if olumsuz:
            kok = self._olumsuz_kok(kok, zaman)

        if zaman == "gecmis":
            return self._gecmis(kok, ozne)
        elif zaman == "gelecek":
            return self._gelecek(kok, ozne)
        else:
            return self._simdiki(kok, ozne)

    def _lokatif(self, mekan):
        """-da/-de/-ta/-te lokatif (bulunma) eki."""
        u = self.genis_uyum[self._son_unlu(mekan)]
        d = "t" if self._sert_mi(mekan) else "d"
        ek = f"{d}a" if u == "a" else f"{d}e"
        return f"{mekan}{ek}"

    def _belirtme(self, isim):
        """-ı/-i/-u/-ü belirtme (akkuzatif) eki."""
        u = self.dar_uyum[self._son_unlu(isim)]
        if isim[-1] in self.unluler:
            return f"{isim}y{u}"
        return f"{isim}{u}"

    # ── ANA FONKSİYON ──────────────────────────────────────────────────

    def cumle_kur(self, kelimeler: list) -> str:
        """
        Kelime listesinden Türkçe cümle kurar.
        Sadece labels.txt'deki kelimeler gelir.
        Liste elemanları labels.txt'deki yazımla birebir aynıdır
        (Türkçe karakterli, boşluklu çok-kelimeli ifadeler dahil).
        """
        if not kelimeler:
            return ""

        # ── 1. Kalıp ifade kontrolü
        # Tek eleman olarak gelebilir: ["teşekkür"] veya ["geçmiş olsun"]
        # Ya da ayrı elemanlar: ["geçmiş", "olsun"]  (geriye dönük uyumluluk)
        for k in kelimeler:
            if k in self.kaliplar:
                return self.kaliplar[k]
        birlesmis = " ".join(kelimeler)
        for anahtar, deger in self.kaliplar.items():
            if birlesmis == anahtar or birlesmis.startswith(anahtar):
                return deger

        # ── 2. Gramer parametreleri
        ozne = "O"
        for k in kelimeler:
            if k.lower() in self.ozne_kelimeleri:
                ozne = self.ozne_kelimeleri[k.lower()]
                break

        zaman = "simdiki"
        for k in kelimeler:
            if k in self.gecmis_zamanlari:
                zaman = "gecmis"
                break
            if k in self.gelecek_zamanlari:
                zaman = "gelecek"
                break

        soru_var = any(k in self.soru_kelimeleri for k in kelimeler)
        olumsuz  = any(k in self.olumsuz_kelimeleri for k in kelimeler)

        # ── 3. Kategorilere ayır
        # Atlanacak meta-kelimeler
        atlanacak = (
            set(self.ozne_kelimeleri.keys()) |
            self.gecmis_zamanlari |
            self.gelecek_zamanlari |
            self.olumsuz_kelimeleri |
            set(self.kaliplar.keys())
            # Not: soru_kelimeleri burada YOK — aşağıda yapi["soru"]'ya eklenir
        )

        yapi = {
            "soru":        [],
            "zaman_zarfi": [],
            "mekan":       [],
            "sifat":       [],
            "nesne":       [],
            "fiil":        [],
        }

        for k in kelimeler:
            kl = k.lower()

            if kl in atlanacak or k in atlanacak:
                continue

            if k in self.soru_kelimeleri:
                yapi["soru"].append(k)

            elif k == "dun":
                yapi["zaman_zarfi"].append("dün")
            elif k == "yarın":
                yapi["zaman_zarfi"].append("yarın")
            elif k == "geçmiş":
                yapi["zaman_zarfi"].append("geçmişte")

            elif k in self.fiil_kokleri:
                yapi["fiil"].append(self.fiil_cek(k, ozne, zaman, olumsuz))

            elif k in self.otomatik_gecmis:
                # Sıfat görünümlü ama fiil gibi çekilenler (yorgun, hasta)
                yapi["fiil"].append(self.fiil_cek(k, ozne, "gecmis", olumsuz))

            elif k in self.mekanlar or k == "Türkiye":
                yapi["mekan"].append(self._lokatif(k))

            elif k in self.sifatlar:
                yapi["sifat"].append(k)

            elif k in self.nesne_isimleri:
                yapi["nesne"].append(self._belirtme(k))

            else:
                # Kategorize edilemeyen: ham olarak nesne pozisyonuna
                yapi["nesne"].append(k)

        # ── 4. SOV sırasıyla birleştir
        parcalar = []

        parcalar.extend(yapi["soru"])

        if ozne != "O":
            parcalar.append(ozne)

        parcalar.extend(yapi["zaman_zarfi"])
        parcalar.extend(yapi["mekan"])
        parcalar.extend(yapi["sifat"])
        parcalar.extend(yapi["nesne"])
        parcalar.extend(yapi["fiil"])

        if not parcalar:
            return ""

        sonuc = " ".join(parcalar).capitalize()
        return (sonuc + "?") if soru_var else (sonuc + ".")