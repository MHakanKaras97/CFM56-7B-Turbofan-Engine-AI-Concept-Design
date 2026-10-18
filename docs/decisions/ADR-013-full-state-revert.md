# ADR-013: Tam durum geri dönüşü ve revert CR'leri

## Karar
- `core.records.revert(modül, rev)` artık yalnızca ACTIVE ve bom.yaml'ı değil, modülün tam durumunu geri getirir. Kayıt doğrudur:
  - bom.yaml anlık görüntüden,
  - params (`analysis/*_params.yaml`) ve `analysis/results.yaml` kayıttan,
  - türetilmiş dosyalar (M0: `rules/icd.yaml`) yeniden üretilir.
- Ardından doğrulama: güncel kod kayıtlı params ile yeniden çalıştırılır. Sonuç farklıysa uyarı verilir ("kayıtlı sonuç ile güncel kod sonucu farklı") ve fark döndürülür; geri yüklenen sonuçların üzerine yazılmaz. Güncel kod eski params ile hiç çalışmıyorsa bu da uyarıdır.
- icd.yaml önce kayıtlı params yeniden çözülerek üretilir. Güncel çözücü eski bir kaydı çözemezse kaydın çalışma noktasında (results.yaml'daki W2, T4, verimler, FPR) tek bir çevrim hesabı yapılır ve kayıtlı itki ve yakıt debisi tutmalıdır; ICD kaynağında `method` alanı bunu belirtir. İkisi de olmazsa icd.yaml değişmez ve uyarı verilir.
- Kaydedilmemiş iş korunur: bom.yaml veya analiz params'ı aktif kayıttan farklıysa geri dönüş reddedilir (force hariç).
- `core.records.revert_concept` her sabitlenmiş modül için aynı tam durum geri dönüşünü yapar.
- Modüle özgü işler hesap eklentisindedir (`engine/<M>/analysis/calc.py`): `restore`, `rerun`, `affected_modules`.

## Revert CR'si
- Arayüzden geri dönüş bir CR üzerinden yapılır: değişiklik türü `revert` ({module, from, to}); konsept geri dönüşünde CR'de `concept` alanı vardır ve bütün modülleri listeler.
- Etki M0 tarafından doldurulur: `impact.by = "M0 revert"`, `affected_modules` = geri dönen modüller + ICD bütçesi değişen modüller (başlamamış olsalar da listelenir).
- Onay penceresindeki karar CR'nin onayı olarak kaydedilir (`decided_by: user (UI)`), sonra CR uygulanır. Doğrulama uyarıları CR'de `apply_warnings` alanında saklanır.
- Uygulamada aktif revizyon CR'deki `from` ile aynı olmalıdır; değilse CR eskimiştir ve reddedilir.

## Neden
- Yalnızca ACTIVE'i değiştirmek, analiz dosyalarını (params, results, ICD) yeni revizyonda bırakıyordu; çalışma alanı ile aktif kayıt tutarsız kalıyordu.
- Geri dönüş de bir tasarım kararıdır; CR ve kullanıcı onayıyla izlenebilir olmalı.

## Sonuç
- rev001-rev003 güncel kodla yeniden çalıştırılamaz ve ICD'leri üretilemez (o dönemin params biçimi). rev004'ün ICD'si çalışma noktasından üretilir. rev005-rev007 yeniden çözülür.
