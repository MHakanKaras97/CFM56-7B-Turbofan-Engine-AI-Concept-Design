# Arayüz spesifikasyonu (Streamlit)

Kaynak maketler: `ui_genel_bakis.png`, `ui_m0.png`, `ui_modul.png`, `ui_talepler.png` (bu klasörde). Karar: ADR-003 (Streamlit).

## 1. Temel kurallar
- **Arayüz hiçbir dosyaya doğrudan yazmaz.** Bütün yazma işlemleri `core/` üzerinden yapılır: `core.requests` (decide, set_impact, apply), `core.records` (revert, revert_concept, create_concept). Okuma doğrudan dosyalardan yapılabilir.
- Türetilmiş dosyalar (`results.yaml`, `icd.yaml`, `section.svg`, `engine_reference.svg`) yalnızca gösterilir; düzenleme alanı olmaz.
- Gösterilen her sayının yanında etiketi ([K], [KS], [H], [G], [T]) ve kaynağı (ör. "kaynak rev005") bulunur. Etiketi [T] olan değerler turuncu rozetle vurgulanır.
- Sayılar dosyalardan okunur; arayüz hesap yapmaz. Tek istisna birim dönüşümüdür (ör. kN gösterimi).
- Dil: Türkçe arayüz metinleri; kimlikler (M1.1.1, CR-004, rev005) olduğu gibi kalır.

## 2. Görsel dil (maketlerden)
- Koyu tema: koyu gri zemin, ince kenarlı yuvarlatılmış kartlar.
- Durum renkleri: yeşil = geçti / tamam / aktif; turuncu = bekliyor / [T] / uyarı; kırmızı = kaldı; mavi = bilgi / seçili revizyon; gri = başlamadı.
- Metrik kartlarında küçük başlık ve büyük değer kullanılır (ör. "İtki / 121,4 kN"). Ondalık ayırıcı virgüldür.

## 3. Her sayfada
- **Üst çubuk:** proje adı ("CFM56-7B27 konsept"), aktif konsept (`records/ACTIVE_CONCEPT`, ör. concept001), aktif modül durum rozeti (ör. "M0 · tamam"), bekleyen onay rozeti ("N onay bekliyor": `status: open` olan CR sayısı). Rozete tıklanınca Talepler açılır.
- **Sol menü:** Genel bakış, M0 motor, Modüller, Talepler, Revizyonlar, Öğrenme.

## 4. Sayfalar

### 4.1 Genel bakış (`ui_genel_bakis.png`)
- **Motor şeridi:** M0-M9 kutuları gaz yolu sırasıyla dizilir (`docs/design/concept_reference.yaml`). Renk modül durumunu gösterir: aktif revizyonu olan yeşil, başlamamış (konseptte null) gri, açık CR'si olan turuncu çerçeveli. Tıklanınca modül sayfası açılır.
- **Metrik kartları:** itki, SFC, EGT payı, W2. Kaynak: aktif M0 revizyonunun `results.yaml` dosyası (`performance.thrust`, `performance.sfc`, EGT sınır kontrolünün `margin` değeri, `calibration.W2`).
- **Modül kartları:** her modül için ad ve durum ("Başlamadı · sıradaki", "revNNN aktif").
- **Son revizyonlar:** M0'ın revizyon zinciri (`parent_revision` ile), aktif olan mavi.
- Ek (maketin dışında): kavramsal düzen referansı `engine_reference.svg` katlanabilir bir panelde gösterilir.

