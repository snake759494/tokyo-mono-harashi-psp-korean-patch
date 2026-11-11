# 빌드 방법

번역 대본·원문은 저장소에 없으므로, 아래는 자신이 가진 원본과 번역 파일로 다시 빌드하는 절차입니다.

## 준비물
- 원본 ISO `Tokyo Mono Harashi - Karasu no Mori Gakuen Kitan (Japan).iso` (MD5 `f4b2213627197cb5f9c97c2d202f0257`)
- Python 3.12+ : `pip install pillow numpy pycdlib websocket-client`
- 복호화한 실행 파일 `work/iso/EBOOT.dec`(ELF)와 EBOOT 서명 도구(`_seboot.exe`, 경로는 `tools/sign.py` 에서 지정)
- 글꼴: 서울한강체·나눔스퀘어네오 (작업 폴더), 갈무리11·9·7 (`fonts_dl/`)

## 폴더 구성
```
<작업 폴더>/
  Tokyo Mono Harashi - Karasu no Mori Gakuen Kitan (Japan).iso
  *.ttf, fonts_dl/
  tools/        (이 저장소의 tools)
  work/
    iso/        EBOOT.dec, PARAM.SFO
    pak/        CROW.PAK 를 풀어 둔 것 (extract)
    tbl/        데이터 표 (table/*.bin)
    font/       원본 글꼴 ipk
    trans/
      txt/      추출한 원문 (extract_text / extract_misc)
      ko/       번역 (키<TAB>번역)  — 저장소 미포함
      img/      그림 글자 스펙 JSON  — 저장소 미포함
      src/eboot.json, script_keys.json
    imgko/clean/  그림 글자 바탕 이미지
```

## 순서
1. ISO에서 `CROW.PAK`, `EBOOT.BIN`, `PARAM.SFO` 꺼내기: `python tools/extract.py 원본.iso work/iso /PSP_GAME/USRDIR/CROW.PAK ...`
2. 원문 추출: `python tools/extract_text.py`, `python tools/extract_misc.py` → `work/trans/txt/`
3. 번역 작성: `work/trans/ko/<이름>.txt` (`docs/TRANSLATION_GUIDE.md`), 누락 검사 `python tools/check_ko.py`
4. 그림 글자: `python tools/dump_gim.py` 로 이미지를 뽑고 `work/trans/img/*.json` 스펙을 작성, `python tools/imgko.py render all` 로 미리보기
5. 빌드: `python tools/build.py` → `Tokyo Mono Harashi - Karasu no Mori Gakuen Kitan (Korean).iso`
6. 차분: `xdelta3 -0 -S none -f -e -s 원본.iso 한글.iso 패치.xdelta`

PPSSPP 원격 디버거로 자동 플레이·화면 캡처를 할 때는 `python tools/play.py <버튼> <횟수> [간격] [태그]` 를 씁니다.
