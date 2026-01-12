import csv

FILE_PATH = "data/ledger.csv"

def load_transactions():
    transactions = []

    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            reader = csv.reader(f)

            # 3) 첫 줄(헤더) 건너뛰기
            next(reader)

            # 4) 각 줄 반복
            for row in reader:
                date = row[0]
                ttype = row[1]
                category = row[2]
                description = row[3]
                amount = int(row[4])

                transaction = {
                    "date": date,
                    "type": ttype,
                    "category": category,
                    "description": description,
                    "amount": amount,
                }

                transactions.append(transaction)

    except FileNotFoundError:
        # 1) 파일 없으면 빈 리스트 반환
        return []

    # 5) 거래 리스트 반환
    return transactions

def save_transactions(transactions):
    with open(FILE_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        # 2) 헤더 작성
        writer.writerow(["date", "type", "category", "description", "amount"])

        # 3) 거래 리스트 반복해서 저장
        for t in transactions:
            writer.writerow([t["date"], t["type"], t["category"], t["description"], t["amount"]])

    # 4) 저장 종료 (with가 자동으로 닫아줌)