### 4.2 M0 motor (`ui_m0.png`)
- **Başlık:** aktif revizyon rozeti, doğrulama özeti ("Girão 18/19", kaynak `analysis/validation_girao.md`), "Revizyonları karşılaştır" düğmesi (Revizyonlar sayfasındaki fark görünümüne gider).
- **İstasyon tablosu:** istasyon, sahip modül, Tt, Pt, W, FAR. Kaynak `rules/icd.yaml` (`stations`). Altında not: "Her değerin yanında etiket: H · kaynak revNNN". Kısaltılmış görünümde ana istasyonlar, genişletince hepsi gösterilir.
- **Kontroller:** `results.yaml` içindeki `checks`. Her satırda ad, değer ve rozet (geçti / kaldı / bilgi). HARD kontroller "(sert)" etiketi taşır. [T] varsayımları ayrı satırda turuncu rozetle gösterilir (ör. "Δη varsayımı · T · 0,017").
- **Modül bütçeleri (ICD):** her modül için kart: ana bütçe kalemleri ve izin verilen sapmalar (`icd.yaml` → `modules.<Mx>.budget`, `tolerances`). Kart tıklanınca tüm kalemler listelenir.
- Ek: belirsizlik bandı ve verim duyarlılığı tablosu (`rules/cycle_inputs.md`, `analysis/acceptance_M0.md`) bilgi sekmesinde.

### 4.3 Modül sayfası, M1-M9 (`ui_modul.png`)
- **Başlık:** modül adı; "Karşılaştır: [rev A] → [rev B]" seçicileri (varsayılan: önceki → aktif); düğmeler: Kesit, 3B, Fusion'da aç.
- **BOM ağacı (solda):** `bom/bom.yaml` parçaları, kimliğe göre hiyerarşik (M1.1 → M1.1.1); tekrar eden parçada "×qty". Seçilen parça kesitte vurgulanır.
- **Kesit görünümü:** iki revizyonun `records/revNNN/section.svg` dosyaları üst üste çizilir (ADR-011). Eski revizyon kesikli gri, yeni revizyon renkli. Değişen ölçüler için ok ve etiket gösterilir (ör. "Δr uç = +13 mm"). Motor ekseni kesikli çizgiyle gösterilir.
- **3B görünüm:** GLB dosyası yerel önbellekten (`.cache/geometry/<modül>/<rev>/`) okunur. Önbellekte yoksa kayıttaki `code_commit` ve parametrelerle yeniden üretilir, SHA-256 kayıtla karşılaştırılır.
- **Değişen ölçüler:** A ile B arasındaki parametre ve BOM farkı (`core.diff.diff_revisions`); ad, eski → yeni, fark (ör. "Fan çapı 1549 → 1575 mm").
- **Analizler:** seçili revizyonun analiz kontrolleri (ör. santrifüj gerilme, uç hızı, Campbell), her biri rozetle.
- **Fusion'da aç:** STEP dosyası önbelleğe dışa aktarılır ve işletim sisteminin dosya ilişkilendirmesiyle açılır (Windows'ta `os.startfile`). İlişkilendirme yoksa arayüz dosya yolunu gösterir ve uyarı verir. Fusion'da yapılan değişiklikler geri yazılmaz; tek kaynak koddur.
- Başlamamış modülde sayfa, ICD bütçesini ve "Başlamadı" durumunu gösterir.

### 4.4 Talepler (`ui_talepler.png`)
- Başlıkta açık ve kapalı CR sayıları. Liste `engine/M0_engine/requests/CR-*.yaml` dosyalarından okunur; açık CR'ler önce gelir.
- **CR kartı:** kimlik, yön ("M3 → M0"), tür ("bütçe ihlali"), gerekçe, etki rozeti ("etki analizi hazır" = `impact` dolu).
- **Etki metrikleri:** ΔSFC, ΔEGT, ΔT41 kartları. Kaynak: CR'nin `impact.metrics` alanı (metrik adı → {value, unit, tag}); bütçe CR'lerinde `dSFC` [%], `dEGT` [K], `dT41` [K], operating_point modunda ayrıca `dThrust` [%]. Alan isteğe bağlıdır: `impact` boş ya da `metrics` yoksa kartlar gösterilmez, yalnızca `impact.notes` görünür.
- **Seçenekler:** CR'deki `options` radyo düğmeleriyle gösterilir: (a) M0 değeri kabul etsin ve çevrimi yeniden dengelesin; (b) modül tasarımını düzeltsin.
- **Karar notu:** zorunlu metin alanı.
- **Karar:** yalnızca `core.requests.decide(cr, approve, note, option=...)` ile verilir.
  - Maketten farkı: (b) bir ret kararıdır, (a) onaydır. Bu yüzden "Onayla / Reddet" yerine tek bir **"Kararı kaydet"** düğmesi olur; onay mı ret mi olduğu seçilen seçenekten çıkar. Seçeneği olmayan CR'lerde Onayla ve Reddet düğmeleri kalır.
  - Etki analizi yoksa onay seçeneği devre dışıdır (`core.requests` zaten reddeder).
