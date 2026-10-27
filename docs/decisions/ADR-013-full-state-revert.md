# ADR-013: Tam durum geri dönüşü ve revert CR'leri

## Karar
- `core.records.revert(modül, rev)` artık yalnızca ACTIVE ve bom.yaml'ı değil, modülün tam durumunu geri getirir. Kayıt doğrudur:
  - bom.yaml anlık görüntüden,
  - params (`analysis/*_params.yaml`) ve `analysis/results.yaml` kayıttan,
  - türetilmiş dosyalar (M0: `rules/icd.yaml`) yeniden üretilir.
- Ardından doğrulama: güncel kod kayıtlı params ile yeniden çalıştırılır. Sonuç farklıysa uyarı verilir ("kayıtlı sonuç ile güncel kod sonucu farklı") ve fark döndürülür; geri yüklenen sonuçların üzerine yazılmaz. Güncel kod eski params ile hiç çalışmıyorsa bu da uyarıdır.
- icd.yaml önce kayıtlı params yeniden çözülerek üretilir. Güncel çözücü eski bir kaydı çözemezse kaydın çalışma noktasında (results.yaml'daki W2, T4, verimler, FPR) tek bir çevrim hesabı yapılır ve kayıtlı itki ve yakıt debisi tutmalıdır; ICD kaynağında `method` alanı bunu belirtir.
- **Yalnızca yeniden üretilebilir revizyonlara dönülür** (`core.records.reproducible`: iki yoldan biri başarılı olmalı). Diğerleri geçmiş kaydıdır: arayüzde görülür ve doğrulanır, "Bu revizyona dön" gerekçesiyle devre dışıdır; `revert` ve `revert_concept` hiçbir şey yazmadan reddeder.
- **ICD kaynak kontrolü:** bütçe okumaları yalnızca `core.budgets.read_icd(tüketici)` ile yapılır; icd.yaml'ın `source.revision` değeri M0'ın aktif revizyonu değilse okuma reddedilir. Arayüz bu durumda bütçe yerine nedeni gösterir.
- Kaydedilmemiş iş korunur: bom.yaml veya analiz params'ı aktif kayıttan farklıysa geri dönüş reddedilir (force hariç).
- `core.records.revert_concept` her sabitlenmiş modül için aynı tam durum geri dönüşünü yapar.
- Modüle özgü işler hesap eklentisindedir (`engine/<M>/analysis/calc.py`): `restore`, `rerun`, `affected_modules`.

## Genel modül hesap arayüzü (2026-10-25, M1 adım 3b)
Her modülün hesap eklentisi `engine/<M>/analysis/calc.py` aynı arayüzü sunar (M0 ve M1 uygular; diğer modüller aynısını izler). `core.records` ve `core.requests` modüle özgü kodu yalnızca bu arayüzden çağırır:
- `PARAMS_FILE`: kayda giren params dosyasının adı (`analysis/` altında).
- `recalculate(root, params_files) -> {"params", "results"}`: params CR'si uygulanırken yeni params ile hesap; olanaksız tasarım `ValueError` ile reddedilir, bütçe dışı sonuç ret değildir.
- `write_outputs(root, out)`: sonuçları `analysis/results.yaml`'a yazar.
- `regenerate(root, revision)`: türetilmiş dosyaları üretir (M0: `rules/icd.yaml`; M1: yok).
- `rerun(root, params) -> results`: güncel kodla kayıtlı params üzerinde yeniden hesap (geri dönüş doğrulaması).
- `restore(root, revision, params, results) -> uyarılar`: params ve sonuçları kayıttan geri yazar.
- `reproducible(root, revision) -> None | neden`: kayda dönülebilir mi.
- Eklentisi olmayan modül yalnızca bom.yaml geri getirir ve her zaman yeniden üretilebilirdir.
- Yeniden üretilebilirlik koruması: `create_revision`, kod (core/, tools/, engine/*/analysis/*.py) commit edilmeden kaydı reddeder; böylece `code_commit` kaydı üreten kodu içerir. M1 rev002 bu korumadan önce kaydedildi (`code_commit` fan_design.py'den önce): REVIEW.md'de işaretli, yerine rev003 (bakım, aynı sayılar).

## Kayıt kontrolü kendi koduyla (2026-10-27)
- **Kayıt kontrolü** (`core.records.reproduce`): kayıt, manifest'teki KENDİ `code_commit`'i ile yeniden çalıştırılır (o commit'te geçici git worktree; hesap eklentisinin `rerun`'u kayıtlı params ile) ve kayıtlı results ile karşılaştırılır. Güncel çalışma ağacı kullanılmaz; sonraki kod değişiklikleri bu kontrolü bozmaz. Fark = kayıt hatası (test kalır).
- **Tasarım sapması** (`core.records.design_drift`, ayrı bilgi kontrolü): güncel kod aktif kaydın params'ı ile farklı sonuç veriyorsa "yeni revizyon gerekli" bildirilir; hata değildir (testte uyarı). Geri dönüşteki `results_diff` uyarısı aynı kavramdır.
- Aktif kayıt testleri (M0 kabul, M1) bu ikisini ayrı kullanır.

## Revert CR'si
- Arayüzden geri dönüş bir CR üzerinden yapılır: değişiklik türü `revert` ({module, from, to}); konsept geri dönüşünde CR'de `concept` alanı vardır ve bütün modülleri listeler.
- Etki M0 tarafından doldurulur: `impact.by = "M0 revert"`, `affected_modules` = geri dönen modüller + ICD bütçesi değişen modüller (başlamamış olsalar da listelenir).
- Onay penceresindeki karar CR'nin onayı olarak kaydedilir (`decided_by: user (UI)`), sonra CR uygulanır. Doğrulama uyarıları CR'de `apply_warnings` alanında saklanır.
- Uygulamada aktif revizyon CR'deki `from` ile aynı olmalıdır; değilse CR eskimiştir ve reddedilir.

## Neden
- Yalnızca ACTIVE'i değiştirmek, analiz dosyalarını (params, results, ICD) yeni revizyonda bırakıyordu; çalışma alanı ile aktif kayıt tutarsız kalıyordu.
- Geri dönüş de bir tasarım kararıdır; CR ve kullanıcı onayıyla izlenebilir olmalı.

## Sonuç
- rev001-rev003 güncel kodla yeniden çalıştırılamaz ve ICD'leri üretilemez (o dönemin params biçimi): geçmiş kaydı, geri dönülemez. rev004'ün ICD'si çalışma noktasından üretilir. rev005-rev007 yeniden çözülür.
- CLAUDE.md kaydı: geri dönüş tam durumdur, yalnızca yeniden üretilebilir revizyonlara izinlidir; modül agent'ları bütçeyi yalnızca read_icd ile okur.
