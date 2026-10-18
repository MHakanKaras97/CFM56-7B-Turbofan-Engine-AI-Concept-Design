# Mimari

## 1. Amaç ve kapsam
- Amaç: CFM56-7B27 sınıfı bir turbofan motorun konsept seviyesinde tasarımı; çok agentlı bir sistemle yürütülür.
- Kapsam dışı: FADEC, sensörler, yakıt sistemi, ateşleme, yangın sistemi, nacelle, thrust reverser.
- Maliyet alanı kapsam dışı; proje sonrası revizyonda eklenecek.

## 2. Katmanlar
- Claude Code = beyin: kararları ve hesap çağrılarını yürütür.
- Dosyalar = durum: tüm tasarım durumu repodaki dosyalarda tutulur.
- Streamlit UI = görünüm + onay: durumu gösterir, kullanıcı onayını alır.

## 3. Agent hiyerarşisi
- M0 (motor agent'ı) ana oturumdur.
- M1-M9 modül agent'ları subagent olarak `.claude/agents/` altında tanımlanır.
- Modüller birbirini çağırmaz; tüm iletişim M0 üzerinden geçer.

## 4. Sahiplik
- Her parçanın tek bir sahip modülü vardır.
- Fan çerçevesi M1, yanma odası kasası M4, türbin çerçevesi M6, yatak destekleri ve hazneleri M8'e aittir.
- M9 bütçe ve gereksinim verir, parça çizmez; yalnızca kendi boru ve conta parçaları istisnadır.
- Bir modül başka modülün dosyasını düzenlemez; değişiklik talebi (CR) açar.

## 5. Numaralandırma
- Parça kimliği: `M<modül>.<kademe>.<parça>`.
- Parça adı: `"<Module> Stage <n> <Part type>"` (İngilizce).
- Tekrar eden parça: tek tanım + `qty`.

## 6. Veri
- `bom/bom.yaml`: modülün tek doğru kaynağı.
- `records/revNNN`: değişmez revizyon kayıtları.
- `engine/M0_engine/requests/CR-###.yaml`: değişiklik talepleri.
- İstasyon tablosu (SAE AS755: 2, 13, 25, 3, 4, 45, 5, 8) M0'da tutulur.

## 7. Revizyon
- Kayıtlar değişmez.
- Geri dönüş = aktif revizyonu değiştirmek; kayıt silinmez veya düzenlenmez.
- Geometri dosyaları için bkz. [ADR-001](decisions/ADR-001-geometry-storage.md).

## 8. Onay akışı
1. Modül bir CR açar.
2. M0 etki analizi yapar (`impact`; üreticisi `impact.by` alanında). Modül CR'lerinde M0 bunu `set_impact` ile yazar. Bütçe CR'leri (seçenekli, M0 analizinin taslağı) etkiyle birlikte oluşturulabilir (`by: "M0 integration_check"`). Onay için `impact.affected_modules` boş olmamalı.
3. Kullanıcı UI üzerinden onaylar veya reddeder. Seçenekli CR'lerde (ör. bütçe CR'si) kullanıcı seçeneği seçer.
4. Onaylanan değişiklik uygulanır.
- CR değişiklik türleri: `bom` (bom.yaml) ve `params` (`engine/<M>/analysis/*_params.yaml`). Bir params değişikliği uygulanınca modül hesabı (`analysis/calc.py`) yeniden çalışır, yeni revizyon oluşur ve türetilmiş dosyalar (M0 için `results.yaml`, `icd.yaml`) yeniden üretilir.
- Bütçe CR'si (M0 entegrasyon kontrolü sınırı aşınca) iki seçenek sunar: (a) ulaşılan değer M0 params'a yazılır ve çevrim yeniden dengelenir, (b) modül yeniden tasarlanır (M0 değişmez).
- Çakışmada kullanıcı karar verir; karar kaydedilir.
- Revizyon türleri (ADR-012): tasarım (sayı/geometri; kabul edilmiş modülde CR şart) ve bakım (yalnızca şema/üst veri/metin; CR yok, sayısal fark varsa core reddeder). Kabul `records/ACCEPTED` ile işaretlenir. Params dosyaları `core/schemas/params.schema.json` ile doğrulanır.
- Geri dönüş tam durumdur (ADR-013): bom, params, results kayıttan; türetilmiş dosyalar yeniden üretilir; güncel kodla doğrulanır. Arayüzden geri dönüş bir revert CR'siyle yapılır.

## 9. Güven etiketleri
- `[K]` birincil kaynak
- `[KS]` ikincil kaynak
- `[H]` hesaplanan
- `[G]` genel mühendislik bilgisi
- `[T]` tahmin

## 10. Kabul listesi (her agent için)
- Kural kontrolleri
- Hesap doğrulama
- Parametre değişikliği testi
- Geri dönüş testi
- Çakışma testi
- M0 kontrolü

## 11. Araçlar
- Python, CadQuery (geometri), Gmsh + CalculiX (ağ ve yapısal analiz), ROSS (rotor dinamiği), Streamlit (UI), git.
- pyCycle daha sonra çevrim hesaplarında çapraz kontrol için eklenecek.

## 12. Telif
- Alıntı veya şekil kopyalama yapılmaz; içerik kendi cümlelerimizle özetlenir.
- Her kaynak lisansıyla birlikte `docs/sources.md` dosyasında listelenir.
