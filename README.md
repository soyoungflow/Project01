## 조원들 각자 기본 설정 가이드 
여러분 반갑습니다.
앞으로 함께 멋있는 프로젝트 만들어보아요.
앞으로 작업 하시기 전, 가장 먼저 하실것들 적어둘게요. (수정,추가될 수 있음)


항상 pull하면 (다운받으면, 터미널에 가장 먼저,입력해줄것)

# 1. 가상환경 생성
uv venv

# 2. 가상환경 활성화
source .venv/bin/activate

# 3. 의존성 설치
uv pip install -r requirements.txt

# 주의 사항
pyproject.toml은 프로젝트 설정 파일이라 팀장만 관리합니다.
라이브러리 추가는 requirements.txt로 공유하세요
