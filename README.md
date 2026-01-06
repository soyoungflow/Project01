## Setup 기본 guide 
항상 pull(다운받으면, 터미널에 가장 먼저 ,입력해줄것)

# 1. 가상환경 생성
uv venv

# 2. 가상환경 활성화
source .venv/bin/activate

# 3. 의존성 설치
uv pip install -r requirements.txt


# 주의 사항
pyproject.toml은 프로젝트 설정 파일이라 팀장만 관리합니다.
라이브러리 추가는 requirements.txt로 공유하세요
