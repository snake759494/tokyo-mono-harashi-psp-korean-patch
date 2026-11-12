# 도쿄 모노하라시 ~카라스노모리 학원 기담~ (PSP) 비공식 한글패치

PSP 일본판 **東京鬼祓師 鴉乃杜學園奇譚 (도쿄 모노하라시 ~카라스노모리 학원 기담~, NPJH-50215)** 비공식 한국어 패치입니다. 이 저장소에는 제작 도구와 기술 문서만 있고, 패치 파일(xdelta)은 [Releases](../../releases)에서 받을 수 있습니다. 게임 원본·일본어 원문·번역 대본은 포함하지 않습니다.

## 적용 방법
1. 아래 해시와 일치하는 **원본 `.iso`** 를 준비합니다. (CSO·CHD 등으로 변환한 이미지에는 적용할 수 없습니다.)
   - PowerShell: `Get-FileHash -Algorithm MD5 -LiteralPath '.\Tokyo Mono Harashi - Karasu no Mori Gakuen Kitan (Japan).iso'`
2. xdeltaUI 같은 도구로 원본 `.iso` 에 `TokyoMonoHarashi_KO_v1.2.xdelta` 를 적용합니다. (Patch = xdelta, Source File = 원본 ISO, Output File = 새 파일명)
   - 명령줄: `xdelta3 -d -s "Tokyo Mono Harashi - Karasu no Mori Gakuen Kitan (Japan).iso" TokyoMonoHarashi_KO_v1.2.xdelta "Tokyo Mono Harashi - Karasu no Mori Gakuen Kitan (Korean).iso"`
3. 만들어진 ISO를 PPSSPP 또는 커스텀 펌웨어(PSP·PS Vita Adrenaline 등)에서 실행합니다.

| 항목 | 값 |
| --- | --- |
| 원본 ISO 크기 | 968,622,080 바이트 |
| 원본 ISO MD5 | `f4b2213627197cb5f9c97c2d202f0257` |
| 원본 ISO SHA-256 | `5e27d6f405708e21b7c81c9219bf068acb16b530992ab59ee6463c3c3e6441a2` |
| xdelta SHA-256 | `20e59927cffc5f6757c6dad9b678ce8e4edfdaca00ac1965104c3540497f98bb` |
| 결과 ISO 크기 | 968,712,192 바이트 |
| 결과 ISO SHA-256 | `fc0d0666b599312813702689d697e4c829dfe6feb2f9fb0c525efa7e5a0498a8` |

## 주의
- 수정한 실행 파일을 다시 서명해 EBOOT로 넣었기 때문에 **PPSSPP·커스텀 펌웨어 전용**입니다. 정품 펌웨어에서는 부팅되지 않습니다.
- 원본에서 만든 **상태저장(세이브 스테이트)** 은 불러오지 마세요. 일반 세이브는 그대로 쓸 수 있습니다.
- 세로쓰기 대사에서 띄어쓰기는 엔진 동작상 한 칸을 통째로 차지합니다.
- xdelta는 2차 압축을 쓰지 않은 형식입니다(약 7.0MB).

## 한글화 내용
- 본편 세로쓰기 대사 23,788줄 전체 직접 번역, 화자 이름·장소 자막 포함
- 선택지 397종(1,209곳)
- 아이템·화찰·퀘스트·용어 사전·Q&A·휴대폰 사이트·메일 등 데이터 표 문자열 7,252개
- 실행 파일 문자열 875개와 표에서 빠져 있던 짧은 서식 문자열(생일 「월·일」, 혈액형 「형」, 계절, 단위, 호칭 등)
- 이름 입력 키보드를 한글 음절 163자 판으로 교체, 주인공 기본 이름 「시치다이 카즈키」
- 그림 글자 113종(127장) — 타이틀 로고·메뉴, 설문지, 감정 선택 원판, 시스템·상태 화면, 휴대폰·OXAS 사이트, 던전 화면과 던전 3D 텍스처, 퀘스트·지도, 이벤트 장 제목, 고지문·장소 제목 카드 등
- 게임 글꼴 3종(대사·시스템·휴대폰)에 한글 2,350자 글리프
- 글꼴: 대사 서울한강체 B, 시스템 서울한강체 EB, 휴대폰 갈무리9, 그림 글자 나눔스퀘어네오·서울한강체, 아주 작은 그림 글자 갈무리

## 그대로 둔 것
- 음성, 화찰 그림 속 붓글씨, 아주 작은 아이템 아이콘·의상·부적 문양, 배경 속 작은 간판 글씨, 내부 ID로만 쓰이는 층 이름, 개발용 자리표시 이미지

## 검증 범위
PPSSPP에서 타이틀, 고지문, 프롤로그 대사, 설문지·이름 입력 키보드, 감정 선택 원판, 선택지, 휴대폰 메뉴·Q&A·프로필, 첫 던전 화면·커맨드 팔레트·아이템 메뉴를 실제 플레이로 확인했습니다. 대본·표·실행 파일 문자열은 번역 누락을 전수 검사했습니다. v1.2에서는 시험 직후 장면(이치루·이사지 대화)부터 오프닝 동영상 뒤 「다음 화로」 막간 메뉴까지 PPSSPP에서 6번 반복 실행해 모두 정상으로 넘어가는 것을 확인했고, 휴대폰 Q&A의 그림 있는 도움말 4종을 끝까지 스크롤해 마지막 줄이 보이는 것을 확인했습니다. 전투·상점·세이브 화면과 2장 이후는 실제 플레이로 확인하지 않았습니다. 문제를 발견하면 Issues에 알려 주세요.

## 문서
- [CHANGELOG.md](CHANGELOG.md) — 변경 기록
- [docs/TECHNICAL.md](docs/TECHNICAL.md) — 파일 형식과 한글화 방법
- [docs/BUILD.md](docs/BUILD.md) — 직접 빌드하는 방법
- [docs/TRANSLATION_GUIDE.md](docs/TRANSLATION_GUIDE.md) — 번역 지침
- [docs/FONT_CREDITS.md](docs/FONT_CREDITS.md) — 글꼴
- [RIGHTS.md](RIGHTS.md) — 권리 및 외부 자료