- **Uygulama:** onaylanmış CR'de "Uygula" düğmesi `core.requests.apply` çağırır. Sonuçta oluşan revizyonlar ve yeniden üretilen dosyalar gösterilir.
- Kapalı CR'ler geçmiş (`history`) ve kararla birlikte salt okunur listelenir.

### 4.5 Revizyonlar
- **Modül zaman çizelgesi:** her modülün revizyonları (`records/revNNN/manifest.yaml`): tarih, özet, gerekçe, CR, kod commit'i; aktif olan işaretli.
- **Konsept zaman çizelgesi:** `conceptNNN` manifestleri ve sabitlenen modül revizyonları.
- **Fark görünümü:** `core.diff.diff_revisions(modül, revA, revB)` sonucundan:
  - `params`: [{path, old, new}] (None = yok; eklenen/silinen anahtar),
  - `results`: [{key, old, new, delta, pct}] (delta ve yüzde yalnızca iki değer de sayıysa),
  - `bom`: {header, added, removed, changed: {parça kimliği: [{path, old, new}]}},
  - `outputs`: [{file, old, new}] (SHA-256 değişimi).
  Yollar noktalıdır (ör. `calibration.W2.value`); kimlik anahtarı olan listeler kimlikle yazılır (ör. `stations[2].W_kg_s`). Boş fark `core.diff.is_empty` ile anlaşılır. Biçimlendirme (ondalık virgül, birim) arayüzün işidir.
- **Konsept farkı:** `core.diff.diff_concepts(cA, cB)` → [{module, old, new}]; satır seçilince o modül için `diff_revisions` gösterilir.
- **Geri dönüş:** "Aktif yap" düğmesi `core.records.revert` (modül) veya `revert_concept` çağırır; önce onay penceresi açılır. Kayıtlar silinmez.
- Doğrulama: `core.records.verify` ile çıktı özetleri kontrol edilir ve sonuç rozetle gösterilir.

### 4.6 Öğrenme
- `docs/learning/` ve `engine/*/learning/` altındaki `.md` dosyaları markdown olarak gösterilir; `.txt` dosyaları (ör. parça bilgi dokümanı) sabit genişlikli metin olarak gösterilir.
- Solda modüle göre gruplanmış dosya listesi bulunur. `learning/sources/` (indirilen kaynaklar, git dışı) listelenmez.

## 5. Uygulama notları
- Streamlit çok sayfalı uygulama: `ui/app.py` ve `ui/pages/`. Kurulu sürüm `pyproject.toml` içinde sabitlenir.
- Okuma katmanı (`ui/data.py`) yalnızca okur ve önbelleğe alır (`st.cache_data`, dosya değişiklik zamanı anahtarlı). Yazma düğmeleri yalnızca `core` fonksiyonlarını çağırır ve sonrasında önbelleği temizler.
- 3B görünüm için GLB görüntüleyici olarak tarayıcıda çalışan bir bileşen (ör. model-viewer) kullanılabilir. Eklenecek bağımlılık için önce onay alınır.

## 6. Açık noktalar
1. ~~Etki metrikleri CR'de yapısal değil~~ — çözüldü (UI faz 1): `impact.metrics`, bütçe CR'lerinde `integration_check` doldurur.
2. **`.step` dosya ilişkilendirmesi:** bu makinede `.step` ve `.stp` uzantıları hiçbir uygulamayla ilişkili değil. "Fusion'da aç" çalışması için ya ilişkilendirme yapılmalı ya da Fusion'ın çalıştırılabilir dosya yolu ayarlardan verilmeli.
3. ~~Revizyon farkı fonksiyonu~~ — çözüldü (UI faz 1): `core/diff.py` (`diff_revisions`, `diff_concepts`).
