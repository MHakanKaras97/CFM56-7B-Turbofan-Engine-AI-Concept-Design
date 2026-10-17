# ADR-004: Yapısal çerçevelerin sahipliği

## Karar
Fan çerçevesi M1, yanma odası kasası M4, türbin çerçevesi M6, yatak destekleri ve hazneleri M8'e aittir. M9 parça çizmez (kendi boru/conta parçaları hariç).

## Neden
Modüller arası sınırdaki parçaların tek ve açık bir sahibi olmalı.

## Sonuç
Diğer modüller bu parçalar için yalnızca M0 üzerinden CR açabilir.
