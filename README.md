## 조원들 각자 기본 설정 가이드 
여러분 반갑습니다.
앞으로 함께 멋있는 프로젝트 만들어보아요.
앞으로 작업 하시기 전, 가장 먼저 하실것들 적어둘게요. (수정,추가될 수 있음)


항상 pull하면 (다운받으면, 터미널에 가장 먼저,입력해줄것)
# 지금 내가 어디위치인지 확인
```bash
git branch # *하고 나오는 브랜치명이 위치
```

# 원하는 브랜치로 이동 + 최신화
```bash
git checkout 브랜치이름
```
# 브랜치의 내용 당겨와서 합치기
```bash
git pull origin 브랜치이름
```

# 브랜치 생성 + 이동
```bash
git checkout -b feature/브랜치이름-작업하는이름 
```
# 브랜치 확인
```bash
git branch
```
`* feature/브랜치이름-작업하는이름` 로 표시되면 성공

# 다른 조원들의 브랜치 확인이 필요할때
```bash
git fetch origin #원격 목록 최신화(업데이트)
git switch feature/브랜치이름-작업하는이름
```
##단, 자신의 브랜치에서 작업하던게 사라지지 않도록

```bash
git stash #내 브랜치 내용 잠시 서랍에 두기
-> #다른 브랜치확인 후 되돌아와서
git switch feature/브랜치이름-작업하는이름
git stash pop #아까 작업 다시 꺼내기
```
-----------------------------------------------

# 1. 가상환경 생성
uv venv

# 2. 가상환경 활성화
source .venv/bin/activate

# 3. 라이브러리 환경 똑같도록 설치 (혹시몰라서)
uv pip install -r requirements.txt

# 4. README.md는 항상 업데이트 (README만 업뎃하는법)
git fetch origin 
git checkout origin/dev# -- README.md 
#origin/dev#에 있는 README.md파일만 내 현재 브랜치로 복사해줘라는 뜻

# 주의 사항
pyproject.toml은 프로젝트 설정 파일이라 팀장만 관리합니다.
라이브러리 추가는 requirements.txt로 공유하세요

-----------------------------------------------

## 코드 작성후, 이렇게 해야 깃허브에 올라갑니다
# 어떤 코드가 바뀌었는지 각자확인
```bash
git status
```
# 코드 수정 후 커밋
```bash
git add 코드 변경된 파일명  # 스테이징(add)
git commit -m "커밋할내용간략히정리"  # 커밋방법(commit)
```

# 원격 브랜치로 push (PR 만들려면 꼭 필요)
	
```bash
git push (처음 한 번은 아래문장의 -u 권장)
git push -u origin feature/브랜치이름
```
	성공하면 GitHub에 feature/브랜치이름  생깁니다.
	이미 생겼다면, add,commit한 내용이 올라갑니다.

  

