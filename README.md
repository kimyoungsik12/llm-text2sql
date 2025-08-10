## 자연어 → SQL → 답변 FastAPI 서버

### 실행 방법
1) 의존성 설치
```bash
pip install -r requirements.txt
```

2) 환경설정
```bash
cp .env.example .env
cp config/databases.yaml.example config/databases.yaml
```
`.env`에서 `LLM_PROVIDER`를 `ollama` 또는 `openai`로 선택하세요.

3) 서버 실행
```bash
uvicorn app.main:app --reload
```

### 엔드포인트
- POST `/api/query`
  - Body: `{ "question": "자연어 질문" }`
  - Response: `{ answer, used_db, sql, rows, error? }`

### 프롬프트 구조
- prompts/templates/
  - `sql_generation.txt` (공통 규칙)
  - `sql_generation__{db}.txt` (선택, DB별 매핑 포함용)
  - `answer.txt` (규칙 + 상황별/공용 답변 폼)
  - `db_selection.txt` (DB 선택 규칙)
- prompts/generated/
  - `{db}__db_structure.txt` (서버 시작 시 자동 생성)

### DB 구성
- `config/databases.yaml`에 다중 DB 연결 정보를 정의합니다.

### 참고
- SQL 생성 실패 시 에러 메시지를 포함해 1회 재시도합니다.
- 한 질문은 하나의 DB만 사용합니다.

### 요구사항 
1. sql생성 프롬프트, 답변 프롬프트, db선택 프롬프트, db구조 프롬프트 4가지를 파일로 관리.
2. sql생성 프롬프트에선 자연어로 적을 규제(규칙) 부분과 db별 테이블이름 - 유저가 부를 수 있는 이름을 쭉 매칭시켜서 적을 수 있는 부분으로 이루어짐.
3. db선택 프롬프트에는 언제 어떤 db를 선택해야되는 지 각 db별로 작성할 수 있는 부분으로 이루어짐.
4. 답변 프롬프트에서는 자연어로 적을 수 있는 규제(규칙) 부분과 상황별 답변 폼, 공용 답변 폼을 적을 수 있는 부분으로 이루어짐.
5. db구조 프롬프트는 서버 시작할때 자동으로 연결된 db의 테이블-컬럼 목록, fk키 목록을 가져와서 db별로 각각의 프롬프트 파일로 작성(예를 들어 db이름+db구조 프롬프트 이렇게 파일 이름 작성).
6. 위 구조를 누구나 쉽게 유지보수 할 수 있게 폴더, 파일 작성.
7. 여러 db연결을 고려해야됨. 아마 3가지 정도(가변적)의 서로 다른 db와 연결을 할 수 있음. db구조 프롬프트는 연결된 db마다 생성되어야 하고, 한 질문에 하나의 db만 바라봐야됨.

예상 사용 흐름:
1. 사용자가 질문을 작성.
2. db 선택을 위한 llm호출(db선택 프롬프트)(연결 된 db가 하나라면 생략)
3. sql쿼리 생성을 위한 llm호출(sql생성 프롬프트, db구조 프롬프트).
4. 쿼리 실행 (만약 실패했다면 실패 원인을 가지고 다시 llm 호출)
5. 쿼리 실행으로 얻은 결과를 답변 생성을 위한 llm호출(답변 프롬프트).
6. 4번의 결과로 사용자에게 답변 전달
